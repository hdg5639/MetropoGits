"""Bounded analytical waterway trees, planned before any source placement.

Environmental morphology only, not a hydrological simulation or code semantics.
The old terrain/0.5 remains a separate, frozen preset.
"""

import math

from .geometry import area, centroid, inside, nearest, point, q
from .river_landscape import _banks, _strip, _planned_crossing
from .seed import derive, draw
from .terrain_varied import complete_landscape

VERSION = "terrain/0.6"
GENERATOR_VERSION = "terrain-adaptive/0.6"
PRESET = "watershed-landscape"
MAX_FEATURES = 64
MAX_WATERWAYS = 5
MAX_VERTICES = 17


def _through(center, yaw, offset, scale, reach, seed):
    u = [math.cos(yaw), math.sin(yaw)]
    n = [-u[1], u[0]]
    phase = draw(seed, 1) * math.tau
    frequency = 0.6 + draw(seed, 2) * 0.9
    amplitude = scale * (0.045 + 0.065 * draw(seed, 3))
    count = 13 + 2 * int(draw(seed, 4) * 2)
    line = []
    for i in range(count):
        t = i / (count - 1)
        bend = amplitude * (
            math.sin(t * math.tau * frequency + phase)
            + 0.23 * math.sin(t * math.tau * (frequency + 1.1) + phase * 0.7)
        )
        # Cover the developable domain, not only its central half followed by
        # long straight extensions. More knots preserve broad natural bends.
        line.append(
            point(
                [
                    center[j] + u[j] * (t - 0.5) * scale * 1.5 + n[j] * (offset + bend)
                    for j in (0, 1)
                ]
            )
        )
    ends = [
        point([a[j] + (a[j] - b[j]) / math.dist(a, b) * reach for j in (0, 1)])
        for a, b in ((line[0], line[1]), (line[-1], line[-2]))
    ]
    return [ends[0], *line, ends[1]]


