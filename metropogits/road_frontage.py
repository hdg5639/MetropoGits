"""Road-first visual entrances with unchanged source geography (ADR-019)."""
from __future__ import annotations

import copy
import heapq
import math
from collections import defaultdict

from metropogits.access_routes import AccessGrid, PITCH, _heading, _pair
from metropogits.block_collectors import _expand, _geometry_score, _rebuild
from metropogits.road_consolidation import _bends, _world

MAX_CANDIDATES = 600
MAX_STATES = 1_000_000
LOCAL_RADIUS = 6  # 21 world units around the building; directory margin remains 7.
MAX_APPROACH_STEPS = 12


def _doors(grid, building):
    left, top, right, bottom = grid.boxes[building['entityId']]
    mx, mz = (left+right)/2, (top+bottom)/2
    proposals = [((math.floor(left/PITCH),round(mz/PITCH)),[left,round(mz/PITCH)*PITCH]),
                 ((math.ceil(right/PITCH),round(mz/PITCH)),[right,round(mz/PITCH)*PITCH]),
                 ((round(mx/PITCH),math.floor(top/PITCH)),[round(mx/PITCH)*PITCH,top]),
                 ((round(mx/PITCH),math.ceil(bottom/PITCH)),[round(mx/PITCH)*PITCH,bottom])]
    return [(node,door) for node,door in proposals if left <= door[0] <= right and top <= door[1] <= bottom
            and grid.clearance(door,_world(node),building['entityId']) > .36]


def _approaches(start, heading, spine, graph, old, budget):
    """Bounded heading-aware local search; every returned approach touches the collector."""
    initial = start, heading, start in spine
    queue, costs, previous, steps = [(0,initial)], {initial:0}, {initial:None}, {initial:0}
    while queue:
        if budget[0] >= MAX_STATES:
            return None
        cost,state = heapq.heappop(queue)
        if costs[state] != cost:
            continue
        budget[0] += 1
        node,direction,touched = state
        if steps[state] >= MAX_APPROACH_STEPS:
            continue
        for other in sorted(graph.get(node,())):
            toward = _heading(node,other)
            key = _pair(node,other)
            weight = 100 if key in old else 130
            if node in spine and other in spine:
                weight = 80
            weight += 30*int(direction != (0,0) and direction != toward)
            following = other,toward,touched or other in spine
            value = cost+weight
            if value < costs.get(following,math.inf):
                costs[following],previous[following],steps[following] = value,state,steps[state]+1
                heapq.heappush(queue,(value,following))
    paths = defaultdict(list)
    for state in sorted(previous):
        if not state[2]:
            continue
        cursor,run = state,[]
        while cursor is not None:
            run.append(cursor[0])
            cursor = previous[cursor]
        run.reverse()
        if len(run)-1 <= MAX_APPROACH_STEPS and len(run) == len(set(run)):
            paths[state[0]].append((costs[state],run))
    return paths


def _surface(paths, routes, doors, fixed_access=()):
    keys = {(routes[r]['kind'],_pair(a,b)) for r,p in paths.items() for a,b in zip(p,p[1:])}
    incidence, access = defaultdict(int), set(fixed_access)
    for kind,door,port in doors.values():
        if list(door) != _world(port):
            access.add((kind,*_pair(tuple(door),tuple(_world(port)))))
    length = 0
    for kind,a,b in access:
        length += abs(a[0]-b[0])+abs(a[1]-b[1])
        for point in (a,b):
            incidence[kind,tuple(v/PITCH for v in point)] += 1
    pavement,junctions,parallel = _geometry_score(keys,incidence)
    return (round(pavement*PITCH+length,6),junctions,parallel), keys


