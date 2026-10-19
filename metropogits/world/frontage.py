"""Shared bounded corridor reservation and frontage sampling for new planners."""

import math
from collections import defaultdict

from metropogits.street_diagonals import overlap
from .geometry import bounds, inside, inset, nearest, point, rectangle, ribbon
from .radial import _clipped

MAX_SEGMENTS = 12_000
MAX_CANDIDATES = 100_000
MAX_INDEX = 1_000_000
MAX_CHECKS = 1_000_000


def frame(polygon, rotation=0, *, axis=None):
    a, b = max(zip(polygon, polygon[1:] + polygon[:1]), key=lambda e: math.dist(*e))
    angle = (math.atan2(b[1] - a[1], b[0] - a[0]) if axis is None else axis) + rotation
    c, s = math.cos(angle), math.sin(angle)

    def local(p):
        return [c * p[0] + s * p[1], -s * p[0] + c * p[1]]

    def world(p):
        return point([c * p[0] - s * p[1], s * p[0] + c * p[1]])

    return angle, local, world


def add_corridor(lanes, polygon, path, identity, width, *, connect=True):
    inner = inset(polygon, 5)
    if len(inner) < 3:
        return
    edges = list(zip(polygon, polygon[1:] + polygon[:1]))
    distance = 0.0
    for i, (a, b) in enumerate(zip(path, path[1:])):
        length = math.dist(a, b)
        if length < 0.001:
            continue
        clipped = _clipped(a, b, inner)
        if clipped:
            start, end = clipped
            lanes.append(
                dict(
                    id=f"{identity}:{i}",
                    group=identity,
                    start=start,
                    end=end,
                    width=width,
                    access=False,
                    offset=distance + math.dist(a, start),
                )
            )
            if connect:
                for j, (original, endpoint) in enumerate(zip((a, b), clipped)):
                    if math.dist(original, endpoint) < 0.001 and not (
                        i == 0 and j == 0 or i == len(path) - 2 and j == 1
                    ):
                        continue
                    target = min(
                        (nearest(endpoint, p, q) for p, q in edges),
                        key=lambda p: math.dist(endpoint, p),
                    )
                    if math.dist(endpoint, target) > 0.001:
                        lanes.append(
                            dict(
                                id=f"{identity}:{i}:boundary:{j}",
                                start=endpoint,
                                end=point(target),
                                width=3,
                                access=False,
                            )
                        )
        distance += length
        if len(lanes) > MAX_SEGMENTS:
            raise ValueError("world frontage street limit")


def frontage_slots(polygon, lanes, *, pitch=9, width=8, depth=8, setback=6.5, profile):
    inner = inset(polygon, 5)
    if len(inner) < 3:
        return []
    cells, polygons = defaultdict(list), []
    entries = checks = seen = 0

    def keys(poly):
        x0, z0, x1, z1 = bounds(poly)
        if max(x1 - x0, z1 - z0) > 10000:
            raise ValueError("world frontage spatial extent limit")
        return [
            (x, z)
            for x in range(math.floor(x0 / 16), math.floor(x1 / 16) + 1)
            for z in range(math.floor(z0 / 16), math.floor(z1 / 16) + 1)
        ]

    def reserve(poly):
        nonlocal entries
        identity = len(polygons)
        polygons.append(poly)
        buckets = keys(poly)
        entries += len(buckets)
        if entries > MAX_INDEX:
            raise ValueError("world frontage spatial index limit")
        for k in buckets:
            cells[k].append(identity)

    for lane in lanes:
        reserve(ribbon(lane["start"], lane["end"], lane["width"] + 0.1))
    for a, b in zip(polygon, polygon[1:] + polygon[:1]):
        reserve(ribbon(a, b, 3.6))
    slots = []
    for lane in lanes:
        if "group" not in lane or not lane.get("frontage", True):
            continue
        a, b = lane["start"], lane["end"]
        length = math.dist(a, b)
        tangent = math.atan2(b[1] - a[1], b[0] - a[0])
        offset = lane["offset"]
        for column in range(
            math.ceil(offset / pitch), math.floor((offset + length) / pitch) + 1
        ):
            t = (column * pitch - offset) / length
            street = point([a[j] + t * (b[j] - a[j]) for j in (0, 1)])
            for side in (-1, 1):
                seen += 1
                if seen > MAX_CANDIDATES:
                    raise ValueError("world frontage candidate limit")
                angle = tangent + (math.pi if side == 1 else 0)
                normal = [-math.sin(angle), math.cos(angle)]
                center = point([street[j] + setback * normal[j] for j in (0, 1)])
                parcel = rectangle(center, angle, width, depth)
                if not all(inside(p, inner) for p in parcel):
                    continue
                blocked = False
                for identity in sorted(
                    {k for cell in keys(parcel) for k in cells[cell]}
                ):
                    checks += 1
                    if checks > MAX_CHECKS:
                        raise ValueError("world frontage clearance work limit")
                    if overlap(parcel, polygons[identity]):
                        blocked = True
                        break
                if blocked:
                    continue
                reserve(parcel)
                slots.append(
                    dict(
                        id=f"{lane['group']}:{column}:{side}",
                        center=center,
                        angle=angle,
                        polygon=parcel,
                        streetPoint=street,
                        entrance=point([center[j] - 3 * normal[j] for j in (0, 1)]),
                        laneId=lane["group"],
                        blockProfile=profile,
                    )
                )
    return slots
