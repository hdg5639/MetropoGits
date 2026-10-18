"""Remove redundant pavement by rerouting on existing same-kind roads (ADR-018)."""
from __future__ import annotations

import copy
import heapq
from collections import defaultdict

from metropogits.access_routes import PITCH, _compact_segments, _heading, _id, _pair
from metropogits.road_hierarchy import demand_grade

MAX_ATTEMPTS = 1200
MAX_SEARCH_STATES = 2_000_000
MAX_ATOMIC_EDGES = 100_000
MAX_ROUTE_STEPS = 1_000_000
MAX_SEARCH_LABELS = 100_000
MAX_JUNCTION_ATTEMPTS = 600
MAX_JUNCTION_LINK_STEPS = 2
MAX_AVENUE_ATTEMPTS = 600
MIN_AVENUE_STEPS = 4


def _distance(a, b):
    return abs(a[0]-b[0]) + abs(a[1]-b[1])


def _bends(points):
    headings = [_heading(a, b) for a, b in zip(points, points[1:]) if a != b]
    return sum(a != b for a, b in zip(headings, headings[1:]))


def _node(point):
    result = tuple(round(v/PITCH) for v in point)
    if any(abs(result[i]*PITCH-point[i]) > 1e-8 for i in (0, 1)):
        raise ValueError('consolidation requires original lattice geometry')
    return result


def _world(node):
    return [v*PITCH for v in node]


def _search(start, end, adjacency, blocked, limit, heading, terminal, bend_limit, budget):
    # Pareto labels retain both length and bends. A shorter path with more bends
    # cannot discard a longer path needed to satisfy the final turn constraint.
    queue = [(_distance(start, end), 0, 0, start, heading, 0)]
    records = [(start, None)]
    labels = defaultdict(list)
    while queue:
        if budget[0] >= MAX_SEARCH_STATES:
            return None
        _, bends, steps, node, direction, record = heapq.heappop(queue)
        budget[0] += 1
        if node == end:
            if bends + int(terminal != (0, 0) and direction != terminal) <= bend_limit:
                path = []
                while record is not None:
                    point, record = records[record]
                    path.append(point)
                return list(reversed(path))
            continue
        for other in sorted(adjacency.get(node, ())):
            if _pair(node, other) in blocked:
                continue
            new_steps = steps+1
            if new_steps+_distance(other, end) > limit:
                continue
            new_direction = _heading(node, other)
            new_bends = bends + int(direction != (0, 0) and new_direction != direction)
            if new_bends > bend_limit:
                continue
            key = other, new_direction
            old = labels[key]
            if any(s <= new_steps and b <= new_bends for s, b in old):
                continue
            labels[key] = [(s, b) for s, b in old if s < new_steps or b < new_bends] + [(new_steps, new_bends)]
            if len(records) >= MAX_SEARCH_LABELS:
                budget[1] += 1
                return None
            records.append((other, record))
            heapq.heappush(queue, (new_steps+_distance(other, end), new_bends, new_steps,
                                   other, new_direction, len(records)-1))
    return None


def _junction_links(adjacency, ports, users):
    """Short links between existing branch nodes, excluding fixed entrance ports."""
    candidates, seen = [], set()
    for kind, graph in sorted(adjacency.items()):
        for start in sorted(graph):
            if len(graph[start]) < 3 or (kind, start) in ports:
                continue
            for neighbor in sorted(graph[start]):
                previous, current = start, neighbor
                stroke = [(kind, _pair(previous, current))]
                while len(graph[current]) == 2 and (kind, current) not in ports and len(stroke) < MAX_JUNCTION_LINK_STEPS:
                    other = next(n for n in graph[current] if n != previous)
                    stroke.append((kind, _pair(current, other)))
                    previous, current = current, other
                keys = tuple(sorted(stroke))
                if current == start or len(graph[current]) < 3 or (kind, current) in ports or keys in seen:
                    continue
                seen.add(keys)
                affected = set().union(*(users[k] for k in keys))
                candidates.append((len(affected), len(keys), keys, start, current))
    return sorted(candidates)


