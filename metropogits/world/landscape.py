"""Optional, bounded flat planting in free land; never source or road geometry."""

import math
from collections import defaultdict

from metropogits.street_diagonals import overlap
from .geometry import area, bounds, centroid, clip, dot, inside, point, q, ribbon
from .seed import derive, draw

VERSION = "landscape/0.1"
MAX_CANDIDATES = 16_000
MAX_INDEX = 250_000
MAX_CHECKS = 500_000
MAX_BROAD_CHECKS = 2_000_000
MAX_PIECES = 12_000
MAX_TREES = 900
CELL = 24


def subtract(poly, obstacle):
    """Convex difference as nonoverlapping convex pieces, no polygon dependency."""
    retained = []
    rest = poly
    for a, b in zip(obstacle, obstacle[1:] + obstacle[:1]):
        normal = [b[1] - a[1], a[0] - b[0]]
        limit = dot(a, normal)
        outside = clip(rest, [-v for v in normal], -limit)
        if len(outside) >= 3 and area(outside) > 0.0001:
            retained.append(outside)
        rest = clip(rest, normal, limit)
        if len(rest) < 3 or area(rest) < 0.0001:
            break
    return retained


def expanded(poly, padding):
    # Clipping the original polygon cannot expand it. Start with a larger box.
    x0, z0, x1, z1 = bounds(poly)
    result = [[x0-padding*4, z0-padding*4], [x1+padding*4, z0-padding*4],
              [x1+padding*4, z1+padding*4], [x0-padding*4, z1+padding*4]]
    for a, b in zip(poly, poly[1:] + poly[:1]):
        normal = [b[1]-a[1], a[0]-b[0]]
        result = clip(result, normal, dot(a, normal) + padding * math.dist(a, b))
    return result


def field(seed, x, z):
    """One smooth world-space field, independent of administrative cuts."""
    x, z = x / 72, z / 72
    i, j = math.floor(x), math.floor(z)
    u, v = x - i, z - j
    u, v = u * u * (3 - 2 * u), v * v * (3 - 2 * v)
    a, b, c, d = [draw(derive(seed, str(i + dx), str(j + dz)))
                  for dx, dz in ((0, 0), (1, 0), (0, 1), (1, 1))]
    return (a * (1 - u) + b * u) * (1 - v) + (c * (1 - u) + d * u) * v


def tree_faces(center, radius, height, seed):
    """Explicit shared low-poly geometry consumed by every renderer."""
    x, z = center
    faces = []
    trunk = [[x - .16, z - .16], [x + .16, z - .16],
             [x + .16, z + .16], [x - .16, z + .16]]
    for a, b in zip(trunk, trunk[1:] + trunk[:1]):
        faces.append(dict(points=[[a[0], 0, a[1]], [b[0], 0, b[1]],
                                  [b[0], 1.9, b[1]], [a[0], 1.9, a[1]]],
                          color="#665b46"))
    phase = draw(seed) * math.tau
    ring = [[q(x + radius * math.cos(phase + i * math.tau / 6)), q(height * .54),
             q(z + radius * math.sin(phase + i * math.tau / 6))] for i in range(6)]
    palette = ("#52785a", "#608466", "#496e51")
    for i, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1])):
        faces.append(dict(points=[a, [x, height, z], b], color=palette[i % 3]))
        faces.append(dict(points=[b, [x, 1.3, z], a], color="#365440"))
    return faces


