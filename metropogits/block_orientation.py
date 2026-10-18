"""ADR-023: fixed-boundary, continuous physical block transformations."""

import copy
import math
from collections import defaultdict

from metropogits.frontage_parcels import corners, transform, area
from metropogits.street_diagonals import bounds

EPS = 1e-8
MAX_BLOCKS = 8
MAX_PIECES = 250_000
MAX_PLAN_CHECKS = 5_000_000


def cross(a, b, c):
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def weights(p, triangle):
    a, b, c = triangle
    denominator = cross(a, b, c)
    return [
        cross(p, b, c) / denominator,
        cross(a, p, c) / denominator,
        cross(a, b, p) / denominator,
    ]


def affine(p, source, target):
    w = weights(p, source)
    return [sum(w[i] * target[i][j] for i in range(3)) for j in (0, 1)]


def clip(poly, triangle):
    winding = sum(
        a[0] * b[1] - a[1] * b[0] for a, b in zip(triangle, triangle[1:] + triangle[:1])
    )
    sign = 1 if winding >= 0 else -1
    for a, b in zip(triangle, triangle[1:] + triangle[:1]):
        output = []
        for p, q in zip(poly, poly[1:] + poly[:1]):
            dp, dq = sign * cross(a, b, p), sign * cross(a, b, q)
            if dp >= -EPS:
                output.append(p)
            if (dp >= -EPS) != (dq >= -EPS):
                t = dp / (dp - dq)
                output.append([p[j] + t * (q[j] - p[j]) for j in (0, 1)])
        poly = output
    return poly


def cage(outer, inner, pivot, angle, shift):
    moved = transform(inner, pivot, angle, shift)
    triangles = []
    for i in range(4):
        j = (i + 1) % 4
        triangles += [
            ([outer[i], outer[j], inner[j]], [outer[i], outer[j], moved[j]]),
            ([outer[i], inner[j], inner[i]], [outer[i], moved[j], moved[i]]),
        ]
    triangles += [
        ([inner[0], inner[1], inner[2]], [moved[0], moved[1], moved[2]]),
        ([inner[0], inner[2], inner[3]], [moved[0], moved[2], moved[3]]),
    ]
    if any(cross(*s) <= EPS or cross(*t) <= EPS for s, t in triangles):
        return None
    return [dict(source=s, target=t) for s, t in triangles]


class BlockMap:
    def __init__(self, plan):
        self.blocks = plan.get("blocks", [])
        self.pieces = 0

    def point(self, p):
        for block in self.blocks:
            lo_x, lo_z, hi_x, hi_z = block["bounds"]
            if lo_x - EPS <= p[0] <= hi_x + EPS and lo_z - EPS <= p[1] <= hi_z + EPS:
                for t in block["triangles"]:
                    if min(weights(p, t["source"])) >= -EPS:
                        return affine(p, t["source"], t["target"])
        return list(p)

    def line(self, a, b):
        cuts = {0.0, 1.0}
        for block in self.blocks:
            x0, z0, x1, z1 = block["bounds"]
            if (
                max(a[0], b[0]) < x0
                or min(a[0], b[0]) > x1
                or max(a[1], b[1]) < z0
                or min(a[1], b[1]) > z1
            ):
                continue
            for t in block["triangles"]:
                for p, q in zip(t["source"], t["source"][1:] + t["source"][:1]):
                    # Segment intersections with the triangulation partition.
                    r = [b[j] - a[j] for j in (0, 1)]
                    s = [q[j] - p[j] for j in (0, 1)]
                    denominator = r[0] * s[1] - r[1] * s[0]
                    if abs(denominator) < EPS:
                        continue
                    d = [p[j] - a[j] for j in (0, 1)]
                    u = (d[0] * s[1] - d[1] * s[0]) / denominator
                    v = (d[0] * r[1] - d[1] * r[0]) / denominator
                    if EPS < u < 1 - EPS and -EPS <= v <= 1 + EPS:
                        cuts.add(round(u, 12))
        self.count(len(cuts))
        return [
            self.point([a[j] + u * (b[j] - a[j]) for j in (0, 1)]) for u in sorted(cuts)
        ]

    def count(self, n):
        self.pieces += n
        if self.pieces > MAX_PIECES:
            raise ValueError("block physical presentation limit")

    def polygon(self, poly):
        bx0, bz0, bx1, bz1 = bounds(poly)
        if not any(
            bx1 > b["bounds"][0]
            and bx0 < b["bounds"][2]
            and bz1 > b["bounds"][1]
            and bz0 < b["bounds"][3]
            for b in self.blocks
        ):
            return [poly]
        # Split on the four outer cage edges first. The remainder stays fixed.
        pending, result = [poly], []
        for block in self.blocks:
            retained = []
            x0, z0, x1, z1 = block["bounds"]
            for original in pending:
                inside = original
                for axis, value, sign in (
                    (0, x0, 1),
                    (0, x1, -1),
                    (1, z0, 1),
                    (1, z1, -1),
                ):
                    halves = [[], []]
                    for p, q in zip(inside, inside[1:] + inside[:1]):
                        dp, dq = sign * (p[axis] - value), sign * (q[axis] - value)
                        halves[0 if dp >= 0 else 1].append(p)
                        if (dp >= 0) != (dq >= 0):
                            u = dp / (dp - dq)
                            v = [p[j] + u * (q[j] - p[j]) for j in (0, 1)]
                            halves[0].append(v)
                            halves[1].append(v)
                    if area(halves[1]) > EPS:
                        retained.append(halves[1])
                    inside = halves[0]
                if area(inside) <= EPS:
                    continue
                for t in block["triangles"]:
                    clipped = clip(inside, t["source"])
                    if area(clipped) > EPS:
                        result.append(
                            [affine(p, t["source"], t["target"]) for p in clipped]
                        )
            pending = retained
        result.extend(pending)
        # Existing render contracts consume quads; triangulate larger polygons.
        self.count(sum(max(0, len(p) - 2) for p in result))
        return [
            [p[0], p[i], p[i + 1], p[i + 1]]
            for p in result
            for i in range(1, len(p) - 1)
        ]


