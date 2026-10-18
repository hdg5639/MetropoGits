"""Joint, evidence-preserving block entrances on certified pavement (ADR-019)."""
from __future__ import annotations

import heapq
import math
from collections import defaultdict

from metropogits.access_routes import AccessGrid, PITCH, _heading, _pair
from metropogits.block_collectors import _expand, _geometry_score, _rebuild
from metropogits.road_consolidation import _bends, _world

MAX_PROPOSALS = 240
MAX_STATES = 1_000_000
GROUP_RADIUS = 6
PATCH_RADIUS = 8
MAX_GROUP = 8
MAX_DISTRICTS = 256
MAX_PATCHES = 480


def _length(points):
    return sum(abs(a[0]-b[0])+abs(a[1]-b[1]) for a,b in zip(points,points[1:]))


def _fan(graph, root, heading, budget, old=None):
    """A bounded heading-aware fan; immutable paths avoid stale predecessor chains."""
    queue = [(0,root,heading,(root,))]
    costs = {(root,heading):0}
    result = defaultdict(list)
    while queue:
        if budget[0] >= MAX_STATES:
            return None
        cost,node,direction,path = heapq.heappop(queue)
        if costs[node,direction] != cost:
            continue
        budget[0] += 1
        result[node].append((cost,path))
        for other in sorted(graph.get(node,())):
            toward = _heading(node,other)
            value = cost+(100 if old is None or _pair(node,other) in old else 130)+200*int(toward != direction)
            if other not in path and value < costs.get((other,toward),float('inf')):
                costs[other,toward] = value
                heapq.heappush(queue,(value,other,toward,(*path,other)))
    return result


def _groups(crossings, demand):
    """Nearby, equally outward-facing boundary links; never join network kinds."""
    seen = set()
    for seed in sorted(crossings,key=lambda e:(-demand[e],e)):
        normal = _heading(*seed)
        neighbors = sorted((e for e in crossings if _heading(*e) == normal
                            and _length([seed[0],e[0]]) <= GROUP_RADIUS),
                           key=lambda e:(_length([seed[0],e[0]]),-demand[e],e))[:MAX_GROUP]
        for choice in ([neighbors] if len(neighbors) <= 3 else [neighbors[:3]]) + [[seed,e] for e in neighbors if e != seed]:
            key = tuple(sorted(choice))
            if len(key) >= 2 and key not in seen:
                seen.add(key)
                yield key