def _branch(parent, others, envelope, scale, reach, seed):
    """One bounded fit; joins only its recorded parent, never crosses a sibling."""
    line = parent["centerline"]
    candidates = [
        i for i in range(2, len(line) - 2) if inside(line[i], envelope, scale * 0.035)
    ]
    if not candidates:
        return None
    start = int(draw(seed) * len(candidates))
    for attempt in range(12):
        k = candidates[(start + attempt // 2) % len(candidates)]
        join = line[k]
        a, b = line[k - 1], line[k + 1]
        yaw = math.atan2(b[1] - a[1], b[0] - a[0])
        side = (1 if draw(seed, 1) > 0.5 else -1) * (-1 if attempt % 2 else 1)
        yaw += side * (0.85 + draw(seed, 2) * 0.75)
        u = [math.cos(yaw), math.sin(yaw)]
        n = [-u[1], u[0]]
        length = scale * (0.52 + 0.15 * draw(seed, 3))
        phase = draw(seed, 4) * math.pi
        count = 5 + int(draw(seed, 5) * 2)
        path = [
            point(
                [
                    join[j]
                    + u[j] * length * t
                    + n[j]
                    * length
                    * (0.06 + 0.08 * draw(seed, 6))
                    * math.sin(t * math.pi)
                    * math.sin(t * math.pi + phase)
                    for j in (0, 1)
                ]
            )
            for t in [i / (count - 1) for i in range(count)]
        ]
        a, b = path[-1], path[-2]
        path.append(
            point([a[j] + (a[j] - b[j]) / math.dist(a, b) * reach for j in (0, 1)])
        )
        if not any(inside(p, envelope, scale * 0.01) for p in path[1:-1]):
            continue
        # Reject accidental crossings and near-parallel duplication. Shared mouth
        # clearance is allowed only at the declared parent junction.
        safe = True
        for other in others:
            for i, (a, b) in enumerate(zip(path, path[1:])):
                for c, d in zip(other["centerline"], other["centerline"][1:]):
                    if (
                        other is parent
                        and math.dist(join, nearest(join, c, d)) < 0.001
                        and i == 0
                    ):
                        continue
                    separation = min(math.dist(p, nearest(p, c, d)) for p in (a, b))
                    separation = min(
                        separation, *(math.dist(p, nearest(p, a, b)) for p in (c, d))
                    )
                    ux, uz = b[0] - a[0], b[1] - a[1]
                    vx, vz = d[0] - c[0], d[1] - c[1]
                    den = ux * vz - uz * vx
                    if abs(den) > 1e-9:
                        dx, dz = c[0] - a[0], c[1] - a[1]
                        t = (dx * vz - dz * vx) / den
                        r = (dx * uz - dz * ux) / den
                        if 0.00001 < t < 0.99999 and 0.00001 < r < 0.99999:
                            safe = False
                    if separation < (other["width"] + 3.2) / 2 + 8:
                        safe = False
        if safe:
            return path
    return None


def generate_watershed_terrain(envelope, seed):
    local = derive(seed, VERSION)
    center = centroid(envelope)
    scale = math.sqrt(area(envelope))
    reach = max(math.dist(center, p) for p in envelope) * 4 + 64
    yaw = draw(derive(local, "bearing")) * math.tau
    main_count = 1 + int(scale >= 280 and draw(derive(local, "main-count")) > 0.45)
    branch_count = (
        0
        if scale < 180
        else int(draw(derive(local, "tributary-count")) * (4 if main_count == 1 else 3))
    )
    waterways = []
    for i in range(main_count):
        identity = derive(local, "main", str(i))
        offset = 0 if main_count == 1 else scale * (-0.16 if i == 0 else 0.16)
        angle = yaw + (draw(identity) - 0.5) * (0.12 if main_count == 2 else 0.5)
        path = _through(center, angle, offset, scale, reach, identity)
        waterways.append(
            dict(
                id="world:channel:" + identity,
                kind="MAIN",
                parentId=None,
                centerline=path,
                width=q(max(6, min(17, scale * (0.018 + 0.008 * draw(identity, 8))))),
            )
        )
    for i in range(branch_count):
        identity = derive(local, "tributary", str(i))
        # Later branches may drain into an earlier branch; this changes graph
        # topology, not just the rotation of one repeated Y shape.
        parents = (
            waterways if i and draw(identity, 10) > 0.45 else waterways[:main_count]
        )
        parent = parents[int(draw(identity, 11) * len(parents))]
        path = _branch(parent, waterways, envelope, scale, reach, identity)
        if path:
            waterways.append(
                dict(
                    id="world:channel:" + identity,
                    kind="TRIBUTARY",
                    parentId=parent["id"],
                    centerline=path,
                    width=q(
                        max(3.2, parent["width"] * (0.38 + 0.16 * draw(identity, 12)))
                    ),
                )
            )
    if len(waterways) > MAX_WATERWAYS or any(
        len(r["centerline"]) > MAX_VERTICES for r in waterways
    ):
        raise ValueError("watershed topology resource limit")
    water = [
        piece
        for r in waterways
        for piece in _strip(r["centerline"], r["width"], r["id"])
    ]
    _banks(water, sparse=True)
    crossings = []
    for r in waterways:
        path = r["centerline"]
        count = 1 if scale < 180 or r["kind"] == "TRIBUTARY" else 3
        segments = [
            (a, b)
            for a, b in zip(path, path[1:])
            if inside([(a[j] + b[j]) / 2 for j in (0, 1)], envelope, 10)
        ]
        for i in range(count):
            if len(crossings) == 8 or not segments:
                break
            k = min(len(segments) - 1, int((i + 0.5) * len(segments) / count))
            for index in sorted(range(len(segments)), key=lambda j: (abs(j - k), j)):
                a, b = segments[index]
                try:
                    crossing = _planned_crossing(
                        a,
                        b,
                        0.5,
                        water,
                        derive(r["id"], "crossing", str(i)),
                        envelope,
                        crossings,
                    )
                except ValueError as error:
                    if "cannot be separated" not in str(error):
                        raise
                    continue
                if crossing:
                    crossings.append(crossing)
                    break
    if not crossings:
        raise ValueError("watershed has no feasible certified water crossing")
    channel = dict(
        centerline=waterways[0]["centerline"],
        tributaries=[r["centerline"] for r in waterways[1:]],
        waterways=waterways,
        waterLevel=0.09,
        extentPolicy="open-through-boundary/0.1",
        policy="analytical-connected-channel-not-drainage-simulation",
    )
    t = dict(
        seed=derive(seed, "global-terrain", VERSION),
        environmental=True,
        initialEnvelope=envelope,
        surfacePolicy="graded-ground-level-foundations",
        elevation=dict(
            version="surface-field/0.1",
            seed=derive(local, "uplands"),
            spacing=16,
            amplitude=q(min(18, max(6, scale * 0.04))),
            riseLength=q(max(90, scale * 0.18)),
            flatRadius=40,
        ),
    )
    return complete_landscape(
        t,
        envelope,
        local,
        water,
        max(r["width"] for r in waterways),
        crossings,
        channel,
        VERSION,
        PRESET,
        max_features=MAX_FEATURES,
    )
