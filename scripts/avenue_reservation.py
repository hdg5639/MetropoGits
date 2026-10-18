"""Opt-in, one-leaf avenue clearance pilot; never execute input assets (ADR-019)."""
from __future__ import annotations

import argparse
import copy
import json
import math
from collections import defaultdict
from pathlib import Path

from metropogits.access_routes import AccessGrid, PITCH, _id, _pair, derive_access_routes
from metropogits.layout import _network_walkable_cells, _route_network
from metropogits.road_consolidation import _avenue_spines, consolidate_routes
from scripts.canonical_json import canonical_json_bytes, loads_strict_json
from scripts.parcel_pilot import contains, geometry_checks, pavement_intersections
from scripts.parcel_viewer import LAYOUT, _apply_hint, _bounded_geometry
from scripts.road_consolidation import package
from scripts.road_metrics import road_metrics
from scripts.validate_city import validate_document as validate_city
from scripts.validate_ucg import validate_document as validate_ucg

VERSION = 'avenue-reservation/0.1'
TARGET_WIDTH = 2.5
HALF = TARGET_WIDTH/2 + .12
MAX_CANDIDATES = 64
MAX_MOVED = 8
MAX_MOVEMENT = 7


def overlap(a, b):
    return (min(a['x']+a['width'], b['x']+b['width']) > max(a['x'], b['x'])+1e-8
            and min(a['z']+a['depth'], b['z']+b['depth']) > max(a['z'], b['z'])+1e-8)


def rectangle(a, b, half):
    horizontal = a[1] == b[1]
    return dict(x=min(a[0], b[0])-(0 if horizontal else half),
                z=min(a[1], b[1])-(half if horizontal else 0),
                width=abs(a[0]-b[0])+(0 if horizontal else 2*half),
                depth=abs(a[1]-b[1])+(2*half if horizontal else 0))


def candidates(scene, routing):
    """Existing demand runs clipped inside a single rectangular footprint part."""
    users = defaultdict(set)
    for segment in routing['segments']:
        if segment['access']:
            continue
        a, b = (tuple(round(v/PITCH) for v in segment[k]) for k in ('start', 'end'))
        dx, dz = (b[0] > a[0])-(b[0] < a[0]), (b[1] > a[1])-(b[1] < a[1])
        while a != b:
            other = a[0]+dx, a[1]+dz
            users[(segment['kind'], _pair(a, other))].update(segment['routeIds'])
            a = other
    _, spines = _avenue_spines(users, {r['id']: r for r in routing['routes']})
    parents = {d['parentId'] for d in scene['districts']}
    result, seen = [], set()
    for spine in spines:
        a, b = spine['path']
        axis = 0 if a[1] == b[1] else 1
        along, across = ('x', 'z') if axis == 0 else ('z', 'x')
        length, breadth = ('width', 'depth') if axis == 0 else ('depth', 'width')
        for district in sorted(scene['districts'], key=lambda d: d['id']):
            if district['id'] in parents:
                continue
            for part in district['footprint']:
                if not part[across]+HALF <= a[1-axis] <= part[across]+part[breadth]-HALF:
                    continue
                lo = max(a[axis], math.ceil((part[along]+HALF)/PITCH)*PITCH)
                hi = min(b[axis], math.floor((part[along]+part[length]-HALF)/PITCH)*PITCH)
                if hi-lo < 4*PITCH:
                    continue
                start, end = list(a), list(b)
                start[axis], end[axis] = lo, hi
                key = district['id'], spine['kind'], tuple(start), tuple(end)
                if key in seen:
                    continue
                seen.add(key)
                reserved = rectangle(start, end, HALF)
                reserved[along] -= HALF
                reserved[length] += 2*HALF
                blockers = [b for b in scene['buildings'] if overlap(b, reserved)]
                if not blockers or len(blockers) > MAX_MOVED or any(b['districtId'] != district['id'] for b in blockers):
                    continue
                result.append(dict(districtId=district['id'], kind=spine['kind'], path=[start, end],
                                   width=TARGET_WIDTH, reservation=reserved,
                                   members=sorted(b['entityId'] for b in blockers)))
    result.sort(key=lambda c: (-sum(abs(a-b) for a, b in zip(*c['path'])), len(c['members']),
                               c['districtId'], c['kind'], c['path']))
    return result


