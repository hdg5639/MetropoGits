"""Complete-trip entrance planning on fixed geography (ADR-019, opt-in only)."""
from __future__ import annotations

import copy
import heapq
import math
from collections import Counter, defaultdict, deque

from metropogits.access_routes import AccessGrid, PITCH, _heading, _pair
from metropogits.block_collectors import _expand, _geometry_score, _rebuild
from metropogits.road_consolidation import _bends, _world
from metropogits.road_frontage import _doors

MAX_ENTRANCES = 1600
MAX_PROPOSALS = 4800
MAX_SEARCH_STATES = 12_000_000
MAX_TRIP_STATES = 12_000
MAX_TRIP_LABELS = 60_000
MAX_GRAPH_EDGES = 100_000
MAX_INPUT_ROUTES = 20_000
CONNECTOR_STEPS = 3


def _length(points):
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def _score(usage, doors, fixed):
    """Exact union metrics from membership counts, without expanding every trip."""
    keys = {(kind, edge) for kind, counts in usage.items() for edge, count in counts.items() if count}
    incidence, access = defaultdict(int), set(fixed)
    for kind, door, port in doors.values():
        if list(door) != _world(port):
            access.add((kind, *_pair(tuple(door), tuple(_world(port)))))
    length = 0
    for kind, a, b in access:
        length += abs(a[0]-b[0])+abs(a[1]-b[1])
        for point in (a, b):
            incidence[kind, tuple(v/PITCH for v in point)] += 1
    pavement, junctions, parallel = _geometry_score(keys, incidence)
    return round(pavement*PITCH+length, 6), junctions, parallel


def _compress(graph, ports):
    """Search-only contraction; retain every unit edge and every bend in a run."""
    result = defaultdict(list)
    for start in sorted(graph):
        if len(graph[start]) == 2 and start not in ports:
            continue
        for other in sorted(graph[start]):
            path, seen = [start, other], {start, other}
            while len(graph[path[-1]]) == 2 and path[-1] not in ports:
                following = next(n for n in graph[path[-1]] if n != path[-2])
                if following in seen:
                    break
                path.append(following)
                seen.add(following)
            keys = frozenset(_pair(a, b) for a, b in zip(path, path[1:]))
            result[start].append((path[-1], tuple(path), keys, _bends(path),
                                  _heading(path[0], path[1]), _heading(path[-2], path[-1])))
    return result


def _search(graph, start, end, usage, limit, bend_limit, heading, terminal, budget):
    """Bounded Pareto search; cap exhaustion is not a proof of infeasibility."""
    def distance(node):
        return abs(node[0]-end[0]) + abs(node[1]-end[1])
    if limit < distance(start) or bend_limit < 0:
        return None
    queue = [(distance(start)*10, 0, 0, 0, start, heading, 0)]
    labels, weights = defaultdict(list), {}
    records = [(None, ())]
    local_states = 0
    while queue:
        if budget[0] >= MAX_SEARCH_STATES or local_states >= MAX_TRIP_STATES:
            budget[1] += 1
            return None
        _, cost, steps, bends, node, direction, record = heapq.heappop(queue)
        budget[0] += 1
        local_states += 1
        if node == end:
            if bends+int(terminal != (0, 0) and direction != terminal) <= bend_limit:
                chunks = []
                while record:
                    record, run = records[record]
                    chunks.append(run)
                path = [start, *[n for chunk in reversed(chunks) for n in chunk]]
                if len(set(path)) == len(path):
                    return path
            continue
        for other, path, keys, internal_bends, first, last in graph.get(node, ()):
            new_steps = steps+len(path)-1
            if new_steps+distance(other) > limit:
                continue
            new_bends = bends+internal_bends+int(direction != (0, 0) and first != direction)
            if new_bends > bend_limit:
                continue
            if keys not in weights:
                weights[keys] = sum(10 if usage[e] else 80 for e in keys)
            new_cost = cost+weights[keys]+(new_bends-bends)*25
            old = labels[other, last]
            if any(c <= new_cost and s <= new_steps and b <= new_bends for c, s, b in old):
                continue
            labels[other, last] = [(c, s, b) for c, s, b in old
                                  if c < new_cost or s < new_steps or b < new_bends]
            labels[other, last].append((new_cost, new_steps, new_bends))
            if len(records) >= MAX_TRIP_LABELS:
                budget[1] += 1
                return None
            records.append((record, path[1:]))
            heapq.heappush(queue, (new_cost+distance(other)*10, new_cost, new_steps,
                                   new_bends, other, last, len(records)-1))
    return None


