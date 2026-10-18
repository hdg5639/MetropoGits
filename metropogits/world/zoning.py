"""Derived role neighborhoods: evidence chooses members, geometry never does."""

from collections import defaultdict
import math

from .geometry import area, centroid, inset, partition, point, shared_boundaries
from .industrial import industrial_slots
from .organic import organic_slots
from .planning import demand, populate, slots
from .power import power_partition
from .radial import radial_slots
from .seed import derive
from .zone_access import access_corridors

VERSION = "semantic-zoning/0.1"
MIN_GROUP = 12
MIN_DISTRICT = 24
ROLE_ZONE = {
    "SERVICE": "SERVICE_QUARTER",
    "PERSISTENCE_ADAPTER": "INDUSTRIAL_LOGISTICS",
    "UI_PAGE": "COMMERCIAL_FRONTEND",
    "ENTRYPOINT": "GATEWAY_CIVIC",
    "TEST": "CAMPUS_RESEARCH",
}
LABELS = {
    "SERVICE_QUARTER": "Service quarter",
    "INDUSTRIAL_LOGISTICS": "Persistence quarter",
    "COMMERCIAL_FRONTEND": "Frontend quarter",
    "GATEWAY_CIVIC": "Entrypoint quarter",
    "CAMPUS_RESEARCH": "Test campus",
    "GENERAL_MIXED": "Mixed / unclassified",
}


def zoning_grid_slots(polygon, seed):
    # Four bounded local fits avoid expanding an entire service for a narrow
    # wedge that simply needs the perpendicular frontage frame or half-period.
    choices = [
        slots(polygon, seed, rotation=rotation, phase_offset=phase)
        for rotation, phase in ((0, 0), (0, 12), (math.pi / 2, 0), (math.pi / 2, 12))
    ]
    return max(choices, key=lambda item: len(item[0]))


def candidates(members, entities, district_id):
    buckets = defaultdict(list)
    claims = {}
    for building in members:
        identity = building["entityId"]
        supported = [
            dict(
                value=r["value"],
                confidence=r["confidence"],
                evidenceIds=sorted(r["evidenceIds"]),
            )
            for r in entities[identity].get("roles", [])
            if r["value"] in ROLE_ZONE
            and r["confidence"] in ("DIRECT", "RESOLVED")
            and r["evidenceIds"]
        ]
        kinds = {ROLE_ZONE[r["value"]] for r in supported}
        key = next(iter(kinds)) if len(kinds) == 1 else "GENERAL_MIXED"
        buckets[key].append(identity)
        claims[identity] = supported
    for key in list(buckets):
        if key != "GENERAL_MIXED" and (
            len(buckets[key]) < MIN_GROUP or len(members) < MIN_DISTRICT
        ):
            buckets["GENERAL_MIXED"].extend(buckets.pop(key))
    result = []
    for key, identities in sorted(buckets.items()):
        if not identities:
            continue
        provenance = (
            []
            if key == "GENERAL_MIXED"
            else [
                dict(
                    entityId=identity,
                    roles=sorted(claims[identity], key=lambda r: r["value"]),
                )
                for identity in sorted(identities)
            ]
        )
        profile = {
            "INDUSTRIAL_LOGISTICS": "INDUSTRIAL",
            "CAMPUS_RESEARCH": "ORGANIC",
            "GATEWAY_CIVIC": "RADIAL" if len(identities) >= 32 else "GRID",
        }.get(key, "GRID")
        result.append(
            dict(
                id="world:zone:" + derive(district_id, key, VERSION),
                parentId=district_id,
                clusterKey=key,
                label=LABELS[key],
                classification=dict(
                    status="INFERRED" if provenance else "UNKNOWN",
                    ruleIds=["zoning:verified-role-quarters/1"] if provenance else [],
                    evidenceIds=sorted(
                        {
                            ev
                            for item in provenance
                            for r in item["roles"]
                            for ev in r["evidenceIds"]
                        }
                    ),
                ),
                memberEntityIds=sorted(identities),
                memberClaims=provenance,
                requestedProfile=profile,
            )
        )
    return result


def zone_demand(clusters, members):
    by_id = {b["entityId"]: b for b in members}
    budgets = [
        demand([by_id[key] for key in z["memberEntityIds"]], z["requestedProfile"])
        for z in clusters
    ]
    return {key: sum(b[key] for b in budgets) for key in budgets[0]}


