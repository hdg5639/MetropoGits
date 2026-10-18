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


def center(building):
    return building['x'] + building['width']/2, building['z'] + building['depth']/2


def distance(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


def contains(rect, x, z, width, depth):
    return (rect['x'] <= x and rect['z'] <= z
            and x+width <= rect['x']+rect['width']
            and z+depth <= rect['z']+rect['depth'])


def sites(district, axis, phase):
    """Paired frontage rows; reservations are NOT evidence-backed roads."""
    nx, nz = int(district['width']//CELL), int(district['depth']//CELL)
    if nx*nz > MAX_CELLS:
        return []
    result = []
    for x in range(nx):
        for z in range(nz):
            row = (x, z)[axis]
            # A crossing reservation breaks long frontage strips into blocks
            # of at most 2x5 parcels, rather than another eight-building wall.
            if row % 3 == phase or (x, z)[1-axis] % 6 == 5:
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


def frontage_band(site, district, axis, phase):
    row = round((site[axis] - district[('x', 'z')[axis]] - .5) / CELL)
    column = round((site[1-axis] - district[('x', 'z')[1-axis]] - .5) / CELL)
    return (row-phase-1)//3, column//6


def band_quotas(available, district, axis, phase, count):
    capacity = defaultdict(int)
    for site in available:
        capacity[frontage_band(site, district, axis, phase)] += 1
    # Largest-remainder apportionment prevents relation attraction from leaving
    # an entire street block vacant. Within each quota, relations choose sites.
    total = len(available)
    quotas = {band: count*size//total for band, size in capacity.items()}
    order = sorted(capacity, key=lambda band: (-(count*capacity[band] % total), band))
    for band in order[:count-sum(quotas.values())]:
        quotas[band] += 1
    return quotas


def propose(scene, graph):
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
        return dict(version='parcel-pilot/0.1', status='NOT_APPLICABLE',
                    reason='No connected 8..64-file leaf with sufficient frontage capacity', overrides=[])
    _, _, district, members, options = min(eligible, key=lambda item: item[:2])
    member_set = set(members)
    candidates = []
    for axis, phase, available in options:
        placed = {}
        quotas = band_quotas(available, district, axis, phase, len(members))
        for identity in sorted(members, key=lambda m: (-len(neighbors[m]), m)):
            # Unplaced local neighbors do not pull back toward old geometry.
            targets = [center(placed[n] if n in placed else buildings[n])
                       for n in sorted(neighbors[identity]) if n in placed or n not in member_set]
            old = center(buildings[identity])
            def cost(site):
                point = (site[0]+3, site[1]+3)
                return (sum(distance(point, t) for t in targets), distance(point, old), site)
            x, z = min((s for s in available if quotas[frontage_band(s, district, axis, phase)]), key=cost)
            quotas[frontage_band((x, z), district, axis, phase)] -= 1
            available.remove((x, z))
            placed[identity] = dict(buildings[identity], x=x, z=z)
        pairs = {tuple(sorted((m, n))) for m in members for n in neighbors[m]}
        score = sum(distance(center(placed.get(a, buildings[a])), center(placed.get(b, buildings[b])))
                    for a, b in sorted(pairs))
        movement = sum(distance(center(buildings[m]), center(placed[m])) for m in members)
        candidates.append((score, movement, axis, phase, placed))
    score, _, axis, phase, placed = min(candidates, key=lambda c: c[:4])
    return dict(version='parcel-pilot/0.1', status='EXPERIMENTAL', districtId=district['id'],
                orientation='vertical' if axis == 0 else 'horizontal', phase=phase,
                demandDistance=score,
                overrides=[dict(entityId=m, x=placed[m]['x'], z=placed[m]['z']) for m in members])


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


def experiment(scene, graph):
    # Strict JSON readers use Decimal. Geometry here is derived float data,
    # while the original canonical documents are never serialized back.
    scene = json.loads(canonical_json_bytes(scene))
    proposal = propose(scene, graph)
    if proposal['status'] == 'NOT_APPLICABLE':
        return proposal
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
    candidate = [dict(b, **{k: v for k, v in overrides.get(b['entityId'], {}).items() if k != 'entityId'})
                 for b in baseline]
    expected = sorted({e for n in networks for e in n['edgeIds']})
    variants = {}
    for name, buildings in [('baseline', baseline), ('candidate', candidate)]:
        routing = derive_access_routes(dict(buildings=buildings, networks=networks), graph)
        represented = sorted({e for r in routing['routes'] for e in r['edgeIds']})
        metrics = dict(road_metrics(routing), pavementBuildingIntersections=pavement_intersections(routing, buildings),
                       exactEdgeCoverage=represented == expected)
        variants[name] = dict(buildings=buildings, routing=routing, metrics=metrics)
    movements = [dict(entityId=a['entityId'], distance=distance(center(a), center(b)))
                 for a, b in zip(baseline, candidate) if center(a) != center(b)]
    proposal.update(variants=variants, movements=movements, comparedEdgeIds=expected,
                    district=next(d for d in scene['districts'] if d['id'] == proposal['districtId']),
                    unchangedOutsideDistrict=all(m['entityId'] in overrides for m in movements))
    district = proposal['district']
    inside = [b for b in candidate if b['entityId'] in overrides]
    outside = sum(not any(contains(r, b['x'], b['z'], b['width'], b['depth'])
                          for r in district.get('footprint', [district])) for b in inside)
    overlaps = sum(min(a['x']+a['width'], b['x']+b['width']) > max(a['x'], b['x'])
                   and min(a['z']+a['depth'], b['z']+b['depth']) > max(a['z'], b['z'])
                   for a in inside for b in candidate if a['entityId'] != b['entityId'])
    proposal['geometryChecks'] = dict(outsideOwnership=outside, overlappingBuildingPairs=overlaps,
                                    districtArea=sum(r['width']*r['depth'] for r in district.get('footprint', [district])),
                                    buildingArea=sum(b['width']*b['depth'] for b in inside))
    proposal['safeCandidate'] = (not outside and not overlaps and proposal['unchangedOutsideDistrict']
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
        print(report['status'], args.out)
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
