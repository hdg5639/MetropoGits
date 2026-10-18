"""Physical source neighborhoods with pre-parcel roads and block-local plans."""

import math

from .affinity import optimize_addresses
from .blocks import road_block_plan, TARGET_FILES
from .geometry import area, centroid, inset, partition, point, shared_boundaries
from .hybrid import hybrid_slots, hybrid_regions
from .industrial import industrial_slots
from .organic import organic_slots
from .planning import demand, populate
from .power import power_partition
from .radial import radial_slots
from .seed import derive
from .zone_access import access_corridors
from .zoning import zoning_grid_slots


def neighborhood_demand(clusters, members):
    by_id = {b["entityId"]: b for b in members}
    result = []
    for cluster in clusters:
        budget = demand(
            [by_id[key] for key in cluster["memberEntityIds"]],
            cluster["requestedProfile"],
        )
        budget["blockReserve"] = 1600 * (
            math.ceil(len(cluster["memberEntityIds"]) / TARGET_FILES) - 1
        )
        budget["total"] += budget["blockReserve"]
        result.append(budget)
    return {
        key: sum(b.get(key, 0) for b in result)
        for key in sorted(set().union(*(b.keys() for b in result)))
    }


def local_profile(cluster, policy, seed):
    from .generator import requested_profile

    if cluster["requestedProfile"] != "GRID":
        return cluster["requestedProfile"]
    profile = requested_profile(policy, derive(seed, cluster["id"], "local-character"))
    # Avoid repeating a whole orbital stencil in every ordinary block. Radial
    # frontage remains available for actual entrypoint neighborhoods.
    return "HYBRID" if profile == "RADIAL" else profile


