"""Seeded, scale-aware rivers, lakes and upland groups, before urban placement."""

import math

from metropogits.street_diagonals import overlap, hull
from .geometry import area, centroid, inside, point, q, ribbon
from .landscape import expanded
from .river_landscape import _strip, _banks, _planned_crossing
from .seed import derive, draw

VERSION = "terrain/0.5"
GENERATOR_VERSION = "terrain-adaptive/0.5"
PRESET = "varied-landscape"
MAX_FEATURES = 48
MAX_CROSSINGS = 8
MAX_WORK = 2_000_000


def _landform(center, major, minor, yaw, local, kind):
    u, v = [math.cos(yaw), math.sin(yaw)], [-math.sin(yaw), math.cos(yaw)]
    ring = [
        point(
            [
                center[j]
                + u[j] * major * math.cos(t) * scale
                + v[j] * minor * math.sin(t) * scale
                for j in (0, 1)
            ]
        )
        for i in range(16)
        for t in [i * math.tau / 16]
        for scale in [0.84 + 0.25 * draw(local, i + 10)]
    ]
    poly = list(reversed(hull(ring)))
    road = [point(p) for p in expanded(poly, 6.5)]
    height = (
        q(min(35, max(7, major * (0.3 + 0.24 * draw(local, 3)))))
        if kind == "HILL"
        else 0.09
    )
    if kind == "HILL":
        # Unequal shoulder and off-centre peak: not one repeated conical mountain.
        inner = [
            [
                q(center[0] + (p[0] - center[0]) * 0.43),
                q(height * 0.65),
                q(center[1] + (p[1] - center[1]) * 0.43),
            ]
            for p in poly
        ]
        peak = [
            q(center[0] + u[0] * major * 0.13),
            height,
            q(center[1] + u[1] * major * 0.13),
        ]
        faces = []
        for i, (p, r) in enumerate(zip(poly, poly[1:] + poly[:1])):
            faces.extend(
                [
                    dict(
                        points=[
                            [p[0], 0.005, p[1]],
                            inner[i],
                            inner[(i + 1) % len(poly)],
                            [r[0], 0.005, r[1]],
                        ],
                        color=("#5e735a", "#687a60", "#586d55")[i % 3],
                    ),
                    dict(
                        points=[inner[i], peak, inner[(i + 1) % len(poly)]],
                        color=("#879080", "#727f6c")[i % 2],
                    ),
                ]
            )
    else:
        inner = [
            point([center[j] + (p[j] - center[j]) * 0.88 for j in (0, 1)]) for p in poly
        ]
        faces = [
            dict(
                points=[
                    [p[0], 0.06, p[1]],
                    [r[0], 0.06, r[1]],
                    [
                        inner[(i + 1) % len(poly)][0],
                        0.09,
                        inner[(i + 1) % len(poly)][1],
                    ],
                    [inner[i][0], 0.09, inner[i][1]],
                ],
                color="#83927a",
            )
            for i, (p, r) in enumerate(zip(poly, poly[1:] + poly[:1]))
        ]
        faces.append(
            dict(points=[[p[0], 0.09, p[1]] for p in reversed(inner)], color="#397c91")
        )
    return dict(
        id="world:nature:" + derive(local),
        kind=kind,
        center=center,
        polygon=poly,
        noBuildPolygon=[point(p) for p in expanded(poly, 2)],
        roadPolygon=road,
        height=height,
        faces=faces,
        **(
            dict(landform="RIDGE" if major / minor > 2 else "HILLS")
            if kind == "HILL"
            else {}
        ),
    )


