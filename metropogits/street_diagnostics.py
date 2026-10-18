"""Bounded explanations of failed street assignment; no changes to trips."""
from __future__ import annotations

import heapq

MAX_DIAGNOSTIC_STATES = 1_000_000


def distance_within(graph, start, end, limit, budget):
    """Shortest lattice length up to limit; None means unknown after the cap."""
    def h(node):
        return abs(node[0]-end[0])+abs(node[1]-end[1])
    queue, best = [(h(start), 0, start)], {start: 0}
    while queue:
        if budget[0] >= MAX_DIAGNOSTIC_STATES:
            return None
        estimate, distance, node = heapq.heappop(queue)
        if distance != best[node]:
            continue
        budget[0] += 1
        if estimate > limit:
            return False
        if node == end:
            return distance
        for other, path, *_ in graph.get(node, ()):
            following = distance+len(path)-1
            if following < best.get(other, float('inf')):
                best[other] = following
                heapq.heappush(queue, (following+h(other), following, other))
    return False


def explain_failure(graph, components, start, end, limit, budget, *, search_capped=False,
                    connector_capped=False):
    if start not in components or end not in components:
        return dict(reason='connector_search_limit' if connector_capped else 'missing_access')
    if components[start] != components[end]:
        return dict(reason='disconnected_streets')
    if search_capped:
        return dict(reason='route_search_limit')
    distance = distance_within(graph, start, end, limit, budget)
    if distance is None:
        return dict(reason='diagnostic_search_limit')
    if distance is False:
        return dict(reason='distance_limit', latticeStepLimit=limit)
    # A distance-feasible route exists, but not necessarily one satisfying both
    # heading/bend constraints and the simple-path rule. Do not claim bend-only.
    return dict(reason='joint_constraints', shortestLatticeSteps=distance, latticeStepLimit=limit)
