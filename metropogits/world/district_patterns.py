"""One reserved street field, physically subdivided source neighborhoods."""

import math

from metropogits.block_orientation import clip
from .affinity import optimize_addresses
from .geometry import area, centroid, inside, inset, point
from .hybrid import hybrid_regions, hybrid_slots
from .industrial import industrial_slots
from .organic import organic_slots
from .planning import demand, populate, slots
from .power import power_partition
from .radial import radial_slots
from .seed import derive

VERSION = "district-patterns/0.1"
MAX_ALLOCATION_ATTEMPTS = 6
MAX_SUBDIVISION_WORK = 5_000_000


def pattern_demand(clusters, members, profile):
    by_id = {b["entityId"]: b for b in members}
    budgets = [
        demand([by_id[k] for k in z["memberEntityIds"]], profile) for z in clusters
    ]
    return {key: sum(b[key] for b in budgets) for key in budgets[0]}


def street_field(polygon, seed, profile, parent_id, *, lane_identity=False):
    """Reserve the entire shared pattern before neighborhood addresses exist.

    Existing planners reserve roads before sampling vacant frontage sites. No
    source building is assigned here; subdivision never restarts these planners.
    """
    planner = {
        "GRID": slots,
        "ORGANIC": organic_slots,
        "RADIAL": radial_slots,
        "INDUSTRIAL": industrial_slots,
        "HYBRID": hybrid_slots,
    }[profile]
    candidates, roads, angle = planner(polygon, seed)
    identity = "world:pattern:" + derive(parent_id, VERSION)
    for slot in candidates:
        slot.update(
            id=identity + ":" + slot["id"],
            laneId=identity + ":" + slot["laneId"],
            polygon=[point(p) for p in inset(slot["polygon"], 0.01)],
        )
        if profile != "HYBRID":
            slot["blockProfile"] = profile
    main = [
        dict(
            r,
            id="world:backbone:" + derive(identity, r["id"], VERSION),
            patternId=identity,
            structural=True,
        )
        for r in roads
        if math.dist(r["start"], r["end"]) > 0.001
    ]
    if lane_identity:
        by_id = {
            "world:backbone:" + derive(identity, r["id"], VERSION): r["id"]
            for r in roads
        }
        for r in main:
            r["sourceLaneId"] = by_id[r["id"]]
    record = dict(
        id=identity,
        version=VERSION,
        parentId=parent_id,
        profile=profile,
        seed=seed,
        primaryAxis=angle,
        slotCapacity=len(candidates),
        roadCount=len(main),
    )
    if profile == "RADIAL":
        record["hub"] = point(centroid(inset(polygon, 5)))
    if profile == "HYBRID":
        record["regions"] = hybrid_regions(polygon, seed)
    return candidates, sorted(main, key=lambda r: r["id"]), record


def sector_slots(candidates, polygon):
    # Semantic boundaries have no physical boundary road. Keep complete lots
    # from the same parent sampling phase, rather than adding five-unit gutters.
    return [
        s for s in candidates if all(inside(p, polygon, 0.01) for p in s["polygon"])
    ]


def plan_district_pattern(
    polygon,
    clusters,
    members,
    seed,
    paths,
    pairs,
    profile,
    previous_zones=(),
    previous_blocks=(),
    previous_slots=None,
):
    parent = clusters[0]["parentId"]
    candidates, roads, pattern = street_field(polygon, seed, profile, parent)
    by_id = {b["entityId"]: b for b in members}
    old = {z["id"]: z for z in previous_zones}
    reuse = set(old) == {z["id"] for z in clusters}
    demands = [
        (z["id"], demand([by_id[k] for k in z["memberEntityIds"]], profile)["total"])
        for z in clusters
    ]
    counts = {z["id"]: len(z["memberEntityIds"]) for z in clusters}
    diagnostics = []
    for attempt in range(MAX_ALLOCATION_ATTEMPTS):
        if reuse:
            polygons = {key: z["polygon"] for key, z in old.items()}
            allocation = dict(algorithm="previous-anchors/0.1", iterations=0)
        else:
            polygons, allocation = power_partition(
                polygon, demands, derive(seed, "inherited-neighborhoods")
            )
        if (
            len(candidates) * sum(len(poly) for poly in polygons.values())
            > MAX_SUBDIVISION_WORK
        ):
            raise ValueError("inherited pattern subdivision work limit")
        choices = {
            key: sector_slots(candidates, poly) for key, poly in polygons.items()
        }
        failed = [key for key in counts if len(choices[key]) < counts[key]]
        if not failed:
            break
        diagnostics.append(
            dict(
                reason="inherited pattern neighborhood capacity repair; requested grammar retained",
                zoneIds=sorted(failed),
                attempt=attempt,
            )
        )
        if reuse:
            reuse = False
        else:
            demands = [
                (
                    key,
                    value
                    * max(
                        0.8,
                        min(
                            1.6,
                            math.sqrt((counts[key] + 2) / max(1, len(choices[key]))),
                        ),
                    ),
                )
                for key, value in demands
            ]
    else:
        return None, [], [], diagnostics, False, [], [], pattern
    total = sum(value for _, value in demands)
    targets = {key: area(polygon) * value / total for key, value in demands}
    allocation = dict(
        allocation,
        maxRelativeAreaError=max(
            abs(area(polygons[key]) - target) / target
            for key, target in targets.items()
        ),
    )
    parcels, records, blocks = [], [], []
    for zone in clusters:
        key = zone["id"]
        poly = polygons[key]
        identities = set(zone["memberEntityIds"])
        population = [by_id[k] for k in sorted(identities)]
        local = derive(seed, key, VERSION)
        placed = populate(
            population,
            choices[key],
            parent,
            paths,
            local,
            previous_slots if reuse else None,
        )
        assignment, report = optimize_addresses(
            placed,
            {
                (a, b): w
                for (a, b), w in pairs.items()
                if a in identities and b in identities
            },
            {},
            local,
            (previous_slots or {}) if reuse else (),
        )
        placed = populate(population, choices[key], parent, paths, local, assignment)
        block_id = "world:block:" + derive(key, VERSION)
        for parcel in placed:
            parcel.update(zoneId=key, blockId=block_id)
        block = dict(
            id=block_id,
            zoneId=key,
            memberEntityIds=zone["memberEntityIds"],
            polygon=poly,
            anchor=point(centroid(poly)),
            areaAllocated=area(poly),
            boundaryTypes=["NEIGHBORHOOD_BOUNDARY"] * len(poly),
            planningSeed=seed,
            planningProfile=profile,
            requestedProfile=profile,
            capacity=len(choices[key]),
            primaryAxis=pattern["primaryAxis"],
            inheritedPatternId=pattern["id"],
            reused=reuse,
            affinity=report,
        )
        if profile == "HYBRID":
            block["planningRegions"] = [
                dict(r, polygon=[point(p) for p in part], areaAllocated=area(part))
                for r in pattern["regions"]
                if len(part := clip(r["polygon"], poly)) >= 3 and area(part) > 0.001
            ]
        blocks.append(block)
        parcels.extend(placed)
        records.append(
            dict(
                zone,
                polygon=poly,
                anchor=point(centroid(poly)),
                planningSeed=local,
                planningProfile="BLOCK_LOCAL",
                areaDemand=demand(population, profile),
                areaAllocated=area(poly),
                areaTarget=targets[key],
                capacity=len(choices[key]),
                allocation=allocation,
                accessPorts=[],
            )
        )
    return parcels, roads, records, diagnostics, reuse, blocks, roads, pattern
