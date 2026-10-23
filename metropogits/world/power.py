"""Bounded capacity-constrained power cells on connected convex land."""

import math

from .geometry import area, centroid, clip, dot, partition, point, shared_boundaries

VERSION = "clipped-power/0.1"
MAX_CELLS = 7
MAX_DISTRICT_CELLS = 16
MAX_ITERATIONS = 32
AREA_TOLERANCE = 0.015


def _solve(matrix, values):
    """Small deterministic pivoted elimination; no unbounded numeric dependency."""
    rows = [list(row) + [value] for row, value in zip(matrix, values)]
    n = len(rows)
    for column in range(n):
        pivot = max(range(column, n), key=lambda i: abs(rows[i][column]))
        if abs(rows[pivot][column]) < 1e-12:
            return None
        rows[column], rows[pivot] = rows[pivot], rows[column]
        scale = rows[column][column]
        rows[column] = [v / scale for v in rows[column]]
        for i in range(n):
            if i != column:
                scale = rows[i][column]
                rows[i] = [a - scale * b for a, b in zip(rows[i], rows[column])]
    return [row[-1] for row in rows]


def _cells(polygon, sites, weights):
    result = []
    for i, p in enumerate(sites):
        cell = polygon
        for j, q in enumerate(sites):
            if i != j:
                normal = [2 * (q[k] - p[k]) for k in (0, 1)]
                limit = dot(q, q) - dot(p, p) + weights[i] - weights[j]
                cell = clip(cell, normal, limit)
        result.append(cell)
    return result


def power_partition(polygon, demands, seed, *, sites=None, max_cells=MAX_CELLS, voronoi=False):
    """Newton area balancing with backtracking; explicit shared-cut fallback."""
    if (
        not 3 <= len(polygon) <= 512
        or any(
            len(p) != 2 or any(not math.isfinite(v) or abs(v) > 100000 for v in p)
            for p in polygon
        )
        or area(polygon) < 1
        or any(
            (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
            < -0.001 * max(math.dist(a, b), math.dist(b, c))
            or math.dist(a, b) < 0.00001
            for a, b, c in zip(
                polygon, polygon[1:] + polygon[:1], polygon[2:] + polygon[:2]
            )
        )
    ):
        raise ValueError("power partition requires bounded CCW convex land")
    demands = sorted(demands)
    if (
        not 1 <= len(demands) <= max_cells
        or len({key for key, _ in demands}) != len(demands)
        or any(not math.isfinite(value) or value <= 0 for _, value in demands)
    ):
        raise ValueError("invalid power cell demands or cell limit")
    baseline = partition(polygon, demands, seed)
    if len(demands) == 1:
        return baseline, dict(
            algorithm="unsplit/0.1", iterations=0, maxRelativeAreaError=0
        )
    if sites is None:
        # Seeded blue-noise Voronoi sites per planning area; bisection centroids
        # remain the deterministic fallback when the land cannot host them.
        from .seed import draw
        # Only for a cold plan: growth hints must keep the previous bisection frames stable.
        scattered = voronoi_sites(polygon, len(demands), seed) if voronoi and len(demands) > 1 else None
        if scattered:
            order = sorted(range(len(scattered)), key=lambda i: draw(seed, 20_000 + i))
            sites = [scattered[i] for i in order]
        else:
            sites = [centroid(baseline[key]) for key, _ in demands]
    sites = list(sites)
    weights = [0.0] * len(sites)
    total = sum(value for _, value in demands)
    targets = [area(polygon) * value / total for _, value in demands]
    cells = _cells(polygon, sites, weights)

    def error(parts):
        return max(abs(area(p) - target) / target for p, target in zip(parts, targets))

    reason = "iteration limit"
    iteration = 0
    for iteration in range(MAX_ITERATIONS):
        if error(cells) <= AREA_TOLERANCE:
            quantized = {
                key: [point(p) for p in cell] for (key, _), cell in zip(demands, cells)
            }
            quantized, _ = shared_boundaries(quantized, polygon)
            return quantized, dict(
                algorithm=VERSION,
                iterations=iteration,
                maxRelativeAreaError=error(list(quantized.values())),
            )
        n = len(sites)
        jacobian = [[0.0] * n for _ in sites]
        for i, cell in enumerate(cells):
            for j, q in enumerate(sites):
                if i == j:
                    continue
                p = sites[i]
                normal = [2 * (q[k] - p[k]) for k in (0, 1)]
                limit = dot(q, q) - dot(p, p) + weights[i] - weights[j]
                boundary = sum(
                    math.dist(a, b)
                    for a, b in zip(cell, cell[1:] + cell[:1])
                    if abs(dot(a, normal) - limit) < 1e-5
                    and abs(dot(b, normal) - limit) < 1e-5
                )
                derivative = boundary / max(1e-9, 2 * math.dist(p, q))
                jacobian[i][i] += derivative
                jacobian[i][j] -= derivative
        delta = _solve(
            [row[:-1] for row in jacobian[:-1]],
            [target - area(cell) for target, cell in zip(targets[:-1], cells[:-1])],
        )
        if delta is None:
            reason = "singular area Jacobian"
            break
        for step in range(16):
            proposed = [w + d * 0.5**step for w, d in zip(weights, delta + [0])]
            updated = _cells(polygon, sites, proposed)
            if all(len(p) >= 3 and area(p) > 0.01 for p in updated) and error(
                updated
            ) < error(cells):
                weights, cells = proposed, updated
                break
        else:
            reason = "area balancing stalled"
            break
    baseline, _ = shared_boundaries(baseline, polygon)
    return baseline, dict(
        algorithm="capacity-bisection/0.1",
        iterations=iteration,
        maxRelativeAreaError=error(list(baseline.values())),
        fallbackReason=reason,
    )


def voronoi_sites(polygon, count, seed):
    """Deterministic blue-noise sites: seeded scatter relaxed by Lloyd iterations."""
    from .geometry import bounds, inside
    from .seed import draw

    x0, z0, x1, z1 = bounds(polygon)
    sites, counter = [], 0
    while len(sites) < count and counter < 4000:
        candidate = [x0 + (x1 - x0) * draw(seed, counter), z0 + (z1 - z0) * draw(seed, counter + 1)]
        counter += 2
        if inside(candidate, polygon, 0.02 * math.sqrt(area(polygon))):
            sites.append(candidate)
    if len(sites) < count:
        return None
    for _ in range(5):
        cells = _cells(polygon, sites, [0.0] * count)
        if any(len(c) < 3 for c in cells):
            return None
        sites = [centroid(c) for c in cells]
    return sites


def voronoi_districts(polygon, demands, seed):
    """Seeded weighted-Voronoi districts with exact-enough capacity areas.

    Returns (polygons, allocation) or None when the land or balancing does not
    support it; callers then keep the proven capacity-bisection geography.
    """
    from .seed import draw

    demands = sorted(demands)
    if not 2 <= len(demands) <= MAX_DISTRICT_CELLS:
        return None
    sites = voronoi_sites(polygon, len(demands), seed)
    if sites is None:
        return None
    order = sorted(range(len(sites)), key=lambda i: draw(seed, 10_000 + i))
    sites = [sites[i] for i in order]
    try:
        polygons, allocation = power_partition(
            polygon, demands, seed, sites=sites, max_cells=MAX_DISTRICT_CELLS)
    except ValueError:
        return None
    if allocation["algorithm"] != VERSION:
        return None
    return polygons, dict(allocation, algorithm="weighted-voronoi/0.1")
