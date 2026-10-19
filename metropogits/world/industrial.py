"""Wide circulation spines and branching service courts; not a semantic claim."""

import math

from .frontage import add_corridor, frame, frontage_slots
from .geometry import bounds, centroid, inset, inside
from .seed import derive, draw


def industrial_slots(polygon, seed, *, axis=None):
    # Court grids can miss narrow corners. Try four fixed local frames rather
    # than repeatedly enlarging unrelated districts or increasing repair caps.
    best = ([], [], 0)
    for turn, phase in ((0, 0), (0, 14), (math.pi / 2, 0), (math.pi / 2, 14)):
        candidate = _court_plan(polygon, seed, turn, phase, axis)
        if len(candidate[0]) > len(best[0]):
            best = candidate
    return best


def _court_plan(polygon, seed, turn, phase, axis=None):
    inner = inset(polygon, 5)
    if len(inner) < 3:
        return [], [], 0
    angle, local, world = frame(polygon, turn, axis=axis)
    x0, z0, x1, z1 = bounds([local(p) for p in inner])
    if max(x1 - x0, z1 - z0) > 5000:
        raise ValueError("world industrial spatial extent limit")
    center_u, center_v = local(centroid(inner))
    spines = [
        column * 72 + center_u
        for column in range(
            math.ceil((x0 + 6 - center_u) / 72),
            math.floor((x1 - 6 - center_u) / 72) + 1,
        )
    ]
    if not spines:
        spines = [center_u]
    lanes = []
    for column, u in enumerate(spines):
        identity = f"industrial:spine:{column}"
        add_corridor(
            lanes, polygon, [world([u, z0 - 10]), world([u, z1 + 10])], identity, 7
        )
        for lane in lanes:
            if lane.get("group") == identity:
                lane["frontage"] = False
        shift = center_v + phase + (draw(derive(seed, "court", str(column))) - 0.5) * 8
        for row in range(
            math.floor((z0 - shift) / 28) - 1, math.ceil((z1 - shift) / 28) + 2
        ):
            v = row * 28 + shift
            if not inside(world([u, v]), inner):
                continue
            # Court branches touch the spine and terminate before the next one.
            path = [world([u - 32, v]), world([u, v]), world([u + 32, v])]
            add_corridor(
                lanes,
                polygon,
                path,
                f"industrial:court:{column}:{row}",
                4,
                connect=False,
            )
    return (
        frontage_slots(
            polygon,
            lanes,
            pitch=10,
            width=9,
            depth=10,
            setback=7.5,
            profile="INDUSTRIAL",
        ),
        lanes,
        angle,
    )
