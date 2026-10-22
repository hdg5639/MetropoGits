"""Demand-first physical programs and variable frontage parcels.

Source City dimensions are historical glyphs, not physical parcel limits. This
module never changes source identity, roles or relationships. The program and
its physical admission are versioned, deterministic visual derivations.
"""

import math
from collections import Counter
from functools import lru_cache

from .geometry import area, inside, point, q, rectangle, ribbon
from .planning import groups
from .seed import derive
from .urban_character import CharacterEngine, verified_claims
from .urban_land import ClearanceIndex

VERSION = 'capacity-replan/0.1'
MAX_PROPOSALS = 1_500_000


@lru_cache(maxsize=64)
def junction_exclusions(geometry):
    from .infrastructure import atomic_streets
    from metropogits.street_diagonals import hull
    from collections import defaultdict
    streets = atomic_streets([dict(start=list(a), end=list(b), width=width, access=False)
                             for a, b, width in geometry])
    tips = defaultdict(list)
    for r in streets:
        for at, other in ((r['start'], r['end']), (r['end'], r['start'])):
            length = math.dist(at, other)
            normal = [-(other[1] - at[1]) / length, (other[0] - at[0]) / length]
            tips[tuple(at)].extend(point([at[i] + side * normal[i] * (r['width'] / 2 + .1) for i in (0, 1)]) for side in (-1, 1))
    return [hull(points) for _, points in sorted(tips.items()) if len(points) >= 4 and len(hull(points)) >= 3]


def architectural_programs(scene, graph):
    engine = CharacterEngine(graph)
    grouped, _ = groups(scene)
    result = {}
    for district, members in grouped.items():
        demand = engine.profile(district, [b['entityId'] for b in members], kind='district')['spatialDemand']
        for b in members:
            identity = b['entityId']
            roles = verified_claims(engine.files[identity], 'roles', engine.evidence)
            values = {r['value'] for r in roles}
            variant = int(derive(identity, VERSION, 'land-program'), 16) % 4
            if values & {'PERSISTENCE_ADAPTER', 'OBJECT_STORAGE_ADAPTER', 'DATA_PROCESSOR', 'ML_COMPONENT'}:
                family = 'HORIZONTAL_WORKS'
                dimensions = ((20, 12), (24, 14), (30, 16), (36, 18))
            elif values & {'SERVICE', 'ENTRYPOINT', 'API_ENDPOINT'}:
                family = 'OFFICE_DEVELOPMENT'
                dimensions = ((12, 10), (16, 12), (20, 14), (24, 16))
            elif values & {'TEST'}:
                family = 'RESEARCH_SUPPORT'
                dimensions = ((10, 8), (12, 10), (16, 10), (18, 12))
            elif values & {'CONFIGURATION', 'GENERAL_COMPONENT', 'DATA_MODEL'}:
                family = 'SUPPORT_BUILDING'
                dimensions = ((6, 6), (8, 6), (10, 8), (12, 8))
            else:
                family = 'NEUTRAL_MIXED_BUILDING'
                dimensions = ((8, 8), (10, 8), (12, 10), (14, 10))
            width, depth = dimensions[variant]
            width, depth = max(width, b['width']), max(depth, b['depth'])
            result[identity] = dict(
                family=family, width=width, depth=depth, area=q(width * depth),
                parcelWidth=width + 2, parcelDepth=depth + 2,
                evidenceIds=sorted({k for r in roles for k in r['evidenceIds']}),
                sourceEnvelope={k: b[k] for k in ('width', 'depth', 'height')},
                districtId=district, districtDemand=demand['perSourceUnits'],
                derived=True, basis='SOURCE_PROGRAM_NOT_PER_FILE_POPULARITY')
    return dict(sorted(result.items()))


