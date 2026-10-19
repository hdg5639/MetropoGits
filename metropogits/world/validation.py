"""Independent geometry and source-conservation checks for world exports."""

import math
from collections import defaultdict

from metropogits.street_diagonals import overlap
from metropogits.block_orientation import clip
from scripts.canonical_json import sha256_digest
from . import VERSION
from .geometry import area, bounds, inside, ribbon, nearest
from .zoning import validate_zoning
from .soft import validate_soft
from .block_validation import validate_blocks


def validate_world(world, scene, graph):
    if world.get("schemaVersion") != VERSION:
        raise ValueError("unsupported world schema")
    if "patternScale" in world and (
        world["patternScale"] not in ("district", "adaptive")
        or world.get("zoningPolicy") != "neighborhoods"
        or world.get("generatorVersion")
        not in (
            ("flat-adaptive-neighborhoods/0.1", "flat-adaptive-neighborhoods/0.2", "flat-adaptive-neighborhoods/0.3", "flat-adaptive-neighborhoods/0.4", "flat-adaptive-neighborhoods/0.5")
            if world["patternScale"] == "adaptive"
            else ("flat-neighborhood-patterns/0.1",)
        )
    ):
        raise ValueError("invalid world pattern scale or generator")
    if (
        world.get("generatorVersion")
        in (
            "flat-neighborhood-patterns/0.1",
            "flat-adaptive-neighborhoods/0.1",
            "flat-adaptive-neighborhoods/0.2",
            "flat-adaptive-neighborhoods/0.3",
            "flat-adaptive-neighborhoods/0.4",
            "flat-adaptive-neighborhoods/0.5",
        )
    ) != (world.get("patternScale") in ("district", "adaptive")):
        raise ValueError("world pattern scale version mismatch")
    if "districtPatterns" in world.get("zoning", {}) and world.get(
        "patternScale"
    ) not in ("district", "adaptive"):
        raise ValueError("district patterns require an explicit pattern scale")
    if world["ucgDigest"] != sha256_digest(graph) or world[
        "sourceCityDigest"
    ] != sha256_digest(scene):
        raise ValueError("world source digest mismatch")
    source = {b["entityId"]: b for b in scene["buildings"]}
    parcels = world["parcels"]
    if {d["id"] for d in world["logicalDistricts"]} != {
        d["id"] for d in scene["districts"]
    }:
        raise ValueError("world logical directory loss")
    for edge in world["topology"]["edges"]:
        if not 1 <= len(edge["districtIds"]) <= 2:
            raise ValueError("invalid shared boundary ownership")
    zones = {d["id"]: d for d in world["districts"]}
    neighborhoods = validate_zoning(world, scene, graph)
    validate_soft(world, scene, graph)
    validate_blocks(world, scene, graph, neighborhoods)
    neighborhood_members = {
        key: set(z["memberEntityIds"]) for key, z in neighborhoods.items()
    }
    if len(parcels) != len(source) or {p["entityId"] for p in parcels} != set(source):
        raise ValueError("world omitted or duplicated source buildings")
    if abs(
        sum(area(d["polygon"]) for d in zones.values()) - area(world["envelope"])
    ) > max(0.01, area(world["envelope"]) * 1e-5):
        raise ValueError("world district area conservation failed")
    zone_list = list(zones.values())
    regions = {}
    for i, d in enumerate(zone_list):
        if (
            len(d["polygon"]) < 3
            or area(d["polygon"]) < 1
            or not all(
                inside(p, world["envelope"], margin=-0.001) for p in d["polygon"]
            )
        ):
            raise ValueError("invalid world district polygon")
        for other in zone_list[:i]:
            # Quantized shared T vertices can be microscopically non-convex;
            # SAT alone treats these as overlaps even with zero common area.
            if area(clip(d["polygon"], other["polygon"])) > 0.001:
                raise ValueError("world district overlap")
        if d.get("planningProfile") == "HYBRID":
            parts = d.get("planningRegions", [])
            if not 2 <= len(parts) <= 4 or len({r["id"] for r in parts}) != len(parts):
                raise ValueError("invalid hybrid planning regions")
            if abs(sum(area(r["polygon"]) for r in parts) - area(d["polygon"])) > 0.02:
                raise ValueError("hybrid planning region area loss")
            for j, r in enumerate(parts):
                if not all(
                    inside(p, d["polygon"], margin=-0.001) for p in r["polygon"]
                ):
                    raise ValueError("hybrid planning region escaped district")
                if any(
                    area(clip(r["polygon"], o["polygon"])) > 0.001 for o in parts[:j]
                ):
                    raise ValueError("hybrid planning region overlap")
                regions[(d["id"], r["id"])] = r
    cells = defaultdict(set)
    polygons = {}
    checks = 0

    def buckets(poly):
        x0, z0, x1, z1 = bounds(poly)
        if max(x1 - x0, z1 - z0) > 10000:
            raise ValueError("world validation spatial extent limit")
        return [
            (x, z)
            for x in range(math.floor(x0 / 16), math.floor(x1 / 16) + 1)
            for z in range(math.floor(z0 / 16), math.floor(z1 / 16) + 1)
        ]

    index_entries = 0
    parcel_cells = defaultdict(set)
    parcel_polygons = {}

    def reserve(poly, key):
        nonlocal index_entries
        polygons[key] = poly
        keys = buckets(poly)
        index_entries += len(keys)
        if index_entries > 2_000_000:
            raise ValueError("world validation index limit")
        for k in keys:
            cells[k].add(key)

    for s in world["streets"]:
        reserve(ribbon(s["start"], s["end"], s["width"]), ("road", s["id"]))
    if world["generatorVersion"] == "flat-adaptive-neighborhoods/0.5":
        for note in world["diagnostics"]:
            if note.get("version") == "frontage-alleys/0.1":
                for alley in note["corridors"]:
                    owner = zones.get(alley["districtId"])
                    poly = ribbon(alley["start"], alley["end"], alley["width"]+.39)
                    if owner is None or not all(inside(v, owner["polygon"]) for v in poly):
                        raise ValueError("alley escaped its principal district")
                    reserve(poly, ("alley", alley["id"]))
    physical_geometry = {s["id"]: s for s in world["streets"]}
    for p in parcels:
        b = source[p["entityId"]]
        if any(
            p[k] != b[k]
            for k in (
                "width",
                "height",
                "depth",
                "archetype",
                "evidenceIds",
                "styleVariant",
            )
        ):
            raise ValueError("world changed source-backed building fields")
        if p["sourceDistrictId"] != b["districtId"]:
            raise ValueError("world directory ownership mismatch")
        poly = p["footprint"]
        if world["generatorVersion"] in ("flat-adaptive-neighborhoods/0.4", "flat-adaptive-neighborhoods/0.5"):
            # Reuse the independent validation index/budget. Optional optimizer
            # exhaustion must not make its untouched fallback invalid.
            connected = False
            for key in sorted({key for c in buckets([p["streetPoint"]]) for key in cells[c]}):
                if key[0] != "road":
                    continue
                checks += 1
                if checks > 5_000_000:
                    raise ValueError("world validation work limit")
                s = physical_geometry[key[1]]
                if not s["access"] and math.dist(p["streetPoint"], nearest(p["streetPoint"], s["start"], s["end"])) < .002:
                    connected = True
                    break
            if not connected:
                raise ValueError("world source building lost physical frontage")
        if neighborhoods:
            owner = neighborhoods.get(p.get("zoneId"))
            if (
                owner is None
                or owner["parentId"] != p["districtId"]
                or p["entityId"] not in neighborhood_members[owner["id"]]
                or (
                    world.get("zoningPolicy") != "neighborhoods"
                    and p.get("blockProfile") != owner["planningProfile"]
                )
                or not all(inside(v, owner["polygon"]) for v in p["parcel"] + poly)
            ):
                raise ValueError("invalid semantic parcel ownership")
        if zones[p["districtId"]].get("planningProfile") == "HYBRID":
            region = regions.get((p["districtId"], p.get("planningRegionId")))
            if (
                region is None
                or p.get("blockProfile") != region["planningProfile"]
                or not all(inside(v, region["polygon"]) for v in p["parcel"] + poly)
            ):
                raise ValueError("invalid hybrid parcel ownership")
        if not all(inside(v, p["parcel"]) for v in poly):
            raise ValueError("world building escaped its parcel")
        parcel_keys = buckets(p["parcel"])
        for key in sorted({k for cell in parcel_keys for k in cells[cell] if k[0] == "alley"}):
            checks += 1
            if checks > 5_000_000:
                raise ValueError("world validation work limit")
            if overlap(p["parcel"], polygons[key]):
                raise ValueError("alley intrudes into a source parcel")
        index_entries += len(parcel_keys)
        if index_entries > 2_000_000:
            raise ValueError("world validation index limit")
        for identity in sorted({k for cell in parcel_keys for k in parcel_cells[cell]}):
            checks += 1
            if checks > 5_000_000:
                raise ValueError("world validation work limit")
            if area(clip(p["parcel"], parcel_polygons[identity])) > 0.001:
                raise ValueError(f"world parcel overlap: {p['entityId']} / {identity}")
        parcel_polygons[p["entityId"]] = p["parcel"]
        for cell in parcel_keys:
            parcel_cells[cell].add(p["entityId"])
        if (
            min(
                math.dist(p["entrance"], nearest(p["entrance"], a, b))
                for a, b in zip(poly, poly[1:] + poly[:1])
            )
            > 0.001
        ):
            raise ValueError("world entrance is not on building perimeter")
        for part in p["parts"]:
            if (
                any(not inside(v, poly) for v in part["footprint"])
                or part["y"] < 0
                or part["y"] + part["height"] > b["height"] + 0.001
            ):
                raise ValueError("world model escaped source envelope")
        if not all(
            inside(v, zones[p["districtId"]]["polygon"]) for v in p["parcel"] + poly
        ):
            raise ValueError("world parcel escaped district: " + p["entityId"])
        if abs(area(poly) - b["width"] * b["depth"]) > 0.01:
            raise ValueError("world building size mismatch")
        near = {identity for k in buckets(poly) for identity in cells[k]}
        for key in near:
            checks += 1
            if checks > 5_000_000:
                raise ValueError("world validation work limit")
            # Quantized doorway surfaces can touch by <0.001 units. Inset the
            # building only by this documented numerical tolerance, not road width.
            from .geometry import rectangle

            conservative = rectangle(
                p["center"], p["angle"], b["width"] - 0.002, b["depth"] - 0.002
            )
            if overlap(conservative, polygons[key]):
                raise ValueError(f"world building intersects {key}: {p['entityId']}")
        reserve(poly, ("building", p["entityId"]))
    adjacent = defaultdict(set)
    for s in world["streets"]:
        a, b = tuple(s["start"]), tuple(s["end"])
        adjacent[a].add(b)
        adjacent[b].add(a)
    visited = set()
    pending = [tuple(parcels[0]["entrance"])]
    while pending:
        current = pending.pop()
        if current in visited:
            continue
        visited.add(current)
        pending.extend(adjacent[current] - visited)
    if any(tuple(p["entrance"]) not in visited for p in parcels):
        raise ValueError("world building lacks structural access")
    routes = world["routing"]["routes"]
    streets = {s["id"]: s for s in world["routing"]["segments"]}
    physical = {s["id"]: s for s in world["streets"]}
    for s in streets.values():
        if "physicalId" in s and (
            s["physicalId"] not in physical
            or any(s[k] != physical[s["physicalId"]][k] for k in ("start", "end", "width"))
        ):
            raise ValueError("world trip lost its physical pavement")
    by_entity = {p["entityId"]: p for p in parcels}
    represented = []
    edge_records = {e["id"]: e for e in graph["edges"]}
    entities = {e["id"]: e for e in graph["entities"]}
    files = {e["path"]: e["id"] for e in graph["entities"] if e["kind"] == "FILE"}

    def endpoint(key):
        return (
            files.get(entities[key].get("path"))
            if entities[key]["kind"] in ("FILE", "SYMBOL")
            else None
        )

    for r in routes:
        for identity in r["edgeIds"]:
            edge = edge_records[identity]
            if (
                endpoint(edge["from"]) != r["source"]
                or endpoint(edge["to"]) != r["target"]
            ):
                raise ValueError("world trip changed semantic endpoints")
        if (
            r["path"][0] != by_entity[r["source"]]["entrance"]
            or r["path"][-1] != by_entity[r["target"]]["entrance"]
        ):
            raise ValueError("world trip doorway mismatch")
        if len(r["segmentIds"]) != len(r["path"]) - 1:
            raise ValueError("world trip segment mismatch")
        for i, key in enumerate(r["segmentIds"]):
            s = streets[key]
            if (
                sorted((s["start"], s["end"]))
                != sorted((r["path"][i], r["path"][i + 1]))
                or r["id"] not in s["routeIds"]
            ):
                raise ValueError("world trip discontinuity")
        represented += r["edgeIds"]
    expected = {e["id"] for e in graph["edges"] if e["type"] != "CONTAINS"}
    classified = (
        represented
        + world["coverage"]["internalEdgeIds"]
        + world["coverage"]["nonLocalEdgeIds"]
    )
    if len(classified) != len(set(classified)) or set(classified) != expected:
        raise ValueError("world edge conservation failed")
    return dict(
        buildings=len(parcels),
        districts=len(zones),
        streets=len(world["streets"]),
        trips=len(routes),
        representedEdges=len(represented),
        geometryChecks=checks,
        buildingOverlaps=0,
        roadOverlaps=0,
        ownerEscapes=0,
        accessibleBuildings=len(parcels),
    )
