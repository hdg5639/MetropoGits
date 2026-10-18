"""Opt-in, non-canonical one-district parcel experiment. Never writes City scenes."""
from __future__ import annotations

import argparse
import copy
import html
import json
from collections import defaultdict
from pathlib import Path

from metropogits.access_routes import derive_access_routes
from scripts.canonical_json import canonical_json_bytes, loads_strict_json
from scripts.road_metrics import road_metrics
from scripts.validate_city import validate_document as validate_city_document
from scripts.validate_ucg import validate_document as validate_ucg_document

CELL = 7
MAX_CELLS = 4096
MAX_ROUTED_CANDIDATES = 6


def center(building):
    return building['x'] + building['width']/2, building['z'] + building['depth']/2


def distance(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


def contains(rect, x, z, width, depth):
    return (rect['x'] <= x and rect['z'] <= z
            and x+width <= rect['x']+rect['width']
            and z+depth <= rect['z']+rect['depth'])


def sites(district, axis, phase, block_width=5, crossing=5):
    """Paired frontage rows; reservations are NOT evidence-backed roads."""
    nx, nz = int(district['width']//CELL), int(district['depth']//CELL)
    if nx*nz > MAX_CELLS:
        return []
    result = []
    for x in range(nx):
        for z in range(nz):
            row = (x, z)[axis]
            # A crossing reservation splits frontage strips into bounded blocks.
            if row % 3 == phase or (x, z)[1-axis] % (block_width+1) == crossing:
                continue
            px, pz = district['x'] + x*CELL + .5, district['z'] + z*CELL + .5
            # Require both the parcel and its adjacent street reservation to
            # fit inside the same polygon union, including concave boundaries.
            direction = -1 if (row-1) % 3 == phase else 1
            sx, sz = px + (direction*CELL if axis == 0 else 0), pz + (direction*CELL if axis == 1 else 0)
            footprint = district.get('footprint', [district])
            if all(any(contains(r, a, b, 6, 6) for r in footprint)
                   for a, b in ((px, pz), (sx, sz))):
                result.append((px, pz))
    return result


def frontage_band(site, district, axis, phase, block_width=5, crossing=5):
    row = round((site[axis] - district[('x', 'z')[axis]] - .5) / CELL)
    column = round((site[1-axis] - district[('x', 'z')[1-axis]] - .5) / CELL)
    return (row-phase-1)//3, (column-crossing-1)//(block_width+1)


def band_quotas(available, district, axis, phase, count, block_width=5, crossing=5):
    capacity = defaultdict(int)
    for site in available:
        capacity[frontage_band(site, district, axis, phase, block_width, crossing)] += 1
    # Largest-remainder apportionment prevents relation attraction from leaving
    # an entire street block vacant. Within each quota, relations choose sites.
    total = len(available)
    quotas = {band: count*size//total for band, size in capacity.items()}
    order = sorted(capacity, key=lambda band: (-(count*capacity[band] % total), band))
    for band in order[:count-sum(quotas.values())]:
        quotas[band] += 1
    return quotas


def empty_rectangle(district, buildings):
    """Largest building-free 7-unit cell rectangle; includes street reservations."""
    nx, nz = int(district['width']//CELL), int(district['depth']//CELL)
    if nx*nz > MAX_CELLS:
        raise ValueError('pilot district exceeds cell budget')
    heights, largest = [0]*nx, 0
    for row in range(nz):
        for col in range(nx):
            x, z = district['x']+col*CELL, district['z']+row*CELL
            inside = any(contains(r, x, z, CELL, CELL) for r in district.get('footprint', [district]))
            occupied = any(b['x'] < x+CELL and b['x']+b['width'] > x
                           and b['z'] < z+CELL and b['z']+b['depth'] > z for b in buildings)
            heights[col] = heights[col]+1 if inside and not occupied else 0
        stack = []
        for col, height in enumerate([*heights, 0]):
            start = col
            while stack and stack[-1][1] > height:
                index, previous = stack.pop()
                largest = max(largest, (col-index)*previous)
                start = index
            if not stack or stack[-1][1] < height:
                stack.append((start, height))
    return largest*CELL*CELL


def propose(scene, graph, alternatives=False):
    """Select one bounded leaf, return explicit overrides or a safe fallback."""
    scene = json.loads(canonical_json_bytes(scene))
    buildings = {b['entityId']: b for b in scene['buildings']}
    owners = defaultdict(list)
    for building in buildings.values():
        owners[building['districtId']].append(building['entityId'])
    nonleaves = {d['parentId'] for d in scene['districts']}
    network_edges = {e for n in scene['networks'] for e in n['edgeIds']}
    neighbors = defaultdict(set)
    for edge in graph['edges']:
        a, b = edge['from'], edge['to']
        if edge['id'] in network_edges and a != b and a in buildings and b in buildings:
            neighbors[a].add(b)
            neighbors[b].add(a)
    eligible = []
    for district in scene['districts']:
        members = sorted(owners[district['id']])
        if district['id'] in nonleaves or not 8 <= len(members) <= 64:
            continue
        # This experimental grid supports current 6x6 parcels only.
        if any((buildings[m]['width'], buildings[m]['depth']) != (6, 6) for m in members):
            continue
        pairs = {tuple(sorted((m, n))) for m in members for n in neighbors[m]}
        options = [(axis, phase, sites(district, axis, phase))
                   for axis in (0, 1) for phase in range(3)]
        options = [o for o in options if len(o[2]) >= len(members)]
        if pairs and options:
            eligible.append((-len(pairs), district['id'], district, members, options))
    if not eligible:
        return dict(version='parcel-pilot/0.2', status='NOT_APPLICABLE',
                    reason='No connected 8..64-file leaf with sufficient frontage capacity', overrides=[])
    _, _, district, members, options = min(eligible, key=lambda item: item[:2])
    member_set = set(members)
    options = [(axis, phase, width, crossing, sites(district, axis, phase, width, crossing))
               for axis in (0, 1) for phase in range(3) for width in (3, 4, 5, 7)
               for crossing in sorted({0, width//2, width})]
    options = [o for o in options if len(o[-1]) >= len(members)]
    candidates = []
    for axis, phase, width, crossing, available in options:
        placed = {}
        quotas = band_quotas(available, district, axis, phase, len(members), width, crossing)
        def band(site):
            return frontage_band(site, district, axis, phase, width, crossing)
        for identity in sorted(members, key=lambda m: (-len(neighbors[m]), m)):
            # Unplaced local neighbors do not pull back toward old geometry.
            targets = [center(placed[n] if n in placed else buildings[n])
                       for n in sorted(neighbors[identity]) if n in placed or n not in member_set]
            old = center(buildings[identity])
            def cost(site):
                point = (site[0]+3, site[1]+3)
                return (sum(distance(point, t) for t in targets), distance(point, old), site)
            x, z = min((s for s in available if quotas[band(s)]), key=cost)
            quotas[band((x, z))] -= 1
            available.remove((x, z))
            placed[identity] = dict(buildings[identity], x=x, z=z)
        pairs = {tuple(sorted((m, n))) for m in members for n in neighbors[m]}
        score = sum(distance(center(placed.get(a, buildings[a])), center(placed.get(b, buildings[b])))
                    for a, b in sorted(pairs))
        movement = sum(distance(center(buildings[m]), center(placed[m])) for m in members)
        candidates.append(dict(version='parcel-pilot/0.2', status='EXPERIMENTAL', districtId=district['id'],
                               orientation='vertical' if axis == 0 else 'horizontal', phase=phase,
                               blockWidth=width, crossing=crossing, demandDistance=score, movement=movement,
                               emptyRectangleArea=empty_rectangle(district, list(placed.values())),
                               overrides=[dict(entityId=m, x=placed[m]['x'], z=placed[m]['z']) for m in members]))
    candidates.sort(key=lambda c: (c['emptyRectangleArea'], c['demandDistance'], c['movement'],
                                   c['orientation'], c['phase'], c['blockWidth'], c['crossing']))
    # Route distinct layouts, not six copies of the same placement.
    distinct, seen = [], set()
    for candidate in candidates:
        identity = canonical_json_bytes(candidate['overrides'])
        if identity not in seen:
            distinct.append(candidate)
            seen.add(identity)
    return distinct[:MAX_ROUTED_CANDIDATES] if alternatives else distinct[0]


def pavement_intersections(routing, buildings):
    """Count positive-area pavement/building overlaps (boundary contact is OK)."""
    count = 0
    for segment in routing['segments']:
        a, b, half = segment['start'], segment['end'], segment['width']/2
        horizontal = a[1] == b[1]
        x0, x1 = min(a[0], b[0])-(0 if horizontal else half), max(a[0], b[0])+(0 if horizontal else half)
        z0, z1 = min(a[1], b[1])-(half if horizontal else 0), max(a[1], b[1])+(half if horizontal else 0)
        for building in buildings:
            if (min(x1, building['x']+building['width'])-max(x0, building['x']) > 1e-7
                    and min(z1, building['z']+building['depth'])-max(z0, building['z']) > 1e-7):
                count += 1
    return count


GUARDED_METRICS = ('routeLength', 'turns', 'pavementCenterlineLength',
                   'nearbyParallelPairLength', 'emptyRectangleArea')


def rejection_reasons(metrics, baseline):
    reasons = [key + ' regressed' for key in GUARDED_METRICS if metrics[key] > baseline[key]]
    for key in ('pavementBuildingIntersections', 'outsideOwnership', 'overlappingBuildingPairs'):
        if metrics[key]:
            reasons.append(key)
    if not metrics['exactEdgeCoverage']:
        reasons.append('incomplete edge coverage')
    return reasons


def geometry_checks(district, buildings, members):
    inside = [b for b in buildings if b['entityId'] in members]
    outside = sum(not any(contains(r, b['x'], b['z'], b['width'], b['depth'])
                          for r in district.get('footprint', [district])) for b in inside)
    overlaps = {tuple(sorted((a['entityId'], b['entityId'])))
                for a in inside for b in buildings if a['entityId'] != b['entityId']
                and min(a['x']+a['width'], b['x']+b['width']) > max(a['x'], b['x'])
                and min(a['z']+a['depth'], b['z']+b['depth']) > max(a['z'], b['z'])}
    return dict(outsideOwnership=outside, overlappingBuildingPairs=len(overlaps),
                districtArea=sum(r['width']*r['depth'] for r in district.get('footprint', [district])),
                buildingArea=sum(b['width']*b['depth'] for b in inside))


def experiment(scene, graph):
    # Strict JSON readers use Decimal. Geometry here is derived float data,
    # while the original canonical documents are never serialized back.
    scene = json.loads(canonical_json_bytes(scene))
    proposals = propose(scene, graph, alternatives=True)
    if isinstance(proposals, dict):
        return proposals
    proposal = proposals[0]
    district = next(d for d in scene['districts'] if d['id'] == proposal['districtId'])
    overrides = {b['entityId']: b for b in proposal['overrides']}
    # Only routes incident to the chosen district are compared. ALL buildings
    # remain obstacles, including unchanged neighboring districts.
    edges = {e['id']: e for e in graph['edges']}
    networks = []
    for network in sorted(scene['networks'], key=lambda n: n['id']):
        selected = sorted(e for e in network['edgeIds']
                          if edges[e]['from'] in overrides or edges[e]['to'] in overrides)
        if selected:
            networks.append(dict(network, edgeIds=selected))
    baseline = sorted(copy.deepcopy(scene['buildings']), key=lambda b: b['entityId'])
    expected = sorted({e for n in networks for e in n['edgeIds']})

    def evaluate(buildings):
        routing = derive_access_routes(dict(buildings=buildings, networks=networks), graph)
        represented = sorted({e for r in routing['routes'] for e in r['edgeIds']})
        metrics = dict(road_metrics(routing), pavementBuildingIntersections=pavement_intersections(routing, buildings),
                       exactEdgeCoverage=represented == expected,
                       emptyRectangleArea=empty_rectangle(district, [b for b in buildings if b['entityId'] in overrides]),
                       **geometry_checks(district, buildings, overrides))
        return dict(buildings=buildings, routing=routing, metrics=metrics)

    original = evaluate(baseline)
    audits, acceptable = [], []
    for index, proposed in enumerate(proposals):
        changes = {b['entityId']: b for b in proposed['overrides']}
        buildings = [dict(b, x=changes[b['entityId']]['x'], z=changes[b['entityId']]['z'])
                     if b['entityId'] in changes else b for b in baseline]
        variant = evaluate(buildings)
        metrics = variant['metrics']
        reasons = rejection_reasons(metrics, original['metrics'])
        if not any(metrics[k] < original['metrics'][k] for k in GUARDED_METRICS):
            reasons.append('no measured improvement')
        audits.append(dict(index=index, blockWidth=proposed['blockWidth'], crossing=proposed['crossing'],
                           orientation=proposed['orientation'], phase=proposed['phase'], metrics=metrics, rejectedBecause=reasons))
        if not reasons:
            score = (metrics['emptyRectangleArea'], metrics['nearbyParallelPairLength'], metrics['routeLength'],
                     metrics['turns'], proposed['movement'], index)
            acceptable.append((score, index, proposed, variant))
    if acceptable:
        _, selected, proposal, chosen = min(acceptable, key=lambda item: item[0])
        proposal = dict(proposal, selection='CANDIDATE_SELECTED')
    else:
        selected, chosen = None, original
        proposal = dict(version='parcel-pilot/0.2', status='EXPERIMENTAL', selection='BASELINE_RETAINED',
                        districtId=district['id'], overrides=[])
    variants = dict(baseline=original, candidate=chosen)
    candidate = chosen['buildings']
    movements = [dict(entityId=a['entityId'], distance=distance(center(a), center(b)))
                 for a, b in zip(baseline, candidate) if center(a) != center(b)]
    proposal.update(variants=variants, movements=movements, comparedEdgeIds=expected,
                    district=district, selectedCandidate=selected, candidateAudits=audits,
                    routingCandidateLimit=MAX_ROUTED_CANDIDATES,
                    unchangedOutsideDistrict=all(m['entityId'] in overrides for m in movements))
    proposal['geometryChecks'] = geometry_checks(district, candidate, overrides)
    proposal['safeCandidate'] = (not proposal['geometryChecks']['outsideOwnership']
                                and not proposal['geometryChecks']['overlappingBuildingPairs'] and proposal['unchangedOutsideDistrict']
                                and all(v['metrics']['exactEdgeCoverage'] and not v['metrics']['pavementBuildingIntersections']
                                        for v in variants.values()))
    # Safety is NOT visual acceptance; no automatic promotion to canonical City.
    return proposal


def render_report(report):
    def esc(value):
        return html.escape(str(value), quote=True)
    head = ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Parcel layout experiment</title><style>'
            'body{background:#0c1420;color:#d4e3f0;font:16px system-ui;margin:24px;overflow-wrap:anywhere}'
            '.panels{display:flex;gap:20px}.panel{width:50%;min-width:0}svg{width:100%;background:#101f30}'
            'td,th{text-align:left;padding:7px 18px;border-bottom:1px solid #31445a}'
            '.warning{color:#fbbf24}summary{cursor:pointer}a{color:#67dfff}'
            '@media(max-width:800px){.panels{display:block}.panel{width:100%}}'
            '</style><h1>Street-front parcels — one-district experiment</h1>'
            '<p class="warning">Experimental 2D geometry comparison, NOT the default city or a WebGL approval.</p>')
    if report['status'] == 'NOT_APPLICABLE':
        return head + '<p>' + esc(report['reason']) + '</p></html>'
    district = report['district']
    bounds = (district['x']-14, district['z']-14, district['width']+28, district['depth']+28)
    output = [head, '<p>' + esc(district['id']) + '</p>',
              '<p>Decision: ' + esc(report.get('selection', 'EXPERIMENTAL')) +
              '. Building-free rectangle area includes street space, not just vacant land.</p>',
              '<p>Safety checks: ' + ('PASS' if report['safeCandidate'] else 'FAIL — do not apply') + '. '
              'Footprint area: ' + str(report['geometryChecks']['districtArea']) + '; building coverage: '
              + str(round(100*report['geometryChecks']['buildingArea']/report['geometryChecks']['districtArea'], 1)) + '% (unchanged).</p>',
              '<p>Identical scale and crop. Colored rectangles = source files; gray = unchanged neighbors. '
              'Roads = actual incident relationships; unpaved gaps are reservations, not connections. '
              'Hover buildings/roads for file IDs and original edge IDs. External paths continue beyond the crop.</p>',
              '<div class="panels">']
    colors = dict(GATE='#f472b6', TEST_FACILITY='#facc15', SERVICE_OFFICE='#60a5fa', STRUCTURED_WAREHOUSE='#34d399')
    for name, variant in report['variants'].items():
        output.append('<section class="panel"><h2>' + name.title() + '</h2><svg role="img" aria-label="' + name
                      + ' parcel geometry" viewBox="' + ' '.join(map(str, bounds)) + '">')
        for rect in district.get('footprint', [district]):
            output.append(f'<rect x="{rect["x"]}" y="{rect["z"]}" width="{rect["width"]}" height="{rect["depth"]}" fill="#182e42" stroke="#5792ad" stroke-width=".25"/>')
        routes = {r['id']: r for r in variant['routing']['routes']}
        for segment in variant['routing']['segments']:
            a, b = segment['start'], segment['end']
            # A shared surface has one stroke, no repeated border/centerline.
            detail = '\n'.join(r['source'] + ' -> ' + r['target'] + '\n' + ', '.join(r['edgeIds'])
                               for r in (routes[rid] for rid in segment['routeIds']))
            output.append(f'<path d="M {a[0]} {a[1]} L {b[0]} {b[1]}" stroke="#718797" stroke-width="{segment["width"]}" fill="none"><title>{esc(detail)}</title></path>')
        for building in variant['buildings']:
            if not (building['x']+building['width'] >= bounds[0] and building['x'] <= bounds[0]+bounds[2]
                    and building['z']+building['depth'] >= bounds[1] and building['z'] <= bounds[1]+bounds[3]):
                continue
            color = colors.get(building['archetype'], '#b0c2d4') if building['districtId'] == district['id'] else '#3d4857'
            output.append(f'<rect x="{building["x"]}" y="{building["z"]}" width="{building["width"]}" height="{building["depth"]}" fill="{color}" stroke="#0c1420" stroke-width=".4"><title>{esc(building["entityId"])}</title></rect>')
        output.append('</svg></section>')
    output.append('</div><h2>Incident-route metrics (not whole-city totals)</h2><table><tr><th>Metric</th><th>Baseline</th><th>Candidate</th></tr>')
    for key, value in report['variants']['baseline']['metrics'].items():
        output.append(f'<tr><td>{esc(key)}</td><td>{esc(value)}</td><td>{esc(report["variants"]["candidate"]["metrics"][key])}</td></tr>')
    output.append('</table><p>Buildings moved: ' + str(len(report['movements'])) + '; outside selected district: 0. '
                  'District area and building area unchanged. The cold-layout pilot has no scene-hint stability guarantee.</p>'
                  '<details><summary>Original file movement (Manhattan world units)</summary><ul>')
    for movement in report['movements']:
        output.append('<li>' + esc(movement['entityId']) + ': ' + str(movement['distance']) + '</li>')
    output.append('</ul></details><p><a href="report.json">Full derived report and provenance</a></p></html>')
    if report.get('candidateAudits'):
        output[-1] = '</ul></details><h2>Candidate decisions (bounded search, not a global optimum)</h2><ul>'
        for audit in report['candidateAudits']:
            result = '; '.join(audit['rejectedBecause']) or ('SELECTED' if audit['index'] == report['selectedCandidate'] else 'Passed; lower ranked')
            output.append('<li>' + esc(f"#{audit['index']} / width {audit['blockWidth']} / {audit['orientation']} / {result}") + '</li>')
        output.append('</ul><p><a href="report.json">Full derived report and provenance</a></p></html>')
    return ''.join(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    try:
        # Never overwrite an existing artifact or use a report as a City hint.
        if args.out.exists():
            raise ValueError('output directory must not already exist')
        def load(name):
            path = args.build / name
            if path.stat().st_size > 64 * 1024 * 1024:
                raise ValueError('pilot input exceeds 64 MiB')
            return loads_strict_json(path.read_text(encoding='utf-8'))
        graph, scene = load('graph.ucg.json'), load('city.json')
        errors = validate_ucg_document(graph) + validate_city_document(scene, graph)
        if errors:
            raise ValueError('; '.join(errors[:8]))
        report = experiment(scene, graph)
        args.out.mkdir(parents=True, exist_ok=False)
        (args.out / 'report.json').write_bytes(canonical_json_bytes(report))
        (args.out / 'index.html').write_text(render_report(report), encoding='utf-8')
        print(report['status'], report.get('selection', ''), args.out)
        if report['status'] == 'EXPERIMENTAL':
            print(report['districtId'])
            for name, variant in report['variants'].items():
                print(name, variant['metrics'])
            return 0 if report['safeCandidate'] else 2
        return 0
    except (OSError, ValueError) as error:
        parser.exit(2, f'Parcel pilot failed: {error}\n')


if __name__ == '__main__':
    raise SystemExit(main())
