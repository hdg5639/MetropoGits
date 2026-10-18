"""Connect actual neighborhood access ports, not every power-cell boundary."""

import math

from .geometry import centroid, nearest, point


def access_corridors(
    polygons, local_roads, parent, *, return_ports=False, affinity=None
):
    ports = {key: set() for key in polygons}
    edges = {}
    outer = []
    for key, poly in polygons.items():
        for a, b in zip(poly, poly[1:] + poly[:1]):
            edges.setdefault(tuple(sorted((tuple(a), tuple(b)))), []).append(key)
            midpoint = point([(a[j] + b[j]) / 2 for j in (0, 1)])
            if (
                min(
                    math.dist(midpoint, nearest(midpoint, p, q))
                    for p, q in zip(parent, parent[1:] + parent[:1])
                )
                < 0.001
            ):
                outer.append((math.dist(a, b), key, tuple(midpoint)))
        for road in local_roads[key]:
            for p in (road["start"], road["end"]):
                if (
                    min(
                        math.dist(p, nearest(p, a, b))
                        for a, b in zip(poly, poly[1:] + poly[:1])
                    )
                    < 0.001
                ):
                    ports[key].add(tuple(p))
    # Stable minimum spanning adjacency: one inter-zone access port per retained
    # connection. Shared borders alone do not cause a road to be emitted.
    roots = {key: key for key in polygons}

    def root(key):
        while roots[key] != key:
            key = roots[key]
        return key

    adjacency = []
    for (a, b), owners in edges.items():
        if len(owners) == 2:
            i, j = sorted(owners)
            adjacency.append(
                (
                    math.dist(centroid(polygons[i]), centroid(polygons[j]))
                    / (1 + math.log1p((affinity or {}).get((i, j), 0))),
                    i,
                    j,
                    a,
                    b,
                )
            )
    for _, i, j, a, b in sorted(adjacency):
        if root(i) != root(j):
            roots[root(i)] = root(j)
            p = tuple(point([(a[k] + b[k]) / 2 for k in (0, 1)]))
            ports[i].add(p)
            ports[j].add(p)
    if len({root(key) for key in polygons}) != 1 or not outer:
        raise ValueError("zoning adjacency lacks connected district access")
    _, owner, p = max(outer)
    ports[owner].add(p)
    roads = []
    for key, poly in polygons.items():
        # Connect required frontage/neighbor ports by the shortest perimeter
        # subtree (remove the largest port-free arc). Do not draw closed cells.
        segments, length = [], 0.0
        for a, b in zip(poly, poly[1:] + poly[:1]):
            segments.append((length, a, b))
            length += math.dist(a, b)
        located = []
        for p in sorted(ports[key]):
            offset, a, b = min(
                segments, key=lambda s: math.dist(p, nearest(p, s[1], s[2]))
            )
            located.append(
                ((offset + math.dist(a, nearest(p, a, b))) % length, list(p))
            )
        located.sort()
        if len(located) < 2:
            continue
        gaps = [
            ((located[(i + 1) % len(located)][0] - p[0]) % length, i)
            for i, p in enumerate(located)
        ]
        gap, index = max(gaps)
        start, p = located[(index + 1) % len(located)]
        finish = start + length - gap
        path = [(start, p), (finish, located[index][1])]
        for offset, a, _ in segments:
            t = offset + (length if offset < start else 0)
            if start + 0.0001 < t < finish - 0.0001:
                path.append((t, a))
        # Include ports explicitly, so numerical projection cannot disconnect
        # a door-facing street from its boundary access point.
        for offset, p in located:
            t = offset + (length if offset < start else 0)
            if start < t < finish:
                path.append((t, p))
        path.sort(key=lambda item: item[0])
        for (_, a), (_, b) in zip(path, path[1:]):
            if math.dist(a, b) > 0.001:
                roads.append(
                    dict(start=point(a), end=point(b), width=3.5, access=False)
                )
    return (roads, ports) if return_ports else roads
