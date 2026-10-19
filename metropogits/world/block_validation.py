"""Independent source/block ownership and reserved-backbone checks."""

from collections import defaultdict
import math

from metropogits.block_orientation import clip
from .affinity import dependency_pairs
from .blocks import road_block_plan
from .geometry import area, bounds, inside, nearest
from .planning import groups


def validate_blocks(world, scene, graph, neighborhoods):
    if world.get("zoningPolicy") != "neighborhoods":
        return
    stored = world["zoning"]
    blocks = stored.get("blocks", [])
    if not 1 <= len(blocks) <= 1024 or len({b["id"] for b in blocks}) != len(blocks):
        raise ValueError("invalid neighborhood block count or identity")
    grouped, _ = groups(scene)
    owners = {b["entityId"]: key for key, members in grouped.items() for b in members}
    pairs = dependency_pairs(graph, owners)
    campus_pairs = dependency_pairs(graph, dict.fromkeys(owners, "campus")) if 'campusPlan' in world else None
    parcels = {p["entityId"]: p for p in world["parcels"]}
    expected_main = []
    inherited = world.get("patternScale") == "district"
    adaptive = world.get("patternScale") == "adaptive"
    expected_patterns = []
    for parent in world["districts"]:
        zones = [z for z in neighborhoods.values() if z["parentId"] == parent["id"]]
        children = [b for b in blocks if b["zoneId"] in {z["id"] for z in zones}]
        polygons = {z["id"]: z["polygon"] for z in zones}
        if adaptive:
            from .adaptive_validation import validate_adaptive_parent
            from .generator import requested_profile

            expected_blocks, main, ports, pattern = validate_adaptive_parent(
                parent,
                zones,
                children,
                parcels,
                pairs,
                requested_profile(
                    world.get("planningPolicy", "grid"), parent["localSeed"]
                ),
                stitch=world["generatorVersion"] in ("flat-adaptive-neighborhoods/0.2", "flat-adaptive-neighborhoods/0.3", "flat-adaptive-neighborhoods/0.4", "flat-adaptive-neighborhoods/0.5", "flat-adaptive-neighborhoods/0.6", "terrain-adaptive/0.1", "terrain-adaptive/0.2", "terrain-adaptive/0.3", "terrain-adaptive/0.4"),
                morphology=world["generatorVersion"] in ("flat-adaptive-neighborhoods/0.3", "flat-adaptive-neighborhoods/0.4", "flat-adaptive-neighborhoods/0.5", "flat-adaptive-neighborhoods/0.6", "terrain-adaptive/0.1", "terrain-adaptive/0.2", "terrain-adaptive/0.3", "terrain-adaptive/0.4"),
                terrain=world.get("terrain"),
                porous=world.get("streetPolicy") == "porous",
                campus='campusPlan' in world,
                campus_pairs=campus_pairs,
                campus_style=world.get('campusPlan',{}).get('style','quad'),
            )
            expected_patterns.append(pattern)
        elif inherited:
            from .district_patterns import street_field
            from .generator import requested_profile

            profile = requested_profile(
                world.get("planningPolicy", "grid"), parent["localSeed"]
            )
            slots, main, pattern = street_field(
                parent["polygon"], parent["localSeed"], profile, parent["id"]
            )
            expected_patterns.append(pattern)
            by_slot = {s["id"]: s for s in slots}
            for b in children:
                if (
                    b.get("inheritedPatternId") != pattern["id"]
                    or b["planningProfile"] != profile
                ):
                    raise ValueError("neighborhood inherited pattern mismatch")
                for key in b["memberEntityIds"]:
                    p = parcels[key]
                    s = by_slot.get(p["slotId"])
                    if (
                        s is None
                        or any(
                            p.get(k) != s.get(k)
                            for k in ("center", "angle", "entrance", "streetPoint")
                        )
                        or p["parcel"] != s["polygon"]
                    ):
                        raise ValueError(
                            "neighborhood address did not inherit its parent pattern"
                        )
            expected_blocks = [
                dict(b, boundaryTypes=["NEIGHBORHOOD_BOUNDARY"] * len(b["polygon"]))
                for b in children
            ]
            ports = {z["id"]: [] for z in zones}
        else:
            expected_blocks, main, ports = road_block_plan(
                zones,
                polygons,
                {},
                pairs,
                parent["localSeed"],
                parent["polygon"],
                children,
            )
        expected_main.extend(main)
        for zone in zones:
            if zone["accessPorts"] != ports[zone["id"]]:
                raise ValueError("neighborhood access port mismatch")
        expected_by_id = {b["id"]: b for b in expected_blocks}
        for b in children:
            if b["boundaryTypes"] != expected_by_id[b["id"]]["boundaryTypes"]:
                raise ValueError("neighborhood block boundary type mismatch")
    if (inherited or adaptive) and stored.get("districtPatterns") != sorted(
        expected_patterns, key=lambda p: p["id"]
    ):
        raise ValueError("neighborhood district pattern metadata mismatch")
    if stored.get("mainRoads") != sorted(expected_main, key=lambda r: r["id"]):
        raise ValueError("neighborhood main-road reservation mismatch")
    for zone in neighborhoods.values():
        children = [b for b in blocks if b["zoneId"] == zone["id"]]
        memberships = [key for b in children for key in b["memberEntityIds"]]
        if sorted(memberships) != zone["memberEntityIds"] or len(
            set(memberships)
        ) != len(memberships):
            raise ValueError("neighborhood block source membership mismatch")
        if not set(zone["coreEntityIds"]).issubset(memberships):
            raise ValueError("neighborhood lost physical source core")
        if (
            abs(sum(area(b["polygon"]) for b in children) - area(zone["polygon"]))
            > 0.03
        ):
            raise ValueError("neighborhood block area loss")
        for i, b in enumerate(children):
            if (
                b["capacity"] < len(b["memberEntityIds"])
                or area(b["polygon"]) < 1
                or not all(inside(p, zone["polygon"], -0.001) for p in b["polygon"])
            ):
                raise ValueError("invalid neighborhood block polygon/capacity")
            if any(
                area(clip(b["polygon"], other["polygon"])) > 0.001
                for other in children[:i]
            ):
                raise ValueError("neighborhood blocks overlap")
            regions = (
                b.get("planningRegions", []) if b["planningProfile"] == "HYBRID" else []
            )
            if regions:
                if abs(
                    sum(area(r["polygon"]) for r in regions) - area(b["polygon"])
                ) > 0.03 or any(
                    not all(inside(v, b["polygon"], -0.001) for v in r["polygon"])
                    for r in regions
                ):
                    raise ValueError("invalid neighborhood hybrid regions")
                if any(
                    area(clip(r["polygon"], other["polygon"])) > 0.001
                    for i, r in enumerate(regions)
                    for other in regions[:i]
                ):
                    raise ValueError("neighborhood hybrid region overlap")
            for key in b["memberEntityIds"]:
                p = parcels[key]
                if (
                    p["blockId"] != b["id"]
                    or p["zoneId"] != zone["id"]
                    or not all(
                        inside(v, b["polygon"]) for v in p["parcel"] + p["footprint"]
                    )
                ):
                    raise ValueError("neighborhood parcel escaped its physical block")
                if key in b.get('campusSite',{}).get('memberEntityIds',[]):
                    if p.get('blockProfile')!='CAMPUS':
                        raise ValueError('campus member lacks a campus frontage plot')
                elif regions:
                    region = next(
                        (r for r in regions if r["id"] == p.get("planningRegionId")),
                        None,
                    )
                    if (
                        region is None
                        or p["blockProfile"] != region["planningProfile"]
                        or not all(
                            inside(v, region["polygon"])
                            for v in p["parcel"] + p["footprint"]
                        )
                    ):
                        raise ValueError("neighborhood parcel escaped hybrid region")
                elif p["blockProfile"] != b["planningProfile"]:
                    raise ValueError("neighborhood local grammar mismatch")
    if world["generatorVersion"] == "flat-adaptive-neighborhoods/0.5" or world.get("streetPolicy") in ("permeable", "porous"):
        notes = [d for d in world["diagnostics"] if d.get("version") == "frontage-alleys/0.1"]
        if len(notes) != 1 or len(notes[0].get("corridors", [])) > 24:
            raise ValueError("invalid alley audit record")
        for r in notes[0]["corridors"]:
            if (not 9.999 <= math.dist(r["start"], r["end"]) <= 44.001
                    or r["width"] != 1.6 or len(set(r["rowEntityIds"])) < 6
                    or any(k not in parcels or parcels[k].get("zoneId") != r["zoneId"]
                           or parcels[k]["districtId"] != r["districtId"] for k in r["rowEntityIds"])):
                raise ValueError("invalid alley frontage provenance")
            expected_main.append(r)
    # Only independently reconstructed, purpose-free campus tails may be unbuilt.
    # Never accept a diagnostic alone as permission to omit reserved main roads.
    from .campus_circulation import verified_omissions

    omissions = verified_omissions(world, expected_main + world["topology"]["edges"])
    # Verify complete reserved coverage by built streets or proven omissions.
    index = defaultdict(list)
    entries = 0
    for s in world["streets"] + omissions:
        x0, z0, x1, z1 = bounds([s["start"], s["end"]])
        if max(x1 - x0, z1 - z0) > 10000:
            raise ValueError("neighborhood backbone spatial extent limit")
        for x in range(math.floor(x0 / 32), math.floor(x1 / 32) + 1):
            for z in range(math.floor(z0 / 32), math.floor(z1 / 32) + 1):
                index[(x, z)].append(s)
                entries += 1
                if entries > 2_000_000:
                    raise ValueError("neighborhood backbone index limit")
    checks = 0
    for r in expected_main:
        length = math.dist(r["start"], r["end"])
        direction = [(r["end"][j] - r["start"][j]) / length for j in (0, 1)]
        x0, z0, x1, z1 = bounds([r["start"], r["end"]])
        if max(x1 - x0, z1 - z0) > 10000:
            raise ValueError("neighborhood backbone spatial extent limit")
        candidates = {
            s["id"]: s
            for x in range(math.floor(x0 / 32), math.floor(x1 / 32) + 1)
            for z in range(math.floor(z0 / 32), math.floor(z1 / 32) + 1)
            for s in index[(x, z)]
        }
        spans = []
        for s in candidates.values():
            checks += 1
            if checks > 5_000_000:
                raise ValueError("neighborhood backbone validation work limit")
            if s["width"] + 0.001 < r["width"] or any(
                math.dist(p, nearest(p, r["start"], r["end"])) > 0.002
                for p in (s["start"], s["end"])
            ):
                continue
            spans.append(
                sorted(
                    sum((p[j] - r["start"][j]) * direction[j] for j in (0, 1))
                    for p in (s["start"], s["end"])
                )
            )
        reach = 0
        for a, b in sorted(spans):
            if a > reach + 0.003:
                break
            reach = max(reach, b)
        if reach < length - 0.003:
            raise ValueError(
                "neighborhood reserved main road missing physical pavement"
            )
