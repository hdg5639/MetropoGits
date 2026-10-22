"""Source-affinity facility sites reserved before file address subdivision."""

import math
from collections import defaultdict

from .campus_fabric import Fabric
from .campus_programmed import annotate_program
from .geometry import inside, nearest, point, rectangle, ribbon
from .seed import derive

VERSION = "campus-plan/0.8"
MAX_GROUP = 8
MAX_PROPOSALS = 12_000


def planning_affinity(graph, zones):
    """Bound shared-target expansion by actual neighborhood, not the metropolis."""
    from .affinity import dependency_pairs
    from .campus_landmarks import campus_affinity

    owners = {key: "campus" for zone in zones for key in zone["memberEntityIds"]}
    pairs = dependency_pairs(graph, owners)
    for zone in sorted(zones, key=lambda z: z["id"]):
        local = campus_affinity(
            graph, dict.fromkeys(zone["memberEntityIds"], zone["id"])
        )
        for key, weight in local.items():
            pairs[key] = max(pairs.get(key, 0), weight)
    return pairs


def requirements(zone, pairs, maximum=MAX_GROUP, rotate=True):
    """Connected visual groups; a shared target is affinity, not a peer edge."""
    ids = set(zone["memberEntityIds"])
    links = defaultdict(dict)
    for (a, b), weight in sorted(pairs.items()):
        if a in ids and b in ids:
            links[a][b] = links[b][a] = weight
    free, result = set(ids), []
    while free:
        anchor = min(free, key=lambda k: (-sum(links[k].values()), k))
        chosen = [anchor]
        free.remove(anchor)
        while len(chosen) < maximum:
            neighbors = {k for a in chosen for k in links[a] if k in free}
            if not neighbors:
                break
            selected = min(
                neighbors, key=lambda k: (-sum(links[k].get(a, 0) for a in chosen), k)
            )
            chosen.append(selected)
            free.remove(selected)
        columns = len(chosen) if len(chosen) <= 3 else math.ceil(len(chosen) / 2)
        rows = math.ceil(len(chosen) / columns)
        identity = "world:facility-site:" + derive(VERSION, zone["id"], *sorted(chosen))
        if rotate and int(derive(identity, "site-aspect"), 16) % 2:
            columns, rows = rows, columns
        result.append(
            dict(
                id=identity,
                memberEntityIds=chosen,
                columns=columns,
                rows=rows,
                width=columns * 8,
                depth=rows * 8,
                groupingBasis="STATIC_EDGES_AND_SHARED_LOCAL_TARGETS",
            )
        )
    return sorted(result, key=lambda r: (-len(r["memberEntityIds"]), r["id"]))


