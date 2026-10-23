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
        "LAKE": count("organic-lakes", scale / 420, 0, 3),
        "HILL": count("organic-hills", scale / 210, 1, 6),
    }


def organic_size(seed, scale, kind="LAKE"):
    """Heavy-tailed sizes: many modest features, occasionally a large one."""
    if kind == "HILL":
        major = min(95, max(9, scale * (0.028 + 0.08 * draw(seed, 2) ** 1.6)))
        return major, major * (0.42 + 0.48 * draw(seed, 3))
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


HILL_TYPES = (
    # name, weight, (profile power, profile exponent), relative height
    ("RIDGE", 0.24, (1.6, 1.1), 0.85),
    ("MASSIF", 0.26, (1.7, 1.2), 1.1),
    ("DOME", 0.22, (2.4, 0.9), 0.62),
    ("MESA", 0.14, (2.2, 0.8), 0.8),
    ("CONE", 0.14, (1.5, 1.5), 1.0),
)


def _hill_type(seed):
    pick, total = draw(seed, 6), 0.0
    for entry in HILL_TYPES:
        total += entry[1]
        if pick < total:
            return entry
    return HILL_TYPES[-1]


def organic_hill(center, major, minor, yaw, seed):
    kind, _, (power, exponent), relative = _hill_type(seed)
    if kind == "RIDGE":
        minor = min(minor, major * (0.26 + 0.16 * draw(seed, 7)))
    elif kind in ("CONE", "DOME"):
        minor = max(minor, major * (0.7 + 0.25 * draw(seed, 7)))
    count, rings = 15, (1.0, 0.72, 0.44, 0.2)
    outline = _outline(center, major, minor, yaw, seed, count=count, roughness=0.5 if kind != "DOME" else 0.28)
    polygon, no_build, road = _reserves(outline, 2, 6.5)
    height = q(min(56, max(8, major * (0.42 + 0.3 * draw(seed, 3)) * relative)))
    u, v = [math.cos(yaw), math.sin(yaw)], [-math.sin(yaw), math.cos(yaw)]
    summits = []  # x, z, amplitude, radius
    if kind == "RIDGE":
        peaks = 2 + int(draw(seed, 4) * 3)
        for s in range(peaks):
            t = (s + 0.5) / peaks * 1.5 - 0.75 + (draw(seed, 160 + s) - 0.5) * 0.12
            across = (draw(seed, 165 + s) - 0.5) * minor * 0.3
            summits.append((center[0] + u[0] * major * t + v[0] * across,
                            center[1] + u[1] * major * t + v[1] * across,
                            0.62 + 0.38 * draw(seed, 180 + s), major * (0.28 + 0.1 * draw(seed, 190 + s))))
    elif kind == "MASSIF":
        for s in range(3 + int(draw(seed, 4) * 3)):
            angle, reach = draw(seed, 160 + s) * math.tau, major * (0.05 + 0.4 * draw(seed, 170 + s))
            summits.append((center[0] + math.cos(angle) * reach, center[1] + math.sin(angle) * reach,
                            0.55 + 0.45 * draw(seed, 180 + s), major * (0.26 + 0.14 * draw(seed, 190 + s))))
    else:
        offset = major * 0.12 * (draw(seed, 160) - 0.5)
        summits.append((center[0] + u[0] * offset, center[1] + u[1] * offset, 1.0,
                        major * (0.55 if kind == "DOME" else 0.42)))
    phase = [draw(seed, 600 + n) * math.tau for n in range(4)]
    plateau = 0.72 if kind == "MESA" else None
    skew = (draw(seed, 8) - 0.5) * 0.5  # steeper on one flank

    def elevation(x, z, rho):
        if rho >= 1:
            return 0.005
        open_air = 1.0
        for sx, sz, a, r in summits:
            open_air *= 1 - a * math.exp(-(math.hypot(x - sx, z - sz) / r) ** 2)
        crest = 1 - open_air  # union of peaks keeps saddles between summits
        relief = (0.7 * math.sin(0.31 * x + phase[0]) * math.sin(0.27 * z + phase[1])
                  + 0.3 * math.sin(0.83 * x + 0.6 * z + phase[2]))
        flank = 1 + skew * ((x - center[0]) * u[0] + (z - center[1]) * u[1]) / max(1e-6, major)
        value = height * (1 - rho ** power) ** exponent * (0.3 + 0.7 * crest) * (1 + 0.13 * relief) * flank
        if plateau:
            value = min(value, height * plateau)
        return q(max(0.005, min(height * 1.05, value)))

    grid = []
    for rho in rings:
        row = []
        for p in outline:
            x, z = center[0] + (p[0] - center[0]) * rho, center[1] + (p[1] - center[1]) * rho
            row.append([q(x), elevation(x, z, rho), q(z)])
        grid.append(row)
    peak = max(summits, key=lambda s: s[2])
    top = [q(peak[0]), q(max(max(v[1] for v in row) for row in grid) * (1.0 if plateau else 1.04)), q(peak[1])]
    faces = []

    stops = ((0.0, (0x4a, 0x68, 0x44)), (0.3, (0x58, 0x77, 0x4c)), (0.55, (0x6c, 0x80, 0x5e)),
             (0.78, (0x86, 0x88, 0x78)), (1.0, (0xa4, 0xa4, 0x9a)))

    def shade(y, i, k):
        # Continuous height ramp (forest to rock) with a faint per-face tint.
        t = max(0.0, min(1.0, y / height))
        for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
            if t <= t1:
                f = (t - t0) / (t1 - t0)
                rgb = [c0[j] + (c1[j] - c0[j]) * f for j in range(3)]
                break
        tint = 0.97 + 0.06 * draw(seed, 400 + i * 7 + k)
        return "#" + "".join("%02x" % max(0, min(255, round(v * tint))) for v in rgb)

    for k in range(len(rings) - 1):
        for i in range(count):
            j = (i + 1) % count
            a, b, c, d = grid[k][i], grid[k + 1][i], grid[k + 1][j], grid[k][j]
            average = (a[1] + b[1] + c[1] + d[1]) / 4
            faces.append(dict(points=_up([a, b, c, d]), color=shade(average, i, k)))
    for i in range(count):
        j = (i + 1) % count
        faces.append(dict(points=_up([grid[-1][i], top, grid[-1][j]]), color=shade(height, i, 9)))
    forest = []
    attempts = int(min(48, math.pi * major * minor * 0.012) * 4)
    for n in range(attempts):
        if len(forest) >= min(48, int(math.pi * major * minor * 0.012)):
            break
        rho = 0.35 + 0.55 * draw(seed, 500 + n)
        edge = outline[int(draw(seed, 700 + n) * count) % count]
        x, z = center[0] + (edge[0] - center[0]) * rho, center[1] + (edge[1] - center[1]) * rho
        y = elevation(x, z, rho)
        radius = 1.0 + draw(seed, 900 + n) * 0.6
        if y / height > 0.6 or y < 0.25 or any(math.dist((x, z), t["center"]) < 2.4 * radius + 0.6 for t in forest):
            continue
        forest.append(dict(center=point([x, z]), y=q(y * 0.97), radius=q(radius),
                           height=q(3.6 + draw(seed, 1100 + n) * 2.4)))
    return dict(id="world:nature:" + derive(seed), kind="HILL", center=point(center), polygon=polygon,
                noBuildPolygon=no_build, roadPolygon=road, height=height, faces=faces, trees=forest,
                landform="RIDGE" if kind == "RIDGE" else "HILLS", hillType=kind)


def _rounded(faces):
    return [dict(points=[[q(v) for v in p] for p in f["points"]], color=f["color"]) for f in faces]
