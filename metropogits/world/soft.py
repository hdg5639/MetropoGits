"""Functional influences and mixed graph-aware placement over existing streets."""

import copy
import math
from collections import defaultdict

from scripts.canonical_json import sha256_digest
from .affinity import dependency_pairs, optimize_addresses
from .geometry import area, centroid, inside, point
from .infrastructure import route_world
from .planning import groups, populate
from .power import power_partition
from .seed import derive
from .zoning import candidates

VERSION = "soft-zoning/0.1"


def address_digest(parcels):
    return sha256_digest(
        sorted(
            [
                p[k]
                for k in (
                    "districtId",
                    "slotId",
                    "center",
                    "angle",
                    "parcel",
                    "entrance",
                    "streetPoint",
                )
            ]
            for p in parcels
        )
    )


def influence_regions(world, scene, graph):
    entities = {e["id"]: e for e in graph["entities"]}
    grouped, _ = groups(scene)
    records = []
    for district in world["districts"]:
        clusters = candidates(grouped[district["id"]], entities, district["id"])
        polygons, allocation = power_partition(
            district["polygon"],
            [(z["id"], len(z["memberEntityIds"])) for z in clusters],
            derive(district["localSeed"], "soft-influences"),
        )
        for cluster in clusters:
            polygon = polygons[cluster["id"]]
            records.append(
                dict(
                    cluster,
                    polygon=polygon,
                    anchor=point(centroid(polygon)),
                    referenceEntityIds=cluster["memberEntityIds"],
                    referenceClaims=cluster["memberClaims"],
                    memberEntityIds=[],
                    memberClaims=[],
                    planningProfile=district["planningProfile"],
                    allocation=allocation,
                    areaAllocated=area(polygon),
                )
            )
    return sorted(records, key=lambda z: z["id"])


def influence_owner(parcel, regions):
    options = [z for z in regions if z["parentId"] == parcel["districtId"]]
    matches = [z for z in options if inside(parcel["center"], z["polygon"])]
    if not matches:
        raise ValueError("soft zoning address outside influence regions")
    return min(matches, key=lambda z: z["id"])["id"]


def generate_soft_world(
    scene,
    graph,
    *,
    seed=None,
    namespace=None,
    previous=None,
    planning="grid",
    outline="ellipse",
):
    from .generator import generate_world

    if previous is not None and not isinstance(previous, dict):
        raise ValueError("invalid previous soft world")
    previous_base = previous
    if previous and previous.get("zoningPolicy") == "soft":
        if (
            not isinstance(previous.get("softZoning"), dict)
            or previous["softZoning"].get("version") != VERSION
        ):
            raise ValueError("unsupported previous soft zoning version")
        previous_base = dict(previous)
        previous_base["generatorVersion"] = previous["softZoning"][
            "baseGeneratorVersion"
        ]
        previous_base.pop("zoningPolicy")
        previous_base.pop("softZoning")
    world = generate_world(
        scene,
        graph,
        seed=seed,
        namespace=namespace,
        previous=previous_base,
        planning=planning,
        outline=outline,
        _route=False,
    )
    base_version = world["generatorVersion"]
    regions = influence_regions(world, scene, graph)
    old_positions = {p["entityId"]: p for p in world["parcels"]}
    owners = {key: p["districtId"] for key, p in old_positions.items()}
    pairs = dependency_pairs(graph, owners)
    paths = {e["id"]: e.get("path", "") for e in graph["entities"]}
    grouped, _ = groups(scene)
    old_ids = (
        {p["entityId"] for p in previous.get("parcels", [])}
        if previous and previous.get("zoningPolicy") == "soft"
        else set()
    )
    reports, placed = [], []
    for district in world["districts"]:
        key = district["id"]
        addresses = [p for p in world["parcels"] if p["districtId"] == key]
        targets = {
            identity: z["anchor"]
            for z in regions
            if z["parentId"] == key and z["clusterKey"] != "GENERAL_MIXED"
            for identity in z["referenceEntityIds"]
        }
        local_pairs = {(a, b): w for (a, b), w in pairs.items() if owners[a] == key}
        pinned = old_ids if key in world["anchors"]["reusedDistrictIds"] else set()
        assignment, report = optimize_addresses(
            addresses, local_pairs, targets, district["localSeed"], pinned
        )
        sites = [
            dict(
                id=p["slotId"],
                center=p["center"],
                angle=p["angle"],
                polygon=p["parcel"],
                entrance=p["entrance"],
                streetPoint=p["streetPoint"],
                laneId=p["blockId"].split(":block:", 1)[1],
                **{
                    field: p[field]
                    for field in ("blockProfile", "planningRegionId")
                    if field in p
                },
            )
            for p in addresses
        ]
        result = populate(
            grouped[key], sites, key, paths, district["localSeed"], assignment
        )
        if result is None:
            raise ValueError("soft zoning lost an occupied address")
        placed.extend(result)
        reports.append(dict(districtId=key, **report))
    by_region = defaultdict(list)
    entities = {e["id"]: e for e in graph["entities"]}
    for parcel in placed:
        parcel["zoneId"] = influence_owner(parcel, regions)
        by_region[parcel["zoneId"]].append(parcel["entityId"])
    for region in regions:
        region["memberEntityIds"] = sorted(by_region[region["id"]])
        region["memberClaims"] = [
            dict(entityId=key, roles=copy.deepcopy(entities[key].get("roles", [])))
            for key in region["memberEntityIds"]
            if entities[key].get("roles")
        ]
    world["parcels"] = sorted(placed, key=lambda p: p["entityId"])
    world["routing"], world["networks"], world["coverage"] = route_world(
        graph, placed, world["streets"]
    )
    world.update(
        generatorVersion="flat-soft-zoning/0.1",
        zoningPolicy="soft",
        softZoning=dict(
            version=VERSION,
            baseGeneratorVersion=base_version,
            zones=regions,
            optimization=reports,
            addressDigest=address_digest(world["parcels"]),
        ),
    )
    return world