class EstateFabric(Fabric):
    VERSION = VERSION

    def __init__(
        self, zone, polygon, axis, seed, roads, pairs, maximum, rotate, complete=True
    ):
        super().__init__(polygon, axis, seed, roads)
        self.requests = requirements(zone, pairs, maximum, rotate)
        self.assignments, self.sites, self.extra_walks = {}, [], []
        self.complete = complete

    def external_ports(self, walks, roads, polygon, connect):
        """Plan real perimeter access to each touching external road component.

        Done before lots exist, so access is reserved infrastructure rather
        than a later connector driven through occupied source buildings.
        """
        from .infrastructure import atomic_streets
        from .radial import _clipped

        if self.complete and not getattr(self, 'connect_perimeter', False):
            return []

        atomic = atomic_streets(roads)
        adjacent = defaultdict(set)
        for r in atomic:
            a, b = tuple(r["start"]), tuple(r["end"])
            adjacent[a].add(b)
            adjacent[b].add(a)
        labels = {}
        for start in sorted(adjacent):
            pending = [start]
            while pending:
                at = pending.pop()
                if at in labels:
                    continue
                labels[at] = start
                pending.extend(sorted(adjacent[at] - labels.keys()))
        touching = defaultdict(list)
        for r in atomic:
            clipped = _clipped(r["start"], r["end"], polygon)
            if clipped and math.dist(*clipped) > 0.01:
                touching[labels[tuple(r["start"])]].append(clipped)
        additions = []
        for index, pieces in enumerate(touching.values()):
            ports = [p for w in walks + additions for p in (w["start"], w["end"])]
            if any(
                math.dist(p, nearest(p, a, b)) < 0.001 for p in ports for a, b in pieces
            ):
                continue
            targets = sorted(
                {tuple(point(nearest(p, a, b))) for p in ports for a, b in pieces},
                key=lambda q: (min(math.dist(p, q) for p in ports), q),
            )[:24]
            joined = connect(
                ports, [list(p) for p in targets], f"exterior-gate:port:{index}"
            )
            if joined is None:
                return None
            additions.extend(joined)
        return additions

    def branches(self, centers, axis, length, segment, clear, lawns):
        # Shared parallel pedestrian spines, not one ray per source building.
        result = []
        for index, center in enumerate(centers):
            ports = self.loop(center, axis, index)
            for side in (-1, 1):
                for half in (56, 44, 32, 22):
                    a, b = [
                        self.place(center, axis, index, [x, side * 27])
                        for x in (-half, half)
                    ]
                    if not clear(a, b, lawns):
                        continue
                    joins = sorted(
                        ((p, nearest(p, a, b)) for p in ports),
                        key=lambda pq: (math.dist(*pq), pq),
                    )
                    join = next(((p, q) for p, q in joins if clear(p, q, lawns)), None)
                    if join:
                        result.append(
                            segment(a, b, f"core:{index}:estate-spine:{side}")
                        )
                        result.append(
                            segment(*join, f"core:{index}:join:estate:{side}")
                        )
                        break
        return result

    def frontage(self, paths, polygon, shapes, collision, terrain):
        from .elevation import suitable
        from .rivers import blocks_ground_connection

        lots, reserved = [], []
        self.assignments, self.sites, self.extra_walks = {}, [], []
        work = 0
        use = defaultdict(int)
        lanes = sorted(
            (r for r in paths if ":estate-spine:" in r["id"]),
            key=lambda r: (-math.dist(r["start"], r["end"]), r["id"]),
        )
        # A campus needs a few large complexes AND supporting buildings, not a
        # compulsory estate for every source. Reserve the four cohesive anchors
        # first; fit remaining real files in the free pedestrian frontage.
        requests = (
            self.requests
            if self.complete
            else [r for r in self.requests if len(r["memberEntityIds"]) >= 3][:4]
        )
        for request in requests:
            fitted = False
            width, depth = request["width"], request["depth"]
            for lane in sorted(
                lanes,
                key=lambda r: (
                    use[r["id"].split(":estate-spine:")[0]],
                    -math.dist(r["start"], r["end"]),
                    r["id"],
                ),
            ):
                a, b = lane["start"], lane["end"]
                length = math.dist(a, b)
                u = [(b[i] - a[i]) / length for i in (0, 1)]
                for station in range(max(0, math.floor((length - width - 6) / 4) + 1)):
                    at = [a[i] + u[i] * (width / 2 + 3 + station * 4) for i in (0, 1)]
                    for side in (-1, 1):
                        work += 1
                        if work > MAX_PROPOSALS:
                            raise ValueError(
                                "campus neighborhood estate proposal limit"
                            )
                        normal = [-u[1] * side, u[0] * side]
                        angle = math.atan2(normal[0], -normal[1])
                        center = point(
                            [at[i] + normal[i] * (depth / 2 + 2) for i in (0, 1)]
                        )
                        site_poly = rectangle(center, angle, width - 0.02, depth - 0.02)
                        if not all(
                            inside(p, polygon, 1) for p in site_poly
                        ) or collision(
                            site_poly,
                            shapes
                            + reserved
                            + [
                                ribbon(w["start"], w["end"], 1.5)
                                for w in self.extra_walks
                            ],
                        ):
                            continue

                        # Rear sources face an OUTER service promenade. No
                        # public path is allowed to slice through the complex.
                        along = [math.cos(angle), math.sin(angle)]
                        back = [at[i] + normal[i] * (depth + 3.5) for i in (0, 1)]
                        left = [at[i] - along[i] * (width / 2 + 1.5) for i in (0, 1)]
                        corner = [
                            back[i] - along[i] * (width / 2 + 1.5) for i in (0, 1)
                        ]
                        right = [back[i] + along[i] * (width / 2 + 1.5) for i in (0, 1)]
                        front_right = [
                            at[i] + along[i] * (width / 2 + 1.5) for i in (0, 1)
                        ]
                        perimeter = []
                        if request["rows"] > 1:
                            perimeter = [
                                dict(
                                    id=request["id"] + f":walk:{j}",
                                    start=point(p),
                                    end=point(q),
                                    width=1.2,
                                    access=False,
                                    structural=True,
                                )
                                for j, (p, q) in enumerate(
                                    (
                                        (left, corner),
                                        (corner, right),
                                        (right, front_right),
                                    )
                                )
                            ]
                            # frontage() receives fixed nature/roads/courts,
                            # followed by one exclusion ribbon per walking path.
                            obstacles = shapes[: -len(paths)]
                            if any(
                                not all(
                                    inside(p, polygon) for p in (w["start"], w["end"])
                                )
                                or collision(
                                    ribbon(w["start"], w["end"], 1.5),
                                    obstacles + reserved,
                                )
                                or (
                                    terrain
                                    and blocks_ground_connection(
                                        w["start"], w["end"], terrain
                                    )
                                )
                                for w in perimeter
                            ):
                                continue
                        proposal, assignment = [], {}
                        for index, identity in enumerate(request["memberEntityIds"]):
                            row, column = divmod(index, request["columns"])
                            x = (column + 0.5) * 8 - width / 2
                            z = 2 + row * 8 + 4
                            location = point(
                                [at[i] + along[i] * x + normal[i] * z for i in (0, 1)]
                            )
                            facing = [-v for v in normal]
                            yaw = angle
                            target = point([at[i] + along[i] * x for i in (0, 1)])
                            if row == request["rows"] - 1 and row:
                                facing, yaw = normal, angle + math.pi
                                target = point([back[i] + along[i] * x for i in (0, 1)])
                            elif row and column == 0:
                                facing, yaw = [-v for v in along], angle + math.pi / 2
                                target = point(
                                    [
                                        at[i]
                                        - along[i] * (width / 2 + 1.5)
                                        + normal[i] * z
                                        for i in (0, 1)
                                    ]
                                )
                            elif row:
                                facing, yaw = along, angle - math.pi / 2
                                target = point(
                                    [
                                        at[i]
                                        + along[i] * (width / 2 + 1.5)
                                        + normal[i] * z
                                        for i in (0, 1)
                                    ]
                                )
                            front = point([location[i] + facing[i] * 3 for i in (0, 1)])
                            slot = dict(
                                id=request["id"] + f":source:{index}",
                                center=location,
                                angle=yaw,
                                polygon=rectangle(location, angle, 7.98, 7.98),
                                entrance=front,
                                streetPoint=target,
                                laneId=lane["id"],
                                blockProfile="CAMPUS",
                            )
                            if (
                                terrain
                                and "elevation" in terrain
                                and (
                                    not suitable(slot, terrain)
                                    or blocks_ground_connection(front, target, terrain)
                                )
                            ):
                                break
                            proposal.append(slot)
                            assignment[identity] = slot["id"]
                        if len(proposal) != len(request["memberEntityIds"]):
                            continue
                        lots.extend(proposal)
                        reserved.append(site_poly)
                        self.extra_walks.extend(perimeter)
                        self.assignments.update(assignment)
                        use[lane["id"].split(":estate-spine:")[0]] += len(proposal)
                        self.sites.append(
                            dict(
                                request,
                                polygon=site_poly,
                                center=center,
                                angle=angle,
                                slotIds=[p["id"] for p in proposal],
                                decorative=False,
                                derived=True,
                            )
                        )
                        fitted = True
                        break
                    if fitted:
                        break
                if fitted:
                    break
            if not fitted and self.complete:
                return []
        assigned = set(self.assignments)
        remaining = sorted(
            k for r in self.requests for k in r["memberEntityIds"] if k not in assigned
        )
        if not remaining:
            return lots
        other = Fabric.frontage(
            paths,
            polygon,
            shapes
            + reserved
            + [ribbon(w["start"], w["end"], 1.5) for w in self.extra_walks],
            collision,
            terrain,
        )
        if len(other) < len(remaining):
            return []  # Never split/drop a source to make capacity pass.
        for identity, slot in zip(remaining, other):
            lots.append(slot)
            self.assignments[identity] = slot["id"]
        return lots