def _avenue_spines(users, routes):
    """Freeze straight, evidenced avenue runs across junctions; never create pavement."""
    lines = defaultdict(dict)
    for (kind, pair), identities in sorted(users.items()):
        if not identities:
            continue
        edges = set().union(*(set(routes[r]['edgeIds']) for r in identities))
        files = {routes[r][k] for r in identities for k in ('source', 'target')}
        if demand_grade(False, len(edges), len(files), 0) != 'AVENUE':
            continue
        a, b = pair
        axis = 0 if a[1] == b[1] else 1
        lines[(kind, axis, a[1-axis])][a[axis]] = (kind, pair)
    preferred, spines = set(), []
    for (kind, axis, offset), positions in sorted(lines.items()):
        runs = []
        for position in sorted(positions):
            if not runs or position != runs[-1][-1]+1:
                runs.append([])
            runs[-1].append(position)
        for run in runs:
            if len(run) < MIN_AVENUE_STEPS:
                continue
            keys = [positions[p] for p in run]
            preferred.update(keys)
            a, b = [0, 0], [0, 0]
            a[axis], b[axis] = run[0], run[-1]+1
            a[1-axis] = b[1-axis] = offset
            spines.append(dict(kind=kind, path=[_world(a), _world(b)], latticeSteps=len(run)))
    return preferred, spines


def _avenue_candidates(adjacency, ports, users, preferred, routes):
    nearby = set()
    for kind, (a, b) in sorted(preferred):
        axis = 1 if a[1] == b[1] else 0
        for offset in (-2, -1, 1, 2):
            shifted = [list(a), list(b)]
            for point in shifted:
                point[axis] += offset
            key = kind, _pair(tuple(shifted[0]), tuple(shifted[1]))
            if key not in preferred and users.get(key):
                nearby.add(key)
    seen, candidates = set(), []
    for key in sorted(nearby):
        if key in seen:
            continue
        kind, (a, b) = key
        stroke = {key}
        for previous, current in ((a, b), (b, a)):
            while len(adjacency[kind][current]) == 2 and (kind, current) not in ports:
                other = next(n for n in adjacency[kind][current] if n != previous)
                extra = kind, _pair(current, other)
                if extra not in nearby or extra in seen or extra in stroke or _heading(previous, current) != _heading(current, other):
                    break
                stroke.add(extra)
                previous, current = current, other
        seen.update(stroke)
        affected = set().union(*(users[k] for k in stroke))
        edges = set().union(*(set(routes[r]['edgeIds']) for r in affected))
        candidates.append((len(edges), -len(stroke), tuple(sorted(stroke))))
    return sorted(candidates)


def _avenue_search(start, end, adjacency, blocked, limit, heading, terminal, bend_limit, budget, preferred):
    """Bounded A*: prefer existing avenue steps (80) over local steps (100).

    Cost, distance and bends are separate Pareto dimensions. A cheap long detour
    must never discard a costlier short prefix needed to meet the frozen bounds.
    """
    queue = [(80*_distance(start, end), 0, 0, 0, start, heading, 0)]
    records, labels = [(start, None)], defaultdict(list)
    while queue:
        if budget[0] >= MAX_SEARCH_STATES:
            return None
        _, bends, steps, cost, node, direction, record = heapq.heappop(queue)
        budget[0] += 1
        if node == end:
            if bends + int(terminal != (0, 0) and direction != terminal) <= bend_limit:
                path = []
                while record is not None:
                    point, record = records[record]
                    path.append(point)
                return list(reversed(path))
            continue
        for other in sorted(adjacency.get(node, ())):
            pair = _pair(node, other)
            if pair in blocked:
                continue
            nsteps = steps+1
            ndirection = _heading(node, other)
            nbends = bends + int(direction != (0, 0) and direction != ndirection)
            if nsteps+_distance(other, end) > limit or nbends > bend_limit:
                continue
            ncost = cost+(80 if pair in preferred else 100)
            key = other, ndirection
            old = labels[key]
            value = ncost, nsteps, nbends
            if any(all(a <= b for a, b in zip(label, value)) for label in old):
                continue
            labels[key] = [label for label in old if not all(a <= b for a, b in zip(value, label))] + [value]
            if len(records) >= MAX_SEARCH_LABELS:
                budget[1] += 1
                return None
            records.append((other, record))
            heapq.heappush(queue, (ncost+80*_distance(other, end), nbends, nsteps, ncost,
                                   other, ndirection, len(records)-1))
    return None


