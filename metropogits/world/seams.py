"""Remove only unused local duplicate streets; preserve morphology and trips."""

import heapq
import math
from collections import defaultdict

from .geometry import bounds, nearest

MAX_INDEX = 500_000
MAX_CHECKS = 200_000
MAX_ATTEMPTS = 256
MAX_STATES = 100_000


def stitch_unused_streets(streets, reserved, routing, parcels, *, preserve_frontages=False):
    """A deletion-only local pass. On exhausted work retain certified geometry."""
    streets = sorted(streets, key=lambda s: s["id"])
    index = defaultdict(set)
    work = entries = states = attempts = 0
    kept = {s["id"]: s for s in streets}
    protected = {s["physicalId"] for s in routing["segments"]}
    doors = {tuple(p["entrance"]) for p in parcels}
    adjacency = defaultdict(dict)

    def cells(s, pad=0):
        a, b, c, d = bounds([s["start"], s["end"]])
        x0, x1 = math.floor((a - pad) / 32), math.floor((c + pad) / 32)
        z0, z1 = math.floor((b - pad) / 32), math.floor((d + pad) / 32)
        if (x1 - x0 + 1) * (z1 - z0 + 1) > MAX_INDEX:
            raise ValueError("seam index budget")
        return [(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)]

    def nearby(s, pad=0):
        return sorted({i for k in cells(s, pad) for i in index[k]})

    def charge():
        nonlocal work
        work += 1
        if work > MAX_CHECKS:
            raise ValueError("seam candidate budget")

    try:
        for s in streets:
            keys = cells(s, 0.003)
            entries += len(keys)
            if entries > MAX_INDEX:
                raise ValueError("seam index budget")
            for key in keys:
                index[key].add(s["id"])
            a, b = tuple(s["start"]), tuple(s["end"])
            length = math.dist(a, b)
            adjacency[a][s["id"]] = (b, length)
            adjacency[b][s["id"]] = (a, length)
            if s["access"] or a in doors or b in doors:
                protected.add(s["id"])
        for r in reserved:
            for key in nearby(r, 0.003):
                charge()
                s = kept[key]
                if all(
                    math.dist(p, nearest(p, r["start"], r["end"])) < 0.002
                    for p in (s["start"], s["end"])
                ):
                    protected.add(key)
        if preserve_frontages:
            # A new shortcut can make a previously indispensable tangent road
            # removable, even on a zero-relationship repository. Its building
            # frontage remains physical infrastructure, not unused decoration.
            for p in parcels:
                at = p["streetPoint"]
                for key in nearby(dict(start=at, end=at), .003):
                    charge()
                    s = kept[key]
                    if not s["access"] and math.dist(at, nearest(at, s["start"], s["end"])) < .002:
                        protected.add(key)
        candidates = []
        for s in streets:
            key = s["id"]
            if key in protected:
                continue
            a, b = s["start"], s["end"]
            length = math.dist(a, b)
            if length < 2:
                continue
            direction = [(b[j] - a[j]) / length for j in (0, 1)]
            parallel = []
            for other in nearby(s, 8):
                charge()
                if other == key or kept[other]["access"]:
                    continue
                r = kept[other]
                p, q = r["start"], r["end"]
                span = math.dist(p, q)
                alignment = abs(
                    sum(direction[j] * (q[j] - p[j]) / span for j in (0, 1))
                )
                distance = math.dist(
                    [(a[j] + b[j]) / 2 for j in (0, 1)],
                    nearest([(a[j] + b[j]) / 2 for j in (0, 1)], p, q),
                )
                if alignment >= math.cos(math.radians(15)) and 0.002 < distance <= 8:
                    parallel.append(other)
            if parallel:
                candidates.append((key, parallel))
    except ValueError as error:
        return streets, dict(
            reason="local seam cleanup retained certified streets", budget=str(error)
        )

    removed = []
    exhausted = False
    for key, parallel in candidates:
        if attempts >= MAX_ATTEMPTS or states >= MAX_STATES:
            exhausted = True
            break
        attempts += 1
        s = kept[key]
        start, end = tuple(s["start"]), tuple(s["end"])
        limit = min(math.dist(start, end) * 1.5 + 8, math.dist(start, end) + 24)
        queue = [(0.0, start, False)]
        costs = {(start, False): 0.0}
        found = False
        while queue:
            cost, node, shared = heapq.heappop(queue)
            if cost != costs.get((node, shared)):
                continue
            states += 1
            if states > MAX_STATES:
                exhausted = True
                break
            if node == end and shared:
                found = True
                break
            for identity, (other, length) in sorted(adjacency[node].items()):
                if identity == key:
                    continue
                flag = shared or identity in parallel
                value = cost + length
                if value <= limit and value < costs.get((other, flag), math.inf):
                    costs[other, flag] = value
                    heapq.heappush(queue, (value, other, flag))
        if found:
            del adjacency[start][key]
            del adjacency[end][key]
            del kept[key]
            removed.append(key)
    return [s for s in streets if s["id"] in kept], dict(
        reason="local unused parallel seam cleanup; source trips and reserved patterns preserved",
        removedStreetIds=removed,
        attempts=attempts,
        searchStates=states,
        candidateChecks=work,
        budgetExhausted=exhausted,
    )
