"""Pavement and junctions derived from the same paths as evidence overlays.

This is presentation geometry, not additional graph facts (ADR-014 amendment).
Unused layout reservations are not paved. All segment provenance resolves to
unchanged canonical networks; non-orthogonal legacy paths keep their overlays.
"""
from __future__ import annotations

from bisect import bisect_left, bisect_right
from collections import Counter, defaultdict
from typing import Any

STREET_CELL_SIZE = 7
CORRIDOR_WIDTH = 5.5


def _segments(scene):
    groups = [defaultdict(list), defaultdict(list)]
    for network in sorted(scene["networks"], key=lambda item: item["id"]):
        for a, b in zip(network["path"], network["path"][1:]):
            x0, z0, x1, z1 = map(float, (*a, *b))
            if x0 == x1 and z0 != z1:
                groups[1][x0].append((min(z0, z1), max(z0, z1), network["id"]))
            elif z0 == z1 and x0 != x1:
                groups[0][z0].append((min(x0, x1), max(x0, x1), network["id"]))
    result = []
    for axis in (0, 1):
        perpendicular = groups[1 - axis]
        coordinates = sorted(perpendicular)
        for fixed, intervals in sorted(groups[axis].items()):
            events = defaultdict(Counter)
            cuts = set()
            for low, high, network_id in intervals:
                events[low][network_id] += 1
                events[high][network_id] -= 1
                cuts.update((low, high))
                for cross in coordinates[bisect_left(coordinates, low):bisect_right(coordinates, high)]:
                    if any(start <= fixed <= end for start, end, _ in perpendicular[cross]):
                        cuts.add(cross)
            cuts = sorted(cuts)
            active = Counter()
            for low, high in zip(cuts, cuts[1:]):
                active.update(events[low])
                network_ids = sorted(key for key, count in active.items() if count > 0)
                if network_ids:
                    start = [low, fixed] if axis == 0 else [fixed, low]
                    end = [high, fixed] if axis == 0 else [fixed, high]
                    result.append(dict(start=start, end=end, networkIds=network_ids))
    return sorted(result, key=lambda part: (part["start"], part["end"], part["networkIds"]))


def street_surfaces(rectangle: dict[str, Any]) -> list[dict[str, Any]]:
    """Layered corridor surface only; paint is derived from its actual path."""
    x, z, width, depth = (float(rectangle[key]) for key in ("x", "z", "width", "depth"))
    inset = min(0.35, width / 6, depth / 6)
    return [dict(x=x, z=z, width=width, depth=depth, color="#526176", elevation=0.12),
            dict(x=x + inset, z=z + inset, width=width - 2 * inset,
                 depth=depth - 2 * inset, color="#253141", elevation=0.13)]


def derive_street_grid(scene: dict[str, Any]) -> dict[str, Any]:
    segments = _segments(scene)
    networks = {item["id"]: item for item in scene["networks"]}
    nodes = defaultdict(lambda: dict(neighbors=set(), networkIds=set()))
    rectangles, curbs, asphalt, paint = [], [], [], []
    radius = CORRIDOR_WIDTH / 2
    for index, segment in enumerate(segments):
        segment["id"] = f"visual:route-segment:{index}"
        segment["edgeIds"] = sorted({edge for key in segment["networkIds"] for edge in networks[key]["edgeIds"]})
        a, b = segment["start"], segment["end"]
        for point, other in ((a, b), (b, a)):
            node = nodes[tuple(point)]
            node["neighbors"].add(tuple(other))
            node["networkIds"].update(segment["networkIds"])
        rectangle = dict(x=a[0] - radius, z=a[1] - radius,
                         width=b[0] - a[0] + CORRIDOR_WIDTH,
                         depth=b[1] - a[1] + CORRIDOR_WIDTH,
                         tier="ROUTE_ACCESS", networkIds=segment["networkIds"], segmentId=segment["id"])
        rectangles.append(rectangle)
        curb, surface = street_surfaces(rectangle)
        provenance = dict(networkIds=segment["networkIds"], segmentId=segment["id"])
        curbs.append({**curb, **provenance})
        asphalt.append({**surface, **provenance})
        horizontal = a[1] == b[1]
        length = (b[0] - a[0]) if horizontal else (b[1] - a[1])
        # Keep turns, intersections and endpoint caps free of longitudinal paint.
        for offset in range(4, int(length) - 4, 8):
            stripe_length = min(3, length - offset - radius)
            paint.append(dict(x=a[0] + offset if horizontal else a[0] - 0.1,
                              z=a[1] - 0.1 if horizontal else a[1] + offset,
                              width=stripe_length if horizontal else 0.2,
                              depth=0.2 if horizontal else stripe_length,
                              color="#a2a996", elevation=0.145, **provenance))
    junctions = [dict(point=list(point), degree=len(node["neighbors"]),
                      networkIds=sorted(node["networkIds"]))
                 for point, node in sorted(nodes.items()) if len(node["neighbors"]) >= 3]
    return dict(cellSize=STREET_CELL_SIZE, semantic=False, basis="network.path",
                segments=segments, junctions=junctions, rectangles=rectangles,
                surfaces=curbs + asphalt + paint)
