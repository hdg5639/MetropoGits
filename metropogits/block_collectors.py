"""Opt-in obstacle-checked block collector trees; no new logical edges (ADR-019)."""
from __future__ import annotations

import copy
import heapq
import math
from collections import defaultdict, deque

from metropogits.access_routes import AccessGrid, PITCH, _compact_segments, _id, _pair
from metropogits.road_consolidation import _bends, _heading, _node, _world

MAX_BLOCKS = 160
MAX_BLOCK_NODES = 4096
MAX_TERMINALS = 96
MAX_STATES = 2_000_000
MAX_STEPS = 1_000_000


def _expand(routing):
    segments = {s['id']: s for s in routing['segments']}
    paths, widths = {}, {}
    total = 0
    for route in routing['routes']:
        points = []
        for i, identity in enumerate(route['segmentIds']):
            segment = segments[identity]
            if segment['access']:
                continue
            a, b = _node(route['path'][i]), _node(route['path'][i+1])
            direction = _heading(a, b)
            if direction[0] and direction[1]:
                raise ValueError('non-orthogonal collector input')
            n = abs(b[0]-a[0])+abs(b[1]-a[1])
            total += n
            if total > MAX_STEPS:
                raise ValueError('collector route-step limit')
            run = [(a[0]+direction[0]*j, a[1]+direction[1]*j) for j in range(n+1)]
            if points and points[-1] != a:
                raise ValueError('non-contiguous collector input')
            points.extend(run if not points else run[1:])
            for x, y in zip(run, run[1:]):
                widths[route['kind'], _pair(x, y)] = segment['width']
        if points:
            paths[route['id']] = points
    return paths, widths


def _tree(graph, terminals, root, old, budget):
    """Grow a connected tree toward demand terminals, reusing its existing trunk."""
    tree = defaultdict(set)
    tree[root]  # even a single-node tree is a valid attachment target
    for terminal in terminals:
        if terminal in tree:
            continue
        queue, distances, previous = [(0, terminal)], {terminal: 0}, {terminal: None}
        hit = None
        while queue:
            if budget[0] >= MAX_STATES:
                return None
            cost, node = heapq.heappop(queue)
            if distances[node] != cost:
                continue
            budget[0] += 1
            if node in tree:
                hit = node
                break
            for other in sorted(graph[node]):
                candidate = cost + (100 if _pair(node, other) in old else 120)
                if candidate < distances.get(other, math.inf):
                    distances[other], previous[other] = candidate, node
                    heapq.heappush(queue, (candidate, other))
        if hit is None:
            return None
        while previous[hit] is not None:
            other = previous[hit]
            tree[hit].add(other)
            tree[other].add(hit)
            hit = other
    return tree


def _tree_path(tree, start, end):
    queue, previous = deque([start]), {start: None}
    while queue:
        node = queue.popleft()
        if node == end:
            path = []
            while node is not None:
                path.append(node)
                node = previous[node]
            return path[::-1]
        for other in sorted(tree[node]):
            if other not in previous:
                previous[other] = node
                queue.append(other)
    return None


def _geometry_score(keys, access_incidence):
    """Exact unit-lattice pavement/parallel counts without rebuilding all routes."""
    degrees = defaultdict(int, access_incidence)
    parallel = 0
    for kind, (a, b) in keys:
        degrees[kind, a] += 1
        degrees[kind, b] += 1
        axis = 1 if a[1] == b[1] else 0
        for offset in (1, 2):
            x, y = list(a), list(b)
            x[axis] += offset
            y[axis] += offset
            parallel += (kind, _pair(tuple(x), tuple(y))) in keys
    return len(keys), sum(n >= 3 for n in degrees.values()), parallel