def estate_layout(
    zone, polygon, axis, seed, roads, terrain, pairs, stats, *, observed_pairs=None, connect_perimeter=False
):
    from .campus_neighborhood import neighborhood_layout

    for maximum, rotate, complete in (
        (8, True, True),
        (8, False, True),
        (4, True, True),
        (4, False, True),
        (8, True, False),
    ):
        form = EstateFabric(
            zone, polygon, axis, seed, roads, pairs, maximum, rotate, complete
        )
        form.connect_perimeter = connect_perimeter
        try:
            result = neighborhood_layout(
                zone, polygon, axis, seed, roads, terrain, pairs, stats, _form=form
            )
        except ValueError as error:
            if not str(error).startswith("campus neighborhood ") or "limit" not in str(
                error
            ):
                raise
            stats["estateResourceFallback"] = str(error)
            break
        if result is None or not form.sites:
            continue
        site = result[2]
        site.update(
            architecturalSites=form.sites,
            facilityAssignments=form.assignments,
            frontagePolicy="FACILITY_SITE_BEFORE_SOURCE_SUBDIVISION",
            facilitySiteVersion=VERSION,
            facilityRequestCount=len(form.requests),
        )
        site["anchorEntityIds"] = []
        site["anchorSlots"] = {}
        for activity in site["activityCenters"]:
            members = sorted(
                k for k, slot in form.assignments.items() if slot in activity["slotIds"]
            )
            activity["anchorEntityId"] = members[0]
            site["anchorEntityIds"].append(members[0])
            site["anchorSlots"][members[0]] = form.assignments[members[0]]
        annotate_program(zone, result)
        stats["facilitySiteCount"] = len(form.sites)
        return result
    stats["estateFallback"] = "DEDICATED_SITE_CAPACITY_OR_ACCESS"
    from .campus_programmed import programmed_layout

    retained = programmed_layout(
        zone,
        polygon,
        axis,
        seed,
        roads,
        terrain,
        observed_pairs if observed_pairs is not None else pairs,
        stats,
    )
    if retained:
        retained[2].update(
            architecturalSites=[],
            facilityAssignments={},
            facilitySiteVersion=VERSION,
            facilityRequestCount=0,
            estateFallback=stats["estateFallback"],
        )
    return retained