def plan_blocks(scene, routing, surfaces, paths):
    """Bounded rectangular leaf pilot; no graph or semantic classification input."""
    members = defaultdict(list)
    for b in scene["buildings"]:
        members[b["districtId"]].append(b)
    parents = {d["parentId"] for d in scene["districts"]}
    proposals, blocks, checks = 0, [], 0

    def charge(n):
        nonlocal checks
        checks += n
        if checks > MAX_PLAN_CHECKS:
            raise ValueError("block planning work limit")

    # Actual physical oblique street axes, not arbitrary compass decoration.
    axes = []
    for chain in routing["diagonalPlan"]["chains"]:
        for a, b in zip(chain["physical"], chain["physical"][1:]):
            charge(1)
            if math.dist(a, b) < 2 or abs(a[0] - b[0]) < 0.1 or abs(a[1] - b[1]) < 0.1:
                continue
            angle = (math.atan2(b[1] - a[1], b[0] - a[0]) + math.pi / 4) % (
                math.pi / 2
            ) - math.pi / 4
            axes.append((a, b, angle))
    for d in sorted(scene["districts"], key=lambda d: d["id"]):
        group = members[d["id"]]
        if d["id"] in parents or not 2 <= len(group) <= 32 or len(blocks) >= MAX_BLOCKS:
            continue
        if (
            abs(
                sum(r["width"] * r["depth"] for r in d.get("footprint", [d]))
                - d["width"] * d["depth"]
            )
            > EPS
        ):
            continue
        models = routing.get("parcelPlan", {}).get("buildings", {})
        if any(b["entityId"] not in models for b in group):
            continue
        x0, z0, x1, z1 = bounds(
            [
                p
                for b in group
                for poly in [
                    models[b["entityId"]]["footprint"],
                    models[b["entityId"]]["pinnedDoors"],
                ]
                + [part["footprint"] for part in models[b["entityId"]]["parts"]]
                for p in poly
            ]
        )
        pivot = [(x0 + x1) / 2, (z0 + z1) / 2]
        from metropogits.frontage_parcels import nearest

        charge(len(axes))
        nearby = sorted(
            (math.dist(pivot, nearest(pivot, a, b)), angle)
            for a, b, angle in axes
            if math.dist(pivot, nearest(pivot, a, b)) <= 42
        )
        if not nearby:
            continue
        inner = corners(
            dict(x=x0 - 0.1, z=z0 - 0.1, width=x1 - x0 + 0.2, depth=z1 - z0 + 0.2)
        )
        outer = corners(d)
        # Centering within the same owner buys clearance without global shuffling.
        shift = [d["x"] + d["width"] / 2 - pivot[0], d["z"] + d["depth"] / 2 - pivot[1]]
        for fraction, shift_fraction in (
            (f, s) for f in (1, 0.5, 0.25) for s in (1, 0.5, 0)
        ):
            proposals += 1
            angle = nearby[0][1] * fraction
            if abs(angle) < math.radians(3):
                continue
            local_shift = [v * shift_fraction for v in shift]
            moved = transform(inner, pivot, angle, local_shift)
            if max(math.dist(a, b) for a, b in zip(inner, moved)) > 14:
                continue
            triangles = cage(outer, inner, pivot, angle, local_shift)
            if not triangles:
                continue
            candidate = dict(
                districtId=d["id"],
                memberEntityIds=sorted(b["entityId"] for b in group),
                bounds=bounds(outer),
                triangles=triangles,
                pivot=pivot,
                angle=angle,
                shift=local_shift,
                alignmentFraction=fraction,
            )
            mapper = BlockMap(dict(blocks=blocks + [candidate]))
            lengths = {}
            for key, path in paths.items():
                charge(len(path))
                mapped = [
                    v for a, b in zip(path, path[1:]) for v in mapper.line(a, b)[1:]
                ]
                mapped.insert(0, mapper.point(path[0]))
                lengths[key] = sum(math.dist(a, b) for a, b in zip(mapped, mapped[1:]))
            old_lengths = {
                k: sum(math.dist(a, b) for a, b in zip(p, p[1:]))
                for k, p in paths.items()
            }
            if any(
                sum(lengths[k] for k in r["segmentIds"])
                > max(
                    sum(old_lengths[k] for k in r["segmentIds"]) * 1.5,
                    sum(old_lengths[k] for k in r["segmentIds"]) + 14,
                )
                + EPS
                for r in routing["routes"]
            ):
                continue
            blocks.append(candidate)
            break
    return dict(
        version="block-orientation/0.1",
        semantic=False,
        blocks=blocks,
        proposals=proposals,
    )