def door(building, old, port):
    """Keep the same street port and approach direction; no new bend or shortcut."""
    point = list(old)
    axis = 0 if old[1] == port[1] else 1
    along, across = ('x', 'z') if axis == 0 else ('z', 'x')
    size, breadth = ('width', 'depth') if axis == 0 else ('depth', 'width')
    if not building[across] <= port[1-axis] <= building[across]+building[breadth]:
        raise ValueError('fixed access port misses building frontage')
    point[axis] = building[along] if port[axis] < old[axis] else building[along]+building[size]
    if (point[axis]-port[axis])*(old[axis]-port[axis]) <= 0:
        raise ValueError('movement crosses fixed access port')
    return point


def reconnect(routing, buildings, moved, candidate):
    """Only access endpoints and certified widths change; through paths stay fixed."""
    result = copy.deepcopy(routing)
    old = {s['id']: s for s in routing['segments']}
    boxes = {b['entityId']: b for b in buildings}
    grid = AccessGrid(buildings)
    segments = {}
    for route in result['routes']:
        for identity, endpoint, index in ((route['source'], 0, 0), (route['target'], -1, -1)):
            if identity in moved:
                if not old[route['segmentIds'][index]]['access']:
                    raise ValueError('moved building has no explicit access spur')
                port = route['path'][1 if endpoint == 0 else -2]
                route['path'][endpoint] = door(boxes[identity], route['path'][endpoint], port)
        ids = []
        for i, sid in enumerate(route['segmentIds']):
            source = old[sid]
            a, b = route['path'][i:i+2]
            start, end = sorted((a, b))
            key = _id('access-segment', [route['kind'], start, end])
            if key not in segments:
                width = source['width']
                if not source['access']:
                    certified = round(min(5.5, 2*(grid.clearance(a, b)-.12)), 4)
                    if certified+1e-8 < width:
                        raise ValueError('movement narrows another existing road')
                    # Only widen the selected full segment, never unselected streets.
                    axis = 0 if a[1] == b[1] else 1
                    p, q = candidate['path']
                    if (source['kind'] == candidate['kind'] and a[1-axis] == b[1-axis] == p[1-axis] == q[1-axis]
                            and min(a[axis], b[axis]) >= min(p[axis], q[axis])
                            and max(a[axis], b[axis]) <= max(p[axis], q[axis])):
                        width = max(width, min(TARGET_WIDTH, certified))
                segments[key] = dict(source, id=key, start=start, end=end, width=width, routeIds=[])
            segments[key]['routeIds'].append(route['id'])
            ids.append(key)
        route['segmentIds'] = ids
    result['segments'] = sorted(segments.values(), key=lambda s: s['id'])
    incidence = defaultdict(list)
    for segment in result['segments']:
        segment['routeIds'] = sorted(set(segment['routeIds']))
        for point in (segment['start'], segment['end']):
            incidence[(segment['kind'], *point)].append(segment['id'])
    result['junctions'] = [dict(id=_id('access-junction', [kind, x, z]), kind=kind, point=[x, z], segmentIds=sorted(ids))
                           for (kind, x, z), ids in sorted(incidence.items()) if len(ids) >= 3]
    return result