def scale_planning(value, scale):
    """Scale planning geography, never road widths or source metadata."""
    if isinstance(value, tuple):
        return tuple(scale_planning(v, scale) for v in value)
    if isinstance(value, list):
        return [scale_planning(v, scale) for v in value]
    if not isinstance(value, dict):
        return value
    result = dict(value)
    for key in ('start', 'end', 'center', 'entrance', 'streetPoint', 'anchor', 'labelAnchor', 'hub'):
        if key in result:
            result[key] = point([x * scale for x in result[key]])
    for key in ('polygon', 'envelope'):
        if key in result:
            result[key] = [point([x * scale for x in p]) for p in result[key]]
    handled = {'start', 'end', 'center', 'entrance', 'streetPoint', 'anchor', 'labelAnchor', 'hub', 'polygon', 'envelope'}
    for key, child in value.items():
        if key not in handled and isinstance(child, (dict, tuple, list)):
            if key == 'envelopes':
                result[key] = [[point([x * scale for x in p]) for p in poly] for poly in child]
            else:
                result[key] = scale_planning(child, scale)
    if 'start' not in value:
        for key in ('width', 'depth'):
            if key in result:
                result[key] *= scale
    if 'areaAllocated' in result:
        result['areaAllocated'] *= scale * scale
    return result


def planning_scale(members):
    # Roads are planned for the actual site depths BEFORE their frontage is
    # subdivided. This is a street-spacing rule, not a uniform parcel size.
    return max(2, (max(b['depth'] for b in members) + 6) / 8)


def program_field(polygon, seed, base, parent, scale):
    from .adaptive import adaptive_field
    small = [point([x / scale for x in p]) for p in polygon]
    candidates, roads, main, pattern = adaptive_field(small, seed, base, parent, stitch=True, morphology=True)
    candidates, roads, main, pattern = scale_planning((candidates, roads, main, pattern), scale)
    if base == 'HYBRID':
        from .hybrid import hybrid_regions
        pattern['regions'] = hybrid_regions(polygon, seed)
    pattern.update(capacityVersion=VERSION, programStreetScale=scale)
    return candidates, roads, main, pattern


def program_local_sites(polygon, seed, selection, parent_candidates, parent_roads, backbone, scale):
    from .adaptive import local_sites
    if selection['mode'] == 'INHERITED':
        plan = local_sites(polygon, seed, selection, parent_candidates, parent_roads, backbone)
    else:
        small = [point([x / scale for x in p]) for p in polygon]
        plan = scale_planning(local_sites(small, seed, selection, [], [], scale_planning(backbone, 1 / scale)), scale)
        if selection['profile'] == 'HYBRID':
            from .hybrid import hybrid_regions
            plan = (*plan[:3], hybrid_regions(polygon, seed))
    if not plan[1]:
        # A tiny sector may fall between two arterial rows. Reserve one actual
        # access street before lots, rather than enlarging the whole city merely
        # to make a periodic stencil hit this polygon.
        from .geometry import centroid, nearest
        from .radial import _clipped
        center = centroid(polygon)
        axis = selection['axis']
        delta = [math.cos(axis) * 10000, math.sin(axis) * 10000]
        segment = _clipped([center[i] - delta[i] for i in (0, 1)],
                           [center[i] + delta[i] for i in (0, 1)], polygon)
        if segment and math.dist(*segment) > 8:
            lane = dict(id='program-access:' + seed, start=point(segment[0]), end=point(segment[1]), width=3, access=False)
            plan = ([], [lane], axis, None)
    return plan