def plan_zones(
    polygon, clusters, members, seed, paths, previous_zones=(), previous_slots=None
):
    """Plan roads first in each cell; retry geometry/grammar without losing members."""
    by_id = {b["entityId"]: b for b in members}
    demands = [
        (
            z["id"],
            demand([by_id[k] for k in z["memberEntityIds"]], z["requestedProfile"])[
                "total"
            ],
        )
        for z in clusters
    ]
    old = {z["id"]: z for z in previous_zones}
    reuse = set(old) == {z["id"] for z in clusters}
    if reuse:
        polygons = {key: z["polygon"] for key, z in old.items()}
        allocation = dict(
            algorithm="previous-anchors/0.1", iterations=0, maxRelativeAreaError=0
        )
    else:
        polygons, allocation = power_partition(
            polygon, demands, derive(seed, "zone-sites")
        )
    diagnostics = []
    for attempt in range(3):
        total = sum(value for _, value in demands)
        allocation = dict(
            allocation,
            maxRelativeAreaError=max(
                abs(area(polygons[key]) - area(polygon) * value / total)
                / (area(polygon) * value / total)
                for key, value in demands
            ),
        )
        records, parcels, lanes = [], [], []
        local_roads = {}
        observed_capacity = {}
        failed = []
        for cluster in clusters:
            key = cluster["id"]
            poly = polygons[key]
            local_seed = derive(seed, key, VERSION)
            profile = (
                old[key]["planningProfile"] if reuse else cluster["requestedProfile"]
            )
            planner = {
                "GRID": zoning_grid_slots,
                "ORGANIC": organic_slots,
                "RADIAL": radial_slots,
                "INDUSTRIAL": industrial_slots,
            }[profile]
            choices, roads, angle = planner(poly, local_seed)
            count = len(cluster["memberEntityIds"])
            if len(choices) < count and profile != "GRID" and not reuse:
                diagnostics.append(
                    dict(
                        reason=f"{profile.lower()} zone capacity insufficient; local GRID fallback",
                        zoneIds=[key],
                    )
                )
                profile = "GRID"
                choices, roads, angle = zoning_grid_slots(poly, local_seed)
            observed_capacity[key] = len(choices)
            for slot in choices:
                slot.update(
                    id=key + ":" + slot["id"],
                    laneId=key + ":" + slot["laneId"],
                    # Real clearance between quantized adjacent lots; overlap
                    # validation remains strict, rather than hiding the jitter.
                    polygon=[point(p) for p in inset(slot["polygon"], 0.01)],
                )
            placed = populate(
                [by_id[k] for k in cluster["memberEntityIds"]],
                choices,
                cluster["parentId"],
                paths,
                local_seed,
                previous_slots if reuse else None,
            )
            if placed is None:
                failed.append(key)
                continue
            for p in placed:
                p.update(zoneId=key, blockProfile=profile)
            parcels.extend(placed)
            lanes.extend(roads)
            local_roads[key] = roads
            records.append(
                dict(
                    cluster,
                    polygon=poly,
                    anchor=point(centroid(poly)),
                    planningSeed=local_seed,
                    planningProfile=profile,
                    primaryAxis=angle,
                    areaDemand=demand(
                        [by_id[k] for k in cluster["memberEntityIds"]],
                        cluster["requestedProfile"],
                    ),
                    areaAllocated=area(poly),
                    areaTarget=area(polygon) * dict(demands)[key] / total,
                    capacity=len(choices),
                    allocation=allocation,
                )
            )
        if not failed:
            lanes.extend(access_corridors(polygons, local_roads, polygon))
            return parcels, lanes, records, diagnostics, reuse
        if reuse:
            diagnostics.append(
                dict(
                    reason="zone capacity exhausted; local replanning within retained parent",
                    zoneIds=failed,
                )
            )
            reuse = False
        elif attempt == 0:
            diagnostics.append(
                dict(
                    reason="rebalance child land from measured frontage capacity within unchanged parent",
                    zoneIds=failed,
                )
            )
            counts = {z["id"]: len(z["memberEntityIds"]) for z in clusters}
            demands = [
                (
                    key,
                    value
                    * max(
                        0.6,
                        min(2.5, counts[key] * 1.15 / max(1, observed_capacity[key])),
                    ),
                )
                for key, value in demands
            ]
            polygons, allocation = power_partition(
                polygon, demands, derive(seed, "zone-capacity-feedback")
            )
            continue
        else:
            diagnostics.append(
                dict(
                    reason="power-cell frontage insufficient; capacity-bisection retry",
                    zoneIds=failed,
                )
            )
        polygons = partition(
            polygon, sorted(demands), derive(seed, "zone-capacity-fallback")
        )
        polygons, _ = shared_boundaries(polygons, polygon)
        allocation = dict(
            algorithm="capacity-bisection/0.1",
            iterations=0,
            maxRelativeAreaError=0,
            fallbackReason="frontage capacity",
        )
    return None, [], [], diagnostics, False