def plan_neighborhoods(
    polygon,
    clusters,
    members,
    seed,
    paths,
    pairs,
    policy,
    previous_zones=(),
    previous_blocks=(),
    previous_slots=None,
):
    by_id = {b["entityId"]: b for b in members}
    old = {z["id"]: z for z in previous_zones}
    reuse = set(old) == {z["id"] for z in clusters}
    demands = [
        (
            z["id"],
            neighborhood_demand([z], [by_id[k] for k in z["memberEntityIds"]])["total"],
        )
        for z in clusters
    ]
    if reuse:
        polygons = {key: z["polygon"] for key, z in old.items()}
        allocation = dict(
            algorithm="previous-anchors/0.1", iterations=0, maxRelativeAreaError=0
        )
    else:
        polygons, allocation = power_partition(
            polygon, demands, derive(seed, "neighborhood-land")
        )
    diagnostics = []
    for attempt in range(3):
        total_demand = sum(value for _, value in demands)
        targets = {key: area(polygon) * value / total_demand for key, value in demands}
        allocation = dict(
            allocation,
            maxRelativeAreaError=max(
                abs(area(polygons[key]) - target) / target
                for key, target in targets.items()
            ),
        )
        blocks, backbone, ports = road_block_plan(
            clusters,
            polygons,
            by_id,
            pairs,
            seed,
            polygon,
            previous_blocks if reuse else (),
        )
        if reuse and not all(b["reused"] for b in blocks):
            diagnostics.append(
                dict(
                    reason="block capacity or membership changed; local block replanning inside retained neighborhood",
                    blockIds=[b["id"] for b in blocks if not b["reused"]],
                )
            )
        placed, local, failed = [], {}, []
        capacities = {z["id"]: 0 for z in clusters}
        cluster_by_id = {z["id"]: z for z in clusters}
        for block in blocks:
            zone = cluster_by_id[block["zoneId"]]
            local_seed = derive(seed, block["id"], "frontage")
            profile = (
                block.get("planningProfile")
                if block["reused"]
                else local_profile(zone, policy, seed)
            )
            requested = profile
            planners = {
                "GRID": zoning_grid_slots,
                "ORGANIC": organic_slots,
                "RADIAL": radial_slots,
                "INDUSTRIAL": industrial_slots,
                "HYBRID": hybrid_slots,
            }
            certificate = zoning_grid_slots(block["polygon"], local_seed)
            capacities[zone["id"]] += len(certificate[0])
            # Only this grammar-independent capacity certificate may trigger
            # upstream land repair. A local style failure uses the certified
            # fallback on the SAME block, never changes the main road plan.
            if len(certificate[0]) < len(block["memberEntityIds"]) and not reuse:
                failed.append(zone["id"])
                continue
            choices, roads, angle = (
                certificate
                if profile == "GRID"
                else planners[profile](block["polygon"], local_seed)
            )
            if (
                len(choices) < len(block["memberEntityIds"])
                and profile != "GRID"
                and not reuse
            ):
                diagnostics.append(
                    dict(
                        reason=f"{profile.lower()} block capacity insufficient; explicit local GRID fallback",
                        blockIds=[block["id"]],
                    )
                )
                profile = "GRID"
                choices, roads, angle = certificate
            for slot in choices:
                slot.update(
                    id=block["id"] + ":" + slot["id"],
                    laneId=block["id"] + ":" + slot["laneId"],
                    polygon=[point(p) for p in inset(slot["polygon"], 0.01)],
                )
                if profile != "HYBRID":
                    slot["blockProfile"] = profile
            block.update(
                planningSeed=local_seed,
                planningProfile=profile,
                requestedProfile=requested,
                capacity=len(choices),
                primaryAxis=angle,
            )
            if profile == "HYBRID":
                block["planningRegions"] = hybrid_regions(block["polygon"], local_seed)
            entities = set(block["memberEntityIds"])
            population = [by_id[k] for k in sorted(entities)]
            records = populate(
                population,
                choices,
                zone["parentId"],
                paths,
                local_seed,
                previous_slots if reuse else None,
            )
            if records is None:
                failed.append(zone["id"])
                continue
            local_pairs = {
                (a, b): w
                for (a, b), w in pairs.items()
                if a in entities and b in entities
            }
            assignment, report = optimize_addresses(
                records,
                local_pairs,
                {},
                local_seed,
                (previous_slots or {}) if reuse else (),
            )
            records = populate(
                population, choices, zone["parentId"], paths, local_seed, assignment
            )
            for parcel in records:
                parcel.update(zoneId=zone["id"], blockId=block["id"])
            block["affinity"] = report
            placed.extend(records)
            local[block["id"]] = roads
        if not failed:
            lanes = list(backbone)
            for zone in clusters:
                children = [b for b in blocks if b["zoneId"] == zone["id"]]
                child_polys = {b["id"]: b["polygon"] for b in children}
                joins = {
                    b["id"]: local[b["id"]]
                    + backbone
                    + [dict(start=p, end=p) for p in ports[zone["id"]]]
                    for b in children
                }
                lanes += access_corridors(child_polys, joins, polygons[zone["id"]])
                for b in children:
                    lanes.extend(local[b["id"]])
            records = [
                dict(
                    z,
                    polygon=polygons[z["id"]],
                    anchor=point(centroid(polygons[z["id"]])),
                    planningSeed=derive(seed, z["id"], "neighborhood"),
                    planningProfile="BLOCK_LOCAL",
                    areaDemand=neighborhood_demand(
                        [z], [by_id[k] for k in z["memberEntityIds"]]
                    ),
                    areaAllocated=area(polygons[z["id"]]),
                    areaTarget=targets[z["id"]],
                    capacity=sum(
                        b["capacity"] for b in blocks if b["zoneId"] == z["id"]
                    ),
                    allocation=allocation,
                    accessPorts=ports[z["id"]],
                )
                for z in clusters
            ]
            return placed, lanes, records, diagnostics, reuse, blocks, backbone
        diagnostics.append(
            dict(
                reason="neighborhood/block frontage capacity repair",
                zoneIds=sorted(set(failed)),
                attempt=attempt,
            )
        )
        if reuse:
            reuse = False
        elif attempt == 0:
            counts = {z["id"]: len(z["memberEntityIds"]) for z in clusters}
            demands = [
                (
                    key,
                    value
                    * max(0.65, min(2.5, counts[key] * 1.15 / max(1, capacities[key]))),
                )
                for key, value in demands
            ]
            polygons, allocation = power_partition(
                polygon, demands, derive(seed, "neighborhood-capacity")
            )
        else:
            polygons = partition(
                polygon, sorted(demands), derive(seed, "neighborhood-simple-fallback")
            )
            polygons, _ = shared_boundaries(polygons, polygon)
            allocation = dict(
                algorithm="capacity-bisection/0.1",
                iterations=0,
                maxRelativeAreaError=0,
                fallbackReason="frontage capacity",
            )
    return None, [], [], diagnostics, False, [], []