def fit_programs(members, polygon, plan, external_roads, terrain, seed, *, courts=(), preferences=None):
    """Subdivide real street frontage into independently sized physical lots.

    Large programs reserve complete sites first. Street directions follow the
    selected district/neighborhood grammar, but lot widths/depths are not fixed
    grid cells. Failure returns an incomplete *internal* proposal and triggers
    parent capacity repair; it can never be exported as successful placement.
    """
    _, lanes, axis, regions = plan
    index = ClearanceIndex()
    roads = sorted(lanes + external_roads, key=lambda r: (str(r.get('id', '')), r['start'], r['end']))
    for number, r in enumerate(roads):
        index.add(('road', str(number)), ribbon(r['start'], r['end'], r['width'] + .1))
    geometry = tuple(sorted({(tuple(r['start']), tuple(r['end']), r['width']) for r in roads}))
    for number, polygon_ in enumerate(junction_exclusions(geometry)):
        index.add(('junction', str(number)), polygon_)
    for f in (terrain or {}).get('features', []):
        index.add(('terrain', f['id']), f['noBuildPolygon'])
    for court in courts:
        index.add(('court', court['id']), court['polygon'])
    field = None
    if terrain and 'elevation' in terrain:
        from .elevation import surface
        field = surface(terrain)
    choices, work = [], 0
    cursors = {}
    occupied = ClearanceIndex()
    rejected_static, accepted_static = set(), set()
    # Keep each source's road-family preference stable rather than ranking
    # sources by their incoming references.
    lane_order = sorted(lanes, key=lambda r: (-math.dist(r['start'], r['end']), str(r.get('id', ''))))
    from .radial import _clipped
    lane_order += [dict(r, start=p[0], end=p[1]) for r in external_roads
                   if (p := _clipped(r['start'], r['end'], polygon)) and math.dist(*p) > 4]
    for b in sorted(members, key=lambda b: (-b['width'] * b['depth'], derive(seed, b['entityId']))):
        width, depth = b['width'], b['depth']
        fitted = None
        preferred = (preferences or {}).get(b['entityId'])
        from .geometry import nearest
        ordered = sorted(lane_order, key=lambda r: (math.dist(preferred, nearest(preferred, r['start'], r['end'])),
                                                    str(r.get('id', '')))) if preferred else lane_order
        for lane in ordered:
            a, end = lane['start'], lane['end']
            length = math.dist(a, end)
            if length < .5:
                continue
            u = [(end[i] - a[i]) / length for i in (0, 1)]
            # Every two units, not fixed 8-unit addresses. Width is reserved
            # atomically, so neighboring sources cannot steal a compound's land.
            lane_key = (tuple(a), tuple(end))
            first = min(cursors.get((lane_key, side), 0) for side in (-1, 1))
            stations = ([length / 2] if length < width + 4 else
                        [width / 2 + 2 + station * 2 for station in
                         range(max(0, math.ceil((first - 2) / 2)), math.floor((length - width - 4) / 2) + 1)])
            for along in stations:
                at = point([a[i] + along * u[i] for i in (0, 1)])
                for side in (-1, 1):
                    if (lane_key, side) in cursors and along - width / 2 < cursors[lane_key, side]:
                        continue
                    candidate_key = (width, depth, lane_key, along, side)
                    if candidate_key in rejected_static:
                        continue
                    work += 1
                    if work > MAX_PROPOSALS:
                        raise ValueError('capacity frontage proposal limit')
                    normal = [-u[1] * side, u[0] * side]
                    setback = max(1.8, lane['width'] / 2 + 1.3)
                    center = point([at[i] + normal[i] * (depth / 2 + setback) for i in (0, 1)])
                    angle = math.atan2(normal[0], -normal[1])
                    parcel = rectangle(center, angle, width + 2, depth + 2)
                    if candidate_key not in accepted_static and (
                        not all(inside(v, polygon, 2.5) for v in parcel) or not index.clear(parcel, set())):
                        rejected_static.add(candidate_key)
                        continue
                    region = next((r for r in regions or [] if all(inside(v, r['polygon']) for v in parcel)), None)
                    if regions and region is None:
                        rejected_static.add(candidate_key)
                        continue
                    entrance = point([center[i] - normal[i] * depth / 2 for i in (0, 1)])
                    approach = ribbon(entrance, at, .9)
                    # Check the access against land/terrain, not the target road
                    # that it intentionally joins.
                    obstacles = {k for c in index.cells_for(approach) for k in index.cells[c] if k[0] not in ('road', 'junction')}
                    from metropogits.street_diagonals import overlap
                    if any(overlap(approach, index.shapes[k]) for k in obstacles):
                        rejected_static.add(candidate_key)
                        continue
                    if field and candidate_key not in accepted_static:
                        from .elevation import MAX_LOT_RELIEF, MAX_ACCESS_GRADE
                        low, high = field.range(parcel)
                        if high - low > MAX_LOT_RELIEF or abs(high + .04 - field.height(at)) / setback > MAX_ACCESS_GRADE - .001:
                            rejected_static.add(candidate_key)
                            continue
                    accepted_static.add(candidate_key)
                    if not occupied.clear(parcel, set()) or not occupied.clear(approach, set()):
                        continue
                    fitted = dict(id='program:' + derive(seed, b['entityId']), entityId=b['entityId'],
                                  center=center, angle=angle, polygon=parcel, entrance=entrance,
                                  streetPoint=at, laneId=lane.get('id', 'program-road'))
                    if 'blockProfile' in b:
                        fitted['blockProfile'] = b['blockProfile']
                    if region:
                        fitted.update(blockProfile=region['planningProfile'], planningRegionId=region['id'])
                    occupied.add(('parcel', b['entityId']), parcel)
                    occupied.add(('approach', b['entityId']), approach)
                    cursors[lane_key, side] = along + width / 2 + 2.1
                    break
                if fitted:
                    break
            if fitted:
                break
        if fitted:
            choices.append(fitted)
    return sorted(choices, key=lambda s: s['id']), lanes, axis, regions