def plan_frontages(scene, original, baseline):
    """Choose the collector first, then reconnect all relations of one building atomically."""
    if (original['version'] != 'visual-access/0.2' or baseline['version'] not in ('visual-access/0.2','visual-access/0.3')
            or any(r['status'] != 'COMPLETE' for r in (original,baseline))):
        raise ValueError('frontage requires complete routing and fresh visual-access/0.2 bounds')
    originals = {r['id']:r for r in original['routes']}
    routes = {r['id']:r for r in baseline['routes']}
    def identity(r):
        return r['source'],r['target'],r['kind'],r['edgeIds'],r['networkIds']
    if originals.keys() != routes.keys() or any(identity(r) != identity(originals[k]) for k,r in routes.items()):
        raise ValueError('frontage provenance mismatch')
    if 'roadFrontage' in baseline:
        raise ValueError('frontage result cannot be fed back into another frontage pass')
    initial, _ = _expand(original)
    paths, widths = _expand(baseline)
    base_segments = {s['id']:s for s in baseline['segments']}
    fixed_access = set()
    for identity,route in routes.items():
        if identity not in paths:
            for sid in route['segmentIds']:
                segment = base_segments[sid]
                fixed_access.add((segment['kind'],*_pair(tuple(segment['start']),tuple(segment['end']))))
    template = copy.deepcopy(baseline)
    template['version'] = 'visual-access/0.3'
    templates = {r['id']:r for r in template['routes']}
    report = dict(version='road-frontage/0.1',attempts=0,accepted=[],rejected={},
                  maxCandidates=MAX_CANDIDATES,maxSearchStates=MAX_STATES,
                  localRadius=LOCAL_RADIUS*PITCH,maxApproachSteps=MAX_APPROACH_STEPS,
                  originalWorldDistanceBoundsPreserved=True)
    if not paths:
        template['roadFrontage'] = {**report,'searchStates':0,'limitReached':False}
        return template
    grid = AccessGrid(scene['buildings'])
    buildings = {b['entityId']:b for b in scene['buildings']}
    districts = {d['id']:d for d in scene['districts']}
    incident, doors, bounds, original_bends = defaultdict(set), {}, {}, {}
    protected = set()
    for identity,route in routes.items():
        for entity in (route['source'],route['target']):
            incident[entity].add(identity)
        if identity not in paths or identity not in initial:
            protected.update((route['source'],route['target']))
            continue
        for entity,index in ((route['source'],0),(route['target'],-1)):
            key = route['kind'],entity
            value = route['kind'],tuple(route['path'][index]),paths[identity][index]
            if key in doors and doors[key] != value:
                raise ValueError('inconsistent building frontage')
            doors[key] = value
        base = originals[identity]
        n = len(initial[identity])-1
        distance = sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(base['path'],base['path'][1:]))
        bounds[identity] = max(n*3//2,n+4)*PITCH + distance-n*PITCH
        original_bends[identity] = _bends(base['path'])
    demand = {e:len(set().union(*(set(routes[r]['edgeIds']) for r in ids))) for e,ids in incident.items()}
    adjacency = defaultdict(lambda:defaultdict(set))
    for identity,nodes in paths.items():
        kind = routes[identity]['kind']
        for a,b in zip(nodes,nodes[1:]):
            adjacency[kind][a].add(b)
            adjacency[kind][b].add(a)
    ports = {(kind,port) for kind,_,port in doors.values()}
    def branch_length(entity):
        lengths = []
        for kind,door,port in (doors[k] for k in doors if k[1] == entity):
            graph = adjacency[kind]
            count,previous,current = 0,None,port
            if len(graph[current]) != 1:
                continue
            while count < MAX_APPROACH_STEPS:
                following = sorted(graph[current]-({previous} if previous is not None else set()))
                if len(following) != 1:
                    break
                previous,current = current,following[0]
                count += 1
                if (kind,current) in ports or len(graph[current]) != 2:
                    break
            lengths.append(count)
        return max(lengths,default=0)
    priorities = {e:branch_length(e) for e in incident}
    budget, rejected = [0], defaultdict(int)
    # Remove the longest private approach first, then use unique-edge demand.
    # Freeze priorities before edits; never move a file to improve the score.
    for entity in sorted(incident,key=lambda e:(-priorities[e],-demand[e],e)):
        if report['attempts'] >= MAX_CANDIDATES or budget[0] >= MAX_STATES:
            break
        affected = incident[entity]
        kinds = {routes[r]['kind'] for r in affected}
        if entity in protected or len(affected) < 2 or len(kinds) != 1:
            rejected['short_or_mixed_kind_frontage'] += 1
            continue
        kind = next(iter(kinds))
        building = buildings[entity]
        district = districts[building['districtId']]
        rectangles = district.get('footprint',[district])
        left,top,right,bottom = grid.boxes[entity]
        def local(node):
            x,z = _world(node)
            return (left-LOCAL_RADIUS*PITCH <= x <= right+LOCAL_RADIUS*PITCH
                    and top-LOCAL_RADIUS*PITCH <= z <= bottom+LOCAL_RADIUS*PITCH
                    and any(r['x']-7 <= x <= r['x']+r['width']+7 and
                            r['z']-7 <= z <= r['z']+r['depth']+7 for r in rectangles))
        graph, new_widths = defaultdict(set), {}
        for x in range(math.floor(left/PITCH)-LOCAL_RADIUS,math.ceil(right/PITCH)+LOCAL_RADIUS+1):
            for z in range(math.floor(top/PITCH)-LOCAL_RADIUS,math.ceil(bottom/PITCH)+LOCAL_RADIUS+1):
                a = x,z
                if not local(a):
                    continue
                for b,clearance in grid.neighbors(a):
                    if local(b) and clearance >= .47:
                        graph[a].add(b)
                        new_widths[kind,_pair(a,b)] = round(min(5.5,2*(clearance-.12)),4)
        before_score, before_keys = _surface(paths,routes,doors,fixed_access)
        old = {pair for k,pair in before_keys if k == kind}
        # Freeze currently used straight local collector runs before choosing a door.
        links = defaultdict(set)
        users = defaultdict(set)
        for identity,nodes in paths.items():
            if routes[identity]['kind'] != kind:
                continue
            for a,b in zip(nodes,nodes[1:]):
                if b not in graph.get(a,()):
                    continue
                key = _pair(a,b)
                users[key].update(routes[identity]['edgeIds'])
                axis = 0 if a[1] == b[1] else 1
                links[axis,a[1-axis]].add(min(a[axis],b[axis]))
        spines = []
        for (axis,offset),steps in sorted(links.items()):
            ordered = sorted(steps)
            runs = []
            for value in ordered:
                if not runs or value != runs[-1][-1]+1:
                    runs.append([])
                runs[-1].append(value)
            for run in runs:
                if len(run) < 2:
                    continue
                nodes = [(v,offset) if axis == 0 else (offset,v) for v in range(run[0],run[-1]+2)]
                edges = set().union(*(users[_pair(a,b)] for a,b in zip(nodes,nodes[1:])))
                if len(edges) >= 4:
                    spines.append((-len(edges),-len(run),tuple(nodes)))
        current = doors[kind,entity]
        options = []
        for node,door in _doors(grid,building):
            if (tuple(door),node) == current[1:] or node not in graph:
                continue
            nearby = [(d,n,p) for d,n,p in spines if min(abs(node[0]-a[0])+abs(node[1]-a[1]) for a in p) <= 4]
            for rank in sorted(nearby)[:2]:
                options.append((*rank,node,tuple(door)))
        best = None
        for rank,negative_length,spine,node,door in sorted(options):
            if report['attempts'] >= MAX_CANDIDATES or budget[0] >= MAX_STATES:
                break
            report['attempts'] += 1
            approach = _approaches(node,_heading(door,_world(node)),set(spine),graph,old,budget)
            if approach is None:
                rejected['search_limit'] += 1
                continue
            replacements, valid = {}, True
            for identity in sorted(affected):
                route = routes[identity]
                reverse = route['target'] == entity
                previous = paths[identity][::-1] if reverse else paths[identity]
                other_door = doors[kind,route['source'] if reverse else route['target']][1]
                choices = []
                for index,join in enumerate(previous):
                    if join not in approach:
                        continue
                    for cost,prefix in approach[join]:
                        candidate = prefix[:-1]+previous[index:]
                        if len(set(candidate)) != len(candidate):
                            continue
                        complete = [door,*map(_world,candidate),other_door]
                        complete = [p for i,p in enumerate(complete) if not i or tuple(p) != tuple(complete[i-1])]
                        length = sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(complete,complete[1:]))
                        bends = _bends(complete)
                        if length <= bounds[identity]+1e-8 and bends <= original_bends[identity]+4:
                            choices.append((cost+100*(len(previous)-index-1),length,bends,candidate))
                if not choices:
                    valid = False
                    break
                candidate = min(choices)[-1]
                replacements[identity] = candidate[::-1] if reverse else candidate
            if not valid:
                rejected['incident_route_bounds_or_connectivity'] += 1
                continue
            candidate_paths = {**paths,**replacements}
            candidate_doors = {**doors,(kind,entity):(kind,door,node)}
            score,_ = _surface(candidate_paths,routes,candidate_doors,fixed_access)
            if score[0] >= before_score[0]-1e-8 or any(score[i] > before_score[i] for i in (1,2)):
                rejected['no_geometry_gain'] += 1
                continue
            order = (*score,rank,negative_length,spine,node,door)
            if best is None or order < best[0]:
                best = order,replacements,door,node,spine,-rank
        if best:
            _,replacements,door,node,spine,edge_count = best
            paths.update(replacements)
            doors[kind,entity] = kind,door,node
            widths.update({k:v for k,v in new_widths.items() if k not in widths})
            for identity in affected:
                index = 0 if routes[identity]['source'] == entity else -1
                templates[identity]['path'][index] = list(door)
            report['accepted'].append(dict(entityId=entity,districtId=building['districtId'],kind=kind,
                oldDoor=list(current[1]),newDoor=list(door),oldPort=_world(current[2]),newPort=_world(node),
                collector=[_world(p) for p in spine],collectorUniqueEdges=edge_count,incidentRoutes=len(affected)))
    result = _rebuild(template,paths,widths)
    report.update(rejected=dict(sorted(rejected.items())),searchStates=budget[0],
                  limitReached=report['attempts'] >= MAX_CANDIDATES or budget[0] >= MAX_STATES)
    result['roadFrontage'] = report
    return result
