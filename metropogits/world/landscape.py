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
PARK_VERSION = "urban-parks/0.1"
PARK_TREE_RESERVE = 200
MAX_STREET_TREES = 1400
STREET_TREE_SPACING = 11
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


def _scaled(poly, center, factor):
    return [point([center[0] + (p[0] - center[0]) * factor, center[1] + (p[1] - center[1]) * factor])
            for p in poly]


def _winding(poly):
    return 1 if sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(poly, poly[1:] + poly[:1])) >= 0 else -1


def _within(poly, shape):
    """Clip a convex shape to a convex polygon of either winding."""
    sign = _winding(poly)
    for a, b in zip(poly, poly[1:] + poly[:1]):
        normal = [sign * (b[1] - a[1]), sign * (a[0] - b[0])]
        shape = clip(shape, normal, dot(a, normal))
        if len(shape) < 3:
            return []
    return shape


def add_parks(world, result, seed):
    """Promote a few large free pockets near real buildings into decorative parks.

    Parks are presentation only: no source entity, no new roads, never on
    parcels, streets or protected terrain (they reuse already-cleared patches).
    """
    patches, trees = result["patches"], result["trees"]
    centers = [centroid(p["parcel"]) for p in world["parcels"]]
    if not patches or not centers:
        return
    target = max(1, min(14, round(len(centers) / 90)))
    candidates = []
    for patch in patches:
        size = area(patch["polygon"])
        if size < 170 or len(patch["polygon"]) > 20:
            continue
        c = centroid(patch["polygon"])
        near = min(math.dist(c, q_) for q_ in centers)
        # Prefer generous pockets that serve nearby blocks, not remote scrub.
        score = min(size, 700) * .02 - abs(near - 28) * .06 + draw(derive(seed, patch["id"], "park")) * 1.5
        candidates.append((score, patch["id"], patch, c, size))
    chosen = []
    for score, _, patch, c, size in sorted(candidates, key=lambda v: (-v[0], v[1])):
        if len(chosen) >= target:
            break
        # Global spacing only: administrative cuts must not change park choice.
        if any(math.dist(c, o[1]) < 70 for o in chosen):
            continue
        chosen.append((patch, c, size))
    for patch, c, size in chosen:
        polygon = patch["polygon"]
        phase = draw(derive(seed, patch["id"], "axis")) * math.pi
        direction = [math.cos(phase), math.sin(phase)]
        normal = [-direction[1], direction[0]]
        reach = math.sqrt(size) * 2
        pond = _scaled(polygon, c, .4) if size >= 330 else None
        pond_radius = math.sqrt(area(pond) / math.pi) if pond else 0
        paths = []
        offsets = (-(pond_radius + 1.8), pond_radius + 1.8) if pond else (0,)
        for offset in offsets:
            mid = [c[0] + normal[0] * offset, c[1] + normal[1] * offset]
            a = [mid[0] - direction[0] * reach, mid[1] - direction[1] * reach]
            b = [mid[0] + direction[0] * reach, mid[1] + direction[1] * reach]
            clipped = _within(_scaled(polygon, c, .96), ribbon(a, b, 1.7))
            if len(clipped) >= 3 and area(clipped) > 1:
                paths.append([point(v) for v in clipped])
        patch["color"] = "#4f7d4c"
        patch["park"] = dict(version=PARK_VERSION, kind="URBAN_PARK", decorative=True,
                             pond=pond, paths=paths,
                             basis="DECORATIVE_OPEN_SPACE_NOT_SOURCE_FACT")
        ring = _scaled(polygon, c, .8)
        for i, v in enumerate(ring):
            if len(trees) >= MAX_TREES + PARK_TREE_RESERVE:
                break
            identity = patch["id"] + ":park-tree:" + str(i)
            r = 1.5 + draw(derive(identity)) * .6
            if not inside(v, polygon, r + .3) or any(math.dist(v, t["center"]) <= r + t["radius"] + .6 for t in trees):
                continue
            if pond and math.dist(v, c) < pond_radius + r + .5:
                continue
            height = q(4.2 + draw(derive(identity), 1) * 1.8)
            trees.append(dict(id=identity, patchId=patch["id"], center=point(v), radius=q(r),
                              height=height, faces=tree_faces(v, r, height, identity)))
    result["parkCount"] = len(chosen)


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
                if moisture < .66:
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
    def blocked(c, r):
        probe = [[c[0] + r * math.cos(i * math.pi / 4), c[1] + r * math.sin(i * math.pi / 4)] for i in range(8)]
        keys = cells(probe)
        if keys is None:
            return True
        box = bounds(probe)
        for i in sorted({i for k in keys for i in index.get(k, ())}):
            other = boxes[i]
            if box[2] < other[0] or other[2] < box[0] or box[3] < other[1] or other[3] < box[1]:
                continue
            if overlap(probe, obstacles[i]):
                return True
        return False

    # Street trees on the wider avenues only: an even, seeded rhythm that
    # dresses open ground without painting every verge.
    street_trees, grid = [], defaultdict(list)
    for t in trees:
        grid[(math.floor(t["center"][0] / 4), math.floor(t["center"][1] / 4))].append(t)
    for street in sorted(world["streets"], key=lambda st: st["id"]):
        if street["width"] < 3 or len(street_trees) >= MAX_STREET_TREES:
            continue
        a, b = street["start"], street["end"]
        length = math.dist(a, b)
        if length < 14 or draw(derive(seed, street["id"], "avenue")) > (1 if street["width"] >= 7 else .38):
            continue
        direction = [(b[0] - a[0]) / length, (b[1] - a[1]) / length]
        normal = [-direction[1], direction[0]]
        steps = int((length - 8) // STREET_TREE_SPACING)
        for step in range(steps + 1):
            for side in (-1, 1):
                identity = "street-tree:" + derive(seed, street["id"], str(step), str(side))
                if draw(identity) < .22:
                    continue
                along = 4 + step * STREET_TREE_SPACING + (draw(identity, 1) - .5) * 3
                radius = 1.1 + draw(identity, 2) * .5
                offset = side * (street["width"] / 2 + .65 + radius + .35)
                c = point([a[0] + direction[0] * along + normal[0] * offset,
                           a[1] + direction[1] * along + normal[1] * offset])
                key = (math.floor(c[0] / 4), math.floor(c[1] / 4))
                if blocked(c, radius) or any(math.dist(c, t["center"]) < radius + t["radius"] + .8
                                             for dx in (-1, 0, 1) for dz in (-1, 0, 1)
                                             for t in grid.get((key[0] + dx, key[1] + dz), ())):
                    continue
                height = q(3.8 + draw(identity, 3) * 1.4)
                tree = dict(id=identity, patchId=None, kind="STREET_TREE", center=c, radius=q(radius),
                            height=height, faces=tree_faces(c, radius, height, identity))
                street_trees.append(tree)
                grid[key].append(tree)
    trees.extend(street_trees)
    result["streetTreeCount"] = len(street_trees)
    add_parks(world, result, seed)
    return result