def _rebuild(base, paths, widths):
    result, segments = copy.deepcopy(base), {}
    original = {s['id']: s for s in base['segments']}
    def add(kind, a, b, width, access, route_id):
        if a == b:
            return None
        start, end = sorted((a, b))
        key = _id('access-segment', [kind, start, end])
        if key not in segments:
            segments[key] = dict(id=key, kind=kind, start=start, end=end,
                                 width=width, access=access, routeIds=[])
        segments[key]['routeIds'].append(route_id)
        return key
    for route in result['routes']:
        identity, kind = route['id'], route['kind']
        if identity not in paths:
            ids = []
            for key in route['segmentIds']:
                s = original[key]
                ids.append(add(kind, s['start'], s['end'], s['width'], s['access'], identity))
            route['segmentIds'] = ids
            continue
        nodes = paths[identity]
        a, b = route['path'][0], route['path'][-1]
        ids = [add(kind, a, _world(nodes[0]), .7, True, identity)]
        ids += [add(kind, _world(x), _world(y), widths[kind, _pair(x, y)], False, identity)
                for x, y in zip(nodes, nodes[1:])]
        ids.append(add(kind, _world(nodes[-1]), b, .7, True, identity))
        points = [a, *map(_world, nodes), b]
        route.update(path=[p for i, p in enumerate(points) if i == 0 or p != points[i-1]],
                     segmentIds=[s for s in ids if s], latticeSteps=len(nodes)-1)
    segments = _compact_segments(segments, result['routes'])
    result['segments'] = sorted(segments.values(), key=lambda s: s['id'])
    incident = defaultdict(list)
    for segment in result['segments']:
        for point in (segment['start'], segment['end']):
            incident[segment['kind'], *point].append(segment['id'])
    result['junctions'] = [dict(id=_id('access-junction', [kind, x, z]), kind=kind,
                                point=[x, z], segmentIds=sorted(ids))
                           for (kind, x, z), ids in sorted(incident.items()) if len(ids) >= 3]
    return result