def update_parcels(scene, routing):
    """Move rigid building parts and their real entrances with their block."""
    result = copy.deepcopy(routing["parcelPlan"])
    buildings = {b["entityId"]: b for b in scene["buildings"]}
    for block in routing["blockPlan"]["blocks"]:
        for key in block["memberEntityIds"]:
            p = result["buildings"].get(key)
            if not p:
                raise ValueError("block member lacks frontage model")

            def move(points):
                return transform(points, block["pivot"], block["angle"], block["shift"])

            for field in ("footprint", "frontageEdge", "pinnedDoors"):
                p[field] = move(p[field])
            for field in ("center", "frontagePoint", "entrance"):
                if p[field] is not None:
                    p[field] = move([p[field]])[0]
            for part in p["parts"]:
                part["footprint"] = move(part["footprint"])
            p["angle"] += block["angle"]
            p["facing"] = [-math.sin(p["angle"]), math.cos(p["angle"])]
            b = buildings[key]
            p["pivot"] = [b["x"] + b["width"] / 2, b["z"] + b["depth"] / 2]
            p["shift"] = [p["center"][j] - p["pivot"][j] for j in (0, 1)]
            p["displacement"] = math.dist(
                p["center"], [b["x"] + b["width"] / 2, b["z"] + b["depth"] / 2]
            )
            p["blockId"] = block["districtId"]
    result["changedFootprintIds"] = sorted(
        set(result["changedFootprintIds"])
        | {key for b in routing["blockPlan"]["blocks"] for key in b["memberEntityIds"]}
    )
    return result


def presentation(routing, surfaces, pavement, curves):
    mapper = BlockMap(routing["blockPlan"])

    def polygons(items):
        return [dict(s, points=p) for s in items for p in mapper.polygon(s["points"])]

    def line(path):
        return [mapper.point(path[0])] + [
            p for a, b in zip(path, path[1:]) for p in mapper.line(a, b)[1:]
        ]

    surfaces = polygons(surfaces)
    pavement = dict(
        pavement, segments={k: polygons(v) for k, v in pavement["segments"].items()}
    )
    paint = {}
    for k, entries in curves["paintSegments"].items():
        paint[k] = []
        for s in entries:
            p = mapper.line(s["start"], s["end"])
            paint[k].extend(dict(start=a, end=b) for a, b in zip(p, p[1:]))
    curves = dict(
        curves,
        version="block-orientation/0.1",
        segments={k: line(p) for k, p in curves["segments"].items()},
        paintSegments=paint,
    )
    return surfaces, pavement, curves
