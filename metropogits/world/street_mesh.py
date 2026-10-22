"""Shared bounded pavement mesh: joined bends and curb-clipped walking surfaces."""

import math
from collections import defaultdict

from metropogits.street_diagonals import overlap, hull
from .geometry import area, bounds, point, ribbon
from .landscape import subtract
from .street_hierarchy import COLORS, CLASSES

VERSION = "world-street-mesh/0.2"
MAX_WORK = 2_000_000
MAX_INDEX = 500_000
MAX_PIECES = 250_000


def street_mesh(world, *, compounds=()):
    if len(world["streets"]) > 50_000:
        raise ValueError("street mesh input limit")
    streets = sorted(world["streets"], key=lambda s: s["id"])
    profiles = world.get("streetPlan", {}).get("segments", {})
    graded = "surface" in world
    paths = []
    adj = defaultdict(list)
    index = defaultdict(set)
    obstacles = []
    work = entries = 0

    def cells(poly):
        x0, z0, x1, z1 = bounds(poly)
        a, b, c, d = (
            math.floor(x0 / 16),
            math.floor(x1 / 16),
            math.floor(z0 / 16),
            math.floor(z1 / 16),
        )
        if (b - a + 1) * (d - c + 1) > MAX_INDEX:
            raise ValueError("street mesh extent limit")
        return [(x, z) for x in range(a, b + 1) for z in range(c, d + 1)]

    def reserve(poly, kind):
        nonlocal entries
        keys = cells(poly)
        entries += len(keys)
        if entries > MAX_INDEX:
            raise ValueError("street mesh index limit")
        for k in keys:
            index[k].add(len(obstacles))
        obstacles.append((poly, kind))

    def nearby(poly, kind):
        nonlocal work
        ids = sorted(
            {i for k in cells(poly) for i in index[k] if obstacles[i][1] == kind}
        )
        work += len(ids)
        if work > MAX_WORK:
            raise ValueError("street mesh clearance work limit")
        return [obstacles[i][0] for i in ids]

    for p in world["parcels"]:
        reserve(p["parcel"], "clearance")
    for compound in compounds:
        if compound.get('physicalProgramVersion') != 'capacity-replan/0.2':
            continue
        model = compound['physicalModel']
        for part in model['parts']:
            if part['y'] <= model.get('baseElevation', 0) + .15 and part.get('materialKind') not in (12, 13, 14):
                reserve(part['footprint'], 'interior')
    for f in world.get("terrain", {}).get("features", []):
        reserve(f["noBuildPolygon"], "clearance")
    for site in world.get("campusPlan", {}).get("sites", []):
        for c in site["courts"]:
            reserve(c["polygon"], "clearance")
    for s in streets:
        cls = profiles.get(s["id"], {}).get(
            "streetClass", "SERVICE" if s["access"] else "LOCAL"
        )
        poly = ribbon(s["start"], s["end"], s["width"])
        walking = cls in ("PEDESTRIAN", "SERVICE")
        paths.append((s, cls, poly, walking))
        if not walking:
            reserve(poly, "vehicle")
        if not s["access"]:
            for p in (s["start"], s["end"]):
                adj[(tuple(p), walking)].append(s)
    joints = []
    # Cross-section hulls give bevel joins with no unbounded miter spikes.
    # Do not sew a bridge ramp to ground-level pavement or invent a road link.
    for (at, walking), incident in sorted(adj.items()):
        if len(incident) < 2 or any(
            s.get("bridgeId") or s.get("tunnelId") for s in incident
        ):
            continue
        tips = []
        for s in incident:
            other = s["end"] if tuple(s["start"]) == at else s["start"]
            d = math.dist(at, other)
            r = s["width"] / 2
            normal = [-(other[1] - at[1]) / d, (other[0] - at[0]) / d]
            tips.extend(
                [
                    point([at[j] + side * normal[j] * r for j in (0, 1)])
                    for side in (-1, 1)
                ]
            )
        poly = list(reversed(hull(tips)))
        if len(poly) < 3 or area(poly) < 0.0001:
            continue
        if any(overlap(poly, p) for p in nearby(poly, "clearance")):
            continue
        s = min(
            incident,
            key=lambda s: (
                CLASSES.index(profiles.get(s["id"], {}).get("streetClass", "LOCAL")),
                -s["width"],
                s["id"],
            ),
        )
        cls = profiles.get(s["id"], {}).get("streetClass", "LOCAL")
        joints.append((s, cls, poly, walking))
        if not walking:
            reserve(poly, "vehicle")
    result = []

    def emit(base, poly, height=None):
        # Both browser renderers consume quads; encode convex faces as explicit
        # triangles (duplicate fourth corner), never silently discard vertices.
        for i in range(1, len(poly) - 1):
            vertices = [poly[0], poly[i + 1], poly[i], poly[i]]
            if area(vertices) < 0.000001:
                continue
            result.append(
                dict(
                    base,
                    points=[point(p) for p in vertices],
                    **(
                        dict(pointHeights=[height(p) for p in vertices])
                        if height
                        else {}
                    ),
                )
            )
            if len(result) > MAX_PIECES:
                raise ValueError("street mesh output limit")

    from .elevation import surface

    field = surface(world["terrain"]) if graded else None
    from .rivers import height_at

    # Coplanar span rectangles used to paint over one another at forks and
    # bends. Partition their union once, with one stable class/colour owner.
    # This edits pavement only: every source path/physical street stays intact.
    union_index = defaultdict(set)
    union_polys = []

    def level(s):
        # Each door ramp retains its own independent slope law. Ordinary walks
        # share the ground field, but never paint over vehicle carriageways.
        return (s.get("bridgeId"), s.get("tunnelId"), s["id"] if s["access"] else None)

    ordered = sorted(
        paths + joints,
        key=lambda r: (r[3], CLASSES.index(r[1]), -r[0]["width"], r[0]["id"], r[2]),
    )
    for s, cls, poly, walking in ordered:
        pieces = [poly]
        if s['access']:
            # A file's logical door may become an interior compound address.
            # Keep its exact routing/provenance, but never paint a public road
            # through that certified complex's ground-floor solid volumes.
            for obstacle in nearby(poly, 'interior'):
                pieces = [part for p in pieces for part in
                          (subtract(p, obstacle) if overlap(p, obstacle) else [p])]
                if len(pieces) > 128:
                    raise ValueError('street mesh interior clipping piece limit')
        if walking:
            for obstacle in nearby(poly, "vehicle"):
                pieces = [
                    part
                    for p in pieces
                    for part in (subtract(p, obstacle) if overlap(p, obstacle) else [p])
                ]
                if len(pieces) > 128:
                    raise ValueError("street mesh clipping piece limit")
        keys = cells(poly)
        group = (walking, level(s))
        for i in sorted({i for key in keys for i in union_index[key]}):
            obstacle, other_level = union_polys[i]
            if other_level != group:
                continue
            work += len(pieces)
            if work > MAX_WORK:
                raise ValueError("street mesh union work limit")
            pieces = [
                part
                for p in pieces
                for part in (subtract(p, obstacle) if overlap(p, obstacle) else [p])
            ]
            if len(pieces) > 128:
                raise ValueError("street mesh union piece limit")
            if not pieces:
                break
        entries += len(keys)
        if entries > MAX_INDEX:
            raise ValueError("street mesh union index limit")
        for key in keys:
            union_index[key].add(len(union_polys))
        union_polys.append((poly, group))
        for poly in pieces:
            base = dict(
                physicalId=s["id"],
                streetClass=cls,
                width=s["width"],
                color=COLORS[cls]["detail"],
                kind="STRUCTURAL",
                access=s["access"],
            )
            if field:
                if s["access"] or s.get("bridgeId") or s.get("tunnelId"):
                    # Clip along each original elevation interval so access ramps
                    # and certified bridge grades retain their exact height law.
                    for a, b in zip(s["heightProfile"], s["heightProfile"][1:]):
                        from metropogits.block_orientation import clip

                        part = clip(
                            poly, list(reversed(ribbon(a[:2], b[:2], s["width"])))
                        )
                        if len(part) < 3 or area(part) < 0.000001:
                            continue
                        road = dict(s, start=a[:2], end=b[:2], heights=[a[2], b[2]])
                        emit(base, part, lambda p: height_at(road, p))
                else:
                    for part in field.pieces(poly):
                        emit(base, part, lambda p: field.height(p) + 0.08)
            else:
                emit(base, poly)
    return result
