"""Seeded organic lakes and hills: irregular shores, multi-summit relief, scale-aware counts.

Collision, no-build and road reserves stay on the convex hull of the visible
shape (the existing planners require convex reserves). Only the rendered mesh
is irregular, and it always lies inside that hull. Procedural scenery, not
geography claims or source facts.
"""

import math

from metropogits.street_diagonals import hull
from .geometry import point, q
from .landscape import expanded
from .seed import derive, draw


def organic_counts(local, scale):
    """Counts follow city size and seed; lakes may be absent, hills never fully."""

    def count(label, expected, low, high):
        spread = 0.3 + 1.5 * draw(derive(local, label))
        extra = draw(derive(local, label, "remainder"))
        return max(low, min(high, int(expected * spread + extra)))

    return {
        "LAKE": count("organic-lakes", scale / 300, 0, 4),
        "HILL": count("organic-hills", scale / 150, 1, 7),
    }


def organic_size(seed, scale):
    """Heavy-tailed sizes: many modest features, occasionally a large one."""
    major = min(70, max(7, scale * (0.02 + 0.06 * draw(seed, 2) ** 1.6)))
    return major, major * (0.4 + 0.5 * draw(seed, 3))


def _outline(center, major, minor, yaw, seed, *, count, roughness):
    """Star-shaped irregular outline about its centre (low harmonics, seeded)."""
    harmonics = [
        (k, roughness * (draw(seed, 100 + k) - 0.25) / (k - 1), draw(seed, 120 + k) * math.tau)
        for k in range(2, 7)
    ]
    u, v = [math.cos(yaw), math.sin(yaw)], [-math.sin(yaw), math.cos(yaw)]
    ring = []
    for i in range(count):
        theta = (i + 0.3 * (draw(seed, 140 + i) - 0.5)) * math.tau / count
        radius = 1 + sum(a * math.cos(k * theta + phase) for k, a, phase in harmonics)
        radius = max(0.62, min(1.4, radius))
        x, z = major * radius * math.cos(theta), minor * radius * math.sin(theta)
        ring.append([center[j] + u[j] * x + v[j] * z for j in (0, 1)])
    return ring


def _reserves(ring, no_build, road):
    polygon = [point(p) for p in reversed(hull([point(p) for p in ring]))]
    return (polygon, [point(p) for p in expanded(polygon, no_build)],
            [point(p) for p in expanded(polygon, road)])


def _up(face):
    """Order a face so its first triangle points up (schema allows 64 faces)."""
    a, b, c = face[0], face[1], face[2]
    ny = (b[2] - a[2]) * (c[0] - a[0]) - (b[0] - a[0]) * (c[2] - a[2])
    return face if ny >= 0 else list(reversed(face))


def organic_lake(center, major, minor, yaw, seed):
    ring = _outline(center, major, minor, yaw, seed, count=28, roughness=0.34)
    polygon, no_build, road = _reserves(ring, 2, 6.5)
    inner = [[center[0] + (p[0] - center[0]) * 0.86, center[1] + (p[1] - center[1]) * 0.86] for p in ring]
    faces = []
    n = len(ring)
    for i in range(n):
        j = (i + 1) % n
        shore = ("#83927a", "#8e9b80", "#7a8a73")[i % 3]
        a, b = [ring[i][0], 0.06, ring[i][1]], [ring[j][0], 0.06, ring[j][1]]
        c, d = [inner[j][0], 0.09, inner[j][1]], [inner[i][0], 0.09, inner[i][1]]
        faces.append(dict(points=_up([a, b, c, d]), color=shore))
        water = ("#397c91", "#3a8196", "#357789")[i % 3]
        faces.append(dict(points=_up([[center[0], 0.09, center[1]], [inner[i][0], 0.09, inner[i][1]],
                                      [inner[j][0], 0.09, inner[j][1]]]), color=water))
    return dict(id="world:nature:" + derive(seed), kind="LAKE", center=point(center), polygon=polygon,
                noBuildPolygon=no_build, roadPolygon=road, height=0.09, faces=_rounded(faces))


def organic_hill(center, major, minor, yaw, seed):
    count, rings = 15, (1.0, 0.72, 0.44, 0.2)
    outline = _outline(center, major, minor, yaw, seed, count=count, roughness=0.5)
    polygon, no_build, road = _reserves(outline, 2, 6.5)
    height = q(min(38, max(7, major * (0.32 + 0.26 * draw(seed, 3)))))
    summit_count = 1 + (draw(seed, 4) > 0.55) + (draw(seed, 5) > 0.85)
    summits = []
    for s in range(summit_count):
        angle = draw(seed, 160 + s) * math.tau
        reach = major * (0.05 if s == 0 else 0.22 + 0.16 * draw(seed, 170 + s))
        summits.append((center[0] + math.cos(angle) * reach, center[1] + math.sin(angle) * reach,
                        1 if s == 0 else 0.62 + 0.28 * draw(seed, 180 + s),
                        major * (0.5 + 0.3 * draw(seed, 190 + s))))

    def elevation(x, z, rho):
        if rho >= 1:
            return 0.005
        crest = max(a * math.exp(-(math.hypot(x - sx, z - sz) / r) ** 2) for sx, sz, a, r in summits)
        noise = 0.93 + 0.14 * draw(seed, 300 + int(abs(x * 3.1 + z * 1.7)) % 400)
        return q(max(0.005, height * (1 - rho ** 1.8) ** 1.3 * (0.42 + 0.58 * crest) * noise))

    grid = []
    for rho in rings:
        row = []
        for p in outline:
            x, z = center[0] + (p[0] - center[0]) * rho, center[1] + (p[1] - center[1]) * rho
            row.append([q(x), elevation(x, z, rho), q(z)])
        grid.append(row)
    peak = max(summits, key=lambda s: s[2])
    top = [q(peak[0]), q(max(max(v[1] for v in row) for row in grid) * 1.04), q(peak[1])]
    faces = []

    def shade(y, i, k):
        t = y / height
        palette = (("#58704f", "#5f7a56", "#55704e") if t < 0.22 else
                   ("#6a8260", "#738868", "#678058") if t < 0.5 else
                   ("#7f8b73", "#8a8f7e", "#778670") if t < 0.76 else
                   ("#9a9b92", "#a9aaa2", "#8f9189"))
        return palette[(i + k + int(draw(seed, 400 + i * 7 + k) * 3)) % 3]

    for k in range(len(rings) - 1):
        for i in range(count):
            j = (i + 1) % count
            a, b, c, d = grid[k][i], grid[k + 1][i], grid[k + 1][j], grid[k][j]
            average = (a[1] + b[1] + c[1] + d[1]) / 4
            faces.append(dict(points=_up([a, b, c, d]), color=shade(average, i, k)))
    for i in range(count):
        j = (i + 1) % count
        faces.append(dict(points=_up([grid[-1][i], top, grid[-1][j]]), color=shade(height, i, 9)))
    return dict(id="world:nature:" + derive(seed), kind="HILL", center=point(center), polygon=polygon,
                noBuildPolygon=no_build, roadPolygon=road, height=height, faces=faces,
                landform="RIDGE" if summit_count > 1 and major / minor > 1.8 else "HILLS")


def _rounded(faces):
    return [dict(points=[[q(v) for v in p] for p in f["points"]], color=f["color"]) for f in faces]