def place(scene, routing, candidate):
    district = next(d for d in scene['districts'] if d['id'] == candidate['districtId'])
    buildings = copy.deepcopy(scene['buildings'])
    positions = {b['entityId']: b for b in buildings}
    a, b = candidate['path']
    axis = 1 if a[1] == b[1] else 0
    coordinate, size = ('x', 'width') if axis == 0 else ('z', 'depth')
    movements = []
    for identity in candidate['members']:
        building = positions[identity]
        sign = -1 if building[coordinate]+building[size]/2 < a[axis] else 1
        placed = None
        for step in (.875, 1.75, 3.5, MAX_MOVEMENT):
            trial = dict(building)
            trial[coordinate] += sign*step
            if (overlap(trial, candidate['reservation'])
                    or not any(contains(r, trial['x'], trial['z'], trial['width'], trial['depth']) for r in district['footprint'])
                    or any(overlap(trial, other) for other in buildings if other['entityId'] != identity)):
                continue
            # A free parcel cannot consume any existing through-road pavement.
            if any(overlap(trial, rectangle(s['start'], s['end'], s['width']/2+.12))
                   for s in routing['segments'] if not s['access']):
                continue
            placed = trial
            movements.append(dict(entityId=identity, distance=step, before=[building['x'], building['z']], after=[trial['x'], trial['z']]))
            break
        if placed is None:
            raise ValueError('no local parcel preserving ownership and existing roads')
        building.update(placed)
    return buildings, movements


def reserve(scene, routing):
    if scene['layoutAlgorithm'] != LAYOUT or routing['status'] != 'COMPLETE':
        raise ValueError('reservation requires a complete experimental parcel city')
    scene, routing = copy.deepcopy(scene), copy.deepcopy(routing)
    scene['buildings'].sort(key=lambda b: b['entityId'])
    routing['routes'].sort(key=lambda r: (r['kind'], r['source'], r['target']))
    proposals = candidates(scene, routing)
    widths = {s['id']: s['width'] for s in routing['segments']}
    audits = []
    for candidate in proposals[:MAX_CANDIDATES]:
        try:
            buildings, movements = place(scene, routing, candidate)
            checks = geometry_checks(next(d for d in scene['districts'] if d['id'] == candidate['districtId']), buildings, candidate['members'])
            if checks['outsideOwnership'] or checks['overlappingBuildingPairs']:
                raise ValueError('invalid parcel geometry')
            after = reconnect(routing, buildings, set(candidate['members']), candidate)
            if pavement_intersections(after, buildings):
                raise ValueError('access pavement intersects a building')
            # Full run must be clear, not just the individually widened fragments.
            grid = AccessGrid(buildings)
            if grid.clearance(*candidate['path'])+.000001 < HALF:
                raise ValueError('reserved run still lacks full clearance')
            a, b = candidate['path']
            axis = 0 if a[1] == b[1] else 1
            covered = 0
            for segment in after['segments']:
                p, q = segment['start'], segment['end']
                if (not segment['access'] and segment['kind'] == candidate['kind']
                        and p[1-axis] == q[1-axis] == a[1-axis]):
                    length = max(0, min(b[axis], max(p[axis], q[axis]))-max(a[axis], min(p[axis], q[axis])))
                    if length and segment['width']+1e-8 < TARGET_WIDTH:
                        raise ValueError('reserved run crosses a narrow unsplit segment')
                    covered += length
            if abs(covered-(b[axis]-a[axis])) > 1e-8:
                raise ValueError('reservation lacks continuous evidenced road membership')
            gained = sum((s['width']-widths[s['id']])
                         *sum(abs(a-b) for a, b in zip(s['start'], s['end']))
                         for s in after['segments'] if not s['access'])
            if gained <= 0:
                raise ValueError('no certified avenue surface gain')
            chosen = copy.deepcopy(scene)
            chosen['buildings'] = buildings
            decision = dict(version=VERSION, selection='CANDIDATE_SELECTED', candidate=candidate,
                            movements=movements, surfaceAreaGain=round(gained, 4), candidateAudits=audits,
                            candidates=len(proposals), maxCandidates=MAX_CANDIDATES,
                            before=road_metrics(routing), after=road_metrics(after), throughPathsPreserved=True)
            after['avenueReservation'] = dict(version=VERSION, path=candidate['path'], width=TARGET_WIDTH,
                                             districtId=candidate['districtId'])
            return chosen, after, decision
        except ValueError as error:
            audits.append(dict(candidate=candidate, rejectedBecause=str(error)))
    return copy.deepcopy(scene), copy.deepcopy(routing), dict(version=VERSION, selection='BASELINE_RETAINED',
        candidates=len(proposals), maxCandidates=MAX_CANDIDATES, candidateAudits=audits,
        limitReached=len(proposals) > MAX_CANDIDATES, movements=[])