def planning_document(world):
    if world.get("zoningPolicy") == "neighborhoods":
        return dict(
            schemaVersion="planning/0.3-experimental",
            zoningVersion=world["zoning"]["version"],
            worldSeed=world["seed"],
            ucgDigest=world["ucgDigest"],
            sourceCityDigest=world["sourceCityDigest"],
            terrainPreset="flat",
            zones=world["zoning"]["zones"],
            blocks=world["zoning"]["blocks"],
            mainRoads=world["zoning"]["mainRoads"],
        )
    if world.get("zoningPolicy") == "soft":
        return dict(
            schemaVersion="planning/0.2-experimental",
            zoningVersion=world["softZoning"]["version"],
            worldSeed=world["seed"],
            ucgDigest=world["ucgDigest"],
            sourceCityDigest=world["sourceCityDigest"],
            terrainPreset="flat",
            **{
                k: world["softZoning"][k]
                for k in (
                    "zones",
                    "optimization",
                    "baseGeneratorVersion",
                    "addressDigest",
                )
            },
        )
    return dict(
        schemaVersion="planning/0.1-experimental",
        zoningVersion=VERSION,
        worldSeed=world["seed"],
        ucgDigest=world["ucgDigest"],
        sourceCityDigest=world["sourceCityDigest"],
        terrainPreset="flat",
        zones=world["zoning"]["zones"],
    )


def validate_zoning(world, scene, graph):
    """Reconstruct the classification from source, independently of stored claims."""
    from metropogits.block_orientation import clip
    from .geometry import inside
    from .planning import groups

    if world.get("zoningPolicy") == "soft":
        if "zoning" in world:
            raise ValueError("hard and soft zoning cannot both own parcels")
        return {}
    physical_neighborhoods = world.get("zoningPolicy") == "neighborhoods"
    if world.get("zoningPolicy") not in ("semantic", "neighborhoods"):
        if "zoning" in world or any("zoneId" in p for p in world["parcels"]):
            raise ValueError("zoning data lacks an explicit policy")
        return {}
    stored = world.get("zoning", {})
    records = stored.get("zones", [])
    if (
        stored.get("version")
        != ("neighborhoods/0.1" if physical_neighborhoods else VERSION)
        or not 1 <= len(records) <= 448
    ):
        raise ValueError("invalid zoning version or zone limit")
    actual = {z["id"]: z for z in records}
    expected = {}
    entities = {e["id"]: e for e in graph["entities"]}
    grouped, _ = groups(scene)
    for key, members in grouped.items():
        from .neighborhoods import neighborhood_candidates

        choices = (
            neighborhood_candidates(members, entities, key, graph)
            if physical_neighborhoods
            else candidates(members, entities, key)
        )
        expected.update({z["id"]: z for z in choices})
    if len(actual) != len(records) or set(actual) != set(expected):
        raise ValueError("zoning ownership or zone identity mismatch")
    for key, cluster in expected.items():
        if any(actual[key].get(field) != value for field, value in cluster.items()):
            raise ValueError("zoning source membership or evidence mismatch")
    for district in world["districts"]:
        children = [z for z in records if z["parentId"] == district["id"]]
        if district["planningProfile"] != "ZONED" or not children:
            raise ValueError("zoning parent mismatch")
        parent_area = area(district["polygon"])
        if abs(sum(area(z["polygon"]) for z in children) - parent_area) > max(
            0.02, parent_area * 1e-5
        ):
            raise ValueError("zoning child area conservation failed")
        for i, z in enumerate(children):
            poly = z["polygon"]
            if (
                not 3 <= len(poly) <= 512
                or area(poly) < 1
                or z["capacity"] < len(z["memberEntityIds"])
                or abs(z["areaAllocated"] - area(poly)) > 0.001
                or z["areaTarget"] <= 0
                or not all(inside(p, poly, margin=-0.001) for p in poly)
                or not all(inside(p, district["polygon"], margin=-0.001) for p in poly)
            ):
                raise ValueError("invalid zoning polygon or capacity")
            if any(area(clip(poly, o["polygon"])) > 0.001 for o in children[:i]):
                raise ValueError("zoning child overlap")
        if abs(sum(z["areaTarget"] for z in children) - parent_area) > 0.02:
            raise ValueError("zoning target area conservation failed")
    return actual
