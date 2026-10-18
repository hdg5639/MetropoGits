"""Experimental geography-first infrastructure and evidenced trips (ADR-020)."""
from __future__ import annotations

import copy
import math
from collections import Counter, defaultdict, deque

from metropogits.access_routes import AccessGrid, PITCH, _heading, _id, _pair
from metropogits.block_collectors import _expand, _rebuild
from metropogits.road_consolidation import _bends, _world
from metropogits.road_frontage import _doors
from metropogits.shared_frontage import _compress, _length, _search

MAX_CELLS = 250_000
MAX_STEPS = 2_000_000
MAX_BUILDINGS = 10_000
MAX_ROUTES = 20_000
MAX_ROUTE_STATES = 3_000_000
MAX_SEED_STEPS = 500_000
BLOCK_FILES = 64
STREET_SPACING = 8  # lattice steps =28 world units


def _blocks(scene):
    children, files = defaultdict(list), defaultdict(list)
    districts = {d['id']: d for d in scene['districts']}
    for d in scene['districts']:
        children[d['parentId']].append(d['id'])
    for b in scene['buildings']:
        files[b['districtId']].append(b)
    # Iterative hierarchy traversal: hostile depth must not consume Python stack.
    order, pending = [], sorted(children[None], reverse=True)
    while pending:
        d = pending.pop()
        order.append(d)
        pending.extend(sorted(children[d], reverse=True))
        if len(order) > len(districts):
            raise ValueError('cyclic street hierarchy')
    if len(order) != len(districts):
        raise ValueError('disconnected street hierarchy')
    counts = {d: len(files[d]) for d in order}
    for d in reversed(order):
        counts[d] += sum(counts[c] for c in children[d])
    result, pending = [], sorted(children[None], reverse=True)
    while pending:
        d = pending.pop()
        if counts[d] <= BLOCK_FILES:
            members, todo = [], [d]
            while todo:
                node = todo.pop()
                members.extend(files[node])
                todo.extend(children[node])
            if members:
                result.append((d, members))
        else:
            if files[d]:
                result.append((d, files[d]))
            pending.extend(sorted(children[d], reverse=True))
    return result


def _adjacency(keys):
    graph = defaultdict(set)
    for a, b in keys:
        graph[a].add(b)
        graph[b].add(a)
    return graph


def _components(graph):
    unseen, components = set(graph), []
    while unseen:
        first = min(unseen)
        group, todo = {first}, [first]
        unseen.remove(first)
        while todo:
            for n in sorted(graph[todo.pop()]):
                if n in unseen:
                    unseen.remove(n)
                    group.add(n)
                    todo.append(n)
        components.append(group)
    return sorted(components, key=lambda c: (-len(c), min(c)))


def _connect(grid, starts, targets, budget, max_distance=None):
    queue = deque(sorted(set(starts)))
    previous = {n: None for n in queue}
    depth = dict.fromkeys(queue, 0)
    while queue:
        if budget[0] >= MAX_STEPS:
            return None
        n = queue.popleft()
        budget[0] += 1
        if n in targets:
            path = []
            while n is not None:
                path.append(n)
                n = previous[n]
            return path[::-1]
        if max_distance is not None and depth[n] >= max_distance:
            continue
        for other, clearance in grid.neighbors(n):
            if clearance >= .47 and other not in previous:
                previous[other], depth[other] = n, depth[n]+1
                queue.append(other)
    return None


