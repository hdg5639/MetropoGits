"""Offline source-neutral campus forms; no source entities are created here."""

import math

from .geometry import point, rectangle
from .seed import derive

VERSION = "campus-plan/0.2"


def tech_park(center, axis, a, b, exit_side, seed):
    """Two compact garden-facing groups, linked before assigning real files."""
    c, s = math.cos(axis), math.sin(axis)

    def place(p):
        return point([center[0] + c * p[0] - s * p[1], center[1] + s * p[0] + c * p[1]])

    identity = "world:campus-court:" + derive(seed, str(center), VERSION, "park")
    plots, walks, courts = [], [], []

    def walk(start, end, key):
        walks.append(
            dict(
                id=identity + ":" + key,
                start=place(start),
                end=place(end),
                width=1.2,
                access=False,
                structural=True,
            )
        )

    def lot(local, angle, front, at, key):
        location = place(local)
        plots.append(
            dict(
                id=identity + ":lot:" + key,
                center=location,
                angle=axis + angle,
                polygon=rectangle(location, axis + angle, 7.98, 7.98),
                entrance=place([local[j] + 3 * front[j] for j in (0, 1)]),
                streetPoint=place(at),
                laneId=identity,
                blockProfile="CAMPUS",
            )
        )

    omitted = {
        "N": (1, "z", 1),
        "S": (0, "z", -1),
        "E": (1, "x", 1),
        "W": (0, "x", -1),
    }[exit_side]
    for i, (x, z) in enumerate(((-11, -5.5), (11, 5.5))):
        corners = [[x - 5, z - 5], [x + 5, z - 5], [x + 5, z + 5], [x - 5, z + 5]]
        for j, (p, r) in enumerate(zip(corners, corners[1:] + corners[:1])):
            walk(p, r, f"garden:{i}:walk:{j}")
        courts.append(
            dict(
                id=identity + f":garden:{i}",
                center=place([x, z]),
                polygon=rectangle(place([x, z]), axis, 7.5, 7.5),
            )
        )
        for side in (-1, 1):
            if omitted != (i, "x", side):
                lot(
                    [x + side * 10, z],
                    side * math.pi / 2,
                    [-side, 0],
                    [x + side * 5, z],
                    f"x:{side}:{i}",
                )
            if omitted != (i, "z", side):
                lot(
                    [x, z + side * 10],
                    math.pi if side == 1 else 0,
                    [0, -side],
                    [x, z + side * 5],
                    f"z:{side}:{i}",
                )

    # Offset access, not a second global grid or decorative vehicle loop.
    promenade = [[-6, -0.5], [-5.5, -0.1], [5.5, 0.1], [6, 0.5]]
    for i, (p, r) in enumerate(zip(promenade, promenade[1:])):
        walk(p, r, f"promenade:{i}")
    for side in (-1, 1):
        lot(
            [0, side * 17],
            math.pi if side == 1 else 0,
            [0, -side],
            [0, side * 12],
            f"z:{side}:spare",
        )
        walk([0, side * 12], [side * 6, side * 10.5], f"garden-link:{side}")
    edge, outer = {
        "N": ([11, 10.5], [11, b + 12]),
        "S": ([-11, -10.5], [-11, -b - 12]),
        "E": ([16, 5.5], [a + 12, 5.5]),
        "W": ([-16, -5.5], [-a - 12, -5.5]),
    }[exit_side]
    walk(edge, outer, "exit")
    return plots, walks, courts, rectangle(center, axis, 2 * (a + 9.5), 2 * (b + 9.5))