def validate_soft(world, scene, graph):
    if world.get("zoningPolicy") != "soft":
        if "softZoning" in world:
            raise ValueError("soft zoning data lacks explicit policy")
        return
    data = world.get("softZoning", {})
    if (
        not isinstance(data, dict)
        or data.get("version") != VERSION
        or not 1 <= len(data.get("zones", [])) <= 448
    ):
        raise ValueError("invalid soft zoning contract")
    if data.get("addressDigest") != address_digest(world["parcels"]):
        raise ValueError("soft zoning occupied address digest mismatch")
    reports = data.get("optimization", [])
    if sorted(r["districtId"] for r in reports) != sorted(
        d["id"] for d in world["districts"]
    ):
        raise ValueError("soft zoning optimizer district mismatch")
    for report in reports:
        if any(
            not math.isfinite(report[key]) or report[key] < 0
            for key in (
                "energyBefore",
                "energyAfter",
                "meanDependencyDistanceBefore",
                "meanDependencyDistanceAfter",
                "sourcePairCount",
                "optimizedPairCount",
                "candidateEvaluations",
                "scoreTerms",
                "swaps",
                "movedBuildings",
                "pinnedBuildings",
            )
        ):
            raise ValueError("soft zoning invalid optimizer measurements")
        if (
            report["energyAfter"] > report["energyBefore"] + 1e-6
            or report["optimizedPairCount"] > report["sourcePairCount"]
        ):
            raise ValueError("soft zoning optimizer invalid energy or pair count")
    regions = influence_regions(world, scene, graph)
    stored = {z["id"]: z for z in data["zones"]}
    if len(stored) != len(data["zones"]) or set(stored) != {z["id"] for z in regions}:
        raise ValueError("soft influence identity mismatch")
    for expected in regions:
        actual = stored[expected["id"]]
        for key, value in expected.items():
            if (
                key not in ("memberEntityIds", "memberClaims")
                and actual.get(key) != value
            ):
                raise ValueError("soft influence source evidence or geometry mismatch")
    occupants = defaultdict(list)
    for p in world["parcels"]:
        if p.get("zoneId") != influence_owner(p, regions):
            raise ValueError("soft influence address ownership mismatch")
        occupants[p["zoneId"]].append(p["entityId"])
    entities = {e["id"]: e for e in graph["entities"]}
    for key, region in stored.items():
        expected_ids = sorted(occupants[key])
        claims = [
            dict(entityId=key, roles=entities[key].get("roles", []))
            for key in expected_ids
            if entities[key].get("roles")
        ]
        if (
            region["memberEntityIds"] != expected_ids
            or region["memberClaims"] != claims
        ):
            raise ValueError("soft influence occupants or source claims mismatch")
