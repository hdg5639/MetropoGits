"""Bounded complete-trip simplification on existing pavement only (ADR-019)."""
from __future__ import annotations

import copy
import heapq
import math
from collections import Counter, defaultdict

from metropogits.access_routes import PITCH, _heading, _pair
from metropogits.block_collectors import _expand, _rebuild
from metropogits.road_consolidation import _bends, _bridge_keys, _corridors, _world
from metropogits.shared_frontage import _compress, _length

MAX_ROUTES = 20_000
MAX_GRAPH_EDGES = 100_000
MAX_STATES = 3_000_000
MAX_TRIP_STATES = 6000
MAX_LABELS = 30_000
TURN_COST = 15
MAX_PROPOSALS = 1200
MAX_ROUNDS = 2
MAX_DIAGNOSTIC_SAMPLES = 24
MAX_SAMPLES_PER_REASON = 8
MAX_DIAGNOSTIC_KEYS = 64
MAX_PROBE_STATES = 100_000
MAX_PROBE_TRIP_STATES = 5000


def _distance_probe(graph, start, end, usage, limit, budget):
    """Independent shortest-distance feasibility probe, ignoring bend limits.

    This only explains rejected proposals; it must never alter routing search
    order, its state budget, or the accepted geometry.
    """
    def distance(p):
        return abs(p[0]-end[0])+abs(p[1]-end[1])
    queue, best, allowed = [(distance(start), 0, start)], {start: 0}, {}
    local = 0
    while queue:
        if budget[0] >= MAX_PROBE_STATES or local >= MAX_PROBE_TRIP_STATES:
            return dict(status='CAPPED', states=local)
        lower, steps, node = heapq.heappop(queue)
        if steps != best[node]:
            continue
        local += 1
        budget[0] += 1
        if lower > limit:
            return dict(status='EXCEEDS_DISTANCE_BUDGET', lowerBoundSteps=lower, states=local)
        if node == end:
            return dict(status='WITHIN_DISTANCE_BUDGET', shortestSteps=steps, states=local)
        for other, path, keys, *_ in graph.get(node, ()):
            if keys not in allowed:
                allowed[keys] = all(usage[e] > 0 for e in keys)
            new_steps = steps+len(path)-1
            if allowed[keys] and new_steps < best.get(other, math.inf):
                best[other] = new_steps
                heapq.heappush(queue, (new_steps+distance(other), new_steps, other))
    return dict(status='DISCONNECTED', states=local)


def _search(graph, start, end, usage, limit, bend_limit, heading, terminal, budget):
    def distance(p):
        return abs(p[0]-end[0])+abs(p[1]-end[1])
    queue = [(distance(start), 0, 0, 0, start, heading, 0)]
    labels, records, allowed = defaultdict(list), [(None, ())], {}
    local = 0
    while queue:
        if budget[0] >= MAX_STATES or local >= MAX_TRIP_STATES:
            budget[1] += 1
            return None
        _, cost, steps, bends, node, direction, record = heapq.heappop(queue)
        budget[0] += 1
        local += 1
        if node == end:
            if bends+int(terminal != (0, 0) and direction != terminal) <= bend_limit:
                chunks = []
                while record:
                    record, run = records[record]
                    chunks.append(run)
                path = [start, *[p for run in reversed(chunks) for p in run]]
                if len(path) == len(set(path)):
                    return path
            continue
        for other, path, keys, internal, first, last in graph.get(node, ()):
            if keys not in allowed:
                allowed[keys] = all(usage[e] > 0 for e in keys)
            if not allowed[keys]:
                continue
            ns = steps+len(path)-1
            nb = bends+internal+int(direction != (0, 0) and first != direction)
            if ns+distance(other) > limit or nb > bend_limit:
                continue
            nc = ns+nb*TURN_COST
            old = labels[other, last]
            if any(s <= ns and b <= nb for s, b in old):
                continue
            labels[other, last] = [(s, b) for s, b in old if s < ns or b < nb]+[(ns, nb)]
            if len(records) >= MAX_LABELS:
                budget[1] += 1
                return None
            records.append((record, path[1:]))
            heapq.heappush(queue, (nc+distance(other), nc, ns, nb, other, last, len(records)-1))
    return None


