"""Bounded, evidence-only placement preferences (ADR-014), not new graph facts."""
from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


RELATIONS = {"IMPORTS": 1, "REFERENCES": 3, "CALLS": 3, "HTTP_CALL": 3,
             "PUBLISHES": 3, "SUBSCRIBES": 3, "EXTENDS": 2, "IMPLEMENTS": 2}
BOUNDARY_ROLES = {"ENTRYPOINT": 3, "API_ENDPOINT": 3, "UI_PAGE": 3,
                  "HTTP_CLIENT": 2, "MESSAGE_PRODUCER": 2, "MESSAGE_ADAPTER": 2}
INNER_ROLES = {"PERSISTENCE_ADAPTER", "DOCUMENT_PERSISTENCE_ADAPTER", "CACHE_ADAPTER"}


@dataclass
class Affinity:
    exposure: dict[str, float] = field(default_factory=dict)
    neighbors: dict[str, dict[str, float]] = field(default_factory=dict)


def arrange_equal_shapes(offsets, shapes, dimensions, movable, affinity):
    """Swap identical sibling footprints only: occupied land never changes."""
    result = dict(offsets)
    groups = defaultdict(list)
    for key in sorted(movable):
        groups[tuple(sorted(shapes[key]))].append(key)
    edges = [(a, b, weight) for a in sorted(offsets)
             for b, weight in sorted(affinity.neighbors.get(a, {}).items())
             if b in offsets and a < b]
    if not edges:
        return result

    def cost():
        def center(key, axis):
            return result[key][axis] + dimensions[key][axis] / 2
        return sum(weight * (abs(center(a, 0) - center(b, 0))
                             + abs(center(a, 1) - center(b, 1))) for a, b, weight in edges)

    best = cost()
    attempts = 0
    for members in groups.values():
        for index, a in enumerate(members):
            for b in members[index + 1:]:
                if attempts >= 512:
                    return result
                attempts += 1
                result[a], result[b] = result[b], result[a]
                candidate = cost()
                if candidate < best - 1e-9:
                    best = candidate
                else:
                    result[a], result[b] = result[b], result[a]
    return result


def derive_affinity(graph: dict[str, Any], owners: dict[str, str],
                    parents: dict[str, str]) -> Affinity:
    """No names, manifest declarations, unknown edges, or duplicate-edge inflation."""
    entities = {item["id"]: item for item in graph["entities"]}
    evidence = {item["evidenceId"] for item in graph["evidence"]}
    pairs: dict[tuple[str, str], float] = {}
    inbound: dict[str, set[str]] = defaultdict(set)
    for edge in graph["edges"]:
        source, target = edge["from"], edge["to"]
        if (edge["type"] not in RELATIONS or source not in owners or target not in owners
                or source == target or edge["confidence"] not in {"DIRECT", "RESOLVED"}
                or not edge["evidenceIds"] or not set(edge["evidenceIds"]) <= evidence):
            continue
        pairs[source, target] = max(pairs.get((source, target), 0), RELATIONS[edge["type"]])
        inbound[target].add(source)
    exposure = {}
    for item_id, owner in owners.items():
        roles = {role["value"] for role in entities[item_id].get("roles", [])
                 if role["confidence"] in {"DIRECT", "RESOLVED"}
                 and role["evidenceIds"] and set(role["evidenceIds"]) <= evidence}
        base = max((BOUNDARY_ROLES.get(role, 0) for role in roles), default=0)
        if not base and roles & INNER_ROLES:
            base = -2
        outside = len({owners[source] for source in inbound[item_id] if owners[source] != owner})
        exposure[item_id] = min(3, base + min(3, outside) * 0.75)

    chains = {}
    for item_id in sorted(owners):
        chain = [item_id, owners[item_id]]
        while chain[-1] in parents:
            chain.append(parents[chain[-1]])
        chains[item_id] = chain
    neighbors: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for (source, target), raw in sorted(pairs.items()):
        weight = raw / math.sqrt(max(1, len(inbound[target])))
        neighbors[source][target] += weight
        neighbors[target][source] += weight
        # Lift only to the two sibling branches below the actual common parent.
        left, right = chains[source], chains[target]
        ancestors = set(right)
        common = next(node for node in left if node in ancestors)
        a, b = left[left.index(common) - 1], right[right.index(common) - 1]
        if a != source or b != target:
            neighbors[a][b] += weight
            neighbors[b][a] += weight
    return Affinity(exposure, {key: dict(value) for key, value in neighbors.items()})


def assign_frontage(slots: dict[str, int], affinity: Affinity,
                    locked: dict[str, int], axis: list[float], page_depth: float) -> dict[str, int]:
    """Assign existing sites within each 64-site page; never move a locked item."""
    result = dict(locked)
    pages: dict[int, list[str]] = defaultdict(list)
    for item_id, slot in slots.items():
        pages[slot // 64].append(item_id)

    def point(slot: int) -> tuple[float, float]:
        return axis[slot % 8], (slot // 64) * page_depth + axis[(slot % 64) // 8]

    for page, members in sorted(pages.items()):
        if not any(affinity.exposure.get(item, 0) or affinity.neighbors.get(item) for item in members):
            result.update({item: slots[item] for item in members})
            continue
        sites = {slots[item] for item in members}
        points = [point(site) for site in sites]
        x0, x1 = min(p[0] for p in points), max(p[0] for p in points)
        z0, z1 = min(p[1] for p in points), max(p[1] for p in points)
        span = max(x1 - x0, z1 - z0, 1)
        available = sites - set(locked.values())
        for item in sorted(set(members) - set(locked),
                           key=lambda key: (-abs(affinity.exposure.get(key, 0)), key)):
            def score(site: int) -> tuple[float, int]:
                x, z = point(site)
                inset = min(x - x0, x1 - x, z - z0, z1 - z) / span
                links = [(other, weight) for other, weight in affinity.neighbors.get(item, {}).items()
                         if other in result and result[other] // 64 == page and other in slots]
                distance = sum(weight * (abs(x - point(result[other])[0]) + abs(z - point(result[other])[1]))
                               for other, weight in links) / max(1, sum(weight for _, weight in links)) / span
                return affinity.exposure.get(item, 0) * inset + distance * 0.35, site
            selected = min(available, key=score)
            result[item] = selected
            available.remove(selected)
    return result