def build_streets(scene):
    """No UCG or network input is read. All streets are explicitly non-semantic."""
    result = dict(version='structural-streets/0.1', semantic=False,
                  basis='directory-and-building-geography', segments=[], entrances=[],
                  blocks=[], diagnostics=[], status='COMPLETE', searchStates=0)
    buildings = scene['buildings']
    if not buildings:
        return result
    if len(buildings) > MAX_BUILDINGS:
        raise ValueError('structural street building limit')
    grid = AccessGrid(buildings)
    x0, z0, x1, z1 = grid.bounds
    if (x1-x0+1)*(z1-z0+1) > MAX_CELLS:
        raise ValueError('structural street area limit')
    keys, owners = set(), defaultdict(set)
    seed_steps = 0
    def add(a, b, district):
        nonlocal seed_steps
        seed_steps += 1
        if seed_steps > MAX_SEED_STEPS:
            raise ValueError('structural street seed limit')
        clearance = grid.clearance(_world(a), _world(b))
        if clearance >= .47:
            key = _pair(a, b)
            keys.add(key)
            owners[key].add(district)
    for district, members in _blocks(scene):
        lo_x = math.floor(min(b['x'] for b in members)/PITCH)-1
        lo_z = math.floor(min(b['z'] for b in members)/PITCH)-1
        hi_x = math.ceil(max(b['x']+b['width'] for b in members)/PITCH)+1
        hi_z = math.ceil(max(b['z']+b['depth'] for b in members)/PITCH)+1
        result['blocks'].append(dict(districtId=district, fileCount=len(members)))
        for z in sorted({lo_z, hi_z, *range(lo_z+STREET_SPACING, hi_z, STREET_SPACING)}):
            for x in range(lo_x, hi_x):
                add((x, z), (x+1, z), district)
        for x in sorted({lo_x, hi_x, *range(lo_x+STREET_SPACING, hi_x, STREET_SPACING)}):
            for z in range(lo_z, hi_z):
                add((x, z), (x, z+1), district)
    budget = [0]
    # Infrastructure components are joined before any logical trips are known.
    while keys:
        groups = _components(_adjacency(keys))
        if len(groups) <= 1:
            break
        target = set().union(*groups[1:])
        path = _connect(grid, groups[0], target, budget)
        if path is None:
            result['diagnostics'].append('Disconnected structural components or search cap')
            break
        keys.update(_pair(a, b) for a, b in zip(path, path[1:]))
    nodes = set().union(*(set(p) for p in keys)) if keys else set()
    for building in sorted(buildings, key=lambda b: b['entityId']):
        options = dict(_doors(grid, building))
        path = _connect(grid, options, nodes, budget) if options and nodes else None
        if path is None:
            result['diagnostics'].append('No structural access: '+building['entityId'])
            continue
        keys.update(_pair(a, b) for a, b in zip(path, path[1:]))
        nodes.update(path)
        result['entrances'].append(dict(entityId=building['entityId'], door=options[path[0]],
                                        port=list(path[0])))
    # Compact only straight runs with equal safe width and hierarchy provenance.
    groups = defaultdict(list)
    for a, b in sorted(keys):
        width = round(min(3.5, 2*(grid.clearance(_world(a), _world(b))-.12)), 4)
        horizontal = a[1] == b[1]
        groups[horizontal, a[1] if horizontal else a[0], width, tuple(sorted(owners[a, b]))].append(
            (a[0], b[0]) if horizontal else (a[1], b[1]))
    for (horizontal, fixed, width, districts), intervals in sorted(groups.items()):
        runs = []
        for a, b in sorted(intervals):
            if runs and runs[-1][1] == a:
                runs[-1][1] = b
            else:
                runs.append([a, b])
        for a, b in runs:
            start, end = ([a, fixed], [b, fixed]) if horizontal else ([fixed, a], [fixed, b])
            result['segments'].append(dict(id=_id('civic-street', [start, end]), start=_world(start),
                end=_world(end), width=width, districtIds=list(districts), semantic=False))
    by_entity = {b['entityId']: b for b in buildings}
    for entrance in result['entrances']:
        door, port = entrance['door'], _world(entrance['port'])
        if door == port:
            continue
        entity = entrance['entityId']
        width = min(.7, 2*(grid.clearance(door, port, entity)-.12))
        result['segments'].append(dict(id=_id('civic-entrance', [entity]), start=door,
            end=port, width=width, districtIds=[by_entity[entity]['districtId']],
            semantic=False, entrance=True))
    result['segments'].sort(key=lambda s: s['id'])
    result['searchStates'] = budget[0]
    result['componentCount'] = len(_components(_adjacency(keys)))
    result['status'] = 'PARTIAL' if result['diagnostics'] else 'COMPLETE'
    return result


