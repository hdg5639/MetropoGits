"""Bounded, non-canonical street-facing placement (ADR-022)."""

import math
from collections import Counter, defaultdict

from metropogits.building_forms import building_parts
from metropogits.street_diagonals import PhysicalMap, bounds, buckets, overlap
from metropogits.structural_streets import street_rectangles
from metropogits.street_demand import demand_pavement
from metropogits.street_curves import curved_presentation
from metropogits.road_hierarchy import derive_road_hierarchy

MAX_CHECKS = 5_000_000
MAX_INDEX_ENTRIES = 2_000_000


def corners(b):
    x, z, w, d = (b[k] for k in ("x", "z", "width", "depth"))
    return [[x, z], [x + w, z], [x + w, z + d], [x, z + d]]


def transform(points, pivot, angle, shift):
    c, s = math.cos(angle), math.sin(angle)
    return [
        [
            pivot[0] + c * (x - pivot[0]) - s * (z - pivot[1]) + shift[0],
            pivot[1] + s * (x - pivot[0]) + c * (z - pivot[1]) + shift[1],
        ]
        for x, z in points
    ]


def area(poly):
    return (
        abs(sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(poly, poly[1:] + poly[:1])))
        / 2
    )


def inside(poly, rectangles):
    # City footprint rectangles are disjoint. Clip the convex footprint against
    # each owner rectangle; checking corners alone misses concave notches.
    covered = 0
    for r in rectangles:
        clipped = poly
        for axis, limit, sign in (
            (0, r["x"], 1),
            (0, r["x"] + r["width"], -1),
            (1, r["z"], 1),
            (1, r["z"] + r["depth"], -1),
        ):
            output = []
            for a, b in zip(clipped, clipped[1:] + clipped[:1]):
                ia, ib = sign * (a[axis] - limit) >= 0, sign * (b[axis] - limit) >= 0
                if ia:
                    output.append(a)
                if ia != ib:
                    t = (limit - a[axis]) / (b[axis] - a[axis])
                    output.append([a[j] + t * (b[j] - a[j]) for j in (0, 1)])
            clipped = output
        covered += area(clipped)
    return covered >= area(poly) - 1e-7


def nearest(point, a, b):
    length = sum((b[j] - a[j]) ** 2 for j in (0, 1))
    t = max(0, min(1, sum((point[j] - a[j]) * (b[j] - a[j]) for j in (0, 1)) / length))
    return [a[j] + t * (b[j] - a[j]) for j in (0, 1)]


