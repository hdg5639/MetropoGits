"""District capacity and frontage-first parcel placement, no source execution."""

import math
from collections import defaultdict

from metropogits.building_forms import building_parts
from metropogits.preview import _major_district_ids
from .geometry import bounds, inset, inside, point, rectangle, nearest
from .seed import derive, draw

MAX_FILES = 10_000
MAX_ZONES = 64
MAX_SLOTS = 100_000


def groups(scene):
    parents = {d["id"]: d["parentId"] for d in scene["districts"]}
    roots = sorted(d for d, p in parents.items() if p is None)
    majors = _major_district_ids(scene)
    result = defaultdict(list)
    for b in sorted(scene["buildings"], key=lambda b: b["entityId"]):
        owner = b["districtId"]
        while owner not in majors and parents[owner] is not None:
            owner = parents[owner]
        result[owner].append(b)
    if len(result) > MAX_ZONES or len(scene["buildings"]) > MAX_FILES:
        raise ValueError("world district/file resource limit")
    return dict(sorted(result.items())), roots


def demand(buildings, profile="GRID"):
    # Real six-unit envelopes + frontage parcels + circulation + 25% reserve.
    parcel = sum(
        (b["width"] + (3 if profile == "INDUSTRIAL" else 2))
        * (b["depth"] + (4 if profile == "INDUSTRIAL" else 2))
        for b in buildings
    )
    access = (60 if profile == "INDUSTRIAL" else 32) * len(buildings)
    reserve = (parcel + access) * 0.25
    boundary = 64 * math.sqrt(len(buildings)) + 400
    return dict(
        parcelArea=parcel,
        streetArea=access,
        growthReserve=reserve,
        boundaryReserve=boundary,
        total=parcel + access + reserve + boundary,
    )


def slots(poly, seed, *, rotation=0, phase_offset=0, axis=None, collectors=True):
    """Two frontage rows per local street, with boundary corridors reserved first."""
    inner = inset(poly, 5)
    if len(inner) < 3:
        return [], [], 0
    edges = list(zip(poly, poly[1:] + poly[:1]))
    a, b = max(edges, key=lambda e: math.dist(*e))
    angle = (math.atan2(b[1] - a[1], b[0] - a[0]) if axis is None else axis) + rotation
    c, s = math.cos(angle), math.sin(angle)

    def to_local(p):
        return [c * p[0] + s * p[1], -s * p[0] + c * p[1]]

    def to_world(p):
        return point([c * p[0] - s * p[1], s * p[0] + c * p[1]])

    local = [to_local(p) for p in inner]
    x0, z0, x1, z1 = bounds(local)
    phase = (draw(seed) - 0.5) * 8 + phase_offset
    candidates, lanes = [], []
    estimated = (int((x1 - x0) / 8) + 3) * (int((z1 - z0) / 24) + 3) * 2
    if estimated > MAX_SLOTS:
        raise ValueError("world parcel candidate limit")
    for row in range(math.floor((z0 - phase) / 24), math.ceil((z1 - phase) / 24) + 1):
        v = row * 24 + phase
        intersections = []
        for p, q in zip(local, local[1:] + local[:1]):
            if min(p[1], q[1]) <= v <= max(p[1], q[1]) and abs(q[1] - p[1]) > 1e-8:
                intersections.append(p[0] + (v - p[1]) / (q[1] - p[1]) * (q[0] - p[0]))
        if len(intersections) < 2:
            continue
        lo, hi = min(intersections), max(intersections)
        if hi - lo < 14:
            continue
        lane_id = f"row:{row}"
        lane = [to_world([lo, v]), to_world([hi, v])]
        for column in range(math.ceil((lo + 5) / 8), math.floor((hi - 5) / 8) + 1):
            u = column * 8
            for sign in (-1, 1):
                center = to_world([u, v + sign * 6])
                parcel = rectangle(center, angle, 8, 8)
                if not all(inside(p, inner) for p in parcel):
                    continue
                candidates.append(
                    dict(
                        id=f"{row}:{column}:{sign}",
                        center=center,
                        angle=angle + (math.pi if sign == 1 else 0),
                        polygon=parcel,
                        entrance=to_world([u, v + sign * 3]),
                        streetPoint=to_world([u, v]),
                        laneId=lane_id,
                    )
                )
        if not any(x["laneId"] == lane_id for x in candidates):
            continue
        lanes.append(
            dict(id=lane_id, start=lane[0], end=lane[1], width=4, access=False)
        )
        for endpoint in lane:
            target = min(
                (nearest(endpoint, p, q) for p, q in edges),
                key=lambda p: math.dist(endpoint, p),
            )
            lanes.append(
                dict(
                    id=lane_id + ":connector:" + str(len(lanes)),
                    start=endpoint,
                    end=point(target),
                    width=3,
                    access=False,
                )
            )
    # Reserve cross collectors before assigning buildings to frontage lots.
    for column in (
        range(math.ceil((x0 + 6) / 70), math.floor((x1 - 6) / 70) + 1)
        if collectors
        else ()
    ):
        u = column * 70
        hits = []
        for p, q in zip(local, local[1:] + local[:1]):
            if min(p[0], q[0]) <= u <= max(p[0], q[0]) and abs(q[0] - p[0]) > 1e-8:
                hits.append(p[1] + (u - p[0]) / (q[0] - p[0]) * (q[1] - p[1]))
        if len(hits) < 2 or max(hits) - min(hits) < 12:
            continue
        candidates = [p for p in candidates if abs(to_local(p["center"])[0] - u) >= 6.5]
        lane = [to_world([u, min(hits)]), to_world([u, max(hits)])]
        lanes.append(
            dict(
                id=f"collector:{column}",
                start=lane[0],
                end=lane[1],
                width=3,
                access=False,
            )
        )
        for endpoint in lane:
            target = min(
                (nearest(endpoint, p, q) for p, q in edges),
                key=lambda p: math.dist(endpoint, p),
            )
            lanes.append(
                dict(
                    id=f"collector:{column}:connector:{len(lanes)}",
                    start=endpoint,
                    end=point(target),
                    width=3,
                    access=False,
                )
            )
    return candidates, lanes, angle