def program_regions(plan, selection, pattern, polygon):
    if selection['profile'] != 'HYBRID':
        return plan
    from metropogits.block_orientation import clip
    regions = plan[3] or [dict(r, polygon=[point(p) for p in part], areaAllocated=area(part))
                          for r in pattern.get('regions', [])
                          if len(part := clip(r['polygon'], polygon)) >= 3 and area(part) > .001]
    if len(regions) == 2 and (abs(sum(area(r['polygon']) for r in regions) - area(polygon)) > .025
                              or any(not inside(v, polygon) for r in regions for v in r['polygon'])):
        # Quantizing two independently clipped outer edges can leave a thin
        # unowned strip at large scale. Split at EXISTING boundary vertices:
        # both cells then share one exact diagonal and conserve the full block,
        # without weakening containment/area tolerances or changing source IDs.
        from .geometry import centroid
        target, center = area(regions[0]['polygon']), centroid(regions[0]['polygon'])
        proposals = []
        if len(polygon) > 128:
            raise ValueError('capacity hybrid cut work limit')
        for i in range(len(polygon)):
            for j in range(i + 2, len(polygon)):
                a, b = polygon[i:j + 1], polygon[j:] + polygon[:i + 1]
                if len(a) < 3 or len(b) < 3 or min(area(a), area(b)) < 1:
                    continue
                for first, second in ((a, b), (b, a)):
                    score = abs(area(first) - target) / area(polygon) + .1 * math.dist(centroid(first), center) / math.sqrt(area(polygon))
                    proposals.append((score, i, j, first, second))
        if proposals:
            _, _, _, first, second = min(proposals)
            regions = [dict(r, polygon=poly, areaAllocated=area(poly), capacityCut='EXACT_EXISTING_VERTEX_DIAGONAL')
                       for r, poly in zip(regions, (first, second))]
    return (*plan[:3], regions or None)


def capacity_campuses(plans, selections, zones, polygons, seed, roads, terrain, pairs, style, grouping_pairs, reserved_zone):
    """Whole source-backed physical sites, not the old fixed glyph subplots."""
    if style != 'precinct':
        raise ValueError('physical campus requires precinct planning')
    return program_precinct(plans, selections, zones, polygons, seed, roads, terrain,
                            grouping_pairs or pairs, reserved_zone)


