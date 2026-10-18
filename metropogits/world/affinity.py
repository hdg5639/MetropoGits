"""Bounded graph-aware address swaps; no new graph facts or physical sites."""

import math
from collections import defaultdict

from .seed import derive

MAX_DEGREE = 24
MAX_PASSES = 3
MAX_CANDIDATES = 32
MAX_EVALUATIONS = 400_000
MAX_SCORE_TERMS = 10_000_000
ROLE_WEIGHT = 0.06


def dependency_pairs(graph, owners):
    entities = {e["id"]: e for e in graph["entities"]}
    files = {e["path"]: e["id"] for e in graph["entities"] if e["kind"] == "FILE"}

    def endpoint(key):
        e = entities[key]
        return files.get(e.get("path")) if e["kind"] in ("FILE", "SYMBOL") else None

    weights = defaultdict(float)
    for e in graph["edges"]:
        if e["type"] in ("CONTAINS", "DECLARES") or e["confidence"] not in (
            "DIRECT",
            "RESOLVED",
        ):
            continue
        a, b = endpoint(e["from"]), endpoint(e["to"])
        if a in owners and b in owners and a != b and owners[a] == owners[b]:
            pair = tuple(sorted((a, b)))
            weights[pair] = min(
                4.0, weights[pair] + (1 if e["type"] == "IMPORTS" else 2)
            )
    if len(weights) > 100_000:
        raise ValueError("soft zoning affinity pair limit")
    return dict(sorted(weights.items()))


def optimize_addresses(parcels, pairs, targets, seed, pinned=()):
    sites = {p["slotId"]: p for p in parcels}
    assignment = {p["entityId"]: p["slotId"] for p in parcels}
    if len(sites) != len(parcels):
        raise ValueError("soft zoning address collision")
    occupant = {slot: identity for identity, slot in assignment.items()}
    original = dict(assignment)
    pinned = set(pinned)
    links = defaultdict(dict)
    for (a, b), weight in sorted(pairs.items(), key=lambda item: (-item[1], item[0])):
        if len(links[a]) < MAX_DEGREE and len(links[b]) < MAX_DEGREE:
            links[a][b] = links[b][a] = weight
    cells = defaultdict(list)
    for key, p in sites.items():
        cells[tuple(math.floor(v / 32) for v in p["center"])].append(key)
    all_sites = sorted(sites)
    coefficients = {
        k: ROLE_WEIGHT * sum(links[k].values()) if k in targets else 0
        for k in assignment
    }

    def position(identity, mapping):
        return sites[mapping[identity]]["center"]

    def energy(mapping):
        value = sum(
            w * math.dist(position(a, mapping), position(b, mapping)) ** 2
            for a in links
            for b, w in links[a].items()
            if a < b
        )
        return value + sum(
            coefficients[k] * math.dist(position(k, mapping), targets[k]) ** 2
            for k in targets
        )

    def lengths(mapping):
        total = sum(pairs.values())
        return (
            sum(
                w * math.dist(position(a, mapping), position(b, mapping))
                for (a, b), w in pairs.items()
            )
            / total
            if total
            else 0.0
        )

    before_energy, before_length = energy(assignment), lengths(assignment)
    evaluations = terms = swaps = 0
    limited = False
    iteration = -1
    for iteration in range(MAX_PASSES):
        for identity in sorted(
            assignment, key=lambda k: derive(seed, "visit", str(iteration), k)
        ):
            if identity in pinned or not links[identity]:
                continue
            degree = sum(links[identity].values())
            target = [
                sum(position(k, assignment)[j] * w for k, w in links[identity].items())
                / degree
                for j in (0, 1)
            ]
            if identity in targets:
                target = [
                    (target[j] + ROLE_WEIGHT * targets[identity][j]) / (1 + ROLE_WEIGHT)
                    for j in (0, 1)
                ]
            cell = [math.floor(v / 32) for v in target]
            nearby = []
            for radius in range(4):
                nearby = [
                    key
                    for x in range(cell[0] - radius, cell[0] + radius + 1)
                    for z in range(cell[1] - radius, cell[1] + radius + 1)
                    for key in cells.get((x, z), ())
                ]
                if len(nearby) >= 24:
                    break
            nearby.sort(key=lambda key: (math.dist(sites[key]["center"], target), key))
            candidates = nearby[:24] + [
                all_sites[
                    int(derive(seed, identity, str(iteration), str(i)), 16)
                    % len(all_sites)
                ]
                for i in range(8)
            ]
            own_slot = assignment[identity]
            best, best_change = None, 0.0
            for slot in dict.fromkeys(candidates[:MAX_CANDIDATES]):
                other = occupant[slot]
                if other == identity or other in pinned:
                    continue
                if any(
                    sites[own_slot][k] != sites[slot][k] for k in ("width", "depth")
                ):
                    continue
                evaluations += 1
                affected = {
                    (min(a, b), max(a, b)): w
                    for a in (identity, other)
                    for b, w in links[a].items()
                }
                terms += len(affected)
                if evaluations > MAX_EVALUATIONS or terms > MAX_SCORE_TERMS:
                    limited = True
                    break
                moved = {
                    identity: sites[slot]["center"],
                    other: sites[own_slot]["center"],
                }
                change = sum(
                    w
                    * (
                        math.dist(
                            moved.get(a, position(a, assignment)),
                            moved.get(b, position(b, assignment)),
                        )
                        ** 2
                        - math.dist(position(a, assignment), position(b, assignment))
                        ** 2
                    )
                    for (a, b), w in affected.items()
                )
                change += sum(
                    coefficients[k]
                    * (
                        math.dist(moved[k], targets[k]) ** 2
                        - math.dist(position(k, assignment), targets[k]) ** 2
                    )
                    for k in moved
                    if k in targets
                )
                if change < best_change - 1e-7:
                    best, best_change = other, change
            if limited:
                break
            if best is not None:
                other_slot = assignment[best]
                assignment[identity], assignment[best] = other_slot, own_slot
                occupant[own_slot], occupant[other_slot] = best, identity
                swaps += 1
        if limited:
            break
    return assignment, dict(
        passes=iteration + 1,
        swaps=swaps,
        candidateEvaluations=evaluations,
        scoreTerms=terms,
        workLimitReached=limited,
        sourcePairCount=len(pairs),
        optimizedPairCount=sum(map(len, links.values())) // 2,
        roleWeight=ROLE_WEIGHT,
        energyBefore=before_energy,
        energyAfter=energy(assignment),
        meanDependencyDistanceBefore=before_length,
        meanDependencyDistanceAfter=lengths(assignment),
        movedBuildings=sum(assignment[k] != original[k] for k in assignment),
        pinnedBuildings=len(pinned & assignment.keys()),
    )