def consolidate_routes(routing, *, merge_junctions=False, avenues=False):
    """Return independent routing; never move buildings, add pavement or lose routes."""
    if routing['version'] != 'visual-access/0.2' or routing['status'] != 'COMPLETE':
        raise ValueError('consolidation requires complete visual-access/0.2 routing')
    if avenues and not merge_junctions:
        raise ValueError('avenue pass requires junction consolidation first')
    result = copy.deepcopy(routing)
    originals = {s['id']: s for s in result['segments']}
    unit, users, paths, anchors, limits, bend_limits = {}, defaultdict(set), {}, {}, {}, {}
    route_by_id = {r['id']: r for r in result['routes']}
    step_count = 0
    for route in result['routes']:
        nodes = []
        for i, identity in enumerate(route['segmentIds']):
            segment = originals[identity]
            if segment['access']:
                continue
            a, b = _node(route['path'][i]), _node(route['path'][i+1])
            direction = _heading(a, b)
            if direction[0] and direction[1]:
                raise ValueError('non-orthogonal road segment')
            count = _distance(a, b)
            step_count += count
            if step_count > MAX_ROUTE_STEPS:
                raise ValueError('consolidation route-step limit exceeded')
            expanded = [(a[0]+direction[0]*j, a[1]+direction[1]*j) for j in range(count+1)]
            if nodes and nodes[-1] != a:
                raise ValueError('non-contiguous road spine')
            nodes.extend(expanded if not nodes else expanded[1:])
            for left, right in zip(expanded, expanded[1:]):
                key = route['kind'], _pair(left, right)
                unit[key] = segment['width']
                users[key].add(route['id'])
                if len(unit) > MAX_ATOMIC_EDGES:
                    raise ValueError('consolidation road-edge limit exceeded')
        if not nodes:
            continue
        identity = route['id']
        paths[identity] = nodes
        anchors[identity] = (_heading(route['path'][0], _world(nodes[0])),
                             _heading(_world(nodes[-1]), route['path'][-1]))
        limits[identity] = max(len(nodes)-1, _distance(nodes[0], nodes[-1])*100//90)
        bend_limits[identity] = _bends(route['path']) + 2

    adjacency = defaultdict(lambda: defaultdict(set))
    for kind, (a, b) in unit:
        adjacency[kind][a].add(b)
        adjacency[kind][b].add(a)

    # Collinear strokes split at branches/ports: remove a real redundant link,
    # not a decorative stripe, without swallowing a building's access node.
    ports = {(route_by_id[r]['kind'], p) for r, nodes in paths.items() for p in (nodes[0], nodes[-1])}
    seen, candidates = set(), []
    for key in sorted(unit):
        if key in seen:
            continue
        kind, (a, b) = key
        stroke = {key}
        ends = [a, b]
        for side in (0, 1):
            previous, current = ends[1-side], ends[side]
            while len(adjacency[kind][current]) == 2 and (kind, current) not in ports:
                other = next(n for n in adjacency[kind][current] if n != previous)
                if _heading(previous, current) != _heading(current, other):
                    break
                extra = kind, _pair(current, other)
                if extra in seen or extra in stroke:
                    break
                stroke.add(extra)
                previous, current = current, other
        seen.update(stroke)
        parallel = 0
        for _, (left, right) in stroke:
            axis = 1 if left[1] == right[1] else 0
            for offset in (-2, -1, 1, 2):
                shifted = [list(left), list(right)]
                for point in shifted:
                    point[axis] += offset
                parallel += (kind, _pair(tuple(shifted[0]), tuple(shifted[1]))) in unit
        if parallel:
            affected = set().union(*(users[k] for k in stroke))
            candidates.append((len(affected), -parallel, -len(stroke), tuple(sorted(stroke))))

    removed = set()
    def remove_link(active, budget, preferred=None):
        kind = active[0][0]
        preferred_pairs = {pair for k, pair in preferred if k == kind} if preferred is not None else None
        blocked = {pair for _, pair in active}
        affected = sorted(set().union(*(users[k] for k in active)))
        replacements = {}
        for identity in affected:
            nodes = paths[identity]
            heading, terminal = anchors[identity]
            previous_label_hits = budget[1]
            args = (nodes[0], nodes[-1], adjacency[kind], blocked, limits[identity],
                    heading, terminal, bend_limits[identity], budget)
            path = _search(*args) if preferred is None else _avenue_search(*args, preferred_pairs)
            if path is None:
                reason = ('search_state_limit' if preferred is not None and budget[0] >= MAX_SEARCH_STATES else
                          'search_label_limit' if budget[1] > previous_label_hits else 'unreachable_or_detour_or_bend_limit')
                return reason
            replacements[identity] = path
        if preferred is not None:
            def hits(nodes):
                return sum((kind, _pair(a, b)) in preferred for a, b in zip(nodes, nodes[1:]))
            if sum(hits(path)-hits(paths[r]) for r, path in replacements.items()) <= 0:
                return 'no_avenue_reuse_gain'
            new_users = defaultdict(set)
            for identity, path in replacements.items():
                for a, b in zip(path, path[1:]):
                    new_users[(kind, _pair(a, b))].add(identity)
            if any(key[0] == kind and not (users[key]-replacements.keys() or new_users[key]) for key in preferred):
                return 'would_orphan_avenue'
        for identity, path in replacements.items():
            for a, b in zip(paths[identity], paths[identity][1:]):
                users[(kind, _pair(a, b))].discard(identity)
            paths[identity] = path
            for a, b in zip(path, path[1:]):
                users[(kind, _pair(a, b))].add(identity)
        orphaned = [key for key in users if key[0] == kind and not users[key] and key not in removed]
        for key in orphaned:
            a, b = key[1]
            adjacency[kind][a].discard(b)
            adjacency[kind][b].discard(a)
            removed.add(key)
        return None

    budget, attempts, accepted, rejected = [0, 0], 0, 0, defaultdict(int)
    for _, _, _, stroke in sorted(candidates):
        if attempts >= MAX_ATTEMPTS or budget[0] >= MAX_SEARCH_STATES:
            break
        active = [key for key in stroke if users.get(key)]
        if not active:
            continue
        attempts += 1
        reason = remove_link(active, budget)
        if reason:
            rejected[reason] += 1
        else:
            accepted += 1

    parallel_removed = len(removed)
    if merge_junctions:
        links = _junction_links(adjacency, ports, users)
        joint_budget, joint_attempts, joint_accepted = [0, 0], 0, 0
        joint_rejected = defaultdict(int)
        for _, _, stroke, start, end in links:
            if joint_attempts >= MAX_JUNCTION_ATTEMPTS or joint_budget[0] >= MAX_SEARCH_STATES:
                break
            kind = stroke[0][0]
            if any(key in removed for key in stroke):
                continue
            degrees = [len(adjacency[kind][point]) for point in (start, end)]
            # At least one T must disappear. A four-way becoming another T is
            # not enough; no access port can be swallowed by this pass.
            if min(degrees) < 3 or 3 not in degrees:
                continue
            joint_attempts += 1
            reason = remove_link(stroke, joint_budget)
            if reason:
                joint_rejected[reason] += 1
            else:
                joint_accepted += 1
        result['junctionConsolidation'] = dict(
            candidates=len(links), attempts=joint_attempts, accepted=joint_accepted,
            removedLatticeEdges=len(removed)-parallel_removed, searchStates=joint_budget[0],
            limitReached=joint_attempts >= MAX_JUNCTION_ATTEMPTS or joint_budget[0] >= MAX_SEARCH_STATES or joint_budget[1] > 0,
            rejected=dict(sorted(joint_rejected.items())), maxAttempts=MAX_JUNCTION_ATTEMPTS,
            maxSearchStates=MAX_SEARCH_STATES, maxSearchLabels=MAX_SEARCH_LABELS,
            maxLinkSteps=MAX_JUNCTION_LINK_STEPS, originalBoundsPreserved=True)
        if joint_budget[1]:
            result['junctionConsolidation']['searchLabelLimitHits'] = joint_budget[1]

    if avenues:
        preferred, spines = _avenue_spines(users, route_by_id)
        avenue_candidates = _avenue_candidates(adjacency, ports, users, preferred, route_by_id)
        avenue_budget, avenue_attempts, avenue_accepted = [0, 0], 0, 0
        avenue_rejected = defaultdict(int)
        before_removed = len(removed)
        reuse_before = sum(len(users[key]) for key in preferred)
        for _, _, stroke in avenue_candidates:
            if avenue_attempts >= MAX_AVENUE_ATTEMPTS or avenue_budget[0] >= MAX_SEARCH_STATES:
                break
            active = [key for key in stroke if users.get(key)]
            if not active:
                continue
            avenue_attempts += 1
            reason = remove_link(active, avenue_budget, preferred)
            if reason:
                avenue_rejected[reason] += 1
            else:
                avenue_accepted += 1
        result['avenueConsolidation'] = dict(
            version='avenue-consolidation/0.1', spines=spines, candidates=len(avenue_candidates),
            attempts=avenue_attempts, accepted=avenue_accepted, rejected=dict(sorted(avenue_rejected.items())),
            removedLatticeEdges=len(removed)-before_removed, preferredLatticeEdges=len(preferred),
            avenueRouteStepsBefore=reuse_before, avenueRouteStepsAfter=sum(len(users[key]) for key in preferred),
            searchStates=avenue_budget[0], searchLabelLimitHits=avenue_budget[1],
            maxAttempts=MAX_AVENUE_ATTEMPTS, maxSearchStates=MAX_SEARCH_STATES, maxSearchLabels=MAX_SEARCH_LABELS,
            limitReached=avenue_attempts >= MAX_AVENUE_ATTEMPTS or avenue_budget[0] >= MAX_SEARCH_STATES or avenue_budget[1] > 0,
            minimumSpineSteps=MIN_AVENUE_STEPS, originalBoundsPreserved=True)

    # Rebuild all memberships and intersections from final complete routes.
    segments = {}
    def add(kind, a, b, width, access, identity):
        if a == b:
            return None
        start, end = sorted((a, b))
        key = _id('access-segment', [kind, start, end])
        if key not in segments:
            segments[key] = dict(id=key, kind=kind, start=start, end=end,
                                 width=width, access=access, routeIds=[])
        segments[key]['routeIds'].append(identity)
        return key
    for identity, route in sorted(route_by_id.items()):
        if identity not in paths:
            for sid in route['segmentIds']:
                old = originals[sid]
                add(old['kind'], old['start'], old['end'], old['width'], old['access'], identity)
            continue
        nodes, kind = paths[identity], route['kind']
        start, end = route['path'][0], route['path'][-1]
        ids = [add(kind, start, _world(nodes[0]), .7, True, identity)]
        ids += [add(kind, _world(a), _world(b), unit[(kind, _pair(a, b))], False, identity)
                for a, b in zip(nodes, nodes[1:])]
        ids.append(add(kind, _world(nodes[-1]), end, .7, True, identity))
        points = [start, *map(_world, nodes), end]
        route.update(path=[p for i, p in enumerate(points) if i == 0 or p != points[i-1]],
                     segmentIds=[s for s in ids if s], latticeSteps=len(nodes)-1)
    result['routes'].sort(key=lambda r: (r['kind'], r['source'], r['target']))
    segments = _compact_segments(segments, result['routes'])
    result['segments'] = sorted(segments.values(), key=lambda s: s['id'])
    incidence = defaultdict(list)
    for segment in result['segments']:
        for point in (segment['start'], segment['end']):
            incidence[(segment['kind'], *point)].append(segment['id'])
    result['junctions'] = [dict(id=_id('access-junction', [kind, x, z]), kind=kind,
                                point=[x, z], segmentIds=sorted(ids))
                           for (kind, x, z), ids in sorted(incidence.items()) if len(ids) >= 3]
    result['version'] = 'visual-access/0.3'
    result['consolidation'] = dict(candidates=len(candidates), attempts=attempts, accepted=accepted,
                                 removedLatticeEdges=parallel_removed, searchStates=budget[0],
                                 limitReached=attempts >= MAX_ATTEMPTS or budget[0] >= MAX_SEARCH_STATES or budget[1] > 0,
                                 rejected=dict(sorted(rejected.items())), maxAttempts=MAX_ATTEMPTS,
                                 maxSearchStates=MAX_SEARCH_STATES, maxSearchLabels=MAX_SEARCH_LABELS,
                                 additionalBends=2)
    if budget[1]:
        result['consolidation']['searchLabelLimitHits'] = budget[1]
    return result
