"""Consolidate real local chains onto existing shared streets, with trip budgets."""

import heapq
import math
from collections import defaultdict

from .geometry import bounds, nearest

GENERATOR_VERSION = "flat-adaptive-neighborhoods/0.4"
MAX_INDEX = 500_000
MAX_CHECKS = 500_000
MAX_ATTEMPTS = 768
MAX_STATES = 500_000
MAX_ROUTE_WORK = 2_000_000


def trip_limit(length):
    return max(length * 1.5, length + 12)


def path_length(path):
    return sum(math.dist(a, b) for a, b in zip(path, path[1:]))


def _pair(a, b):
    return tuple(sorted((tuple(a), tuple(b))))


def protect(streets, reserved, parcels):
    """Preserve ALL main curves and actual tangent frontage, not every used road."""
    index = defaultdict(set)
    by_id = {s["id"]: s for s in streets}
    main, frontage = set(), {s["id"] for s in streets if s["access"]}
    work = entries = 0

    def cells(a, b):
        x0, z0, x1, z1 = bounds([a, b])
        nx = math.floor((x1 + .003) / 32) - math.floor((x0 - .003) / 32) + 1
        nz = math.floor((z1 + .003) / 32) - math.floor((z0 - .003) / 32) + 1
        if nx * nz > MAX_INDEX:
            raise ValueError("shared junction index extent")
        return [(x, z) for x in range(math.floor((x0-.003)/32), math.floor((x1+.003)/32)+1)
                for z in range(math.floor((z0-.003)/32), math.floor((z1+.003)/32)+1)]

    for s in streets:
        keys = cells(s["start"], s["end"])
        entries += len(keys)
        if entries > MAX_INDEX:
            raise ValueError("shared junction index budget")
        for key in keys:
            index[key].add(s["id"])
    for r in reserved:
        for key in sorted({key for c in cells(r["start"], r["end"]) for key in index[c]}):
            work += 1
            if work > MAX_CHECKS:
                raise ValueError("shared junction reservation budget")
            if all(math.dist(p, nearest(p, r["start"], r["end"])) < .002
                   for p in (by_id[key]["start"], by_id[key]["end"])):
                main.add(key)
    for p in parcels:
        at = p["streetPoint"]
        tangent = [math.cos(p["angle"]), math.sin(p["angle"])]
        matches, touching = [], []
        for key in sorted({key for c in cells(at, at) for key in index[c]}):
            work += 1
            if work > MAX_CHECKS:
                raise ValueError("shared junction frontage budget")
            s = by_id[key]
            if s["access"] or math.dist(at, nearest(at, s["start"], s["end"])) > .002:
                continue
            touching.append(key)
            span = math.dist(s["start"], s["end"])
            alignment = abs(sum(tangent[j]*(s["end"][j]-s["start"][j])/span for j in (0, 1)))
            if alignment > math.cos(math.radians(5)):
                matches.append(key)
        if not touching:
            raise ValueError("source building has no physical frontage")
        frontage.update(matches or touching)
    return main, frontage


def _chains(streets, protected):
    adjacency = defaultdict(list)
    by_id = {s["id"]: s for s in streets}
    for s in streets:
        for a, b in ((s["start"], s["end"]), (s["end"], s["start"])):
            adjacency[tuple(a)].append((s["id"], tuple(b)))
    seen, chains = set(), []
    starts = sorted(p for p, edges in adjacency.items()
                    if len(edges) != 2 or any(k in protected for k, _ in edges))
    for start in starts:
        for identity, end in sorted(adjacency[start]):
            if identity in seen or identity in protected:
                continue
            ids, nodes = [identity], [start, end]
            seen.add(identity)
            while len(adjacency[nodes[-1]]) == 2 and not any(
                k in protected for k, _ in adjacency[nodes[-1]]
            ):
                key, following = next((k, p) for k, p in adjacency[nodes[-1]] if k != ids[-1])
                if key in seen:
                    break
                ids.append(key)
                nodes.append(following)
                seen.add(key)
            if nodes[0] == nodes[-1] or path_length(nodes) > 120:
                continue
            # Prefer needless close forks over an isolated well-shaped block.
            acute = 0.0
            for a, b in ((nodes[0], nodes[1]), (nodes[-1], nodes[-2])):
                u = [b[j]-a[j] for j in (0, 1)]
                for key, c in adjacency[a]:
                    if key in ids:
                        continue
                    v = [c[j]-a[j] for j in (0, 1)]
                    acute = max(acute, sum(u[j]*v[j] for j in (0, 1))/math.dist(a,b)/math.dist(a,c))
            degree = len(adjacency[nodes[0]]) + len(adjacency[nodes[-1]])
            chains.append((-acute, -degree, -path_length(nodes), tuple(ids), tuple(nodes)))
    return sorted(chains), by_id


def _simple(nodes):
    path, positions = [], {}
    for node in nodes:
        if node in positions:
            while len(path) > positions[node] + 1:
                del positions[path.pop()]
        else:
            positions[node] = len(path)
            path.append(node)
    return path