def plan_gateways(scene, original, baseline):
    """Pool nearby boundary crossings; necessary old cross-links remain intact."""
    if original['version'] != 'visual-access/0.2' or any(r['status'] != 'COMPLETE' for r in (original,baseline)):
        raise ValueError('gateways require complete routing and original visual-access/0.2 bounds')
    if baseline['version'] not in ('visual-access/0.2','visual-access/0.3') or 'blockGateways' in baseline:
        raise ValueError('invalid or repeated gateway baseline')
    def identity(routing):
        return {r['id']:(r['source'],r['target'],r['kind'],r['edgeIds'],r['networkIds']) for r in routing['routes']}
    if identity(original) != identity(baseline):
        raise ValueError('gateway provenance mismatch')
    paths,widths = _expand(baseline)
    initial,_ = _expand(original)
    routes = {r['id']:r for r in baseline['routes']}
    originals = {r['id']:r for r in original['routes']}
    bounds = {}
    for rid,nodes in paths.items():
        n = len(initial[rid])-1
        bounds[rid] = max(n*3//2,n+4)*PITCH+_length(originals[rid]['path'])-n*PITCH
    incidence = defaultdict(int)
    fixed = set()
    for segment in baseline['segments']:
        if segment['access']:
            for point in (segment['start'],segment['end']):
                incidence[segment['kind'],tuple(v/PITCH for v in point)] += 1
        elif all(rid not in paths for rid in segment['routeIds']):
            fixed.add((segment['kind'],_pair(*(tuple(v/PITCH for v in p) for p in (segment['start'],segment['end'])))))
    route_keys = {rid:{(routes[rid]['kind'],_pair(a,b)) for a,b in zip(p,p[1:])} for rid,p in paths.items()}
    keys = fixed.union(*(route_keys.values()))
    districts = {d['id']:d for d in scene['districts']}
    grid = AccessGrid(scene['buildings'])
    members = defaultdict(set)
    for building in scene['buildings']:
        key,seen = building['districtId'],set()
        while key in districts and key not in seen:
            seen.add(key)
            members[key].add(building['entityId'])
            key = districts[key].get('parentId')
    report = dict(version='block-gateways/0.1',attempts=0,accepted=[],rejected={},
                  maxProposals=MAX_PROPOSALS,maxSearchStates=MAX_STATES,
                  groupRadius=GROUP_RADIUS*PITCH,patchRadius=PATCH_RADIUS*PITCH,
                  maxGroup=MAX_GROUP,maxDistricts=MAX_DISTRICTS,maxPatches=MAX_PATCHES,
                  patches=0,originalWorldDistanceBoundsPreserved=True)
    budget,rejected,seen_groups = [0],defaultdict(int),set()
    candidates = sorted((len(m),k) for k,m in members.items() if 4 <= len(m) <= 96)
    for _,district_id in candidates[:MAX_DISTRICTS]:
        if report['attempts'] >= MAX_PROPOSALS or budget[0] >= MAX_STATES or report['patches'] >= MAX_PATCHES:
            break
        district = districts[district_id]
        rectangles = district.get('footprint',[district])
        def inside(node):
            x,z = _world(node)
            return any(r['x'] <= x <= r['x']+r['width'] and r['z'] <= z <= r['z']+r['depth'] for r in rectangles)
        for kind in sorted({r['kind'] for r in routes.values()}):
            users = defaultdict(set)
            for rid,edges in route_keys.items():
                for k,e in edges:
                    if k == kind:
                        users[e].add(rid)
            crossings = []
            for a,b in sorted(users):
                if inside(a) != inside(b):
                    crossings.append((a,b) if inside(a) else (b,a))
            demand = {e:len(set().union(*(set(routes[r]['edgeIds']) for r in users[_pair(*e)]))) for e in crossings}
            for group in _groups(crossings,demand):
                if report['attempts'] >= MAX_PROPOSALS or budget[0] >= MAX_STATES or report['patches'] >= MAX_PATCHES:
                    break
                active = [e for e in group if (kind,_pair(*e)) in keys]
                if len(active) < 2:
                    continue
                signature = (kind,group,tuple(sorted((r['x'],r['z'],r['width'],r['depth']) for r in rectangles)))
                if signature in seen_groups:
                    continue
                seen_groups.add(signature)
                report['patches'] += 1
                # Common patch, independent of the chosen gateway; spans outside stay fixed.
                cx = (min(a[0] for a,b in active)+max(a[0] for a,b in active))/2
                cz = (min(a[1] for a,b in active)+max(a[1] for a,b in active))/2
                def local(n):
                    return abs(n[0]-cx) <= PATCH_RADIUS and abs(n[1]-cz) <= PATCH_RADIUS
                side_graphs = (defaultdict(set),defaultdict(set))
                local_widths = {}
                for k,(a,b) in sorted(keys):
                    if k == kind and local(a) and local(b) and inside(a) == inside(b):
                        graph = side_graphs[int(inside(a))]
                        graph[a].add(b)
                        graph[b].add(a)
                for x in range(math.ceil(cx-PATCH_RADIUS),math.floor(cx+PATCH_RADIUS)+1):
                    for z in range(math.ceil(cz-PATCH_RADIUS),math.floor(cz+PATCH_RADIUS)+1):
                        a = x,z
                        for b,clearance in grid.neighbors(a):
                            midpoint = ((a[0]+b[0])/2,(a[1]+b[1])/2)
                            if local(b) and inside(a) == inside(b) == inside(midpoint) and clearance >= .47:
                                side_graphs[int(inside(a))][a].add(b)
                                local_widths[kind,_pair(a,b)] = round(min(5.5,2*(clearance-.12)),4)
                old = {e for k,e in keys if k == kind}
                crossing_keys = {(kind,_pair(*e)) for e in active}
                affected = sorted(r for r,ks in route_keys.items() if ks & crossing_keys)
                spans = {}
                for rid in affected:
                    nodes = paths[rid]
                    hits = [i for i,(a,b) in enumerate(zip(nodes,nodes[1:])) if (kind,_pair(a,b)) in crossing_keys]
                    left,right = min(hits),max(hits)+1
                    while left > 0 and local(nodes[left-1]):
                        left -= 1
                    while right+1 < len(nodes) and local(nodes[right+1]):
                        right += 1
                    if all(local(n) for n in nodes[left:right+1]) and inside(nodes[left]) != inside(nodes[right]):
                        spans[rid] = left,right
                before_score = _geometry_score(keys,incidence)
                best = None
                for gate in sorted(active,key=lambda e:(-demand[e],e))[:3]:
                    if report['attempts'] >= MAX_PROPOSALS or budget[0] >= MAX_STATES:
                        break
                    a,b = gate  # inside -> outside
                    inner = _fan(side_graphs[1],a,_heading(b,a),budget,old)
                    outer = _fan(side_graphs[0],b,_heading(a,b),budget,old)
                    if inner is None or outer is None:
                        rejected['search_limit'] += 1
                        break
                    if not any(e != gate and e[0] in inner and e[1] in outer for e in active):
                        rejected['disconnected_gateway_sides'] += 1
                        continue
                    report['attempts'] += 1
                    replacements,bend_delta = {},0
                    for rid,(left,right) in sorted(spans.items()):
                        nodes = paths[rid]
                        start,end = nodes[left],nodes[right]
                        reverse = not inside(start)
                        entry,exit = (end,start) if reverse else (start,end)
                        choices = []
                        for c1,p1 in inner.get(entry,()):
                            for c2,p2 in outer.get(exit,()):
                                run = (*reversed(p1),*p2)
                                if reverse:
                                    run = run[::-1]
                                new = [*nodes[:left],*run,*nodes[right+1:]]
                                if len(set(new)) != len(new):
                                    continue
                                complete = [routes[rid]['path'][0],*map(_world,new),routes[rid]['path'][-1]]
                                bends = _bends(complete)
                                if _length(complete) <= bounds[rid]+1e-8 and bends <= _bends(originals[rid]['path'])+4:
                                    choices.append((c1+c2,bends,len(new),new))
                        if choices:
                            _,turns,_,new = min(choices)
                            if new != nodes:
                                replacements[rid] = new
                                old_complete = [routes[rid]['path'][0],*map(_world,nodes),routes[rid]['path'][-1]]
                                bend_delta += turns-_bends(old_complete)
                    changed_keys = {r:{(kind,_pair(a,b)) for a,b in zip(p,p[1:])} for r,p in replacements.items()}
                    candidate_keys = fixed.union(*(changed_keys.get(r,ks) for r,ks in route_keys.items()))
                    removed = crossing_keys-candidate_keys
                    score = _geometry_score(candidate_keys,incidence)
                    if not removed or score[0] >= before_score[0] or any(score[i] > before_score[i] for i in (1,2)) or bend_delta > 0:
                        rejected['no_removed_crossing' if not removed else 'no_pavement_gain' if score[0] >= before_score[0]
                                 else 'more_bends' if bend_delta > 0 else 'junction_or_parallel_regression'] += 1
                        continue
                    order = (*score,bend_delta,gate)
                    if best is None or order < best[0]:
                        best = order,replacements,changed_keys,candidate_keys,removed,gate
                if best:
                    _,replacements,changed_keys,keys,removed,gate = best
                    paths.update(replacements)
                    route_keys.update(changed_keys)
                    widths.update({k:v for k,v in local_widths.items() if k not in widths})
                    report['accepted'].append(dict(districtId=district_id,kind=kind,
                        gateway=[_world(n) for n in gate],crossingsBefore=len(active),
                        crossingsAfter=len(active)-len(removed),changedRoutes=len(replacements),
                        retainedRoutes=len(affected)-len(replacements),
                        removedCrossings=[[_world(n) for n in edge] for k,edge in sorted(removed)]))
    result = _rebuild(baseline,paths,widths)
    result['version'] = 'visual-access/0.3'
    report.update(rejected=dict(sorted(rejected.items())),searchStates=budget[0],
                  limitReached=report['attempts'] >= MAX_PROPOSALS or budget[0] >= MAX_STATES
                  or report['patches'] >= MAX_PATCHES or len(candidates) > MAX_DISTRICTS)
    result['blockGateways'] = report
    return result