def study(scene, graph, previous=None):
    errors = validate_ucg(graph) + validate_city(scene, graph)
    if errors:
        raise ValueError('; '.join(errors[:8]))
    if scene['layoutAlgorithm'] != LAYOUT:
        raise ValueError('requires existing experimental parcel layout; default layout is not relabeled')
    _bounded_geometry(scene)
    scene = json.loads(canonical_json_bytes(scene))
    baseline = consolidate_routes(derive_access_routes(scene, graph), merge_junctions=True, avenues=True)
    if previous is not None:
        chosen = copy.deepcopy(scene)
        _apply_hint(chosen, previous)
        errors = validate_city(chosen, graph)
        if errors:
            raise ValueError('; '.join(errors[:8]))
        after = consolidate_routes(derive_access_routes(chosen, graph), merge_junctions=True, avenues=True)
        decision = dict(version=VERSION, selection='HINT_APPLIED', hintPolicy='same-structure-only')
    else:
        chosen, after, decision = reserve(scene, baseline)
    # Canonical aggregate anchors must follow the actual moved buildings too.
    if chosen['buildings'] != scene['buildings']:
        buildings = {b['entityId']: b for b in chosen['buildings']}
        edges = {e['id']: e for e in graph['edges']}
        walkable = _network_walkable_cells(chosen['districts'], chosen['buildings'])
        for network in chosen['networks']:
            members = [edges[e] for e in network['edgeIds']]
            network['path'] = _route_network(walkable,
                {e['from']: buildings[e['from']] for e in members},
                {e['to']: buildings[e['to']] for e in members})
    errors = validate_city(chosen, graph)
    expected = {e for n in scene['networks'] for e in n['edgeIds']}
    if errors or after['status'] != 'COMPLETE' or {e for r in after['routes'] for e in r['edgeIds']} != expected:
        raise ValueError('reservation failed scene/edge coverage validation: ' + '; '.join(errors[:8]))
    if pavement_intersections(after, chosen['buildings']):
        raise ValueError('reservation pavement intersects buildings')
    return baseline, chosen, after, decision


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--previous-scene', type=Path)
    args = parser.parse_args()
    try:
        if args.out.exists():
            raise ValueError('output directory must not already exist')
        def read(path):
            if path.stat().st_size > 64*1024*1024:
                raise ValueError('input exceeds 64 MiB')
            return loads_strict_json(path.read_text(encoding='utf-8'))
        scene, graph = read(args.build/'city.json'), read(args.build/'graph.ucg.json')
        previous = json.loads(canonical_json_bytes(read(args.previous_scene))) if args.previous_scene else None
        before, chosen, after, decision = study(scene, graph, previous)
        outputs = {name: package(city, graph, routing, decision)
                   for name, city, routing in [('before', scene, before), ('after', chosen, after)]}
        for artifacts in outputs.values():
            manifest = json.loads(artifacts['manifest.json'])
            manifest['options']['reservationVersion'] = VERSION
            manifest['options']['hintPolicy'] = 'same-structure-only'
            artifacts['manifest.json'] = canonical_json_bytes(manifest)
        args.out.mkdir(parents=True, exist_ok=False)
        for name, artifacts in outputs.items():
            for relative, content in artifacts.items():
                target = args.out/name/relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(content)
        print(json.dumps(dict(selection=decision['selection'], movements=decision.get('movements', []),
                             candidates=decision.get('candidates'), rejected=len(decision.get('candidateAudits', []))), sort_keys=True))
    except (OSError, ValueError) as error:
        parser.exit(2, f'Avenue reservation failed: {error}\n')


if __name__ == '__main__':
    main()