def generate_landscape(world):
    """Paint safe pockets, not every border or vacant lot. Input stays untouched."""
    patches, trees = [], []
    report = dict(candidates=0, checks=0, broadChecks=0, indexEntries=0, fragmentedCandidates=0,
                  budgetExhausted=None)
    result = dict(version=VERSION, decorative=True, terrainPreset="flat",
                  patches=patches, trees=trees, diagnostics=report)
    seed = derive(world["seed"], VERSION)
    obstacles, boxes, index = [], [], defaultdict(set)

    def cells(poly):
        x0, z0, x1, z1 = bounds(poly)
        nx, nz = math.floor(x1 / CELL) - math.floor(x0 / CELL) + 1, math.floor(z1 / CELL) - math.floor(z0 / CELL) + 1
        if nx * nz > MAX_INDEX:
            return None
        return [(i, j) for i in range(math.floor(x0 / CELL), math.floor(x1 / CELL) + 1)
                for j in range(math.floor(z0 / CELL), math.floor(z1 / CELL) + 1)]

    def reserve(poly):
        keys = cells(poly)
        if keys is None or report["indexEntries"] + len(keys) > MAX_INDEX:
            report["budgetExhausted"] = "spatial index"
            return False
        report["indexEntries"] += len(keys)
        for key in keys:
            index[key].add(len(obstacles))
        obstacles.append(poly)
        boxes.append(bounds(poly))
        return True

    for p in sorted(world["parcels"], key=lambda p: p["entityId"]):
        if not reserve(expanded(p["parcel"], .6)):
            return result  # Incomplete obstacle index: no planting is safe.
    incidence = {}
    for s in sorted(world["streets"], key=lambda s: s["id"]):
        if not reserve(expanded(ribbon(s["start"], s["end"], s["width"]), .65)):
            return result
        for p in (s["start"], s["end"]):
            incidence.setdefault(tuple(p), []).append(s["width"])
    for p, widths in sorted(incidence.items()):
        if len(widths) < 3:
            continue
        r = max(widths) / 2 + .7
        if not reserve([[p[0] + r * math.cos(i * math.pi / 4),
                         p[1] + r * math.sin(i * math.pi / 4)] for i in range(8)]):
            return result
    for f in world.get("terrain", {}).get("features", []):
        if not reserve(expanded(f["noBuildPolygon"], .3)):
            return result
    for site in world.get('campusPlan',{}).get('sites',[]):
        for court in site['courts']:
            if not reserve(court['polygon']):
                return result

    for district in sorted(world["districts"], key=lambda d: d["id"]):
        land = district["polygon"]
        x0, z0, x1, z1 = bounds(land)
        for row in range(math.floor(z0 / 16), math.ceil(z1 / 16) + 1):
            for column in range(math.floor(x0 / 16), math.ceil(x1 / 16) + 1):
                report["candidates"] += 1
                if report["candidates"] > MAX_CANDIDATES:
                    report["budgetExhausted"] = "candidates"
                    return result
                local = derive(seed, str(column), str(row))
                center = [column * 16 + (draw(local) - .5) * 7,
                          row * 16 + (draw(local, 1) - .5) * 7]
                moisture = field(seed, *center)
                if moisture < .48:
                    continue
                radius = 11 + draw(local, 2) * 5
                phase = draw(local, 3) * math.tau
                poly = [[center[0] + radius * math.cos(phase + i * math.tau / 12),
                         center[1] + radius * math.sin(phase + i * math.tau / 12)] for i in range(12)]
                # Intersect the patch with its parent land; never the child cell.
                for a, b in zip(land, land[1:] + land[:1]):
                    normal = [b[1] - a[1], a[0] - b[0]]
                    poly = clip(poly, normal, dot(a, normal))
                if len(poly) < 3 or area(poly) < 6:
                    continue
                keys = cells(poly)
                if keys is None:
                    report["budgetExhausted"] = "candidate extent"
                    return result
                near = sorted({i for k in keys for i in index[k]})
                box = bounds(poly)
                pieces = [poly]
                for i in near:
                    report["broadChecks"] += 1
                    if report["broadChecks"] > MAX_BROAD_CHECKS:
                        report["budgetExhausted"] = "broad phase"
                        return result
                    other = boxes[i]
                    if box[2] < other[0] or other[2] < box[0] or box[3] < other[1] or other[3] < box[1]:
                        continue
                    kept = []
                    for piece in pieces:
                        report["checks"] += 1
                        if report["checks"] > MAX_CHECKS:
                            report["budgetExhausted"] = "obstacle checks"
                            return result
                        kept.extend(subtract(piece, obstacles[i]) if overlap(piece, obstacles[i]) else [piece])
                    pieces = kept
                    if len(pieces) > 64:
                        pieces = []  # Discard this uncertified/fragmented candidate.
                        report["fragmentedCandidates"] += 1
                        break
                    if not pieces:
                        break
                for i, poly in enumerate(pieces):
                    poly = [point(p) for p in poly]
                    if area(poly) < 12 or len(poly) > 24:
                        continue
                    if len(patches) >= MAX_PIECES:
                        report["budgetExhausted"] = "output patches"
                        return result
                    identity = "landscape:" + derive(local, district["id"], str(i))
                    patches.append(dict(id=identity, districtId=district["id"], polygon=poly,
                                        color="#405747"))
                    c = point(centroid(poly))
                    r = 1.4 + draw(derive(identity), 1) * .7
                    if (len(trees) < MAX_TREES and draw(derive(identity)) < .7
                            and inside(c, poly, r + .2)
                            and all(math.dist(c, t["center"]) > r + t["radius"] + .5
                                    for t in trees)):
                        height = q(3.6 + draw(derive(identity), 2) * 1.6)
                        trees.append(dict(id=identity + ":tree", patchId=identity,
                                          center=c, radius=q(r), height=height,
                                          faces=tree_faces(c, r, height, identity)))
    return result