def plan_shared_frontages(scene, original, baseline):
    """Atomically orient entrances toward shared complete trips, never new facts."""
    if (original['version'] != 'visual-access/0.2'
            or baseline['version'] not in ('visual-access/0.2', 'visual-access/0.3')
            or any(r['status'] != 'COMPLETE' for r in (original, baseline))):
        raise ValueError('shared frontage requires complete routing and fresh original0.2 bounds')
    if 'sharedFrontage' in baseline:
        raise ValueError('shared frontage cannot compound its own result')
    def identities(routing):
        return {r['id']: (r['kind'], r['source'], r['target'], r['edgeIds'], r['networkIds'])
                for r in routing['routes']}
    if identities(original) != identities(baseline):
        raise ValueError('shared frontage provenance mismatch')
    if max(len(original['routes']), len(baseline['routes'])) > MAX_INPUT_ROUTES:
        raise ValueError('shared frontage route limit')
    paths, widths = _expand(baseline)
    initial, _ = _expand(original)
    # A prior valid frontage can collapse a trip to access spurs at one port.
    # Preserve those trips; only new through trips without original bounds fail.
    if not paths.keys() <= initial.keys():
        raise ValueError('shared frontage lattice provenance mismatch')
    template = copy.deepcopy(baseline)
    routes = {r['id']: r for r in template['routes']}
    originals = {r['id']: r for r in original['routes']}
    report = dict(version='shared-frontage/0.1', attempts=0, accepted=[], rejected={},
                  maxEntrances=MAX_ENTRANCES, maxProposals=MAX_PROPOSALS,
                  maxSearchStates=MAX_SEARCH_STATES, maxTripStates=MAX_TRIP_STATES,
                  maxTripLabels=MAX_TRIP_LABELS, maxGraphEdges=MAX_GRAPH_EDGES,
                  connectorSteps=CONNECTOR_STEPS, originalWorldDistanceBoundsPreserved=True)
    def finish(result, budget, limited=False):
        result['version'] = 'visual-access/0.3'
        report.update(searchStates=budget[0], cappedSearches=budget[1], limitReached=limited or budget[1] > 0)
        result['sharedFrontage'] = report
        return result
    if not paths:
        return finish(template, [0, 0])
    incident, doors, usage = defaultdict(set), {}, defaultdict(Counter)
    adjacency = defaultdict(lambda: defaultdict(set))
    limits, protected, fixed = {}, set(), set()
    segments = {s['id']: s for s in baseline['segments']}
    for rid, route in sorted(routes.items()):
        for entity in (route['source'], route['target']):
            incident[entity].add(rid)
        if rid not in paths:
            protected.update((route['source'], route['target']))
            for sid in route['segmentIds']:
                segment = segments[sid]
                fixed.add((segment['kind'], *_pair(tuple(segment['start']), tuple(segment['end']))))
            continue
        nodes, kind = paths[rid], route['kind']
        for a, b in zip(nodes, nodes[1:]):
            usage[kind][_pair(a, b)] += 1
            adjacency[kind][a].add(b)
            adjacency[kind][b].add(a)
        for entity, index in ((route['source'], 0), (route['target'], -1)):
            value = kind, tuple(route['path'][index]), nodes[index]
            if (kind, entity) in doors and doors[kind, entity] != value:
                raise ValueError('inconsistent shared frontage entrance')
            doors[kind, entity] = value
        n = len(initial[rid])-1
        limits[rid] = max(n*3//2, n+4)*PITCH+_length(originals[rid]['path'])-n*PITCH
        if _length(route['path']) > limits[rid]+1e-8 or _bends(route['path']) > _bends(originals[rid]['path'])+4:
            raise ValueError('shared frontage baseline exceeds original bounds')
    if sum(len(v) for v in usage.values()) > MAX_GRAPH_EDGES:
        report['rejected'] = {'graph_limit': 1}
        return finish(template, [0, 0], True)
    def private_length(entity):
        counts = Counter((routes[rid]['kind'], _pair(a, b)) for rid in incident[entity] if rid in paths
                         for a, b in zip(paths[rid], paths[rid][1:]))
        return sum(usage[kind][pair] == count for (kind, pair), count in counts.items())
    buildings = {b['entityId']: b for b in scene['buildings']}
    eligible = [e for e in incident if e not in protected
                and len({routes[r]['kind'] for r in incident[e]}) == 1]
    eligible.sort(key=lambda e: (-private_length(e), e))
    limited = len(eligible) > MAX_ENTRANCES
    eligible = eligible[:MAX_ENTRANCES]
    grid, alternatives = AccessGrid(scene['buildings']), {}
    edge_count = sum(len(v) for v in usage.values())
    for entity in eligible:
        kind = routes[min(incident[entity])]['kind']
        alternatives[kind, entity] = _doors(grid, buildings[entity])
        for port, _ in alternatives[kind, entity]:
            queue, seen = deque([(port, 0)]), {port}
            while queue:
                node, depth = queue.popleft()
                if depth >= CONNECTOR_STEPS:
                    continue
                for other, clearance in grid.neighbors(node):
                    if clearance < .47:
                        continue
                    if other not in adjacency[kind][node]:
                        edge_count += 1
                        if edge_count > MAX_GRAPH_EDGES:
                            report['rejected'] = {'graph_limit': 1}
                            return finish(template, [0, 0], True)
                    adjacency[kind][node].add(other)
                    adjacency[kind][other].add(node)
                    widths.setdefault((kind, _pair(node, other)), round(min(5.5, 2*(clearance-.12)), 4))
                    if other not in seen:
                        seen.add(other)
                        queue.append((other, depth+1))
    ports = {(kind, port) for kind, _, port in doors.values()}
    ports.update((kind, port) for (kind, _), options in alternatives.items() for port, _ in options)
    graph = {kind: _compress(g, {p for k, p in ports if k == kind}) for kind, g in sorted(adjacency.items())}
    report.update(candidateBuildings=len(eligible), candidateGraphEdges=edge_count)
    score = _score(usage, doors, fixed)
    budget, rejected = [0, 0], Counter()
    for entity in eligible:
        if report['attempts'] >= MAX_PROPOSALS or budget[0] >= MAX_SEARCH_STATES:
            limited = True
            break
        kind = routes[min(incident[entity])]['kind']
        affected = sorted(incident[entity], key=lambda rid: (-len(paths[rid]), rid))
        removed = Counter(_pair(a, b) for rid in affected for a, b in zip(paths[rid], paths[rid][1:]))
        rest, best = usage[kind]-removed, None
        for port, door in alternatives[kind, entity]:
            if (tuple(door), port) == doors[kind, entity][1:]:
                continue
            if report['attempts'] >= MAX_PROPOSALS or budget[0] >= MAX_SEARCH_STATES:
                limited = True
                break
            report['attempts'] += 1
            trial_doors = {**doors, (kind, entity): (kind, tuple(door), port)}
            changes, shared = {}, rest.copy()
            for rid in affected:
                route = routes[rid]
                _, a, start = trial_doors[kind, route['source']]
                _, b, end = trial_doors[kind, route['target']]
                spurs = math.dist(a, _world(start))+math.dist(b, _world(end))
                limit = math.floor((limits[rid]-spurs+1e-8)/PITCH)
                path = _search(graph[kind], start, end, shared, limit, _bends(originals[rid]['path'])+4,
                               _heading(a, _world(start)), _heading(_world(end), b), budget)
                if path is None:
                    rejected['route_constraint_or_search_cap'] += 1
                    break
                changes[rid] = path
                shared.update(_pair(x, y) for x, y in zip(path, path[1:]))
            else:
                candidate_score = _score({**usage, kind: shared}, trial_doors, fixed)
                if candidate_score[0] >= score[0] or any(candidate_score[i] > score[i] for i in (1, 2)):
                    rejected['no_global_geometry_gain'] += 1
                    continue
                if best is None or candidate_score < best[0]:
                    best = candidate_score, changes, trial_doors, shared, door
        if best:
            new_score, changes, trial_doors, shared, door = best
            report['accepted'].append(dict(entityId=entity, oldDoor=list(doors[kind, entity][1]),
                                           newDoor=door, removedLength=score[0]-new_score[0],
                                           changedRoutes=len(changes)))
            paths.update(changes)
            doors, usage[kind], score = trial_doors, shared, new_score
            for rid in affected:
                if routes[rid]['source'] == entity:
                    routes[rid]['path'][0] = door
                if routes[rid]['target'] == entity:
                    routes[rid]['path'][-1] = door
    report['rejected'] = dict(sorted(rejected.items()))
    result = _rebuild(template, paths, widths)
    before_bends = sum(_bends(r['path']) for r in baseline['routes'])
    after_bends = sum(_bends(r['path']) for r in result['routes'])
    report.update(beforeBends=before_bends, candidateBends=after_bends, rolledBack=after_bends > before_bends)
    if report['rolledBack']:
        report['candidateAccepted'] = report['accepted']
        report['accepted'] = []
        result = copy.deepcopy(baseline)
    return finish(result, budget, limited)