def assign_streets(scene, original):
    if original['version'] != 'visual-access/0.2' or original['status'] != 'COMPLETE':
        raise ValueError('street assignment requires complete original0.2 routing')
    if len(original['routes']) > MAX_ROUTES:
        raise ValueError('street assignment route limit')
    streets = build_streets(scene)
    paths, widths = _expand(original)
    template = copy.deepcopy(original)
    template['version'] = 'visual-access/0.3'
    report = dict(assignedRouteIds=[], fallbackRouteIds=[], connectorSteps=4,
                  maxSearchStates=MAX_ROUTE_STATES, originalBoundsPreserved=True)
    template['streetGrid'] = {**streets, 'assignment': report}
    if not paths or not streets['segments']:
        report['fallbackRouteIds'] = sorted(r['id'] for r in original['routes'])
        return template
    grid = AccessGrid(scene['buildings'])
    keys = set()
    for s in streets['segments']:
        if s.get('entrance'):
            continue
        a, b = (tuple(round(v/PITCH) for v in s[k]) for k in ('start', 'end'))
        d = _heading(a, b)
        for i in range(abs(b[0]-a[0])+abs(b[1]-a[1])):
            p = a[0]+i*d[0], a[1]+i*d[1]
            q = p[0]+d[0], p[1]+d[1]
            keys.add(_pair(p, q))
    street_nodes = set().union(*(set(p) for p in keys))
    ports = {p[i] for p in paths.values() for i in (0, -1)}
    connector_budget = [0]
    for p in sorted(ports):
        path = _connect(grid, [p], street_nodes, connector_budget, max_distance=4)
        if path:
            keys.update(_pair(a, b) for a, b in zip(path, path[1:]))
    graph = _compress(_adjacency(keys), ports)
    usage, budget = Counter(dict.fromkeys(keys, 1)), [0, 0]
    for route in sorted(original['routes'], key=lambda r: r['id']):
        rid, kind = route['id'], route['kind']
        if rid not in paths:
            report['fallbackRouteIds'].append(rid)
            continue
        p = paths[rid]
        n = route['latticeSteps']
        candidate = _search(graph, p[0], p[-1], usage, max(n*3//2, n+4),
            _bends(route['path'])+4, _heading(route['path'][0], _world(p[0])),
            _heading(_world(p[-1]), route['path'][-1]), budget, state_limit=MAX_ROUTE_STATES)
        if candidate is None:
            report['fallbackRouteIds'].append(rid)
            continue
        paths[rid] = candidate
        report['assignedRouteIds'].append(rid)
        for a, b in zip(candidate, candidate[1:]):
            widths[kind, _pair(a, b)] = round(min(3.5, 2*(grid.clearance(_world(a), _world(b))-.12)), 4)
    result = _rebuild(template, paths, widths)
    result['streetGrid']['assignment'].update(searchStates=budget[0], cappedSearches=budget[1],
        connectorSearchStates=connector_budget[0], beforeLength=sum(_length(r['path']) for r in original['routes']),
        afterLength=sum(_length(r['path']) for r in result['routes']))
    return result


def street_rectangles(routing):
    """One unpainted infrastructure surface; no fabricated network membership."""
    result = []
    for segment in routing['streetGrid']['segments']:
        a, b, half = segment['start'], segment['end'], segment['width']/2
        horizontal = a[1] == b[1]
        x = min(a[0], b[0])-(0 if horizontal else half)
        z = min(a[1], b[1])-(half if horizontal else 0)
        result.append(dict(id=segment['id'], x=x, z=z,
            width=abs(b[0]-a[0])+(0 if horizontal else 2*half),
            depth=abs(b[1]-a[1])+(2*half if horizontal else 0),
            color='#43515d', elevation=.10, semantic=False))
    return result