def plan_collectors(scene, original, baseline):
    """Return a separate local street plan; failed proposals preserve every old path."""
    if original['version'] != 'visual-access/0.2' or original['status'] != 'COMPLETE':
        raise ValueError('collectors require fresh complete visual-access/0.2 bounds')
    if baseline['status'] != 'COMPLETE':
        raise ValueError('collectors require complete baseline')
    def identities(routing):
        return {r['id']: tuple(str(r[k]) for k in ('kind', 'source', 'target', 'edgeIds', 'networkIds'))
                for r in routing['routes']}
    if identities(original) != identities(baseline):
        raise ValueError('collector provenance mismatch')
    initial, _ = _expand(original)
    paths, widths = _expand(baseline)
    originals = {r['id']: r for r in original['routes']}
    routes = {r['id']: r for r in baseline['routes']}
    access_incidence = defaultdict(int)
    for segment in baseline['segments']:
        if segment['access']:
            for point in (segment['start'], segment['end']):
                # Nonlattice doors cannot coincide with a through-road junction.
                node = tuple(p/PITCH for p in point)
                access_incidence[segment['kind'], node] += 1
    for identity, nodes in paths.items():
        if identity not in initial or (nodes[0], nodes[-1]) != (initial[identity][0], initial[identity][-1]):
            raise ValueError('collector baseline changed ports')
        if any(routes[identity]['path'][i] != originals[identity]['path'][i] for i in (0, -1)):
            raise ValueError('collector baseline changed doors')
    result = copy.deepcopy(baseline)
    report = dict(version='block-collectors/0.1', attempts=0, accepted=[], rejected={}, searchStates=0,
                  maxBlocks=MAX_BLOCKS, maxBlockNodes=MAX_BLOCK_NODES, maxTerminals=MAX_TERMINALS,
                  maxSearchStates=MAX_STATES, originalUrbanBoundsPreserved=True)
    rejected, budget = defaultdict(int), [0]
    if not paths:
        result['blockCollectors'] = {**report, 'limitReached': False}
        return result
    grid = AccessGrid(scene['buildings'])
    districts = {d['id']: d for d in scene['districts']}
    members = defaultdict(set)
    for building in scene['buildings']:
        key, seen = building['districtId'], set()
        while key in districts and key not in seen:
            seen.add(key)
            members[key].add(building['entityId'])
            key = districts[key].get('parentId')
    # Smaller ownership blocks first; later parent trials still use original bounds.
    candidates = sorted((len(m), key) for key, m in members.items() if 4 <= len(m) <= 64)
    for _, district_id in candidates:
        if report['attempts'] >= MAX_BLOCKS or budget[0] >= MAX_STATES:
            break
        district = districts[district_id]
        rectangles = district.get('footprint', [district])
        def inside(node):
            x, z = _world(node)
            return any(r['x'] <= x <= r['x']+r['width'] and r['z'] <= z <= r['z']+r['depth'] for r in rectangles)
        lo_x = math.ceil(min(r['x'] for r in rectangles)/PITCH)
        hi_x = math.floor(max(r['x']+r['width'] for r in rectangles)/PITCH)
        lo_z = math.ceil(min(r['z'] for r in rectangles)/PITCH)
        hi_z = math.floor(max(r['z']+r['depth'] for r in rectangles)/PITCH)
        if (hi_x-lo_x+1)*(hi_z-lo_z+1) > MAX_BLOCK_NODES:
            rejected['block_size_limit'] += 1
            continue
        local = {n for x in range(lo_x, hi_x+1) for z in range(lo_z, hi_z+1) if inside(n := (x, z))}
        graph, local_widths = defaultdict(set), {}
        for a in sorted(local):
            for b, clearance in grid.neighbors(a):
                # Midpoint check prevents bridging a notch of a polygon footprint.
                if b in local and inside(((a[0]+b[0])/2, (a[1]+b[1])/2)) and clearance >= .47:
                    graph[a].add(b)
                    local_widths[_pair(a, b)] = round(min(5.5, 2*(clearance-.12)), 4)
        for kind in sorted({r['kind'] for r in routes.values()}):
            if report['attempts'] >= MAX_BLOCKS or budget[0] >= MAX_STATES:
                break
            runs, demand, old = {}, defaultdict(set), set()
            for identity, points in paths.items():
                if routes[identity]['kind'] != kind:
                    continue
                spans, start = [], None
                for i, (a, b) in enumerate(zip(points, points[1:])):
                    eligible = a in graph and b in graph[a]
                    if eligible:
                        old.add(_pair(a, b))
                        if start is None:
                            start = i
                    elif start is not None:
                        spans.append((start, i))
                        start = None
                if start is not None:
                    spans.append((start, len(points)-1))
                if spans:
                    runs[identity] = spans
                    for a, b in spans:
                        for index in (a, b):
                            demand[points[index]].update(routes[identity]['edgeIds'])
            terminals = sorted(demand, key=lambda n: (-len(demand[n]), n))
            if not 3 <= len(terminals) <= MAX_TERMINALS:
                rejected['terminal_count'] += 1
                continue
            report['attempts'] += 1
            best = None
            route_keys = {r: {(routes[r]['kind'], _pair(a, b)) for a, b in zip(p, p[1:])}
                          for r, p in paths.items()}
            before_keys = set().union(*route_keys.values())
            before_score = _geometry_score(before_keys, access_incidence)
            external_keys = set().union(*(keys for r, keys in route_keys.items() if r not in runs))
            for root in terminals[:3]:
                tree = _tree(graph, terminals, root, old, budget)
                if tree is None:
                    rejected['unreachable_or_search_limit'] += 1
                    continue
                replacements, cache, retained = {}, {}, 0
                for identity, spans in sorted(runs.items()):
                    points, new, cursor = paths[identity], [], 0
                    for a, b in spans:
                        key = _pair(points[a], points[b])
                        if key not in cache:
                            cache[key] = _tree_path(tree, *key)
                        run = cache[key]
                        if points[a] != key[0]:
                            run = run[::-1]
                        new.extend(points[cursor:a])
                        new.extend(run[:-1])
                        cursor = b
                    new.extend(points[cursor:])
                    initial_steps = len(initial[identity])-1
                    complete = [routes[identity]['path'][0], *map(_world, new), routes[identity]['path'][-1]]
                    complete = [p for i, p in enumerate(complete) if not i or p != complete[i-1]]
                    if (len(set(new)) != len(new) or len(new)-1 > max(initial_steps*3//2, initial_steps+4)
                            or _bends(complete) > _bends(originals[identity]['path'])+4):
                        retained += 1
                        continue
                    replacements[identity] = new
                if not replacements:
                    rejected['all_routes_need_crosslinks'] += 1
                    continue
                candidate_keys = set(external_keys)
                for identity in runs:
                    nodes = replacements.get(identity, paths[identity])
                    candidate_keys.update((kind, _pair(a, b)) for a, b in zip(nodes, nodes[1:]))
                geometry = _geometry_score(candidate_keys, access_incidence)
                if geometry[0] >= before_score[0] or any(geometry[i] > before_score[i] for i in (1, 2)):
                    rejected['no_global_geometry_gain'] += 1
                    continue
                score = (*geometry, root)
                if best is None or score < best[0]:
                    best = score, replacements, root, retained
            if best:
                _, replacements, root, retained = best
                paths.update(replacements)
                widths.update({(kind, k): v for k, v in local_widths.items() if (kind, k) not in widths})
                report['accepted'].append(dict(districtId=district_id, kind=kind, root=_world(root),
                                                terminals=len(terminals), affectedRoutes=len(runs), retainedCrosslinkRoutes=retained))
    result = _rebuild(baseline, paths, widths)
    report.update(rejected=dict(sorted(rejected.items())), searchStates=budget[0],
                  limitReached=budget[0] >= MAX_STATES or report['attempts'] >= MAX_BLOCKS)
    result['blockCollectors'] = report
    return result
