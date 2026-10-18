"""Flat capacity world: independent physical geography, immutable source facts."""

import math

from scripts.canonical_json import sha256_digest
from scripts.validate_city import validate_document
from metropogits.street_diagonals import hull
from . import VERSION
from .geometry import area, centroid, partition, point, shared_boundaries
from .infrastructure import atomic_streets, route_world
from .planning import demand, groups, populate, slots
from .seed import ALGORITHM, derive, draw, world_seed


def generate_world(scene, graph, *, seed=None, namespace=None, previous=None):
    if previous is not None:
        if (
            not isinstance(previous, dict)
            or not isinstance(previous.get("districts"), list)
            or not isinstance(previous.get("parcels"), list)
        ):
            raise ValueError("invalid previous world structure")
        if len(previous["districts"]) > 64 or len(previous["parcels"]) > 10000:
            raise ValueError("previous world resource limit")
        if any(
            not isinstance(d, dict) or not isinstance(d.get("id"), str)
            for d in previous["districts"]
        ):
            raise ValueError("invalid previous world district")
        if any(
            not isinstance(p, dict)
            or not isinstance(p.get("entityId"), str)
            or not isinstance(p.get("slotId"), str)
            for p in previous["parcels"]
        ):
            raise ValueError("invalid previous world parcel")
        polygons = [previous.get("envelope", [])] + [
            d.get("polygon", []) if isinstance(d, dict) else []
            for d in previous["districts"]
        ]
        for polygon in polygons:
            if (
                not isinstance(polygon, list)
                or not 3 <= len(polygon) <= 512
                or any(
                    not isinstance(p, (list, tuple))
                    or len(p) != 2
                    or any(
                        not isinstance(v, (int, float))
                        or isinstance(v, bool)
                        or not math.isfinite(v)
                        or abs(v) > 100000
                        for v in p
                    )
                    for p in polygon
                )
            ):
                raise ValueError("invalid previous world polygon")
    errors = validate_document(scene, graph)
    if errors:
        raise ValueError("invalid world input: " + "; ".join(errors[:3]))
    grouped, _ = groups(scene)
    if not grouped:
        raise ValueError("world requires at least one analyzed source file")
    identity = namespace or graph["repository"]["id"]
    resolved_seed = world_seed(identity, seed)
    entity_paths = {e["id"]: e.get("path", "") for e in graph["entities"]}
    budgets = {k: demand(v) for k, v in grouped.items()}
    # A tiny corner district still needs a complete frontage/circulation cell.
    # Budget it locally rather than inflating every large district to repair it.
    if len(grouped) > 1:
        for budget in budgets.values():
            extra = max(0, 3000 - budget["total"])
            budget["boundaryReserve"] += extra
            budget["total"] += extra
    labels = {e["id"]: e.get("path", ".") for e in graph["entities"]}
    compatible = bool(
        previous
        and previous.get("schemaVersion") == VERSION
        and previous.get("seed") == resolved_seed
        and previous.get("repositoryNamespace") == identity
        and set(d["id"] for d in previous.get("districts", [])) == set(grouped)
    )
    old_districts = {d["id"]: d for d in previous["districts"]} if compatible else {}
    old_parcels = (
        {p["entityId"]: p["slotId"] for p in previous["parcels"]} if compatible else {}
    )
    repairs = []
    if previous and not compatible:
        repairs.append(
            dict(
                reason="incompatible previous world; deterministic cold rebuild",
                districtIds=sorted(grouped),
            )
        )
    for attempt in range(5):
        if attempt == 0 and compatible:
            polygons = {k: old_districts[k]["polygon"] for k in grouped}
            envelope = previous["envelope"]
        else:
            # Seeded affine octagon remains convex and has a readable wide silhouette.
            rotation = (draw(resolved_seed) - 0.5) * 0.7
            envelope = [
                point(
                    [
                        math.cos(rotation) * math.cos(t) * 1.25
                        - math.sin(rotation) * math.sin(t) * 0.8,
                        math.sin(rotation) * math.cos(t) * 1.25
                        + math.cos(rotation) * math.sin(t) * 0.8,
                    ]
                )
                for t in (2 * math.pi * i / 12 for i in range(12))
            ]
            radius = math.sqrt(
                sum(b["total"] for b in budgets.values()) / area(envelope)
            )
            envelope = [point([v * radius for v in p]) for p in envelope]
            polygons = partition(
                envelope,
                [(k, budgets[k]["total"]) for k in grouped],
                derive(resolved_seed, "district-topology"),
            )
        polygons, envelope = shared_boundaries(polygons, envelope)
        envelope = list(
            reversed(hull([p for polygon in polygons.values() for p in polygon]))
        )
        districts = []
        parcels = []
        raw = []
        failed = []
        for key, members in grouped.items():
            local_seed = derive(
                resolved_seed,
                "district",
                labels.get(key, "." if key.endswith(":directory:.") else key),
            )
            candidates, lanes, angle = slots(polygons[key], local_seed)
            placed = populate(
                members,
                candidates,
                key,
                entity_paths,
                local_seed,
                old_parcels if attempt == 0 and compatible else None,
            )
            if placed is None:
                failed.append(key)
                continue
            parcels += placed
            poly = polygons[key]
            districts.append(
                dict(
                    id=key,
                    sourceDirectoryId=key,
                    label=labels.get(
                        key, "Root" if key.endswith(":directory:.") else key
                    ),
                    polygon=poly,
                    anchor=point(centroid(poly)),
                    localSeed=local_seed,
                    planningProfile="GRID",
                    primaryAxis=angle,
                    areaDemand=budgets[key],
                    areaAllocated=area(poly),
                    capacity=len(candidates),
                    buildingCount=len(members),
                )
            )
            for a, b in zip(poly, poly[1:] + poly[:1]):
                raw.append(dict(start=a, end=b, width=3.5, access=False))
            raw.extend(lanes)
            for p in placed:
                raw.append(
                    dict(
                        start=p["entrance"],
                        end=p["streetPoint"],
                        width=0.7,
                        access=True,
                    )
                )
        if not failed:
            break
        repairs.append(
            dict(
                attempt=attempt,
                reason="insufficient frontage capacity",
                districtIds=failed,
            )
        )
        for key in failed:
            extra = budgets[key]["total"] * 0.5
            budgets[key]["repairReserve"] = budgets[key].get("repairReserve", 0) + extra
            budgets[key]["total"] += extra
    else:
        raise ValueError(
            "world parcel capacity infeasible after bounded envelope repair"
        )
    streets = atomic_streets(raw)
    routing, networks, coverage = route_world(graph, parcels, streets)
    reused = sorted(grouped) if compatible and attempt == 0 else []
    topology = {}
    for d in districts:
        for a, b in zip(d["polygon"], d["polygon"][1:] + d["polygon"][:1]):
            edge = tuple(sorted((tuple(a), tuple(b))))
            topology.setdefault(edge, []).append(d["id"])
    logical = [
        dict(id=d["id"], parentId=d["parentId"])
        for d in sorted(scene["districts"], key=lambda d: d["id"])
    ]
    return dict(
        schemaVersion=VERSION,
        generatorVersion="flat-capacity/0.1",
        seed=resolved_seed,
        seedAlgorithm=ALGORITHM,
        repositoryNamespace=identity,
        sourceCityDigest=sha256_digest(scene),
        ucgDigest=sha256_digest(graph),
        coordinateSystem="x-z-ground-y-up",
        coordinateQuantum=0.0001,
        terrainPreset="flat",
        allocationAlgorithm="capacity-bisection/0.1",
        envelope=envelope,
        districts=districts,
        logicalDistricts=logical,
        topology=dict(
            edges=[
                dict(
                    id="world:boundary:" + derive(str(a), str(b)),
                    start=list(a),
                    end=list(b),
                    districtIds=sorted(ids),
                )
                for (a, b), ids in sorted(topology.items())
            ]
        ),
        parcels=sorted(parcels, key=lambda p: p["entityId"]),
        streets=streets,
        routing=routing,
        networks=networks,
        coverage=coverage,
        diagnostics=repairs,
        anchors=dict(
            reusedDistrictIds=reused,
            replannedDistrictIds=sorted(set(grouped) - set(reused)),
        ),
    )