def populate(buildings, candidates, zone_id, entity_paths, seed, previous=None):
    if len(candidates) < len(buildings):
        return None
    available = {p["id"]: p for p in candidates}
    assignments = {}
    probes = 0
    for b in buildings:
        key = (previous or {}).get(b["entityId"])
        if key in available:
            assignments[b["entityId"]] = available.pop(key)
    ordered = sorted(available)
    for b in buildings:
        if b["entityId"] in assignments:
            continue
        start = int(derive(seed, "parcel", entity_paths[b["entityId"]]), 16) % len(
            ordered
        )
        for i in range(len(ordered)):
            probes += 1
            if probes > 1_000_000:
                raise ValueError("world parcel assignment work limit")
            key = ordered[(start + i) % len(ordered)]
            if key in available:
                assignments[b["entityId"]] = available.pop(key)
                break
    result = []
    for b in buildings:
        slot = assignments[b["entityId"]]
        angle = slot["angle"]
        c, s = math.cos(angle), math.sin(angle)
        center = slot["center"]

        def place(x, z):
            return point([center[0] + c * x - s * z, center[1] + s * x + c * z])

        local = dict(
            b,
            x=-b["width"] / 2,
            z=-b["depth"] / 2,
            entityId=derive(seed, "building", entity_paths[b["entityId"]]),
        )
        parts = []
        for part in building_parts(local):
            poly = rectangle(
                [part["x"] + part["width"] / 2, part["z"] + part["depth"] / 2],
                0,
                part["width"],
                part["depth"],
            )
            parts.append(dict(part, footprint=[place(*p) for p in poly]))
        result.append(
            dict(
                entityId=b["entityId"],
                sourceDistrictId=b["districtId"],
                districtId=zone_id,
                slotId=slot["id"],
                blockId=f"{zone_id}:block:{slot['laneId']}",
                center=center,
                angle=angle,
                footprint=rectangle(center, angle, b["width"], b["depth"]),
                parts=parts,
                parcel=slot["polygon"],
                entrance=slot["entrance"],
                streetPoint=slot["streetPoint"],
                archetype=b["archetype"],
                width=b["width"],
                depth=b["depth"],
                height=b["height"],
                evidenceIds=b["evidenceIds"],
                styleVariant=b["styleVariant"],
            )
        )
        if "blockProfile" in slot:
            result[-1]["blockProfile"] = slot["blockProfile"]
        if "planningRegionId" in slot:
            result[-1]["planningRegionId"] = slot["planningRegionId"]
    return result
