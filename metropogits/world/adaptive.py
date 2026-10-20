"""Sparse shared pattern skeleton, source-mixed locally adapted neighborhoods."""

import math
import re
from collections import defaultdict

from metropogits.street_diagonals import overlap
from .affinity import optimize_addresses
from .district_patterns import street_field, sector_slots
from .geometry import area, bounds, centroid, inset, inside, nearest, point, ribbon
from .hybrid import hybrid_regions, hybrid_slots
from .industrial import industrial_slots
from .organic import organic_slots
from .planning import demand, populate, slots
from .power import power_partition
from .radial import _clipped, radial_slots
from .seed import derive
from .zone_access import access_corridors

# Retain the address/identity seed namespace when revising arterial selection.
VERSION = "adaptive-patterns/0.1"
SEAM_VERSION = "adaptive-patterns/0.3"
GENERATOR_VERSION = "flat-adaptive-neighborhoods/0.3"


def adaptive_field(polygon, seed, base, parent, *, stitch=False, morphology=False):
    candidates, roads, pattern = street_field(
        polygon, seed, base, parent, lane_identity=True
    )
    main = skeleton(roads, stitch=stitch, morphology=morphology)
    return (
        candidates,
        roads,
        main,
        dict(
            pattern,
            version=SEAM_VERSION if morphology else "adaptive-patterns/0.2" if stitch else VERSION,
            protectedStreetIds=sorted(r["id"] for r in main),
            fullFieldRoadCount=len(roads),
            roadCount=len(main),
        ),
    )


def skeleton(roads, *, stitch=False, morphology=False):
    if stitch:
        # Avoid a second linear frontage stencil across adapted neighborhoods.
        # Selected orbital families define the parent's morphology: retaining
        # spokes alone erased that identity and rotated whole local grids.
        arteries = [
            r
            for r in roads
            if any(k in r["sourceLaneId"] for k in ("collector:", "spoke:", "spine:"))
            or (morphology and (orbit := re.search(r"orbit:(\d+)", r["sourceLaneId"]))
                and int(orbit[1]) % 4 == 0)
        ]
        if arteries:
            return arteries
    retained = []
    for r in roads:
        key = r["sourceLaneId"]
        row = re.search(r"(?:organic:)?row:(-?\d+)", key)
        orbit = re.search(r"orbit:(\d+)", key)
        court = re.search(r"court:\d+:(-?\d+)", key)
        if (
            "collector:" in key
            or "spoke:" in key
            or "spine:" in key
            or (row and int(row[1]) % 3 == 0)
            or (orbit and int(orbit[1]) % 4 == 0)
            or (court and int(court[1]) % 3 == 0)
        ):
            retained.append(r)
    if not retained and roads:
        retained = [
            max(roads, key=lambda r: (math.dist(r["start"], r["end"]), r["id"]))
        ]
    return retained


def pattern_profiles(zones, base):
    inherited = min(
        zones,
        key=lambda z: (-len(z["memberEntityIds"]), -len(z["internalEdgeIds"]), z["id"]),
    )["id"]
    result = {}
    for z in zones:
        key = z["id"]
        local = base if key == inherited else z["requestedProfile"]
        if key != inherited and local == "GRID":
            local = "ORGANIC" if base in ("GRID", "RADIAL") else "GRID"
        result[key] = local
    return result


def adaptive_demand(clusters, members, base):
    by_id = {b["entityId"]: b for b in members}
    profiles = pattern_profiles(clusters, base)
    budgets = [
        demand([by_id[k] for k in z["memberEntityIds"]], profiles[z["id"]])
        for z in clusters
    ]
    return {key: sum(b[key] for b in budgets) for key in budgets[0]}


def profile_plan(zones, polygons, pattern, backbone):
    result = {}
    for z in zones:
        key = z["id"]
        base = pattern["profile"]
        local = pattern_profiles(zones, base)[key]
        center = centroid(polygons[key])
        road = min(
            backbone,
            key=lambda r: (
                math.dist(center, nearest(center, r["start"], r["end"])),
                r["id"],
            ),
            default=None,
        )
        axis = (
            math.atan2(
                road["end"][1] - road["start"][1], road["end"][0] - road["start"][0]
            )
            if road
            else pattern["primaryAxis"]
        )
        result[key] = dict(
            profile=local, mode="INHERITED" if local == base else "ADAPTED", axis=axis
        )
    return result


