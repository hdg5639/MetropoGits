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


def validate_adaptive_parent(parent, zones, blocks, parcels, pairs, base, *, stitch=False, morphology=False, terrain=None, porous=False, campus=False, campus_pairs=None, campus_style="quad"):
    candidates, roads, main, pattern = adaptive_field(
        parent["polygon"], parent["localSeed"], base, parent["id"], stitch=stitch, morphology=morphology
    )
    polygons = {z["id"]: z["polygon"] for z in zones}
    selections = profile_plan(zones, polygons, pattern, skeleton(roads) if morphology else main)
    plans = {
        z["id"]: local_sites(
            z["polygon"],
            derive(parent["localSeed"], z["id"], VERSION),
            selections[z["id"]],
            candidates,
            roads,
            main,
        )
        for z in zones
    }
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
    if campus:
        from .campus import apply_campuses

        decisions, sites = apply_campuses(plans,selections,zones,polygons,parent['localSeed'],main+boundary,terrain,
                                         campus_pairs if campus_pairs is not None else pairs, campus_style)
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
