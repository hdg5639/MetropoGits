"""Optional large multi-summit reserves; procedural geology, not code facts."""

import math

from .geometry import area, point, q
from .landscape import expanded
from .seed import derive, draw

LEGACY_VERSION = "terrain/0.7"
LEGACY_GENERATOR_VERSION = "terrain-adaptive/0.7"
VERSION = "terrain/0.8"
GENERATOR_VERSION = "terrain-adaptive/0.8"
PRESET = "mountain-landscape"
MAX_FEATURES = 64


def mountain_landform(center, major, minor, yaw, seed):
    """A continuous triangulated ridge with shoulders and unequal summits.

    Cross-sections cover the complete convex base exactly. Peaks are part of
    that same surface, not overlapping cone props or a stretched old hill.
    """
    c, s = math.cos(yaw), math.sin(yaw)
    height = q(min(160, max(55, major * (0.95 + 0.55 * draw(seed, 3)))))
    stations = (-1, -0.72, -0.4, -0.08, 0.27, 0.64, 1)
    peaks = (
        (0, 0.68, 1, 0.58, 0.9, 0.55, 0)
        if draw(seed, 4) > 0.5
        else (0, 0.55, 0.86, 1, 0.62, 0.89, 0)
    )
    rows = []
    for i, u in enumerate(stations):
        width = minor * math.sqrt(max(0, 1 - u * u))
        offset = width * (draw(seed, 10 + i) - 0.5) * 0.3
        ridge = height * peaks[i]
        local = [
            (-width, 0.005),
            ((-width + offset) * 0.52, ridge * 0.32),
            (offset, max(0.005, ridge)),
            ((width + offset) * 0.52, ridge * 0.4),
            (width, 0.005),
        ]
        rows.append(
            [
                [
                    q(center[0] + c * major * u - s * v),
                    q(h),
                    q(center[1] + s * major * u + c * v),
                ]
                for v, h in local
            ]
        )
    poly = point_rows = [point([r[0][0], r[0][2]]) for r in rows]
    poly = point_rows + [point([r[-1][0], r[-1][2]]) for r in reversed(rows[1:-1])]
    # Reconstruct using a hull to drop duplicate end vertices / quantized collinearity.
    from metropogits.street_diagonals import hull

    poly = list(reversed(hull(poly)))
    faces = []
    for i, (a, b) in enumerate(zip(rows, rows[1:])):
        for j in range(4):
            for tri in ([a[j], b[j], b[j + 1]], [a[j], b[j + 1], a[j + 1]]):
                if area([[p[0], p[2]] for p in tri]) < 0.00001:
                    continue
                average = sum(p[1] for p in tri) / 3
                color = (
                    ("#acb5b8", "#879293")[(i + j) % 2]
                    if average > height * 0.66
                    else ("#626f68", "#778175", "#53675d")[(i + j) % 3]
                    if average > height * 0.23
                    else ("#475c44", "#52694a", "#5c704f")[(i + j) % 3]
                )
                faces.append(dict(points=tri, color=color))
    return dict(
        id="world:mountain:" + derive(seed),
        kind="HILL",
        landform="MOUNTAIN_RANGE",
        center=point(center),
        polygon=poly,
        noBuildPolygon=[point(p) for p in expanded(poly, 4)],
        roadPolygon=[point(p) for p in expanded(poly, 9)],
        height=height,
        faces=faces,
        summits=[
            r[2]
            for i, r in enumerate(rows)
            if 0 < i < len(rows) - 1
            and peaks[i] > peaks[i - 1]
            and peaks[i] >= peaks[i + 1]
        ],
    )


def generate_mountain_terrain(envelope, seed, *, version=VERSION):
    from .watershed import generate_watershed_terrain
    from .terrain_varied import complete_landscape

    t = generate_watershed_terrain(envelope, seed)
    # Keep the established horizontal geography and old reconstruction exact.
    local = derive(seed, LEGACY_VERSION)
    t["seed"] = derive(seed, "global-terrain", LEGACY_VERSION)
    t = complete_landscape(
        t,
        envelope,
        local,
        [f for f in t["features"] if f["kind"] == "RIVER"],
        max(w["width"] for w in t["channel"]["waterways"]),
        t["crossings"],
        t["channel"],
        LEGACY_VERSION,
        PRESET,
        max_features=MAX_FEATURES,
        mountains=True,
    )
    if version == LEGACY_VERSION:
        return t
    if version != VERSION:
        raise ValueError("unsupported mountain terrain version")
    for feature in t["features"]:
        if feature.get("landform") != "MOUNTAIN_RANGE":
            continue
        # Relief is subordinate to horizontal mountain breadth, not a needle
        # made taller than the whole surrounding city. World units, not metres.
        breadth = math.sqrt(area(feature["polygon"]))
        height = q(min(68, feature["height"] * 0.45, breadth * 0.45))
        factor = (height - 0.005) / (feature["height"] - 0.005)
        for face in feature["faces"]:
            face["points"] = [
                [x, q(0.005 + (y - 0.005) * factor), z]
                for x, y, z in reversed(face["points"])
            ]
        feature["summits"] = [
            [x, q(0.005 + (y - 0.005) * factor), z] for x, y, z in feature["summits"]
        ]
        feature["height"] = height
    t.update(version=VERSION, seed=derive(seed, "global-terrain", VERSION))
    return t
