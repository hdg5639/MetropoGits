"""Clip paint at actual same-level crossing/merge mouths, never at fake nodes."""

import math
from collections import defaultdict

from metropogits.street_diagonals import overlap
from .geometry import area, bounds, point, ribbon
from .landscape import subtract

MAX_STREETS = 50_000
MAX_INDEX = 500_000
MAX_WORK = 2_000_000
MAX_PIECES = 100_000


def clean_markings(world, markings):
    if len(world["streets"]) > MAX_STREETS or len(markings) > MAX_PIECES:
        raise ValueError("street marking input limit")
    profiles = world["streetPlan"]["segments"]
    roads = {s["id"]: s for s in world["streets"]}
    index = defaultdict(set)
    polygons = {}
    entries = work = 0

    def cells(poly):
        x0, z0, x1, z1 = bounds(poly)
        a, b, c, d = (math.floor(v / 16) for v in (x0, x1, z0, z1))
        if (b - a + 1) * (d - c + 1) > MAX_INDEX:
            raise ValueError("street marking extent limit")
        return [(x, z) for x in range(a, b + 1) for z in range(c, d + 1)]

    def level(s):
        return s.get("bridgeId"), s.get("tunnelId")

    for s in sorted(roads.values(), key=lambda s: s["id"]):
        if s["access"] or profiles[s["id"]]["streetClass"] in ("SERVICE", "PEDESTRIAN"):
            continue
        poly = ribbon(s["start"], s["end"], s["width"])
        keys = cells(poly)
        entries += len(keys)
        if entries > MAX_INDEX:
            raise ValueError("street marking index limit")
        polygons[s["id"]] = poly
        for key in keys:
            index[key].add(s["id"])
    result = []
    from .elevation import surface
    from .rivers import height_at

    field = surface(world["terrain"]) if "surface" in world else None
    for marking in markings:
        s = roads[marking["physicalId"]]
        a, b = s["start"], s["end"]
        length = math.dist(a, b)
        u = [(b[j] - a[j]) / length for j in (0, 1)]
        pieces = [marking["points"]]
        touched = False
        for key in sorted(
            {k for cell in cells(marking["points"]) for k in index[cell]}
        ):
            other = roads[key]
            if key == s["id"] or level(other) != level(s):
                continue
            c, d = other["start"], other["end"]
            v = [(d[j] - c[j]) / math.dist(c, d) for j in (0, 1)]
            # Atomic pieces of the SAME straight carriageway must not erase
            # each other's dashes. Parallel but laterally offset lanes can merge.
            if abs(u[0] * v[1] - u[1] * v[0]) < 0.002 and all(
                abs((p[0] - a[0]) * u[1] - (p[1] - a[1]) * u[0]) < 0.002 for p in (c, d)
            ):
                continue
            clipped = []
            for poly in pieces:
                work += len(poly) * len(polygons[key])
                if work > MAX_WORK:
                    raise ValueError("street marking clipping work limit")
                if overlap(poly, polygons[key]):
                    clipped.extend(subtract(poly, polygons[key]))
                    touched = True
                else:
                    clipped.append(poly)
            pieces = clipped
            if len(pieces) > 64:
                raise ValueError("street marking fragmentation limit")
            if not pieces:
                break
        if not touched:
            result.append(marking)
        else:
            for poly in pieces:
                for i in range(1, len(poly) - 1):
                    points = [
                        point(poly[0]),
                        point(poly[i]),
                        point(poly[i + 1]),
                        point(poly[i + 1]),
                    ]
                    if area(points) < 0.0001:
                        continue
                    item = dict(marking, points=points)
                    if field:
                        item["pointHeights"] = [
                            height_at(s, p) + 0.04
                            if s.get("bridgeId") or s.get("tunnelId")
                            else field.height(p) + 0.12
                            for p in points
                        ]
                    result.append(item)
        if len(result) > MAX_PIECES:
            raise ValueError("street marking output limit")
    return result
