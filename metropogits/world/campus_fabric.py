"""Different fitted campus compositions, never a repeated radial emblem."""

import math
from collections import defaultdict

from metropogits.street_diagonals import hull
from .geometry import bounds, inside, nearest, point, rectangle
from .seed import derive

VERSION = "campus-plan/0.6"
COMPOSITIONS = ("MEANDERING_MALL", "OPEN_ARCADE", "GARDEN_LANES")


class Fabric:
    VERSION = VERSION

    def __init__(self, polygon, axis, seed, roads):
        self.axis, self.seed, self.roads = axis, seed, roads
        c, s = math.cos(axis), math.sin(axis)
        lo, zo, hi, zh = bounds(
            [[c * p[0] + s * p[1], -s * p[0] + c * p[1]] for p in polygon]
        )
        self.first = (
            0
            if max(hi - lo, zh - zo) / max(1, min(hi - lo, zh - zo)) > 2
            else int(derive(seed, VERSION, "composition"), 16) % 3
        )

    def kind(self, index):
        return COMPOSITIONS[(self.first + index) % 3]

    def bearing(self, center, index):
        if not self.roads:
            return self.axis
        r = min(
            self.roads,
            key=lambda r: (
                math.dist(center, nearest(center, r["start"], r["end"])),
                r["id"],
            ),
        )
        yaw = math.atan2(r["end"][1] - r["start"][1], r["end"][0] - r["start"][0])
        # Stable local order from real frontage, not compass rays from a hub.
        return yaw + math.radians((-8, 11, -14)[index])

    def place(self, center, axis, index, p):
        yaw = self.bearing(center, index)
        c, s = math.cos(yaw), math.sin(yaw)
        return point([center[0] + c * p[0] - s * p[1], center[1] + s * p[0] + c * p[1]])

    def outline(self, center, axis, index, outer):
        kind = self.kind(index)
        if kind == "MEANDERING_MALL":
            shape = [(-15, -3), (-10, -6), (11, -5), (16, -1), (12, 5), (-11, 5)]
        elif kind == "OPEN_ARCADE":
            shape = [
                (-11, -6),
                (-6, -8),
                (10, -7),
                (13, -2),
                (10, 7),
                (-6, 8),
                (-13, 3),
                (-13, -2),
            ]
        else:
            shape = [(-8, -9), (5, -8), (9, -1), (6, 9), (-5, 10), (-10, 3)]
        if outer:
            # A homothetic offset is conservative at these bounded convex sizes.
            shape = [(x * 1.25, z * 1.25) for x, z in shape]
        # Convex source-free commons; all terrain/parcels are independently checked.
        return list(reversed(hull([self.place(center, axis, index, p) for p in shape])))

    def lawn(self, center, axis, index):
        return self.outline(center, axis, index, False)

    def loop(self, center, axis, index):
        return self.outline(center, axis, index, True)

    def branches(self, centers, axis, length, segment, clear, lawns):
        result = []
        for index, center in enumerate(centers):
            kind = self.kind(index)
            ports = self.loop(center, axis, index)
            if kind == "MEANDERING_MALL":
                shapes = [
                    [
                        (-48, -22),
                        (-32, -25),
                        (-16, -24),
                        (0, -20),
                        (17, -18),
                        (33, -20),
                        (48, -16),
                    ],
                    [(-42, 26), (-25, 24), (-8, 29), (9, 30), (26, 26), (44, 29)],
                ]
            elif kind == "OPEN_ARCADE":
                shapes = [
                    [
                        (-34, -15),
                        (-30, -29),
                        (-13, -34),
                        (7, -32),
                        (26, -24),
                        (33, -8),
                        (28, 12),
                        (15, 25),
                    ],
                    [(-22, 29), (-36, 23), (-42, 7), (-39, -12), (-27, -25)],
                ]
            else:
                shapes = [
                    [(-27, -41), (-31, -23), (-28, -5), (-24, 12), (-28, 31)],
                    [(24, -26), (28, -9), (27, 9), (34, 26), (31, 43)],
                    [(-15, 32), (1, 35), (18, 32), (35, 36), (48, 30)],
                ]
            for branch, shape in enumerate(shapes):
                points = [self.place(center, axis, index, p) for p in shape]
                # Keep a connected feasible run, not an entire decorative curve
                # whose end crosses a zone or a different commons.
                runs, run = [], []
                for a, b in zip(points, points[1:]):
                    if clear(a, b, lawns):
                        if not run:
                            run = [a]
                        run.append(b)
                    elif run:
                        runs.append(run)
                        run = []
                if run:
                    runs.append(run)
                for run in sorted(
                    runs,
                    key=lambda p: (-sum(math.dist(a, b) for a, b in zip(p, p[1:])), p),
                ):
                    if sum(math.dist(a, b) for a, b in zip(run, run[1:])) < 16:
                        continue
                    link = next(
                        (
                            [p, q]
                            for p, q in sorted(
                                ((p, q) for p in ports for q in run),
                                key=lambda pq: (math.dist(*pq), pq),
                            )
                            if clear(p, q, lawns)
                        ),
                        None,
                    )
                    if link is None:
                        continue
                    result.append(segment(*link, f"core:{index}:join:{branch}"))
                    result.extend(
                        segment(a, b, f"core:{index}:fabric:{branch}:{i}")
                        for i, (a, b) in enumerate(zip(run, run[1:]))
                    )
                    break
        return result

    @staticmethod
    def frontage(paths, polygon, shapes, collision, terrain):
        from .elevation import suitable
        from .rivers import blocks_ground_connection

        groups = defaultdict(list)
        for r in paths:
            # Connectors are circulation, not separate rows of buildings.
            if ":join:" in r["id"] or ":exterior-gate" in r["id"]:
                continue
            key = (
                r["id"].rsplit(":", 1)[0]
                if ":fabric:" in r["id"] or ":loop:" in r["id"]
                else r["id"]
            )
            groups[key].append(r)
        lots = []
        for key, pieces in groups.items():
            total = sum(math.dist(r["start"], r["end"]) for r in pieces)
            for station in range(max(0, math.floor((total - 8) / 9.6) + 1)):
                remaining = 4 + station * 9.6
                for r in pieces:
                    a, b = r["start"], r["end"]
                    length = math.dist(a, b)
                    if remaining > length:
                        remaining -= length
                        continue
                    u = [(b[j] - a[j]) / length for j in (0, 1)]
                    at = point([a[j] + remaining * u[j] for j in (0, 1)])
                    break
                for side in (-1, 1):
                    normal = [-u[1] * side, u[0] * side]
                    center = point([at[j] + normal[j] * 6.3 for j in (0, 1)])
                    angle = math.atan2(normal[0], -normal[1])
                    poly = rectangle(center, angle, 7.98, 7.98)
                    p = dict(
                        id=key + f":lot:{station}:{side}",
                        center=center,
                        angle=angle,
                        polygon=poly,
                        entrance=point([center[j] - normal[j] * 3 for j in (0, 1)]),
                        streetPoint=at,
                        laneId=r["id"],
                        blockProfile="CAMPUS",
                    )
                    if (
                        not all(inside(v, polygon, 1) for v in poly)
                        or collision(poly, shapes + [p["polygon"] for p in lots])
                        or (
                            terrain
                            and "elevation" in terrain
                            and (
                                not suitable(p, terrain)
                                or blocks_ground_connection(p["entrance"], at, terrain)
                            )
                        )
                    ):
                        continue
                    lots.append(p)
        return lots


def fabric_layout(*args):
    from .campus_neighborhood import neighborhood_layout

    form = Fabric(args[1], args[2], args[3], args[4])
    result = neighborhood_layout(*args, _form=form)
    if result is None:
        from .campus_landscape import landscape_layout

        result = landscape_layout(*args)
        args[-1]["fabricFallback"] = "FULL_NONRADIAL_CAPACITY_OR_ACCESS"
        return result
    plots, walks, site = result
    site["frontagePolicy"] = "FITTED_NONRADIAL_COMMONS"
    site["compositions"] = [
        dict(kind=form.kind(i), bearing=form.bearing(c["center"], i))
        for i, c in enumerate(site["courts"])
    ]
    return plots, walks, site
