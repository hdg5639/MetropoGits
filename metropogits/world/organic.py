"""Meandering local streets with independently phased oblique collectors."""

import math

from .frontage import add_corridor, frame, frontage_slots
from .geometry import bounds, inset
from .seed import derive, draw


def organic_slots(polygon, seed, *, axis=None, collectors=True):
    inner = inset(polygon, 5)
    if len(inner) < 3:
        return [], [], 0
    angle, local, world = frame(
        polygon, (draw(derive(seed, "axis")) - 0.5) * 0.4, axis=axis
    )
    x0, z0, x1, z1 = bounds([local(p) for p in inner])
    if max(x1 - x0, z1 - z0) > 5000:
        raise ValueError("world organic spatial extent limit")
    phase = draw(seed) * math.tau
    lanes = []
    for row in range(math.floor(z0 / 26) - 1, math.ceil(z1 / 26) + 2):
        jitter = (draw(derive(seed, "row", str(row))) - 0.5) * 4
        path = []
        for column in range(math.floor(x0 / 12) - 2, math.ceil(x1 / 12) + 3):
            u = column * 12
            v = (
                row * 26
                + jitter
                + 7 * math.sin(u / 65 + phase)
                + 3 * math.sin(u / 31 + row * 0.47 + phase)
            )
            path.append(world([u, v]))
        add_corridor(lanes, polygon, path, f"organic:row:{row}", 3.5)
    for column in (
        range(math.floor(x0 / 90) - 1, math.ceil(x1 / 90) + 2) if collectors else ()
    ):
        path = []
        for row in range(math.floor(z0 / 14) - 2, math.ceil(z1 / 14) + 3):
            v = row * 14
            u = (
                column * 90
                + 14 * math.sin(v / 95 + phase + column * 0.7)
                + (v - (z0 + z1) / 2) * 0.18
            )
            path.append(world([u, v]))
        add_corridor(lanes, polygon, path, f"organic:collector:{column}", 4)
        for lane in lanes:
            if lane.get("group") == f"organic:collector:{column}":
                lane["frontage"] = False
    return frontage_slots(polygon, lanes, profile="ORGANIC"), lanes, angle
