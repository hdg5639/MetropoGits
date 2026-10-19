"""Reserve a few useful cross-streets before candidate lots become buildings."""

import heapq
import math
from collections import defaultdict

from metropogits.street_diagonals import overlap
from .geometry import bounds, inside, nearest, point, ribbon
from .infrastructure import atomic_streets
from .seed import derive, draw

VERSION = "permeability/0.1"
GENERATOR_VERSION = "flat-adaptive-neighborhoods/0.6"
WIDTH = 1.8
MAX_LENGTH = 88
MIN_SPACING = 72
MAX_LINKS = 4
MAX_ROADS = 20_000
MAX_SLOTS = 100_000
MAX_INDEX = 200_000
MAX_CANDIDATES = 6000
MAX_EVALUATIONS = 240
MAX_CHECKS = 500_000
MAX_STATES = 300_000


def reserve_links(plans, main, boundary, polygon, pattern, required, terrain=None):
    """Pure planning transform. Reclaim vacant supply only, never source objects."""
    note = dict(
        version=VERSION,
        corridors=[],
        reclaimedSlotIds=[],
        candidates=0,
        geometryChecks=0,
        searchStates=0,
        shortestPathQueries=0,
        budgetExhausted=None,
    )
    accepted, removed = [], set()
    raw = main + boundary + [r for p in plans.values() for r in p[1]]
    slots = {(z, s["id"]): s for z, p in plans.items() for s in p[0]}
    remaining = {z: len(p[0]) for z, p in plans.items()}
    reclaim_budget = min(8, max(2, len(slots) // 60))
    cap = min(
        MAX_LINKS,
        1 + int(sum(required.values()) >= 100) + int(sum(required.values()) >= 250),
    )
    index, road_index = defaultdict(set), defaultdict(set)
    entries = 0

    def cells(poly):
        x0, z0, x1, z1 = bounds(poly)
        lo, hi = (
            (math.floor(x0 / 32), math.floor(z0 / 32)),
            (math.floor(x1 / 32), math.floor(z1 / 32)),
        )
        if (hi[0] - lo[0] + 1) * (hi[1] - lo[1] + 1) > MAX_INDEX:
            raise ValueError("permeability spatial extent budget")
        return [
            (x, z) for x in range(lo[0], hi[0] + 1) for z in range(lo[1], hi[1] + 1)
        ]

    def nearby(at):
        box = [
            [at[0] - MAX_LENGTH, at[1] - MAX_LENGTH],
            [at[0] + MAX_LENGTH, at[1] + MAX_LENGTH],
        ]
        return sorted({key for c in cells(box) for key in road_index[c]})

    def graph(roads):
        edges = atomic_streets([dict(r, access=False) for r in roads])
        adjacency = defaultdict(list)
        for r in edges:
            a, b = tuple(r["start"]), tuple(r["end"])
            adjacency[a].append((b, math.dist(a, b)))
            adjacency[b].append((a, math.dist(a, b)))
        return edges, adjacency

    def search(adjacency, source, target, a, b, limit):
        # Include new interior split nodes after accepted links, not only the
        # old atomic endpoints. Otherwise later cuts would ignore shared access.
        def attachments(road, at):
            points = [road["start"], road["end"]]
            points += [
                p
                for s in accepted
                for p in (s["start"], s["end"])
                if math.dist(p, nearest(p, road["start"], road["end"])) < 0.0003
            ]
            return {tuple(p): math.dist(p, at) for p in points}

        costs = attachments(source, a)
        goals = attachments(target, b)
        heap = [(v, k) for k, v in costs.items()]
        heapq.heapify(heap)
        best = math.inf
        while heap:
            cost, at = heapq.heappop(heap)
            if cost != costs[at] or cost > min(best, limit):
                continue
            note["searchStates"] += 1
            if note["searchStates"] > MAX_STATES:
                raise ValueError("permeability shortest-path budget")
            if at in goals:
                best = min(best, cost + goals[at])
            for other, length in adjacency[at]:
                value = cost + length
                if (
                    value <= min(best, limit)
                    and value < costs.get(other, math.inf) - 1e-9
                ):
                    costs[other] = value
                    heapq.heappush(heap, (value, other))
        return best

    try:
        if len(raw) > MAX_ROADS or len(slots) > MAX_SLOTS:
            raise ValueError("permeability input budget")
        if sum(required.values()) < 24:
            return plans, main, dict(pattern, permeability=note)
        # The outer physical collector exists in the final generator too. Include
        # its terrain-safe pieces in the detour metric, not an invented shortcut.
        perimeter = [
            dict(start=a, end=b, width=3.5, access=False)
            for a, b in zip(polygon, polygon[1:] + polygon[:1])
        ]
        if terrain:
            from .terrain import adapt_roads

            perimeter = adapt_roads(perimeter, terrain)
        roads, adjacency = graph(raw + perimeter)
        by_id = {r["id"]: r for r in roads}
        for key, s in slots.items():
            keys = cells(s["polygon"])
            entries += len(keys)
            if entries > MAX_INDEX:
                raise ValueError("permeability index budget")
            for c in keys:
                index[c].add(key)
        for r in roads:
            keys = cells([r["start"], r["end"]])
            entries += len(keys)
            if entries > MAX_INDEX:
                raise ValueError("permeability index budget")
            for c in keys:
                road_index[c].add(r["id"])
        # Distance along streets to an existing intersection ranks long isolated
        # rows, including curved chains composed of short atomic pieces.
        distance = {p: 0.0 for p, edges in adjacency.items() if len(edges) != 2}
        heap = [(0.0, p) for p in distance]
        heapq.heapify(heap)
        while heap:
            cost, at = heapq.heappop(heap)
            if cost != distance[at]:
                continue
            note["searchStates"] += 1
            if note["searchStates"] > MAX_STATES:
                raise ValueError("permeability junction-distance budget")
            for other, length in adjacency[at]:
                value = cost + length
                if value < distance.get(other, math.inf):
                    distance[other] = value
                    heapq.heappush(heap, (value, other))
        candidates = {}
        for r in roads:
            length = math.dist(r["start"], r["end"])
            fractions = [0.35 + 0.3 * draw(derive(pattern["seed"], r["id"], VERSION))]
            fractions += [
                t
                for t, k in ((0, "start"), (1, "end"))
                if len(adjacency[tuple(r[k])]) == 1
            ]
            for fraction in fractions:
                a = point(
                    [
                        r["start"][j] + fraction * (r["end"][j] - r["start"][j])
                        for j in (0, 1)
                    ]
                )
                choices = []
                for key in nearby(a):
                    note["geometryChecks"] += 1
                    if note["geometryChecks"] > MAX_CHECKS:
                        raise ValueError("permeability neighbor budget")
                    other = by_id[key]
                    if key == r["id"]:
                        continue
                    b = point(nearest(a, other["start"], other["end"]))
                    gap = math.dist(a, b)
                    if not 7 <= gap <= MAX_LENGTH:
                        continue
                    along = abs(
                        sum(
                            (b[j] - a[j]) * (r["end"][j] - r["start"][j])
                            for j in (0, 1)
                        )
                    ) / (gap * length)
                    if fraction not in (0, 1) and along > 0.75:
                        continue
                    choices.append((gap, key, b))
                for gap, key, b in sorted(choices)[:6]:
                    other = by_id[key]
                    if any(
                        len(adjacency[tuple(p)]) >= 3 and math.dist(at, p) < 6
                        for at, s in ((a, r), (b, other))
                        for p in (s["start"], s["end"])
                    ):
                        continue
                    corridor = ribbon(a, b, WIDTH + 0.6)
                    if not all(inside(p, polygon, 0.2) for p in corridor):
                        continue
                    if terrain and any(
                        overlap(corridor, f["noBuildPolygon"])
                        for f in terrain["features"]
                    ):
                        continue
                    if terrain and "elevation" in terrain:
                        from .elevation import surface
                        from .rivers import blocks_ground_connection

                        if blocks_ground_connection(a,b,terrain):
                            continue
                        profile = surface(terrain).profile(a, b)
                        if any(
                            abs(y[2] - x[2]) / math.dist(x[:2], y[:2]) > 0.1598
                            for x, y in zip(profile, profile[1:])
                        ):
                            continue
                    identities = sorted({k for c in cells(corridor) for k in index[c]})
                    note["geometryChecks"] += len(identities)
                    if note["geometryChecks"] > MAX_CHECKS:
                        raise ValueError("permeability lot budget")
                    blocked = [
                        k for k in identities if overlap(corridor, slots[k]["polygon"])
                    ]
                    if len(blocked) > 3:
                        continue
                    identity = derive(pattern["id"], str(sorted((a, b))), VERSION)
                    priority = min(
                        distance.get(tuple(r["start"]), 200) + math.dist(a, r["start"]),
                        distance.get(tuple(r["end"]), 200) + math.dist(a, r["end"]),
                    )
                    priority += min(
                        distance.get(tuple(other["start"]), 200)
                        + math.dist(b, other["start"]),
                        distance.get(tuple(other["end"]), 200)
                        + math.dist(b, other["end"]),
                    )
                    candidates[identity] = (
                        len(blocked),
                        -priority,
                        gap,
                        identity,
                        a,
                        b,
                        r,
                        other,
                        blocked,
                    )
                    if len(candidates) > MAX_CANDIDATES:
                        raise ValueError("permeability candidate budget")
        for _, _, length, identity, a, b, source, target, blocked in sorted(
            candidates.values()
        ):
            if len(accepted) >= cap or note["shortestPathQueries"] >= MAX_EVALUATIONS:
                break
            note["candidates"] += 1
            center = point([(a[j] + b[j]) / 2 for j in (0, 1)])
            if any(math.dist(center, r["center"]) < MIN_SPACING for r in accepted):
                continue
            victims = set(blocked) - removed
            if len(removed | victims) > reclaim_budget:
                continue
            losses = defaultdict(int)
            for zone, key in victims:
                losses[zone] += 1
            if any(remaining[z] - n < required[z] + 1 for z, n in losses.items()):
                continue
            note["shortestPathQueries"] += 1
            limit = min(600, max(180, length * 5))
            before = search(adjacency, source, target, a, b, limit)
            if before <= max(length * 1.9, length + 40):
                continue
            record = dict(
                id="world:permeability:" + identity,
                start=a,
                end=b,
                width=WIDTH,
                center=center,
                access=False,
                structural=True,
                patternId=pattern["id"],
                reclaimedSlotIds=sorted(k for _, k in victims),
                previousDistance=round(min(before, limit), 4),
                distanceIsLowerBound=not math.isfinite(before),
            )
            accepted.append(record)
            removed |= victims
            for z, n in losses.items():
                remaining[z] -= n
            _, adjacency = graph(raw + perimeter + accepted)
        note["corridors"] = accepted
        note["reclaimedSlotIds"] = sorted(k for _, k in removed)
    except ValueError as error:
        note.update(
            budgetExhausted=str(error),
            corridors=accepted,
            reclaimedSlotIds=sorted(k for _, k in removed),
        )
    result = {
        z: ([s for s in p[0] if (z, s["id"]) not in removed], *p[1:])
        for z, p in plans.items()
    }
    record = dict(pattern, permeability=note)
    if accepted:
        record.update(
            protectedStreetIds=sorted(r["id"] for r in main + accepted),
            roadCount=len(main) + len(accepted),
        )
    return result, main + accepted, record