def clear_frontage(candidates, roads):
    index, shapes = defaultdict(set), []
    work = entries = 0

    def cells(poly):
        x0, z0, x1, z1 = bounds(poly)
        if max(x1 - x0, z1 - z0) > 10000:
            raise ValueError("adaptive frontage extent limit")
        return [
            (x, z)
            for x in range(math.floor(x0 / 16), math.floor(x1 / 16) + 1)
            for z in range(math.floor(z0 / 16), math.floor(z1 / 16) + 1)
        ]

    for r in roads:
        shape = ribbon(r["start"], r["end"], r["width"])
        keys = cells(shape)
        entries += len(keys)
        if entries > 1_000_000:
            raise ValueError("adaptive frontage index limit")
        for k in keys:
            index[k].add(len(shapes))
        shapes.append(shape)
    result = []
    for s in candidates:
        blocked = False
        for i in sorted({i for k in cells(s["polygon"]) for i in index[k]}):
            work += 1
            if work > 5_000_000:
                raise ValueError("adaptive frontage work limit")
            if overlap(s["polygon"], shapes[i]):
                blocked = True
                break
        if not blocked:
            result.append(s)
    return result


def local_sites(polygon, seed, selection, parent_candidates, parent_roads, backbone):
    profile = selection["profile"]
    if selection["mode"] == "INHERITED":
        candidates = [
            s
            for s in sector_slots(parent_candidates, polygon)
            if inside(s["streetPoint"], polygon)
        ]
        roads = [
            dict(r, start=path[0], end=path[1])
            for r in parent_roads
            if (path := _clipped(r["start"], r["end"], polygon))
        ]
        return candidates, roads, selection["axis"], None
    planner = {
        "GRID": slots,
        "ORGANIC": organic_slots,
        "RADIAL": radial_slots,
        "INDUSTRIAL": industrial_slots,
        "HYBRID": hybrid_slots,
    }[profile]
    kwargs = {} if profile == "RADIAL" else dict(axis=selection["axis"])
    if profile in ("GRID", "ORGANIC", "HYBRID"):
        # Shared collectors were already reserved. Do not overlay a second
        # automatic transverse grid and then enlarge land to fit around both.
        kwargs["collectors"] = False
    candidates, roads, angle = planner(polygon, seed, **kwargs)
    for s in candidates:
        s.update(
            id=derive(seed, "site") + ":" + s["id"],
            polygon=[point(p) for p in inset(s["polygon"], 0.01)],
        )
        if profile != "HYBRID":
            s["blockProfile"] = profile
    return (
        clear_frontage(candidates, backbone),
        roads,
        angle,
        hybrid_regions(polygon, seed) if profile == "HYBRID" else None,
    )


def access_plan(polygons, local, main, parent_polygon, pattern, zones, pairs):
    joins = {
        key: roads
        + [
            dict(r, start=p[0], end=p[1])
            for r in main
            if (p := _clipped(r["start"], r["end"], polygons[key]))
        ]
        for key, roads in local.items()
    }
    owners = {key: z["id"] for z in zones for key in z["memberEntityIds"]}
    affinity = defaultdict(float)
    for (a, b), weight in pairs.items():
        if a in owners and b in owners and owners[a] != owners[b]:
            affinity[tuple(sorted((owners[a], owners[b])))] += weight
    boundary, ports = access_corridors(
        polygons, joins, parent_polygon, return_ports=True, affinity=affinity
    )
    roads = [
        dict(
            r,
            id="world:backbone:"
            + derive(pattern["parentId"], str(r["start"]), str(r["end"]), VERSION),
            structural=True,
            patternId=pattern["id"],
        )
        for r in boundary
    ]
    return roads, ports


def reserve_complete_plan(plans, polygons, main, parent_polygon, pattern, zones, pairs):
    local = {key: p[1] for key, p in plans.items()}
    boundary, ports = access_plan(
        polygons, local, main, parent_polygon, pattern, zones, pairs
    )
    physical = main + boundary + [r for roads in local.values() for r in roads]
    if sum(len(p[0]) for p in plans.values()) > 100_000 or len(physical) > 20_000:
        raise ValueError("adaptive plan candidate/street resource limit")
    valid = {
        p["id"]
        for p in clear_frontage(
            [p for plan in plans.values() for p in plan[0]], physical
        )
    }
    return (
        {
            key: ([s for s in p[0] if s["id"] in valid], *p[1:])
            for key, p in plans.items()
        },
        boundary,
        ports,
    )


def retained_addresses(population, original, choices, parent, paths, seed, pairs):
    """Keep surviving reference addresses when a few vacant lots become streets."""
    reference = populate(population, original, parent, paths, seed)
    baseline, _ = optimize_addresses(reference, pairs, {}, seed)
    available = {s["id"] for s in choices}
    return {entity: slot for entity, slot in baseline.items() if slot in available}


