"""Whole-neighborhood pedestrian precincts, reserved before source assignment."""

import math
from collections import defaultdict

from metropogits.street_diagonals import overlap
from .geometry import bounds, inside, nearest, point, rectangle, ribbon
from .radial import _clipped
from .seed import derive

VERSION = "campus-plan/0.3"
MAX_WORK = 300_000


def neighborhood_layout(zone, polygon, axis, seed, roads, terrain, pairs, stats, *, _form=None):
    """Replace local circulation in full, or return an explicit safe fallback."""
    n = len(zone["memberEntityIds"])
    if not 12 <= n <= 256:
        stats["rejected"] = "NEIGHBORHOOD_SIZE"
        return None
    from .elevation import suitable, surface
    from .rivers import blocks_ground_connection

    natural = [f["noBuildPolygon"] for f in (terrain or {}).get("features", [])]
    road_shapes = [ribbon(r["start"], r["end"], r["width"] + 0.3) for r in roads]
    work = 0

    def collision(poly, shapes):
        nonlocal work
        box = bounds(poly)
        for other in shapes:
            b = bounds(other)
            if box[2] < b[0] or b[2] < box[0] or box[3] < b[1] or b[3] < box[1]:
                continue
            work += 1
            if work > MAX_WORK:
                raise ValueError("campus neighborhood clearance work limit")
            if overlap(poly, other):
                return True
        return False

    field = surface(terrain) if terrain and "elevation" in terrain else None

    def path_clear(a, b, courts):
        if math.dist(a, b) < 0.01 or not all(
            inside(p, polygon, -0.001) for p in (a, b)
        ):
            return False
        if collision(ribbon(a, b, 1.4), natural + courts):
            return False
        if field:
            if blocks_ground_connection(a, b, terrain):
                return False
            profile = field.profile(a, b)
            if any(
                abs(v[2] - u[2]) / math.dist(u[:2], v[:2]) > 0.1598
                for u, v in zip(profile, profile[1:])
            ):
                return False
        return True

    c, s = math.cos(axis), math.sin(axis)

    def local(p):
        return [c * p[0] + s * p[1], -s * p[0] + c * p[1]]

    def world(p):
        return point([c * p[0] - s * p[1], s * p[0] + c * p[1]])

    x0, z0, x1, z1 = bounds([local(p) for p in polygon])
    grid = [
        world([x0 + (i + 0.5) * (x1 - x0) / 12, z0 + (j + 0.5) * (z1 - z0) / 12])
        for i in range(12)
        for j in range(12)
    ]
    identity = "world:campus-court:" + derive(seed, zone["id"], _form.VERSION if _form else VERSION)
    # A feasible lawn alone is not a feasible campus center. Prefer sites with
    # room for actual surrounding building groups, not a park wedged into a
    # road/terrain gap whose frontage wings will all be clipped away.
    room = {}
    for center in grid:
        lawn = rectangle(center, axis, 22, 16)
        if not all(inside(p, polygon, 7) for p in lawn) or collision(
            lawn, natural + road_shapes
        ):
            room[tuple(center)] = -1000
            continue
        cx, cz = local(center)
        room[tuple(center)] = sum(
            all(inside(p, polygon, 1) for p in parcel)
            and not collision(parcel, natural + road_shapes)
            for u in (-36, -20, 0, 20, 36)
            for v in (-32, -16, 0, 16, 32)
            if (abs(u) > 12 or abs(v) > 10)
            for parcel in [rectangle(world([cx + u, cz + v]), axis, 7.98, 7.98)]
        )
    # Only real source relationships choose activity anchors, not role sorting.
    ids = set(zone["memberEntityIds"])
    links = defaultdict(dict)
    for (a, b), weight in pairs.items():
        if a in ids and b in ids:
            links[a][b] = links[b][a] = weight
    degree = {k: sum(links[k].values()) for k in ids}
    ranked = sorted(ids, key=lambda k: (-degree[k], k))
    trials = [(3 if n >= 64 else 2, 0), (2, 1), (3 if n >= 64 else 2, 2)]
    stats.update(required=n, attempts=0, maxCapacity=0)
    for count, trial in trials:
        stats["attempts"] += 1
        courts, centers, walks = [], [], []
        targets = (
            [[0.25, 0.32], [0.72, 0.32], [0.5, 0.72]]
            if count == 3
            else [[0.28, 0.5], [0.72, 0.5]]
        )
        if trial == 1:
            targets = [[v, u] for u, v in targets]
        if trial == 2:
            targets = [[1 - u, 1 - v] for u, v in targets]

        def segment(a, b, key):
            return dict(
                id=identity + ":" + key,
                start=point(a),
                end=point(b),
                width=1.2,
                access=False,
                structural=True,
            )

        for index, (u, v) in enumerate(targets):
            target = world([x0 + u * (x1 - x0), z0 + v * (z1 - z0)])
            for center in sorted(
                grid,
                key=lambda p: (
                    (-room[tuple(p)] + math.dist(p, target) * 0.06)
                    if trial == 2
                    else math.dist(p, target),
                    math.dist(p, target),
                    derive(seed, str(p)),
                ),
            ):
                lawn = (_form.lawn(center, axis, index) if _form
                        else rectangle(center, axis, 22, 16))
                if not all(inside(p, polygon, 7) for p in lawn) or collision(
                    lawn,
                    natural
                    + road_shapes
                    + [rectangle(p, axis, 54, 46) for p in centers],
                ):
                    continue
                corners = (_form.loop(center, axis, index) if _form
                           else rectangle(center, axis, 25, 19))
                ring = [
                    segment(a, b, f"core:{index}:loop:{i}")
                    for i, (a, b) in enumerate(zip(corners, corners[1:] + corners[:1]))
                ]
                if not all(path_clear(r["start"], r["end"], [lawn]) for r in ring):
                    continue
                courts.append(
                    dict(id=identity + f":court:{index}", center=center, polygon=lawn)
                )
                centers.append(center)
                walks.extend(ring)
                break
        if len(centers) != count:
            stats["rejected"] = "SHARED_SPACE_FIT"
            continue
        lawns = [court["polygon"] for court in courts]

        def connect(a_points, b_points, key):
            options = sorted(
                ((a, b) for a in a_points for b in b_points),
                key=lambda p: (math.dist(*p), p),
            )[:32]
            for a, b in options:
                al, bl = local(a), local(b)
                for path in (
                    [a, b],
                    [a, world([al[0], bl[1]]), b],
                    [a, world([bl[0], al[1]]), b],
                ):
                    pieces = [
                        segment(p, q, key + f":{i}")
                        for i, (p, q) in enumerate(zip(path, path[1:]))
                        if math.dist(p, q) > 0.01
                    ]
                    if pieces and all(
                        path_clear(r["start"], r["end"], lawns) for r in pieces
                    ):
                        return pieces
            return None

        # Short real links make one compound, rather than independently gated gardens.
        connected = {0}
        while len(connected) < count:
            options = sorted(
                ((i, j) for i in connected for j in range(count) if j not in connected),
                key=lambda ij: (math.dist(centers[ij[0]], centers[ij[1]]), ij),
            )
            for i, j in options:
                link = connect(
                    _form.loop(centers[i], axis, i) if _form else rectangle(centers[i], axis, 25, 19),
                    _form.loop(centers[j], axis, j) if _form else rectangle(centers[j], axis, 25, 19),
                    f"promenade:{i}:{j}",
                )
                if link:
                    walks.extend(link)
                    connected.add(j)
                    break
            else:
                break
        if len(connected) < count:
            stats["rejected"] = "DISCONNECTED_ACTIVITY_CENTERS"
            continue
        border_roads = [
            dict(r, start=p[0], end=p[1])
            for r in roads
            if (p := _clipped(r["start"], r["end"], polygon)) and math.dist(*p) > 0.01
        ]
        corners = [p for i, center in enumerate(centers)
                   for p in (_form.loop(center, axis, i) if _form else rectangle(center, axis, 25, 19))]
        targets = sorted(
            {
                tuple(point(nearest(p, r["start"], r["end"])))
                for p in corners
                for r in border_roads
            },
            key=lambda p: (min(math.dist(p, q) for q in corners), p),
        )[:24]
        gate = connect(corners, [list(p) for p in targets], "exterior-gate")
        if not gate:
            stats["rejected"] = "NO_ACTUAL_EXTERIOR_ACCESS"
            continue
        walks.extend(gate)

        # Short frontage wings feed the promenade; no inherited vehicle rows survive.
        # A one-file edit must not bend every occupied curved frontage again.
        # Organic capacity is fitted against a fixed local reserve, not a
        # population-dependent curve whose tangent changes under small growth.
        arm_length = 64 if _form else max(28, min(72, math.sqrt(n / count) * 10))
        if _form:
            walks.extend(_form.branches(centers, axis, arm_length, segment, path_clear, lawns))
        for index, center in enumerate([] if _form else centers):
            cx, cz = local(center)
            for side, (dx, dz) in enumerate(((1, 0), (0, 1), (-1, 0), (0, -1))):
                start = world([cx + dx * 12.5, cz + dz * 9.5])
                for length in (arm_length, arm_length * 0.7, arm_length * 0.45):
                    end = world([cx + dx * (12.5 + length), cz + dz * (9.5 + length)])
                    if path_clear(start, end, lawns):
                        walks.append(segment(start, end, f"core:{index}:wing:{side}"))
                        break
            # Side wings share the north/south approach, rather than every
            # building row getting its own road out to the district boundary.
            for side in (-1, 1):
                at = world([cx, cz + side * 29.5])
                parent = world([cx, cz + side * 9.5])
                if not path_clear(parent, at, lawns):
                    continue
                for direction in (-1, 1):
                    for length in (arm_length * 0.8, arm_length * 0.5, 20):
                        end = world([cx + direction * length, cz + side * 29.5])
                        if path_clear(at, end, lawns):
                            walks.extend(
                                [
                                    segment(
                                        parent, at, f"core:{index}:approach:{side}"
                                    ),
                                    segment(
                                        at,
                                        end,
                                        f"core:{index}:lateral:{side}:{direction}",
                                    ),
                                ]
                            )
                            break
        walks = list({r["id"]: r for r in walks}.values())

        def frontage(paths):
            shapes = (
                natural
                + road_shapes
                + lawns
                + [ribbon(r["start"], r["end"], r["width"] + 0.25) for r in paths]
            )
            if _form:
                return _form.frontage(paths, polygon, shapes, collision, terrain)
            lots = []
            for r in paths:
                if ":exterior-gate" in r["id"]:
                    continue
                a, b = r["start"], r["end"]
                length = math.dist(a, b)
                dx, dz = (b[0] - a[0]) / length, (b[1] - a[1]) / length
                if ":core:" in r["id"]:
                    # Keep local axes exact when a growing wing's quantized end moves.
                    direction = axis + round(
                        (math.atan2(dz, dx) - axis) / (math.pi / 2)
                    ) * (math.pi / 2)
                    dx, dz = math.cos(direction), math.sin(direction)
                for i in range(max(0, math.floor((length - 8) / 8.6) + 1)):
                    t = 4 + i * 8.6
                    at = point([a[0] + dx * t, a[1] + dz * t])
                    for side in (-1, 1):
                        normal = [-dz * side, dx * side]
                        center = point([at[j] + normal[j] * 6 for j in (0, 1)])
                        angle = math.atan2(normal[0], -normal[1])
                        poly = rectangle(center, angle, 7.98, 7.98)
                        p = dict(
                            id=r["id"] + f":lot:{i}:{side}",
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
                            or collision(poly, shapes + [v["polygon"] for v in lots])
                            or (field and not suitable(p, terrain))
                            or (
                                field
                                and blocks_ground_connection(p["entrance"], at, terrain)
                            )
                        ):
                            continue
                        lots.append(p)
            return lots

        plots = frontage(walks)
        # Grow only useful secondary wings. Each proposal must increase actual
        # safe frontage capacity; a crossing that destroys more plots is rejected.
        for index, center in enumerate([] if _form else centers):
            if len(plots) >= n:
                break
            cx, cz = local(center)
            for side in (-1, 1):
                if len(plots) >= n:
                    break
                at = world([cx + side * 32.5, cz])
                parent = world([cx + side * 12.5, cz])
                proposed = [
                    segment(parent, at, f"core:{index}:secondary-approach:{side}")
                ]
                if not path_clear(parent, at, lawns):
                    continue
                for direction in (-1, 1):
                    for length in (arm_length * 0.8, arm_length * 0.5, 20):
                        end = world([cx + side * 32.5, cz + direction * length])
                        if path_clear(at, end, lawns):
                            proposed.append(
                                segment(
                                    at,
                                    end,
                                    f"core:{index}:secondary-wing:{side}:{direction}",
                                )
                            )
                            break
                if len(proposed) < 2:
                    continue
                candidate = frontage(walks + proposed)
                if len(candidate) > len(plots):
                    plots = candidate
                    walks += proposed
        stats["maxCapacity"] = max(stats["maxCapacity"], len(plots))
        # Campus planning also needs perimeter/through-road vehicle frontage.
        # Reuse the actual protected corridor, never the old local row plan.
        # Internal pedestrian groups must still supply at least half the files.
        edge_slots = []
        if n * 0.5 <= len(plots) < n:
            for r in sorted(border_roads, key=lambda r: r["id"]):
                a, b = r["start"], r["end"]
                length = math.dist(a, b)
                if length < 8:
                    continue
                dx, dz = (b[0] - a[0]) / length, (b[1] - a[1]) / length
                for i in range(max(1, math.floor(length / 8.6))):
                    t = length / 2 if length < 16 else 4 + i * 8.6
                    at = point([a[0] + dx * t, a[1] + dz * t])
                    for side in (-1, 1):
                        normal = [-dz * side, dx * side]
                        center = point(
                            [
                                at[j] + normal[j] * (r["width"] / 2 + 4.75)
                                for j in (0, 1)
                            ]
                        )
                        angle = math.atan2(normal[0], -normal[1])
                        poly = rectangle(center, angle, 7.98, 7.98)
                        p = dict(
                            id=identity + ":edge:" + r["id"] + f":{i}:{side}",
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
                            or collision(
                                poly,
                                natural
                                + road_shapes
                                + lawns
                                + [
                                    ribbon(w["start"], w["end"], w["width"] + 0.25)
                                    for w in walks
                                ]
                                + [v["polygon"] for v in plots],
                            )
                            or (field and not suitable(p, terrain))
                            or (
                                field
                                and blocks_ground_connection(p["entrance"], at, terrain)
                            )
                        ):
                            continue
                        plots.append(p)
                        edge_slots.append(p["id"])
                        if len(plots) >= n + 1:
                            break
                    if len(plots) >= n + 1:
                        break
                if len(plots) >= n + 1:
                    break
        stats["maxCapacity"] = max(stats["maxCapacity"], len(plots))
        if len(plots) < n:
            stats["rejected"] = "FULL_NEIGHBORHOOD_CAPACITY"
            continue
        groups = []
        anchor_slots = {}
        anchors = []
        for index, center in enumerate(centers):
            available = [
                p
                for p in plots
                if min(
                    range(count), key=lambda j: (math.dist(p["center"], centers[j]), j)
                )
                == index
            ]
            if len(available) < 6:
                break
            anchor = min(
                (k for k in ranked if k not in anchors),
                key=lambda k: (
                    -degree[k] / (1 + sum(links[k].get(a, 0) for a in anchors)),
                    k,
                ),
            )
            anchors.append(anchor)
            if _form and hasattr(_form, 'anchor'):
                anchors.pop()
                anchor = _form.anchor(ids, degree, links, anchors)
                anchors.append(anchor)
            slot = min(
                available, key=lambda p: (math.dist(p["center"], center), p["id"])
            )
            anchor_slots[anchor] = slot["id"]
            groups.append(
                dict(
                    id=identity + f":group:{index}",
                    center=center,
                    courtId=courts[index]["id"],
                    anchorEntityId=anchor,
                    slotIds=sorted(p["id"] for p in available),
                )
            )
        if len(groups) != count:
            stats["rejected"] = "UNSUPPORTED_ACTIVITY_GROUP"
            continue
        stats.update(
            rejected=None, capacity=len(plots), removedLocalPlan=True, work=work
        )
        return (
            plots,
            walks,
            dict(
                zoneId=zone["id"],
                parentId=zone["parentId"],
                variant="PEDESTRIAN_PRECINCT",
                memberEntityIds=sorted(ids),
                retainedMemberEntityIds=[],
                anchorEntityIds=anchors,
                anchorSlots=anchor_slots,
                activityCenters=groups,
                courts=courts,
                walkways=walks,
                axis=axis,
                capacity=len(plots),
                envelopes=[polygon],
                scope="NEIGHBORHOOD",
                vehicleFrontageSlotIds=edge_slots,
            ),
        )
    stats["work"] = work
    return None