def plan_parcels(scene, routing):
    indexed = 0

    def reserve(index, poly, identity, margin=0):
        nonlocal indexed
        for cell in buckets(bounds(poly), margin):
            indexed += 1
            if indexed > MAX_INDEX_ENTRIES:
                raise ValueError("frontage parcel spatial index limit")
            index[cell].add(identity)

    hierarchy = derive_road_hierarchy(scene, routing)
    surfaces = street_rectangles(routing)
    pavement = demand_pavement(routing, hierarchy, surfaces)
    surfaces, pavement, _ = curved_presentation(routing, surfaces, pavement, hierarchy)
    road_polys = [s["points"] for s in surfaces]
    road_polys += [
        p["points"] for parts in pavement["segments"].values() for p in parts
    ]
    road_index = defaultdict(set)
    for i, p in enumerate(road_polys):
        reserve(road_index, p, i, 1)
    mapper = PhysicalMap(routing["diagonalPlan"])
    streets = []
    for s in sorted(routing["streetGrid"]["segments"], key=lambda s: s["id"]):
        if s.get("entrance"):
            continue
        for _, _, a, b, w in mapper.spans(s["start"], s["end"]):
            if math.dist(a, b) > 2:
                streets.append((s["id"], a, b, max(w) if w else s["width"]))
    street_index = defaultdict(set)
    for i, (_, a, b, _) in enumerate(streets):
        reserve(street_index, [a, b], i)
    occupied = {b["entityId"]: corners(b) for b in scene["buildings"]}
    building_index = defaultdict(set)
    by_id = {b["entityId"]: b for b in scene["buildings"]}
    for key, p in occupied.items():
        reserve(building_index, p, key)
    anchors = defaultdict(set)
    for r in routing["routes"]:
        anchors[r["source"]].add(tuple(r["path"][0]))
        anchors[r["target"]].add(tuple(r["path"][-1]))
    # Civic entrances also pin a building even when no semantic trip uses it.
    for s in routing["streetGrid"]["segments"]:
        if s.get("entrance"):
            for p in (s["start"], s["end"]):
                nearby = {
                    key
                    for cell in buckets(bounds([p]), 0)
                    for key in building_index[cell]
                }
                for key in sorted(nearby):
                    b = by_id[key]
                    if (
                        b["x"] <= p[0] <= b["x"] + b["width"]
                        and b["z"] <= p[1] <= b["z"] + b["depth"]
                    ):
                        anchors[b["entityId"]].add(tuple(p))
    districts = {d["id"]: d for d in scene["districts"]}
    result, rejected = {}, Counter()
    checks = 0
    for b in sorted(scene["buildings"], key=lambda b: b["entityId"]):
        identity = b["entityId"]
        center = [b["x"] + b["width"] / 2, b["z"] + b["depth"] / 2]
        pivot = center
        candidates = []
        local = {
            i for cell in buckets(bounds([center]), 21) for i in street_index[cell]
        }
        ranked = sorted(
            (streets[i] for i in sorted(local)),
            key=lambda s: (math.dist(center, nearest(center, s[1], s[2])), s[0], s[1]),
        )[:6]
        checks += len(local)
        if checks > MAX_CHECKS:
            raise ValueError("frontage parcel check limit")
        for sid, a, end, width in ranked:
            q = nearest(center, a, end)
            distance = math.dist(center, q)
            if distance > 21 or distance < 1e-6:
                continue
            angle = math.atan2(end[1] - a[1], end[0] - a[0])
            # Local front is +Z. Turn it toward the selected street, preserving
            # actual rectangular dimensions instead of reducing to square symmetry.
            if (
                -math.sin(angle) * (q[0] - center[0])
                + math.cos(angle) * (q[1] - center[1])
                < 0
            ):
                angle += math.pi
            angle = (angle + math.pi) % (2 * math.pi) - math.pi
            move = (
                min(7, max(0, distance - width / 2 - b["depth"] / 2 - 1))
                if not anchors[identity]
                else 0
            )
            for amount in sorted({0, move / 2, move}, reverse=True):
                shift = [(q[j] - center[j]) * amount / distance for j in (0, 1)]
                poly = transform(corners(b), pivot, angle, shift)

                def on_boundary(point):
                    return any(
                        math.dist(point, nearest(point, a, c)) < 1e-7
                        for a, c in zip(poly, poly[1:] + poly[:1])
                    )

                if any(not on_boundary(p) for p in anchors[identity]):
                    continue
                physical = transform([center], pivot, angle, shift)[0]
                if math.dist(center, physical) > 7 + 1e-8:
                    continue
                frontage = (
                    math.dist(physical, nearest(physical, a, end))
                    - b["depth"] / 2
                    - width / 2
                )
                candidates.append(
                    (
                        distance,
                        frontage,
                        math.dist(center, physical),
                        sid,
                        angle,
                        shift,
                        poly,
                        physical,
                    )
                )
        for _, frontage, _, sid, angle, shift, poly, physical in sorted(candidates):
            owner = districts[b["districtId"]]
            if not inside(poly, owner.get("footprint", [owner])):
                rejected["ownership"] += 1
                continue
            nearby = set()
            for cell in buckets(bounds(poly), 1):
                nearby.update(road_index[cell])
            other_buildings = {
                key for cell in buckets(bounds(poly), 0) for key in building_index[cell]
            } - {identity}
            checks += len(other_buildings) + len(nearby)
            if checks > MAX_CHECKS:
                raise ValueError("frontage parcel check limit")
            if any(overlap(poly, occupied[key]) for key in sorted(other_buildings)):
                rejected["building"] += 1
                continue
            if any(overlap(poly, road_polys[i]) for i in sorted(nearby)):
                rejected["road"] += 1
                continue
            parts = [
                dict(p, footprint=transform(corners(p), pivot, angle, shift))
                for p in building_parts(b)
            ]
            # A small facade canopy identifies the local +Z front. It stays
            # inside the certified envelope and is visual, not a new entity.
            canopy = dict(
                x=b["x"] + b["width"] * 0.275,
                z=b["z"] + b["depth"] * 0.92,
                width=b["width"] * 0.45,
                depth=b["depth"] * 0.08,
                y=b["height"] * 0.18,
                height=min(0.25, b["height"] * 0.1),
                shade=0.45,
                kind="frontage-marker",
            )
            parts.append(
                dict(canopy, footprint=transform(corners(canopy), pivot, angle, shift))
            )
            result[identity] = dict(
                entityId=identity,
                districtId=b["districtId"],
                streetId=sid,
                angle=angle,
                pivot=pivot,
                shift=shift,
                center=physical,
                footprint=poly,
                parts=parts,
                frontageEdge=[poly[2], poly[3]],
                facing=[-math.sin(angle), math.cos(angle)],
                entrance=list(next(iter(anchors[identity])))
                if len(anchors[identity]) == 1
                else None,
                frontagePoint=[(poly[2][j] + poly[3][j]) / 2 for j in (0, 1)],
                displacement=math.dist(center, physical),
                frontageGap=frontage,
                pinnedDoors=[list(p) for p in sorted(anchors[identity])],
            )
            occupied[identity] = poly
            reserve(building_index, poly, identity)
            break
    return dict(
        version="street-parcels/0.1",
        semantic=False,
        buildings=result,
        changedFootprintIds=sorted(
            b["entityId"]
            for b in scene["buildings"]
            if b["entityId"] in result
            and {tuple(round(v, 7) for v in p) for p in corners(b)}
            != {
                tuple(round(v, 7) for v in p)
                for p in result[b["entityId"]]["footprint"]
            }
        ),
        rejected=dict(sorted(rejected.items())),
        checks=checks,
        basis="physical street frontage; original file identity and doorway anchors",
    )