def simplify_routes(original, baseline):
    if (original['version'] != 'visual-access/0.2'
            or baseline['version'] not in ('visual-access/0.2', 'visual-access/0.3')
            or any(r['status'] != 'COMPLETE' for r in (original, baseline))):
        raise ValueError('simplification requires complete routing and original0.2 bounds')
    if 'routeSimplification' in baseline:
        raise ValueError('simplification cannot compound its own result')
    def identity(data):
        return {r['id']: (r['kind'], r['source'], r['target'], r['edgeIds'], r['networkIds']) for r in data['routes']}
    if (any(len(identity(data)) != len(data['routes']) for data in (original, baseline))
            or identity(original) != identity(baseline)):
        raise ValueError('simplification provenance mismatch')
    if len(baseline['routes']) > MAX_ROUTES:
        raise ValueError('simplification route limit')
    paths, widths = _expand(baseline)
    initial_pavement = set(widths)
    originals = {r['id']: r for r in original['routes']}
    routes = {r['id']: r for r in baseline['routes']}
    usage, adjacency, ports = defaultdict(Counter), defaultdict(lambda: defaultdict(set)), defaultdict(set)
    for rid, nodes in sorted(paths.items()):
        kind = routes[rid]['kind']
        ports[kind].update((nodes[0], nodes[-1]))
        for a, b in zip(nodes, nodes[1:]):
            usage[kind][_pair(a, b)] += 1
            adjacency[kind][a].add(b)
            adjacency[kind][b].add(a)
    report = dict(version='route-simplification/0.1', attempted=0, accepted=[],
                  maxStates=MAX_STATES, maxTripStates=MAX_TRIP_STATES, maxLabels=MAX_LABELS,
                  maxRoutes=MAX_ROUTES, maxGraphEdges=MAX_GRAPH_EDGES,
                  noNewPavement=True, fixedEntrances=True, maxProposals=MAX_PROPOSALS,
                  maxRounds=MAX_ROUNDS, corridorAttempts=0, removedCorridors=[])
    report['turnCost'] = TURN_COST
    diagnostics = dict(version='corridor-constraints/0.1', rejected={}, skipped={}, samples=[],
                       sampleLimit=MAX_DIAGNOSTIC_SAMPLES, maxProbeStates=MAX_PROBE_STATES,
                       maxProbeTripStates=MAX_PROBE_TRIP_STATES, samplePerReasonLimit=MAX_SAMPLES_PER_REASON,
                       maxSampleKeys=MAX_DIAGNOSTIC_KEYS)
    rejected, skipped, probe_budget = Counter(), Counter(), [0]
    def can_sample(reason):
        return (len(diagnostics['samples']) < MAX_DIAGNOSTIC_SAMPLES
                and sum(s['reason'] == reason for s in diagnostics['samples']) < MAX_SAMPLES_PER_REASON)
    budget = [0, 0]
    limited = sum(len(u) for u in usage.values()) > MAX_GRAPH_EDGES
    graph = {} if limited else {k: _compress(g, ports[k]) for k, g in sorted(adjacency.items())}
    limits = {}
    for rid, route in sorted(routes.items()):
        old = originals[rid]
        n = old['latticeSteps']
        bound = max(n*3//2, n+4)*PITCH+_length(old['path'])-n*PITCH
        if _length(route['path']) > bound+1e-8 or _bends(route['path']) > _bends(old['path'])+4:
            raise ValueError('simplification baseline exceeds original bounds')
        if rid in paths:
            nodes = paths[rid]
            spurs = math.dist(route['path'][0], _world(nodes[0]))+math.dist(_world(nodes[-1]), route['path'][-1])
            limits[rid] = math.floor((bound-spurs+1e-8)/PITCH)
    order = sorted(paths, key=lambda rid: (-_bends(routes[rid]['path']), -len(paths[rid]), rid))
    for rid in order:
        if limited or budget[0] >= MAX_STATES:
            limited = True
            break
        route, nodes = routes[rid], paths[rid]
        bends = _bends(route['path'])
        if bends == 0:
            continue
        kind = route['kind']
        report['attempted'] += 1
        path = _search(graph[kind], nodes[0], nodes[-1], usage[kind], len(nodes)-1, bends,
                       _heading(route['path'][0], _world(nodes[0])),
                       _heading(_world(nodes[-1]), route['path'][-1]), budget)
        if path is None:
            continue
        new_bends = _bends([route['path'][0], *map(_world, path), route['path'][-1]])
        if new_bends > bends or len(path) > len(nodes) or (new_bends == bends and len(path) == len(nodes)):
            continue
        usage[kind].subtract(_pair(a, b) for a, b in zip(nodes, nodes[1:]))
        usage[kind].update(_pair(a, b) for a, b in zip(path, path[1:]))
        paths[rid] = path
        report['accepted'].append(dict(routeId=rid, removedBends=bends-new_bends,
                                       removedSteps=len(nodes)-len(path)))
    def path_bends(rid, path):
        return _bends([routes[rid]['path'][0], *map(_world, path), routes[rid]['path'][-1]])
    for _ in range(MAX_ROUNDS if graph else 0):
        users, adjacency = defaultdict(set), defaultdict(lambda: defaultdict(set))
        for rid, nodes in sorted(paths.items()):
            kind = routes[rid]['kind']
            for a, b in zip(nodes, nodes[1:]):
                users[kind, _pair(a, b)].add(rid)
                adjacency[kind][a].add(b)
                adjacency[kind][b].add(a)
        bridges = _bridge_keys(adjacency)
        graph = {k: _compress(g, ports[k]) for k, g in sorted(adjacency.items())}
        candidates = _corridors(adjacency, {(k, p) for k, ps in ports.items() for p in ps}, users, routes)
        candidates.sort(key=lambda c: (len(set().union(*(users[k] for k in c[2]))), -len(c[2]), c[2]))
        accepted = 0
        for _, _, keys, _, _ in candidates:
            if budget[0] >= MAX_STATES or report['corridorAttempts'] >= MAX_PROPOSALS:
                limited = True
                break
            if any(k in bridges for k in keys):
                skipped['connectivity_bridge'] += 1
                continue
            if any(not users[k] for k in keys):
                skipped['already_removed'] += 1
                continue
            kind = keys[0][0]
            affected = sorted(set().union(*(users[k] for k in keys)))
            report['corridorAttempts'] += 1
            allowed = usage[kind].copy()
            for _, pair in keys:
                allowed[pair] = 0
            changes = {}
            for rid in affected:
                route, nodes = routes[rid], paths[rid]
                caps_before = budget[1]
                path = _search(graph[kind], nodes[0], nodes[-1], allowed, limits[rid],
                               _bends(originals[rid]['path'])+4,
                               _heading(route['path'][0], _world(nodes[0])),
                               _heading(_world(nodes[-1]), route['path'][-1]), budget)
                if path is None:
                    reason = 'search_cap' if budget[1] > caps_before else 'no_admissible_trip'
                    rejected[reason] += 1
                    if can_sample(reason):
                        sample = dict(reason=reason, routeId=rid, affectedRoutes=len(affected),
                                      blockedKeys=[[kind, [list(a), list(b)]] for kind, (a, b) in keys[:MAX_DIAGNOSTIC_KEYS]],
                                      blockedKeyCount=len(keys), blockedKeysTruncated=len(keys) > MAX_DIAGNOSTIC_KEYS,
                                      distanceBudgetSteps=limits[rid],
                                      bendBudget=_bends(originals[rid]['path'])+4)
                        if reason == 'no_admissible_trip':
                            sample['distanceProbe'] = _distance_probe(
                                graph[kind], nodes[0], nodes[-1], allowed, limits[rid], probe_budget)
                        diagnostics['samples'].append(sample)
                    break
                changes[rid] = path
            else:
                delta = sum(path_bends(rid, path)-path_bends(rid, paths[rid]) for rid, path in changes.items())
                if delta > 0:
                    rejected['total_bend_regression'] += 1
                    if can_sample('total_bend_regression'):
                        diagnostics['samples'].append(dict(reason='total_bend_regression',
                            affectedRoutes=len(affected), bendDelta=delta,
                            blockedKeyCount=len(keys), blockedKeysTruncated=len(keys) > MAX_DIAGNOSTIC_KEYS,
                            blockedKeys=[[kind, [list(a), list(b)]] for kind, (a, b) in keys[:MAX_DIAGNOSTIC_KEYS]]))
                    continue
                for rid, path in changes.items():
                    for a, b in zip(paths[rid], paths[rid][1:]):
                        users[kind, _pair(a, b)].discard(rid)
                        usage[kind][_pair(a, b)] -= 1
                    for a, b in zip(path, path[1:]):
                        users[kind, _pair(a, b)].add(rid)
                        usage[kind][_pair(a, b)] += 1
                    paths[rid] = path
                accepted += 1
                report['removedCorridors'].append(dict(
                    keys=[[kind, [list(a), list(b)]] for kind, (a, b) in keys],
                    routeIds=affected, bendDelta=delta))
        if not accepted or limited:
            break
    result = _rebuild(copy.deepcopy(baseline), paths, widths) if graph else copy.deepcopy(baseline)
    result['routes'].sort(key=lambda r: r['id'])
    if not set(_expand(result)[1]).issubset(initial_pavement):
        raise ValueError('simplification introduced new pavement')
    if sum(_bends(r['path']) for r in result['routes']) > sum(_bends(r['path']) for r in baseline['routes']):
        raise ValueError('simplification increased total bends')
    for route in result['routes']:
        rid = route['id']
        if (route['path'][0] != routes[rid]['path'][0]
                or route['path'][-1] != routes[rid]['path'][-1]
                or _bends(route['path']) > _bends(originals[rid]['path'])+4
                or (rid in paths and len(paths[rid])-1 > limits[rid])):
            raise ValueError('simplification changed a door or exceeded original bounds')
    result['version'] = 'visual-access/0.3'
    diagnostics.update(rejected=dict(sorted(rejected.items())), skipped=dict(sorted(skipped.items())),
                       probeStates=probe_budget[0],
                       unsampledRejections=sum(rejected.values())-len(diagnostics['samples']))
    report['constraints'] = diagnostics
    report.update(searchStates=budget[0], cappedSearches=budget[1], limitReached=limited or budget[1] > 0)
    result['routeSimplification'] = report
    return result
