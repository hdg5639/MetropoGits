"""Flat capacity world: independent physical geography, immutable source facts."""

import math

from scripts.canonical_json import sha256_digest
from scripts.validate_city import validate_document
from metropogits.street_diagonals import hull
from . import VERSION
from .geometry import area, centroid, inside, partition, point, shared_boundaries
from .infrastructure import atomic_streets, route_world
from .seams import stitch_unused_streets
from .junctions import (
    GENERATOR_VERSION as SHARED_GENERATOR_VERSION,
    check_trip_budgets,
    consolidate_junctions,
    path_length,
)
from .alleys import GENERATOR_VERSION as ALLEY_GENERATOR_VERSION, add_alleys
from .terrain import (
    GENERATOR_VERSION as TERRAIN_GENERATOR_VERSION, PRESET as NATURAL_PRESET,
    adapt_roads, generate_terrain, validate_terrain,
)
from .rivers import GENERATOR_VERSION as RIVER_GENERATOR_VERSION, PRESET as RIVER_PRESET, annotate_crossings
from .elevation import GENERATOR_VERSION as VALLEY_GENERATOR_VERSION, PRESET as VALLEY_PRESET, annotate, build_surface
from .planning import demand, groups, populate, slots
from .radial import radial_slots
from .organic import organic_slots
from .industrial import industrial_slots
from .hybrid import hybrid_slots, hybrid_regions
from .outline import VERSION as OUTLINE_VERSION, varied_outline
from .seed import ALGORITHM, derive, draw, world_seed
from .zoning import (
    VERSION as ZONING_VERSION,
    candidates as zone_candidates,
    plan_zones,
    zone_demand,
)
from .affinity import dependency_pairs
from .neighborhoods import VERSION as NEIGHBORHOOD_VERSION, neighborhood_candidates
from .neighborhood_layout import neighborhood_demand, plan_neighborhoods
from .district_patterns import pattern_demand, plan_district_pattern
from .functional import functional_candidates, VERSION as FUNCTIONAL_VERSION
from .adaptive import (
    GENERATOR_VERSION as ADAPTIVE_GENERATOR_VERSION,
    plan_adaptive,
    adaptive_demand,
)


def requested_profile(planning, seed):
    if planning == "mixed":
        return "RADIAL" if draw(derive(seed, "planning-profile")) < 0.5 else "GRID"
    if planning == "varied":
        return ("GRID", "ORGANIC", "RADIAL", "INDUSTRIAL", "HYBRID")[
            int(draw(derive(seed, "varied-profile")) * 5)
        ]
    return planning.upper()


