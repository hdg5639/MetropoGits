"""Reconstruct mixed-neighborhood pattern selection and vacant address supply."""

from .adaptive import (
    VERSION,
    adaptive_field,
    profile_plan,
    local_sites,
    reserve_complete_plan,
)
from .seed import derive


def validate_adaptive_parent(parent, zones, blocks, parcels, pairs, base, *, stitch=False):
    candidates, roads, main, pattern = adaptive_field(
        parent["polygon"], parent["localSeed"], base, parent["id"], stitch=stitch
    )
    polygons = {z["id"]: z["polygon"] for z in zones}
    selections = profile_plan(zones, polygons, pattern, main)
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
    for z in zones:
        children = [b for b in blocks if b["zoneId"] == z["id"]]
        if len(children) != 1:
            raise ValueError("adaptive neighborhood sector count mismatch")
        b = children[0]
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