def plan_adaptive(
    polygon,
    clusters,
    members,
    seed,
    paths,
    pairs,
    base,
    previous_zones=(),
    previous_blocks=(),
    previous_slots=None,
    terrain=None,
    porous=False,
    campus=False,
    campus_pairs=None,
    campus_style="quad",
):
    parent = clusters[0]["parentId"]
    parent_candidates, parent_roads, main, pattern = adaptive_field(
        polygon, seed, base, parent, stitch=True, morphology=True
    )
    by_id = {b["entityId"]: b for b in members}
    profiles = pattern_profiles(clusters, base)
    demands = [
        (
            z["id"],
            demand([by_id[k] for k in z["memberEntityIds"]], profiles[z["id"]])[
                "total"
            ],
        )
        for z in clusters
    ]
    old = {z["id"]: z for z in previous_zones}
    reuse = set(old) == {z["id"] for z in clusters}
    notes = []
    for attempt in range(4):
        if reuse:
            polygons = {key: z["polygon"] for key, z in old.items()}
            allocation = dict(algorithm="previous-anchors/0.1", iterations=0)
        else:
            polygons, allocation = power_partition(
                polygon, demands, derive(seed, "functional-land")
            )
        invalid = [
            key
            for key, poly in polygons.items()
            if not all(inside(p, poly, -0.001) and inside(p, polygon, -0.001) for p in poly)
        ]
        if invalid:
            notes.append(
                dict(
                    reason="adaptive shared-cut quantization repair",
                    zoneIds=invalid,
                    attempt=attempt,
                )
            )
            # A quantized T vertex can make a supporting edge slightly concave.
            # Move the shared cut, not its tolerance; spend the existing local
            # attempts before asking the parent for more land.
            reuse = False
            demands = [
                (key, value * (1.002 if key in invalid else 1))
                for key, value in demands
            ]
            continue
        selections = profile_plan(clusters, polygons, pattern, skeleton(parent_roads))
        plans = {
            z["id"]: local_sites(
                polygons[z["id"]],
                derive(seed, z["id"], VERSION),
                selections[z["id"]],
                parent_candidates,
                parent_roads,
                main,
            )
            for z in clusters
        }
        plans, boundary, ports = reserve_complete_plan(
            plans, polygons, main, polygon, pattern, clusters, pairs
        )
        actual_main, actual_pattern = main, pattern
        if terrain:
            from .terrain import terrain_plan

            plans, actual_main, boundary, ports, actual_pattern = terrain_plan(
                plans, main, boundary, ports, pattern, polygon, terrain
            )
        unreserved_plans = plans
        if porous:
            from .permeability import reserve_links

            plans, actual_main, actual_pattern = reserve_links(
                plans, actual_main, boundary, polygon, actual_pattern,
                {z["id"]: len(z["memberEntityIds"]) for z in clusters}, terrain,
            )
        failed = [
            z["id"]
            for z in clusters
            if len(plans[z["id"]][0]) < len(z["memberEntityIds"])
        ]
        if not failed:
            break
        notes.append(
            dict(
                reason="adaptive neighborhood frontage capacity repair; no silent grammar substitution",
                zoneIds=failed,
                attempt=attempt,
                capacities={
                    z["id"]: dict(
                        required=len(z["memberEntityIds"]),
                        available=len(plans[z["id"]][0]),
                        profile=selections[z["id"]]["profile"],
                    )
                    for z in clusters
                    if z["id"] in failed
                },
            )
        )
        if reuse:
            reuse = False
        else:
            counts = {z["id"]: len(z["memberEntityIds"]) for z in clusters}
            demands = [
                (
                    key,
                    value
                    * max(
                        0.75,
                        min(
                            1.7,
                            math.sqrt((counts[key] + 2) / max(1, len(plans[key][0]))),
                        ),
                    ),
                )
                for key, value in demands
            ]
    else:
        return None, [], [], notes, False, [], [], pattern
    # First finish the original capacity repairs. An optional pocket must not
    # rescue an earlier allocation attempt and change unrelated zone boundaries.
    campus_decisions, campus_sites = {}, {}
    if campus:
        from .campus import apply_campuses

        campus_decisions, campus_sites = apply_campuses(
            plans, selections, clusters, polygons, seed, actual_main + boundary, terrain,
            campus_pairs if campus_pairs is not None else pairs, campus_style)
    main = actual_main + boundary
    pattern = actual_pattern
    if campus_sites:
        walks = [w for site in campus_sites.values() for w in site['walkways']]
        for w in walks:
            w['patternId'] = pattern['id']
        main += walks
        pattern = dict(pattern, campusWalkwayCount=len(walks), roadCount=pattern['roadCount']+len(walks),
                       protectedStreetIds=sorted(set(pattern['protectedStreetIds'])|{w['id'] for w in walks}))
    parcels, records, blocks = [], [], []
    total = sum(v for _, v in demands)
    targets = {key: area(polygon) * v / total for key, v in demands}
    allocation = dict(
        allocation,
        maxRelativeAreaError=max(
            abs(area(polygons[k]) - v) / v for k, v in targets.items()
        ),
    )
    for z in clusters:
        key = z["id"]
        choices, roads, angle, regions = plans[key]
        ids = set(z["memberEntityIds"])
        population = [by_id[k] for k in sorted(ids)]
        local_seed = derive(seed, key, VERSION)
        local_pairs = {(a, b): w for (a, b), w in pairs.items() if a in ids and b in ids}
        preferred = previous_slots if reuse else None
        if porous and not reuse and len(choices) < len(unreserved_plans[key][0]):
            # Removing a few vacant candidates changes the modulo-based address
            # order. Retain surviving baseline addresses instead of rerolling an
            # entire neighborhood. This reference assignment happens only after
            # the final physical corridors have been reserved.
            preferred = retained_addresses(
                population, unreserved_plans[key][0], choices, parent, paths, local_seed, local_pairs
            )
        if key in campus_sites:
            campus_ids = set(campus_sites[key]['memberEntityIds'])
            if campus_style in ('neighborhood','landscape','organic','fabric','programmed'):
                preferred = dict(preferred or {})
                preferred.update(campus_sites[key]['anchorSlots'])
            placed = []
            for is_campus in (False,True):
                selected_population = [b for b in population if (b['entityId'] in campus_ids)==is_campus]
                selected_choices = [s for s in choices if (s.get('blockProfile')=='CAMPUS')==is_campus]
                if not selected_population:
                    continue
                portion = populate(selected_population,selected_choices,parent,paths,local_seed,preferred)
                fixed_pairs = {(a,b):w for (a,b),w in local_pairs.items()
                               if a in {p['entityId'] for p in portion} and b in {p['entityId'] for p in portion}}
                assignment, _ = optimize_addresses(portion,fixed_pairs,{},local_seed,preferred or ())
                placed.extend(populate(selected_population,selected_choices,parent,paths,local_seed,assignment))
            placed.sort(key=lambda p:p['entityId'])
            affinity = dict(algorithm='campus-fixed-members/0.1', preservedMembers=True)
        else:
            placed = populate(
                population, choices, parent, paths, local_seed, preferred)
            assignment, affinity = optimize_addresses(
                placed, local_pairs, {}, local_seed, preferred or ())
            placed = populate(population, choices, parent, paths, local_seed, assignment)
        block_id = "world:block:" + derive(key, VERSION)
        for p in placed:
            p.update(zoneId=key, blockId=block_id)
        poly = polygons[key]
        block = dict(
            id=block_id,
            zoneId=key,
            memberEntityIds=z["memberEntityIds"],
            polygon=poly,
            anchor=point(centroid(poly)),
            areaAllocated=area(poly),
            boundaryTypes=["NEIGHBORHOOD_BOUNDARY"] * len(poly),
            planningSeed=local_seed,
            planningProfile=selections[key]["profile"],
            requestedProfile=selections[key]["profile"],
            capacity=len(choices),
            primaryAxis=angle,
            inheritedPatternId=pattern["id"],
            patternMode=selections[key]["mode"],
            reused=reuse,
            affinity=affinity,
        )
        if campus:
            block['campusDecision'] = campus_decisions[key]
        if key in campus_sites:
            block.update(urbanGrammar='CAMPUS' if campus_style in ('neighborhood','landscape','organic','fabric','programmed') else 'MIXED_CAMPUS',campusSite=campus_sites[key])
        if regions:
            block["planningRegions"] = regions
        elif selections[key]["mode"] == "INHERITED" and base == "HYBRID":
            from metropogits.block_orientation import clip

            block["planningRegions"] = [
                dict(r, polygon=[point(p) for p in part], areaAllocated=area(part))
                for r in pattern["regions"]
                if len(part := clip(r["polygon"], poly)) >= 3 and area(part) > 0.001
            ]
        blocks.append(block)
        parcels.extend(placed)
        records.append(
            dict(
                z,
                polygon=poly,
                anchor=point(centroid(poly)),
                planningSeed=local_seed,
                planningProfile="BLOCK_LOCAL",
                areaDemand=demand(population, selections[key]["profile"]),
                areaAllocated=area(poly),
                areaTarget=targets[key],
                capacity=len(choices),
                allocation=allocation,
                accessPorts=[list(p) for p in sorted(ports[key])],
            )
        )
    lanes = main + [r for plan in plans.values() for r in plan[1]]
    return (
        parcels,
        lanes,
        records,
        notes,
        reuse,
        blocks,
        sorted(main, key=lambda r: r["id"]),
        pattern,
    )