def program_precinct(plans, selections, zones, polygons, seed, roads, terrain, pairs, reserved_zone):
    """A whole, variable-lot pedestrian campus, without glyph-sized subplots."""
    from .campus import eligibility
    from .campus_programmed import ProgrammedFabric, annotate_program
    from .geometry import centroid, nearest
    from .terrain import outside
    from metropogits.street_diagonals import overlap

    decisions = {z['id']: eligibility(z, pairs, seed) for z in zones}
    sites = {}
    for zone in zones:
        key = zone['id']
        decision = decisions[key]
        if not decision['eligible'] or decision['draw'] >= decision['probability']:
            continue
        if key != reserved_zone:
            decision['reason'] = 'NO_SAFE_PRECINCT_RESERVATION' if reserved_zone is None else 'RESERVED_OTHER_NEIGHBORHOOD'
            continue
        poly, axis = polygons[key], selections[key]['axis']
        form = ProgrammedFabric(zone, poly, axis, seed, roads)
        center = centroid(poly)
        obstacles = [f['noBuildPolygon'] for f in (terrain or {}).get('features', [])]
        obstacles += [ribbon(r['start'], r['end'], r['width'] + .4) for r in roads]
        selected = None
        # The commons is planned before lots and can occupy an old local road:
        # that road is cut/rejoined at its loop, never drawn through the court.
        candidates = [center] + [point([center[i] * .65 + corner[i] * .35 for i in (0, 1)]) for corner in poly]
        for at in candidates:
            lawn, loop = form.lawn(at, axis, 0), form.loop(at, axis, 0)
            if (all(inside(v, poly, 3) for v in loop)
                    and not any(overlap(loop, other) for other in obstacles)):
                selected = (at, lawn, loop)
                break
        if selected is None:
            decision['reason'] = 'PROTECTED_COMMONS_FIT'
            continue
        at, lawn, loop = selected
        identity = 'world:program-campus:' + derive(seed, key, VERSION)
        walks = []
        for number, road in enumerate(plans[key][1]):
            for piece, (a, b) in enumerate(outside(road['start'], road['end'], loop)):
                walks.append(dict(road, id=identity + f':spine:{number}:{piece}',
                                  start=point(a), end=point(b), width=1.6, structural=True))
        ring = [dict(id=identity + f':commons:{i}', start=a, end=b, width=1.4, access=False, structural=True)
                for i, (a, b) in enumerate(zip(loop, loop[1:] + loop[:1]))]
        if not walks:
            decision['reason'] = 'NO_INTERNAL_PEDESTRIAN_SUPPLY'
            continue
        # Link a commons not already cut by an internal street to the nearest
        # real spine. No files exist yet, so the access is reserved first.
        linked = any(math.dist(v, nearest(v, w['start'], w['end'])) < .002 for v in loop for w in walks)
        if not linked:
            joins = sorted(((math.dist(p, q), p, q) for p in loop for w in walks
                            for q in [point(nearest(p, w['start'], w['end']))]), key=lambda v: (v[0], v[1], v[2]))
            join = next(((p, q) for length, p, q in joins if length > .01
                         and not overlap(ribbon(p, q, 1.8), lawn)
                         and not any(overlap(ribbon(p, q, 1.8), f['noBuildPolygon']) for f in (terrain or {}).get('features', []))), None)
            if join:
                walks.append(dict(id=identity + ':commons-access', start=join[0], end=join[1], width=1.4, access=False, structural=True))
            else:
                decision['reason'] = 'NO_COMMONS_ACCESS'
                continue
        walks += ring
        # This site's real physical paths are checked against the global height
        # field during final road grading, before a valid World can be exported.
        anchor = min(zone['memberEntityIds'], key=lambda k: (-sum(w for (a, b), w in pairs.items() if k in (a, b)), k))
        court = dict(id=identity + ':court', center=point(at), polygon=lawn)
        site = dict(zoneId=key, parentId=zone['parentId'], variant='PROGRAM_FRONTAGE_PRECINCT',
                    memberEntityIds=sorted(zone['memberEntityIds']), retainedMemberEntityIds=[],
                    anchorEntityIds=[anchor], anchorSlots={},
                    activityCenters=[dict(id=identity + ':activity', center=point(at), courtId=court['id'], anchorEntityId=anchor, slotIds=[])],
                    courts=[court], walkways=walks, axis=axis, capacity=len(zone['memberEntityIds']),
                    envelopes=[poly], scope='NEIGHBORHOOD', vehicleFrontageSlotIds=[],
                    facilityAssignments={}, architecturalSites=[], capacityVersion=VERSION)
        annotate_program(zone, ([], walks, site))
        plans[key] = ([], walks, axis, None)
        sites[key] = site
        decision.update(status='SELECTED', reason='WHOLE_PHYSICAL_PROGRAM_PRECINCT',
                        eligibilityBasis='STATIC_SOURCE_AFFINITY_NOT_RUNTIME_TRAFFIC')
    return decisions, sites


