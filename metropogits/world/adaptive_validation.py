"""Reconstruct mixed-neighborhood pattern selection and vacant address supply."""

from .adaptive import (
    VERSION,
    adaptive_field,
    profile_plan,
    local_sites,
    reserve_complete_plan,
    skeleton,
)
from .seed import derive


def validate_adaptive_parent(parent, zones, blocks, parcels, pairs, base, *, stitch=False, morphology=False, terrain=None, porous=False, campus=False, campus_pairs=None, campus_style="quad", campus_groups=None, capacity_programs=None):
    if capacity_programs is not None:
        from .capacity import program_field, planning_scale
        members = [parcels[k] for z in zones for k in z['memberEntityIds']]
        scale = planning_scale(members)
        candidates, roads, main, pattern = program_field(parent['polygon'], parent['localSeed'], base, parent['id'], scale)
    else:
        candidates, roads, main, pattern = adaptive_field(
            parent["polygon"], parent["localSeed"], base, parent["id"], stitch=stitch, morphology=morphology
        )
    polygons = {z["id"]: z["polygon"] for z in zones}
    selections = profile_plan(zones, polygons, pattern, skeleton(roads) if morphology else main)
    if campus and campus_style == 'precinct':
        from .campus_reservation import reserve_precinct
        main, pattern = reserve_precinct(zones, polygons, parent['localSeed'], main, pattern, terrain,
                                        campus_groups if campus_groups is not None else campus_pairs or {})
    from .capacity import program_local_sites
    plans = {
        z["id"]: (program_local_sites if capacity_programs is not None else local_sites)(
            z["polygon"],
            derive(parent["localSeed"], z["id"], VERSION),
            selections[z["id"]],
            candidates,
            roads,
            main,
            **(dict(scale=scale) if capacity_programs is not None else {}),
        )
        for z in zones
    }
    if capacity_programs is not None:
        from .capacity import program_regions
        plans = {z['id']: program_regions(plans[z['id']], selections[z['id']], pattern, polygons[z['id']]) for z in zones}
    plans, boundary, ports = reserve_complete_plan(
        plans, polygons, main, parent["polygon"], pattern, zones, pairs
    )
    if terrain:
        from .terrain import terrain_plan

        plans, main, boundary, ports, pattern = terrain_plan(
            plans, main, boundary, ports, pattern, parent["polygon"], terrain
        )
    if porous:
        from .permeability import reserve_links

        plans, main, pattern = reserve_links(
            plans, main, boundary, parent["polygon"], pattern,
            {z["id"]: len(z["memberEntityIds"]) for z in zones}, terrain,
        )
    decisions, sites = {}, {}
    if capacity_programs is not None:
        from .capacity import fit_programs, capacity_campuses, update_campus_addresses
        if campus:
            decisions, sites = capacity_campuses(
                plans, selections, zones, polygons, parent['localSeed'], main + boundary, terrain,
                campus_pairs if campus_pairs is not None else pairs, campus_style, campus_groups,
                pattern.get('campusReservation', {}).get('zoneId'))
        complete_roads = main + boundary + [r for plan in plans.values() for r in plan[1]]
        for z in zones:
            key = z['id']
            site = sites.get(key)
            choices = {s['id']: s for s in plans[key][0]}
            preferred = {identity: choices[slot]['center'] for identity, slot in
                         (site or {}).get('facilityAssignments', {}).items() if slot in choices}
            plans[key] = fit_programs(
                [dict(parcels[k], blockProfile='CAMPUS' if site else selections[key]['profile']) for k in z['memberEntityIds']],
                polygons[key], plans[key], complete_roads, terrain, derive(parent['localSeed'], key, VERSION),
                courts=(site or {}).get('courts', []), preferences=preferred)
            if site and len(plans[key][0]) == len(z['memberEntityIds']):
                update_campus_addresses(site, plans[key][0])
    if campus and capacity_programs is None:
        from .campus import apply_campuses

        decisions, sites = apply_campuses(plans,selections,zones,polygons,parent['localSeed'],main+boundary,terrain,
                                         campus_pairs if campus_pairs is not None else pairs, campus_style, grouping_pairs=campus_groups,
                                         reserved_zone=pattern.get('campusReservation', {}).get('zoneId'))
    if sites:
        walks = [w for site in sites.values() for w in site['walkways']]
        for w in walks:
            w['patternId'] = pattern['id']
        main = main + walks
        pattern = dict(pattern,campusWalkwayCount=len(walks),roadCount=pattern['roadCount']+len(walks),
                       protectedStreetIds=sorted(set(pattern['protectedStreetIds'])|{w['id'] for w in walks}))
    for z in zones:
        children = [b for b in blocks if b["zoneId"] == z["id"]]
        if len(children) != 1:
            raise ValueError("adaptive neighborhood sector count mismatch")
        b = children[0]
        if campus and (b.get('campusDecision')!=decisions[z['id']] or b.get('campusSite')!=sites.get(z['id'])):
            raise ValueError('campus decision or reserved geometry mismatch')
        if z['id'] in sites and b.get('urbanGrammar') != ('CAMPUS' if campus_style in ('neighborhood','landscape','organic','fabric','programmed','estate','precinct') else 'MIXED_CAMPUS'):
            raise ValueError('campus block grammar does not match the selected planning scope')
        selection = selections[z["id"]]
        choices = plans[z["id"]][0]
        if (
            b["id"] != "world:block:" + derive(z["id"], VERSION)
            or b.get("inheritedPatternId") != pattern["id"]
            or b.get("patternMode") != selection["mode"]
            or b["planningProfile"] != selection["profile"]
            or b["capacity"] != len(choices)
        ):
            raise ValueError("adaptive neighborhood grammar/inheritance mismatch")
        by_id = {p["id"]: p for p in choices}
        for key in z["memberEntityIds"]:
            p = parcels[key]
            s = by_id.get(p["slotId"])
            if (
                s is None
                or p["parcel"] != s["polygon"]
                or any(
                    p.get(k) != s.get(k)
                    for k in ("center", "angle", "entrance", "streetPoint")
                )
            ):
                raise ValueError(
                    "adaptive frontage did not follow its reserved road plan"
                )
            if z['id'] in sites and ((key in sites[z['id']]['memberEntityIds']) != (s.get('blockProfile')=='CAMPUS')):
                raise ValueError('campus source membership did not follow its assigned plots')
    expected = [
        dict(b, boundaryTypes=["NEIGHBORHOOD_BOUNDARY"] * len(b["polygon"]))
        for b in blocks
    ]
    return (
        expected,
        main + boundary,
        {key: [list(p) for p in sorted(points)] for key, points in ports.items()},
        pattern,
    )
