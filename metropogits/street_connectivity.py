"""Bounded geography-only connections between neighboring block street components."""
from collections import deque

from metropogits.access_routes import _pair


def join_components(grid, keys, components, budget, limit):
    """Keep one contact per wave-neighbor pair, including local alternate circuits.

    A spanning tree alone can impose long detours between adjacent blocks. The
    extra links come from geometric wave adjacency, never dependency demand.
    This is not a global minimum-length or all-pairs shortest-path guarantee.
    """
    if len(components) <= 1:
        return True
    roots = list(range(len(components)))
    def root(i):
        while roots[i] != i:
            roots[i] = roots[roots[i]]
            i = roots[i]
        return i
    owner = {node:i for i,group in enumerate(components) for node in sorted(group)}
    queue = deque(sorted(owner))
    previous = dict.fromkeys(owner)
    remaining = len(components)
    linked = set()
    def attach(node):
        while previous[node] is not None:
            other = previous[node]
            keys.add(_pair(node,other))
            node = other
    while queue and budget[0] < limit:
        node = queue.popleft()
        budget[0] += 1
        for other, clearance in grid.neighbors(node):
            if clearance < .47:
                continue
            if other not in owner:
                owner[other],previous[other] = owner[node],node
                queue.append(other)
            elif owner[node] != owner[other] and _pair(owner[node],owner[other]) not in linked:
                linked.add(_pair(owner[node],owner[other]))
                a,b = root(owner[node]),root(owner[other])
                if a != b:
                    roots[max(a,b)] = min(a,b)
                    remaining -= 1
                attach(node)
                attach(other)
                keys.add(_pair(node,other))
    return remaining == 1 and not queue