def update_campus_addresses(site, choices):
    """Replace glyph-slot hints with actual, source-owned physical addresses."""
    by_id = {s['entityId']: s for s in choices}
    site['anchorSlots'] = {k: by_id[k]['id'] for k in site['anchorEntityIds']}
    groups = site.get('activityCenters', [])
    for group in groups:
        group['slotIds'] = []
    for s in choices:
        if groups:
            group = min(groups, key=lambda g: (math.dist(s['center'], g['center']), g['id']))
            group['slotIds'].append(s['id'])
    for group in groups:
        # Preserve the real evidenced anchor in its actual occupied group.
        anchor = group.get('anchorEntityId')
        if anchor in by_id and by_id[anchor]['id'] not in group['slotIds']:
            group['slotIds'].append(by_id[anchor]['id'])
        group['slotIds'].sort()
    site['facilityAssignments'] = {k: s['id'] for k, s in by_id.items()}


def capacity_report(world, programs):
    parcels = {p['entityId']: p for p in world['parcels']}
    if set(parcels) != set(programs):
        raise ValueError('capacity replan omitted or duplicated source entities')
    for identity, wanted in programs.items():
        p = parcels[identity]
        if p['width'] != wanted['width'] or p['depth'] != wanted['depth']:
            raise ValueError('capacity replan shrank or changed a physical program')
    districts = {}
    for d in world['districts']:
        identities = [k for k, p in programs.items() if p['districtId'] == d['id']]
        districts[d['id']] = dict(
            requiredFootprintArea=q(sum(programs[k]['area'] for k in identities)),
            requiredParcelArea=q(sum(programs[k]['parcelWidth'] * programs[k]['parcelDepth'] for k in identities)),
            requiredTotalArea=q(d['areaDemand']['total']), allocatedLandArea=q(area(d['polygon'])),
            sourceEntities=len(identities), allocatedEntities=len(identities), unresolved=0)
    return dict(version=VERSION, derived=True, programs=programs, districts=districts,
                counts={'ALLOCATED': len(parcels), 'DEFERRED_REPLAN': 0},
                families=dict(sorted(Counter(p['family'] for p in programs.values()).items())))


def stabilize_infrastructure(streets, parcels, terrain):
    """Resolve clipping/intersection quantization seams before final routing.

    Do not delete short edges and leave disconnected routes. Coalesce their
    non-source junction endpoints with the existing certified seam operation;
    all doors, frontage points and bridge/tunnel ports stay fixed.
    """
    from .infrastructure import atomic_streets
    from .river_landscape import joined_streets
    before = len(streets)
    for _ in range(4):
        repaired = atomic_streets(joined_streets(streets, parcels, terrain, tolerance=.002))
        if repaired == streets:
            break
        streets = repaired
    for road in streets:
        if road['access']:
            road['linearRamp'] = True
    return streets, dict(version=VERSION, reason='coalesce physical clipping seams before final routing',
                         beforeSegments=before, afterSegments=len(streets), sourceDoorsPinned=True)
