"""Small bounded convex geometry kernel for the flat world prototype."""

import math

EPS = 1e-7


def q(value):
    value = round(float(value), 4)
    return 0.0 if value == 0 else value


def point(p):
    return [q(p[0]), q(p[1])]


def area(poly):
    return (
        abs(sum(a[0] * b[1] - a[1] * b[0] for a, b in zip(poly, poly[1:] + poly[:1])))
        / 2
    )


def bounds(poly):
    return [
        min(p[0] for p in poly),
        min(p[1] for p in poly),
        max(p[0] for p in poly),
        max(p[1] for p in poly),
    ]


def centroid(poly):
    # Vertex average lies inside every nonempty convex polygon.
    return [sum(p[j] for p in poly) / len(poly) for j in (0, 1)]


def shared_boundaries(polygons, envelope):
    """Insert the SAME quantized T vertices into both incident polygon edges."""
    vertices = sorted(
        {tuple(p) for poly in [envelope, *polygons.values()] for p in poly}
    )
    if len(vertices) * sum(len(p) for p in [envelope, *polygons.values()]) > 2_000_000:
        raise ValueError("world shared-boundary work limit")

    def split(poly):
        output = []
        for a, b in zip(poly, poly[1:] + poly[:1]):
            candidates = [
                p for p in vertices if math.dist(p, nearest(p, a, b)) <= 0.0002
            ]
            candidates.sort(key=lambda p: math.dist(a, p))
            for p in candidates:
                p = list(p)
                if p != b and (not output or p != output[-1]):
                    output.append(p)
        if output[-1] == output[0]:
            output.pop()
        return output

    return {k: split(p) for k, p in polygons.items()}, split(envelope)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def clip(poly, normal, limit):
    result = []
    for a, b in zip(poly, poly[1:] + poly[:1]):
        da, db = dot(a, normal) - limit, dot(b, normal) - limit
        if da <= EPS:
            result.append(a)
        if (da <= EPS) != (db <= EPS):
            t = da / (da - db)
            result.append([a[j] + t * (b[j] - a[j]) for j in (0, 1)])
    return result


def inset(poly, distance):
    result = poly
    for a, b in zip(poly, poly[1:] + poly[:1]):
        length = math.dist(a, b)
        normal = [(b[1] - a[1]) / length, (a[0] - b[0]) / length]
        result = clip(result, normal, dot(a, normal) - distance)
    return result


def inside(p, poly, margin=0):
    return all(
        (b[0] - a[0]) * (p[1] - a[1]) - (b[1] - a[1]) * (p[0] - a[0])
        >= (margin - 0.00015) * math.dist(a, b)
        for a, b in zip(poly, poly[1:] + poly[:1])
    )


def rectangle(center, angle, width, depth):
    c, s = math.cos(angle), math.sin(angle)
    return [
        point([center[0] + c * x - s * z, center[1] + s * x + c * z])
        for x, z in (
            (-width / 2, -depth / 2),
            (width / 2, -depth / 2),
            (width / 2, depth / 2),
            (-width / 2, depth / 2),
        )
    ]


def nearest(p, a, b):
    delta = [b[j] - a[j] for j in (0, 1)]
    t = max(0, min(1, dot([p[j] - a[j] for j in (0, 1)], delta) / dot(delta, delta)))
    return [a[j] + t * delta[j] for j in (0, 1)]


def ribbon(a, b, width):
    length = math.dist(a, b)
    v = [-(b[1] - a[1]) / length * width / 2, (b[0] - a[0]) / length * width / 2]
    return [
        point([a[j] - v[j] for j in (0, 1)]),
        point([b[j] - v[j] for j in (0, 1)]),
        point([b[j] + v[j] for j in (0, 1)]),
        point([a[j] + v[j] for j in (0, 1)]),
    ]


def partition(poly, demands, seed):
    """Capacity bisection, each boundary computed once. No Voronoi claim."""
    from .seed import derive, draw

    if len(demands) == 1:
        return {demands[0][0]: [point(p) for p in poly]}
    total = sum(d for _, d in demands)
    split = min(
        range(1, len(demands)),
        key=lambda i: abs(sum(d for _, d in demands[:i]) - total / 2),
    )
    left, right = demands[:split], demands[split:]
    x0, z0, x1, z1 = bounds(poly)
    angle = (0 if x1 - x0 >= z1 - z0 else math.pi / 2) + (draw(seed) - 0.5) * 0.65
    normal = [math.cos(angle), math.sin(angle)]
    lo, hi = min(dot(p, normal) for p in poly), max(dot(p, normal) for p in poly)
    target = area(poly) * sum(d for _, d in left) / total
    for _ in range(42):
        mid = (lo + hi) / 2
        if area(clip(poly, normal, mid)) < target:
            lo = mid
        else:
            hi = mid
    # Clip both sides from this same cut, preserving a shared boundary.
    limit = (lo + hi) / 2
    a = clip(poly, normal, limit)
    b = clip(poly, [-v for v in normal], -limit)
    return {
        **partition(a, left, derive(seed, "left")),
        **partition(b, right, derive(seed, "right")),
    }