def generate_varied_terrain(envelope, seed):
    from .elevation import generate_valley

    local = derive(seed, VERSION)
    t = generate_valley(envelope, derive(seed, "varied-main-water"))
    line = t["channel"]["centerline"]
    c, scale = centroid(envelope), math.sqrt(area(envelope))
    reach = max(math.dist(c, p) for p in envelope) * 4 + 64
    water = [f for f in t["features"] if f["kind"] == "RIVER"]
    width = math.dist(
        *sorted(water[0]["polygon"], key=lambda p: math.dist(p, line[0]))[:2]
    )
    ends = [
        point([a[j] + (a[j] - b[j]) / math.dist(a, b) * reach for j in (0, 1)])
        for a, b in ((line[0], line[1]), (line[-1], line[-2]))
    ]
    from .rivers import _feature

    for i, (far, f, at) in enumerate(
        ((ends[0], water[0], line[0]), (ends[1], water[-1], line[-1]))
    ):
        section = sorted(f["polygon"], key=lambda p: math.dist(p, at))[:2]
        water.append(
            _feature(
                section
                + [point([p[j] + far[j] - at[j] for j in (0, 1)]) for p in section],
                "world:water:" + derive(local, "end", str(i)),
                "RIVER",
            )
        )
    # Zero to three branches, sometimes a second through-flowing river rather
    # than the same Y stencil. Counts respond to area, never to source roles.
    branch_count = int(
        draw(derive(local, "branch-count")) * (min(3, 1 + int(scale / 450)) + 1)
    )
    # A tiny domain cannot safely hold several grade-certified bridge ramps.
    if scale < 180:
        branch_count = 0
    branches, cross_specs = (
        [],
        (
            [(line[3], line[4], 0.5)]
            if scale < 180
            else [(line[1], line[2], 0.4), (line[6], line[7], 0.6)]
        ),
    )
    for i in range(branch_count):
        bs = derive(local, "branch", str(i))
        k = 2 + i * 2
        join = line[k]
        a, b = line[k - 1], line[k + 1]
        u = [(b[j] - a[j]) / math.dist(a, b) for j in (0, 1)]
        side = (-1 if i % 2 else 1) * (1 if draw(bs) > 0.5 else -1)
        n = [-u[1] * side, u[0] * side]
        bend = point(
            [
                join[j]
                + n[j] * scale * (0.23 + 0.12 * draw(bs, 1))
                + u[j] * scale * (draw(bs, 2) - 0.5) * 0.2
                for j in (0, 1)
            ]
        )
        far = point(
            [
                join[j] + n[j] * reach + u[j] * reach * (draw(bs, 3) - 0.5) * 0.3
                for j in (0, 1)
            ]
        )
        path = [join, bend, far]
        if i == 0 and scale > 450 and draw(derive(local, "second-river")) > 0.5:
            other = point(
                [join[j] - n[j] * reach + u[j] * reach * 0.12 for j in (0, 1)]
            )
            path = [other, join, bend, far]
            cross_specs.append((other, join, 0.88))
        branches.append(path)
        water.extend(
            _strip(
                path,
                max(3.2, width * (0.28 + 0.28 * draw(bs, 4))),
                "world:stream:" + derive(bs),
            )
        )
        cross_specs.append((join, bend, 0.55))
    _banks(water)
    crossings = []
    for i, (a, b, fraction) in enumerate(cross_specs):
        crossing = _planned_crossing(
            a,
            b,
            fraction,
            water,
            derive(local, "crossing", str(i)),
            envelope,
            crossings,
        )
        if crossing:
            crossings.append(crossing)
    if not crossings:
        raise ValueError("varied terrain has no feasible water crossings")
    channel = dict(
        t["channel"],
        centerline=[ends[0], *line, ends[1]],
        tributaries=branches,
        extentPolicy="open-through-boundary/0.1",
    )
    return complete_landscape(
        t, envelope, local, water, width, crossings, channel, VERSION, PRESET
    )