def consolidate_junctions(streets, reserved, parcels, routing):
    """Deletion-only physical reuse. Source routes are rerouted by the caller."""
    original = sorted(streets, key=lambda s: s["id"])
    note = dict(reason="shared junction consolidation", version="shared-junctions/0.1",
                removedStreetIds=[], attempts=0, searchStates=0, routeWork=0,
                affectedTripIds=[], budgetExhausted=None)
    try:
        main, frontage = protect(original, reserved, parcels)
    except ValueError as error:
        note["budgetExhausted"] = str(error)
        return original, note
    chains, kept = _chains(original, main | frontage)
    adjacency = defaultdict(dict)
    pairs = {}
    for s in original:
        a, b = tuple(s["start"]), tuple(s["end"])
        adjacency[a][s["id"]] = b
        adjacency[b][s["id"]] = a
        pairs[_pair(a, b)] = s["id"]
    paths, limits, users = {}, {}, defaultdict(set)
    for r in routing["routes"]:
        nodes = [tuple(p) for p in r["path"]]
        note["routeWork"] += len(nodes)
        if note["routeWork"] > MAX_ROUTE_WORK:
            note["budgetExhausted"] = "initial trip index"
            return original, note
        paths[r["id"]] = nodes
        limits[r["id"]] = trip_limit(path_length(nodes))
        for a, b in zip(nodes, nodes[1:]):
            users[pairs[_pair(a, b)]].add(r["id"])
    preferred = main | {key for key, ids in users.items() if len(ids) >= 4}
    affected_total = set()
    for _, _, _, ids, nodes in chains:
        if note["attempts"] >= MAX_ATTEMPTS or note["searchStates"] >= MAX_STATES:
            note["budgetExhausted"] = "attempt/search budget"
            break
        note["attempts"] += 1
        excluded = set(ids)
        start, finish = nodes[0], nodes[-1]
        limit = min(path_length(nodes) * 1.5 + 8, path_length(nodes) + 32)
        x0, z0, x1, z1 = bounds(nodes)
        queue = [(0.0, start, False)]
        costs, previous = {(start, False): 0.0}, {}
        found = None
        while queue:
            cost, at, shared = heapq.heappop(queue)
            if cost != costs.get((at, shared)):
                continue
            note["searchStates"] += 1
            if note["searchStates"] > MAX_STATES:
                note["budgetExhausted"] = "search budget"
                break
            if at == finish and shared:
                found = (at, shared)
                break
            for key, other in sorted(adjacency[at].items()):
                if key in excluded or not (x0-16 <= other[0] <= x1+16 and z0-16 <= other[1] <= z1+16):
                    continue
                flag = shared or key in preferred
                value = cost + math.dist(at, other)
                if value <= limit and value < costs.get((other, flag), math.inf)-1e-9:
                    costs[(other, flag)] = value
                    previous[(other, flag)] = (at, shared)
                    heapq.heappush(queue, (value, other, flag))
        if found is None:
            continue
        alternate = [found[0]]
        while found in previous:
            found = previous[found]
            alternate.append(found[0])
        alternate = _simple(list(reversed(alternate)))
        if not any(pairs[_pair(a, b)] in preferred for a, b in zip(alternate, alternate[1:])):
            continue  # A loop through an artery is not actual corridor reuse.
        affected = sorted(set().union(*(users[key] for key in ids)))
        replacements = {}
        for rid in affected:
            path = paths[rid]
            note["routeWork"] += len(path) * 3 + len(alternate)
            if note["routeWork"] > MAX_ROUTE_WORK:
                note["budgetExhausted"] = "trip update budget"
                break
            matched = False
            for pattern, via in ((nodes, alternate), (nodes[::-1], alternate[::-1])):
                try:
                    i = path.index(pattern[0])
                except ValueError:
                    continue
                if tuple(path[i:i+len(pattern)]) == pattern:
                    replacement = _simple(path[:i] + via + path[i+len(pattern):])
                    if path_length(replacement) <= limits[rid] + .0001:
                        replacements[rid] = replacement
                    matched = True
                    break
            if not matched or rid not in replacements:
                break
        if note["budgetExhausted"]:
            break
        if len(replacements) != len(affected):
            continue
        for rid, replacement in replacements.items():
            for a, b in zip(paths[rid], paths[rid][1:]):
                users[pairs[_pair(a, b)]].discard(rid)
            paths[rid] = replacement
            for a, b in zip(replacement, replacement[1:]):
                users[pairs[_pair(a, b)]].add(rid)
        affected_total.update(affected)
        for key in ids:
            s = kept.pop(key)
            del adjacency[tuple(s["start"])][key]
            del adjacency[tuple(s["end"])][key]
            note["removedStreetIds"].append(key)
    note["affectedTripIds"] = sorted(affected_total)
    note["removedStreetIds"].sort()
    return sorted(kept.values(), key=lambda s: s["id"]), note


def check_trip_budgets(original, replacement):
    before = {r["id"]: r for r in original["routes"]}
    after = {r["id"]: r for r in replacement["routes"]}
    if set(before) != set(after):
        raise ValueError("junction consolidation changed source trips")
    for key, r in after.items():
        old = before[key]
        if any(r[k] != old[k] for k in ("source", "target", "kind", "edgeIds", "networkIds")):
            raise ValueError("junction consolidation changed source identity")
        if path_length(r["path"]) > trip_limit(path_length(old["path"])) + .001:
            raise ValueError("junction consolidation exceeded original trip budget")