def generate_world(
    scene,
    graph,
    *,
    seed=None,
    namespace=None,
    previous=None,
    planning="grid",
    outline="ellipse",
    zoning="none",
    pattern_scale="block",
    street_policy="original",
    terrain="flat",
    _route=True,
):
    if terrain not in ("flat", NATURAL_PRESET, RIVER_PRESET, VALLEY_PRESET) or (
        terrain != "flat" and (pattern_scale != "adaptive" or not _route)
    ):
        raise ValueError("natural terrain requires routed adaptive neighborhoods")
    if street_policy not in ("original", "shared", "permeable") or (
        street_policy != "original" and (pattern_scale != "adaptive" or not _route)
    ):
        raise ValueError("shared street policy requires routed adaptive neighborhoods")
    if pattern_scale not in ("block", "district", "adaptive") or (
        pattern_scale != "block" and zoning != "neighborhoods"
    ):
        raise ValueError("district pattern scale requires neighborhoods zoning")
    if zoning not in ("none", "semantic", "soft", "neighborhoods"):
        raise ValueError("unsupported world zoning policy")
    if zoning == "soft":
        from .soft import generate_soft_world

        return generate_soft_world(
            scene,
            graph,
            seed=seed,
            namespace=namespace,
            previous=previous,
            planning=planning,
            outline=outline,
        )
    if zoning == "semantic" and planning != "grid":
        raise ValueError(
            "semantic zoning selects neighborhood grammars; use --planning grid (default)"
        )
    if outline not in ("ellipse", "varied"):
        raise ValueError("unsupported world outline policy")
    if planning not in (
        "grid",
        "mixed",
        "radial",
        "organic",
        "industrial",
        "hybrid",
        "varied",
    ):
        raise ValueError("unsupported world planning policy")
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
        if "zoning" in previous:
            recorded = previous["zoning"]
            if (
                not isinstance(recorded, dict)
                or not isinstance(recorded.get("zones"), list)
                or not 1 <= len(recorded["zones"]) <= 448
                or any(
                    not isinstance(z, dict)
                    or not isinstance(z.get("id"), str)
                    or not isinstance(z.get("parentId"), str)
                    or z.get("planningProfile")
                    not in ("GRID", "ORGANIC", "RADIAL", "INDUSTRIAL", "BLOCK_LOCAL")
                    for z in recorded["zones"]
                )
            ):
                raise ValueError("invalid previous world zoning structure")
            if "blocks" in recorded and (
                not isinstance(recorded["blocks"], list)
                or len(recorded["blocks"]) > 1024
                or any(
                    not isinstance(b, dict)
                    or not isinstance(b.get("zoneId"), str)
                    or not isinstance(b.get("memberEntityIds"), list)
                    or len(b["memberEntityIds"]) > 10000
                    for b in recorded["blocks"]
                )
            ):
                raise ValueError("invalid previous world block structure")
            polygons.extend(z.get("polygon", []) for z in recorded["zones"])
            polygons.extend(b.get("polygon", []) for b in recorded.get("blocks", []))
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
    labels = {e["id"]: e.get("path", ".") for e in graph["entities"]}
    local_seeds = {
        k: derive(
            resolved_seed,
            "district",
            labels.get(k, "." if k.endswith(":directory:.") else k),
        )
        for k in grouped
    }
    requested = {k: requested_profile(planning, local_seeds[k]) for k in grouped}
    budgets = {k: demand(v, requested[k]) for k, v in grouped.items()}
    clusters = {}
    zoned = zoning in ("semantic", "neighborhoods")
    if zoned:
        entities = {e["id"]: e for e in graph["entities"]}
        clusters = {
            k: functional_candidates(v, entities, k, graph)
            if pattern_scale == "adaptive"
            else neighborhood_candidates(v, entities, k, graph)
            if zoning == "neighborhoods"
            else zone_candidates(v, entities, k)
            for k, v in grouped.items()
        }
        budgets = {
            k: (
                neighborhood_demand
                if zoning == "neighborhoods" and pattern_scale != "adaptive"
                else zone_demand
            )(clusters[k], members)
            for k, members in grouped.items()
        }
        if pattern_scale == "district":
            budgets = {
                k: pattern_demand(clusters[k], members, requested[k])
                for k, members in grouped.items()
            }
        elif pattern_scale == "adaptive":
            budgets = {
                k: adaptive_demand(clusters[k], members, requested[k])
                for k, members in grouped.items()
            }
    owners = {b["entityId"]: key for key, members in grouped.items() for b in members}
    pairs = dependency_pairs(graph, owners) if zoning == "neighborhoods" else {}
    # A tiny corner district still needs a complete frontage/circulation cell.
    # Budget it locally rather than inflating every large district to repair it.
    if len(grouped) > 1:
        for budget in budgets.values():
            extra = max(0, 3000 - budget["total"])
            budget["boundaryReserve"] += extra
            budget["total"] += extra
    if terrain != "flat":
        # Even one source file needs room for a real protected feature and access.
        total = sum(b["total"] for b in budgets.values())
        if total < 4000:
            for budget in budgets.values():
                extra = (4000-total)*budget["total"]/total
                budget["terrainEnvelopeReserve"] = extra
                budget["total"] += extra
    compatible = bool(
        previous
        and previous.get("schemaVersion") == VERSION
        and previous.get("seed") == resolved_seed
        and previous.get("repositoryNamespace") == identity
        and previous.get("planningPolicy", "grid") == planning
        and previous.get("outlinePolicy", "ellipse") == outline
        and previous.get("zoningPolicy", "none") == zoning
        and previous.get("patternScale", "block") == pattern_scale
        and previous.get("terrainPreset", "flat") == terrain
        and (
            pattern_scale == "block"
            or previous.get("generatorVersion") in (
                ((VALLEY_GENERATOR_VERSION,) if terrain == VALLEY_PRESET else
                 (RIVER_GENERATOR_VERSION,) if terrain == RIVER_PRESET else (TERRAIN_GENERATOR_VERSION,)) if terrain != "flat" else
                (ADAPTIVE_GENERATOR_VERSION, SHARED_GENERATOR_VERSION, ALLEY_GENERATOR_VERSION)
                if pattern_scale == "adaptive"
                else ("flat-neighborhood-patterns/0.1",)
            )
        )
        and set(d["id"] for d in previous.get("districts", [])) == set(grouped)
    )
    old_districts = {d["id"]: d for d in previous["districts"]} if compatible else {}
    if any(
        d.get("planningProfile")
        not in (
            ("ZONED",)
            if zoned
            else ("GRID",)
            if planning == "grid"
            else ("GRID", "RADIAL", "ORGANIC", "INDUSTRIAL", "HYBRID")
        )
        for d in old_districts.values()
    ):
        raise ValueError("invalid previous world planning profile")
    old_parcels = (
        {p["entityId"]: p["slotId"] for p in previous["parcels"]} if compatible else {}
    )
    repairs = []
    terrain_data = previous.get("terrain") if compatible and terrain != "flat" else None
    if terrain_data:
        validate_terrain(terrain_data, resolved_seed)
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
            # Preserve the legacy affine dodecagon unless variation is requested.
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
            if outline == "varied":
                envelope, _ = varied_outline(resolved_seed)
            radius = math.sqrt(
                sum(b["total"] for b in budgets.values()) / area(envelope)
            )
            envelope = [point([v * radius for v in p]) for p in envelope]
            if terrain != "flat" and terrain_data is None:
                # Natural reserves precede district polygons, roads and source addresses.
                terrain_data = (generate_terrain(envelope, resolved_seed, terrain) if terrain in (RIVER_PRESET, VALLEY_PRESET)
                                else generate_terrain(envelope, resolved_seed))
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
        quantization_failed = set()
        planning_diagnostics = []
        semantic_zones = []
        development_blocks, main_roads = [], []
        district_patterns = []
        reused_zoned = []
        for key, members in grouped.items():
            if zoning == "neighborhoods" and not all(
                inside(v, polygons[key], -0.001) for v in polygons[key]
            ):
                failed.append(key)
                quantization_failed.add(key)
                continue
            local_seed = local_seeds[key]
            profile = requested[key]
            if attempt == 0 and compatible:
                profile = old_districts[key]["planningProfile"]
            planner = {
                "GRID": slots,
                "RADIAL": radial_slots,
                "ORGANIC": organic_slots,
                "INDUSTRIAL": industrial_slots,
                "HYBRID": hybrid_slots,
            }.get(profile, slots)
            if zoned:
                old_zones = (
                    [
                        z
                        for z in previous.get("zoning", {}).get("zones", [])
                        if z["parentId"] == key
                    ]
                    if compatible and attempt == 0
                    else []
                )
                if zoning == "neighborhoods":
                    old_blocks = (
                        [
                            b
                            for b in previous.get("zoning", {}).get("blocks", [])
                            if b["zoneId"] in {z["id"] for z in old_zones}
                        ]
                        if compatible and attempt == 0
                        else []
                    )
                    args = (
                        polygons[key],
                        clusters[key],
                        members,
                        local_seed,
                        entity_paths,
                        {(a, b): w for (a, b), w in pairs.items() if owners[a] == key},
                        requested[key] if pattern_scale != "block" else planning,
                        old_zones,
                        old_blocks,
                        old_parcels if compatible and attempt == 0 else None,
                    )
                    if pattern_scale != "block":
                        (
                            placed,
                            lanes,
                            records,
                            notes,
                            zone_reuse,
                            blocks,
                            backbone,
                            pattern,
                        ) = (
                            plan_adaptive
                            if pattern_scale == "adaptive"
                            else plan_district_pattern
                        )(*args, **(dict(terrain=terrain_data) if terrain_data else {}))
                        district_patterns.append(pattern)
                    else:
                        placed, lanes, records, notes, zone_reuse, blocks, backbone = (
                            plan_neighborhoods(*args)
                        )
                    development_blocks.extend(blocks)
                    main_roads.extend(backbone)
                else:
                    placed, lanes, records, notes, zone_reuse = plan_zones(
                        polygons[key],
                        clusters[key],
                        members,
                        local_seed,
                        entity_paths,
                        old_zones,
                        old_parcels if compatible and attempt == 0 else None,
                    )
                semantic_zones.extend(records)
                planning_diagnostics.extend(notes)
                if zone_reuse:
                    reused_zoned.append(key)
                candidates = range(sum(z["capacity"] for z in records))
                profile, angle = "ZONED", 0
            else:
                candidates, lanes, angle = planner(polygons[key], local_seed)
            if (
                zoning == "none"
                and planning in ("mixed", "varied")
                and profile != "GRID"
                and len(candidates) < len(members)
                and not (attempt == 0 and compatible)
            ):
                missing_profile = profile
                profile = "GRID"
                candidates, lanes, angle = slots(polygons[key], local_seed)
                planning_diagnostics.append(
                    dict(
                        reason=f"{missing_profile.lower()} frontage capacity insufficient; local GRID fallback",
                        districtIds=[key],
                    )
                )
            if zoning == "none":
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
                if pattern_scale == "adaptive":
                    repairs.extend(
                        n
                        for n in notes
                        if n["reason"] == "adaptive shared-cut quantization repair"
                    )
                if (
                    pattern_scale == "adaptive"
                    and notes
                    and all(n["reason"] == "adaptive shared-cut quantization repair" for n in notes)
                ):
                    quantization_failed.add(key)
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
                    planningProfile=profile,
                    primaryAxis=angle,
                    areaDemand=budgets[key],
                    areaAllocated=area(poly),
                    capacity=len(candidates),
                    buildingCount=len(members),
                )
            )
            if profile == "HYBRID":
                districts[-1]["planningRegions"] = hybrid_regions(poly, local_seed)
            perimeter = [dict(start=a, end=b, width=3.5, access=False)
                         for a, b in zip(poly, poly[1:] + poly[:1])]
            raw.extend(adapt_roads(perimeter, terrain_data) if terrain_data else perimeter)
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
        if quantization_failed:
            repairs.append(
                dict(
                    reason="quantized shared-cut convexity repair; bounded local demand adjustment",
                    districtIds=sorted(quantization_failed),
                )
            )
        for key in failed:
            extra = budgets[key]["total"] * (
                0.002 if key in quantization_failed else 0.5
            )
            budgets[key]["repairReserve"] = budgets[key].get("repairReserve", 0) + extra
            budgets[key]["total"] += extra
    else:
        raise ValueError(
            "world parcel capacity infeasible after bounded envelope repair"
        )
    streets = atomic_streets(raw)
    if terrain == VALLEY_PRESET:
        annotate(streets,parcels,terrain_data)
    routing, networks, coverage = (
        route_world(graph, parcels, streets) if _route else ({}, [], {})
    )
    if pattern_scale == "adaptive" and _route:
        boundaries = [
            dict(start=a, end=b)
            for d in districts
            for a, b in zip(d["polygon"], d["polygon"][1:] + d["polygon"][:1])
        ]
        streets, seam_note = stitch_unused_streets(
            streets, main_roads + boundaries, routing, parcels
        )
        planning_diagnostics.append(seam_note)
        if street_policy in ("shared", "permeable"):
            candidate, junction_note = consolidate_junctions(
                streets, main_roads + boundaries, parcels, routing
            )
            if junction_note["removedStreetIds"]:
                try:
                    new_routing, new_networks, new_coverage = route_world(graph, parcels, candidate)
                    check_trip_budgets(routing, new_routing)
                except ValueError as error:
                    junction_note.update(
                        reason="shared junction fallback; original certified routes retained",
                        rejectedStreetIds=junction_note["removedStreetIds"],
                        removedStreetIds=[], affectedTripIds=[], fallback=str(error),
                    )
                else:
                    streets, routing, networks, coverage = candidate, new_routing, new_networks, new_coverage
            planning_diagnostics.append(junction_note)
        if street_policy == "permeable":
            additions, alley_note = add_alleys(streets, parcels, districts, **(
                dict(reserves=[f["noBuildPolygon"] for f in terrain_data["features"]]) if terrain_data else {}
            ))
            if additions:
                try:
                    candidate = atomic_streets(streets + additions)
                    if terrain == VALLEY_PRESET:
                        annotate(candidate,parcels,terrain_data)
                    new_routing, new_networks, new_coverage = route_world(graph, parcels, candidate)
                    check_trip_budgets(routing, new_routing)
                    prior_lengths = {r["id"]: path_length(r["path"]) for r in routing["routes"]}
                    if any(path_length(r["path"]) > prior_lengths[r["id"]]+.003 for r in new_routing["routes"]):
                        raise ValueError("alley addition increased an existing trip")
                except ValueError as error:
                    alley_note.update(rejectedCorridors=alley_note["corridors"],
                                      corridors=[], fallback=str(error))
                else:
                    streets, routing, networks, coverage = candidate, new_routing, new_networks, new_coverage
            planning_diagnostics.append(alley_note)
    reused = sorted(grouped) if compatible and attempt == 0 else []
    if zoned:
        reused = sorted(reused_zoned) if compatible and attempt == 0 else []
    topology = {}
    for d in districts:
        for a, b in zip(d["polygon"], d["polygon"][1:] + d["polygon"][:1]):
            edge = tuple(sorted((tuple(a), tuple(b))))
            topology.setdefault(edge, []).append(d["id"])
    logical = [
        dict(id=d["id"], parentId=d["parentId"])
        for d in sorted(scene["districts"], key=lambda d: d["id"])
    ]
    world = dict(
        schemaVersion=VERSION,
        generatorVersion="flat-capacity/0.1"
        if planning == "grid"
        else (
            "flat-planning/0.3"
            if planning in ("organic", "industrial", "hybrid", "varied")
            else "flat-planning/0.2"
        ),
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
        diagnostics=repairs + planning_diagnostics,
        anchors=dict(
            reusedDistrictIds=reused,
            replannedDistrictIds=sorted(set(grouped) - set(reused)),
        ),
    )
    if planning != "grid":
        world["planningPolicy"] = planning
    if outline == "varied":
        world.update(
            generatorVersion="flat-world/0.4",
            outlinePolicy="varied",
            outlineVersion=OUTLINE_VERSION,
            outlineFamily=varied_outline(resolved_seed)[1],
        )
    if zoned:
        world.update(
            generatorVersion="flat-neighborhoods/0.1"
            if zoning == "neighborhoods"
            else "flat-zoning/0.1",
            zoningPolicy=zoning,
            zoning=dict(
                version=FUNCTIONAL_VERSION
                if pattern_scale == "adaptive"
                else NEIGHBORHOOD_VERSION
                if zoning == "neighborhoods"
                else ZONING_VERSION,
                zones=sorted(semantic_zones, key=lambda z: z["id"]),
            ),
        )
        if zoning == "neighborhoods":
            world["zoning"].update(
                blocks=sorted(development_blocks, key=lambda b: b["id"]),
                mainRoads=sorted(main_roads, key=lambda r: r["id"]),
            )
            if pattern_scale != "block":
                world.update(
                    patternScale=pattern_scale,
                    generatorVersion=ADAPTIVE_GENERATOR_VERSION
                    if pattern_scale == "adaptive"
                    else "flat-neighborhood-patterns/0.1",
                )
                world["zoning"]["districtPatterns"] = sorted(
                    district_patterns, key=lambda p: p["id"]
                )
    if street_policy == "shared":
        world["generatorVersion"] = SHARED_GENERATOR_VERSION
    elif street_policy == "permeable":
        world["generatorVersion"] = ALLEY_GENERATOR_VERSION
    if terrain_data:
        if terrain in (RIVER_PRESET,VALLEY_PRESET):
            annotate_crossings(streets, routing, terrain_data)
        if terrain == VALLEY_PRESET:
            world["surface"]=build_surface(terrain_data,districts)
            physical={s["id"]:s for s in streets}
            for s in routing["segments"]:
                for field in ("heights","heightProfile"):
                    s[field]=physical[s["physicalId"]][field]
        world.update(generatorVersion=VALLEY_GENERATOR_VERSION if terrain == VALLEY_PRESET else RIVER_GENERATOR_VERSION if terrain == RIVER_PRESET else TERRAIN_GENERATOR_VERSION, terrainPreset=terrain,
                     terrain=terrain_data, streetPolicy=street_policy)
    return world
