"""Bounded orbital/spoke streets and tangential frontage parcels on convex land."""

import math
from collections import defaultdict

from metropogits.street_diagonals import overlap
from .geometry import bounds, centroid, inside, inset, nearest, point, rectangle, ribbon
from .seed import draw

MAX_CANDIDATES = 100_000
MAX_STREETS = 12_000
MAX_CHECKS = 1_000_000
MAX_INDEX = 1_000_000


def _clipped(a, b, polygon):
    """Convex half-plane segment clipping, before output coordinate quantization."""
    lo, hi = 0.0, 1.0
    for p, q in zip(polygon, polygon[1:] + polygon[:1]):
        dx, dz = q[0] - p[0], q[1] - p[1]
        first = dx * (a[1] - p[1]) - dz * (a[0] - p[0])
        change = dx * (b[1] - a[1]) - dz * (b[0] - a[0])
        if abs(change) < 1e-9:
            if first < -1e-7:
                return None
            continue
        t = -first / change
        if change > 0:
            lo = max(lo, t)
        else:
            hi = min(hi, t)
        if lo >= hi:
            return None
    a, b = [point([a[j] + t * (b[j] - a[j]) for j in (0, 1)]) for t in (lo, hi)]
    return [a, b] if math.dist(a, b) > 0.001 else None


def radial_slots(polygon, seed):
    """Return the same slot/lane interface as GRID; no semantic input or claims."""
    inner = inset(polygon, 5)
    if len(inner) < 3:
        return [], [], 0
    hub = centroid(inner)
    radius = max(math.dist(hub, p) for p in inner)
    if radius > 5000:
        raise ValueError("world radial spatial extent limit")
    phase = draw(seed) * math.tau
    spokes = 3 + int(draw(seed, 1) * 3)
    lanes, rings = [], []

    def emit(identity, a, b, width):
        if math.dist(a, b) > 0.001:
            lanes.append(
                dict(
                    id=identity, start=point(a), end=point(b), width=width, access=False
                )
            )
        if len(lanes) > MAX_STREETS:
            raise ValueError("world radial street limit")

    edges = list(zip(polygon, polygon[1:] + polygon[:1]))
    for i in range(spokes):
        angle = phase + i * math.tau / spokes
        end = [
            hub[0] + math.cos(angle) * (radius + 20),
            hub[1] + math.sin(angle) * (radius + 20),
        ]
        path = _clipped(hub, end, polygon)
        if path:
            emit(f"spoke:{i}", *path, 4)

    for ring in range(math.ceil(radius / 24)):
        r = 22 + ring * 24
        count = max(24, math.ceil(math.tau * r / 8))
        if count > 4096:
            raise ValueError("world radial ring complexity limit")
        circle = [
            [
                hub[0] + math.cos(phase + i * math.tau / count) * r,
                hub[1] + math.sin(phase + i * math.tau / count) * r,
            ]
            for i in range(count)
        ]
        ring_segments = {}
        for i, (a, b) in enumerate(zip(circle, circle[1:] + circle[:1])):
            path = _clipped(a, b, inner)
            if not path:
                continue
            ring_segments[i] = path
            emit(f"orbit:{ring}:{i}", *path, 3.5)
            # Only actual clipped ends need boundary access; regular ring
            # vertices remain connected to their next segment and the spokes.
            for j, (original, clipped) in enumerate(zip((a, b), path)):
                if math.dist(original, clipped) < 0.001:
                    continue
                target = min(
                    (nearest(clipped, p, q) for p, q in edges),
                    key=lambda p: math.dist(clipped, p),
                )
                emit(f"orbit:{ring}:{i}:end:{j}", clipped, target, 3)
        rings.append((ring, r, count, ring_segments))

    cells = defaultdict(list)
    shapes = []
    checks = candidates_seen = index_entries = 0

    def keys(poly):
        x0, z0, x1, z1 = bounds(poly)
        return [
            (x, z)
            for x in range(math.floor(x0 / 16), math.floor(x1 / 16) + 1)
            for z in range(math.floor(z0 / 16), math.floor(z1 / 16) + 1)
        ]

    def reserve(poly):
        nonlocal index_entries
        identity = len(shapes)
        shapes.append(poly)
        buckets = keys(poly)
        index_entries += len(buckets)
        if index_entries > MAX_INDEX:
            raise ValueError("world radial spatial index limit")
        for key in buckets:
            cells[key].append(identity)

    for lane in lanes:
        reserve(ribbon(lane["start"], lane["end"], lane["width"] + 0.1))
    # Reserve the actual boundary road too, not only the inset clipping polygon.
    for a, b in edges:
        reserve(ribbon(a, b, 3.6))
    slots = []
    for ring, r, count, segments in rings:
        for side in (-1, 1):
            # Inner frontage is shorter; give it fewer, safely spaced lots.
            lots = max(1, math.floor(math.tau * (r + side * 6.5) / 10))
            for column in range(lots):
                candidates_seen += 1
                if candidates_seen > MAX_CANDIDATES:
                    raise ValueError("world radial parcel candidate limit")
                theta = phase + (column + 0.5) * math.tau / lots
                index = int(((theta - phase) % math.tau) / math.tau * count) % count
                path = segments.get(index)
                if not path:
                    continue
                a, b = path
                guess = [hub[0] + math.cos(theta) * r, hub[1] + math.sin(theta) * r]
                frontage = point(nearest(guess, a, b))
                tangent = math.atan2(b[1] - a[1], b[0] - a[0])
                angle = tangent + (math.pi if side == 1 else 0)
                normal = [-math.sin(angle), math.cos(angle)]
                center = point([frontage[j] + normal[j] * 6.5 for j in (0, 1)])
                parcel = rectangle(center, angle, 8, 8)
                if not all(inside(p, inner) for p in parcel):
                    continue
                near = {k for cell in keys(parcel) for k in cells[cell]}
                blocked = False
                for identity in sorted(near):
                    checks += 1
                    if checks > MAX_CHECKS:
                        raise ValueError("world radial clearance work limit")
                    if overlap(parcel, shapes[identity]):
                        blocked = True
                        break
                if blocked:
                    continue
                reserve(parcel)
                slots.append(
                    dict(
                        id=f"radial:{ring}:{side}:{column}",
                        center=center,
                        angle=angle,
                        polygon=parcel,
                        entrance=point([center[j] - normal[j] * 3 for j in (0, 1)]),
                        streetPoint=frontage,
                        laneId=f"orbit:{ring}:{index}",
                    )
                )
    return slots, lanes, phase