def complete_landscape(
    t,
    envelope,
    local,
    water,
    width,
    crossings,
    channel,
    version,
    preset,
    *,
    max_features=MAX_FEATURES,
    mountains=False,
    organic=False,
):
    """Shared landform/ground finish; old seeds and output ordering stay intact."""
    scale = math.sqrt(area(envelope))
    features = list(water)
    # Candidate centres cover the entire initial domain, not the previous
    # fixed central belt. Rejected candidates do not consume another RNG stream.
    x0, z0 = min(p[0] for p in envelope), min(p[1] for p in envelope)
    x1, z1 = max(p[0] for p in envelope), max(p[1] for p in envelope)
    counts = {
        "LAKE": 1
        + int(draw(derive(local, "lake-count")) * (min(4, 1 + int(scale / 250)))),
        "HILL": 1
        + int(draw(derive(local, "hill-count")) * (min(6, 1 + int(scale / 200)))),
    }
    if organic:
        from .landforms import organic_counts
        counts = organic_counts(local, scale)
    if mountains:
        counts["HILL"] = int(draw(derive(local, "foothill-count")) * 3)
        counts["MOUNTAIN"] = (
            0 if scale < 110 else int(draw(derive(local, "mountain-count")) * 3)
        )
    for kind in ("LAKE", "HILL", "MOUNTAIN") if mountains else ("LAKE", "HILL"):
        placed = 0
        for i in range(160):
            if placed >= counts[kind]:
                break
            fs = derive(local, kind, str(i))
            center = point([x0 + (x1 - x0) * draw(fs), z0 + (z1 - z0) * draw(fs, 1)])
            major = min(65, max(6, scale * (0.025 + 0.045 * draw(fs, 2))))
            minor = major * (0.35 + 0.5 * draw(fs, 3))
            if organic:
                from .landforms import organic_size
                major, minor = organic_size(fs, scale)
            if len(features) >= max_features - 4:
                break
            if kind == "MOUNTAIN":
                from .mountains import mountain_landform

                major = min(160, max(36, scale * (0.075 + 0.06 * draw(fs, 2))))
                minor = major * (0.34 + 0.22 * draw(fs, 3))
                feature = mountain_landform(
                    center, major, minor, draw(fs, 4) * math.tau, fs
                )
            elif organic:
                from .landforms import organic_hill, organic_lake
                feature = (organic_lake if kind == "LAKE" else organic_hill)(
                    center, major, minor, draw(fs, 4) * math.tau, fs
                )
            else:
                feature = _landform(
                    center, major, minor, draw(fs, 4) * math.tau, fs, kind
                )
            if (
                not all(inside(p, envelope, 1) for p in feature["roadPolygon"])
                or any(
                    overlap(feature["roadPolygon"], expanded(f["roadPolygon"], 5))
                    for f in features
                )
                or any(
                    overlap(
                        feature["roadPolygon"],
                        ribbon(c["path"][0], c["path"][-1], c["width"] + 3),
                    )
                    for c in crossings
                )
            ):
                continue
            features.append(feature)
            placed += 1
    t.update(
        version=version,
        preset=preset,
        features=features,
        crossings=crossings,
        tunnels=[],
        channel=channel,
    )
    t["elevation"]["flatRadius"] = q(max(32, width / 2 + 32))
    # Independent lake basins are level world-space features, not sloping water
    # glued to the uplands. Surface construction flattens only their local basins.
    t["protectedArea"] = sum(area(f["noBuildPolygon"]) for f in features)
    # Water strips overlap: preserve union-area accounting.
    from .landscape import subtract

    protected = []
    union_work = 0
    for f in features:
        parts = [f["noBuildPolygon"]]
        for other in protected:
            union_work += sum(len(p) * len(other) for p in parts)
            if union_work > MAX_WORK:
                raise ValueError("varied terrain union work limit")
            parts = [
                p
                for s in parts
                for p in (
                    [s]
                    if version in ("terrain/0.6", "terrain/0.7")
                    and not overlap(s, other)
                    else subtract(s, other)
                )
            ]
        protected.extend(parts)
        if len(protected) > 4096:
            raise ValueError("varied terrain union face limit")
    t["protectedArea"] = sum(map(area, protected))
    from .elevation import surface
    from .terrain import outside

    field = surface(t)
    for mountain in (f for f in features if f["kind"] == "HILL"):
        poly = mountain["polygon"]
        center = mountain["center"]
        xx = sum((p[0] - center[0]) ** 2 for p in poly)
        zz = sum((p[1] - center[1]) ** 2 for p in poly)
        xz = sum((p[0] - center[0]) * (p[1] - center[1]) for p in poly)
        yaw = 0.5 * math.atan2(2 * xz, xx - zz)
        normal = [-math.sin(yaw), math.cos(yaw)]
        far = [
            point([center[j] + side * normal[j] * 200 for j in (0, 1)])
            for side in (-1, 1)
        ]
        spans = outside(*far, mountain["roadPolygon"])
        if len(spans) != 2 or mountain["height"] < 12:
            continue
        path = [spans[0][1], spans[1][0]]
        heights = [q(field.height(p) + 0.08) for p in path]
        if abs(heights[1] - heights[0]) / math.dist(*path) > 0.16:
            continue
        t["tunnels"].append(
            dict(
                id="world:tunnel:" + derive(local, mountain["id"]),
                hillId=mountain["id"],
                path=path,
                heights=heights,
                width=3.5,
                maxGrade=0.16,
                clearance=3.2,
                structural=True,
            )
        )
        if len(t["tunnels"]) == 3:
            break
    if len(features) > max_features or len(crossings) > MAX_CROSSINGS:
        raise ValueError("varied terrain output limit")
    return t
