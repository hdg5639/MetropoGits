"""Bounded three-arm reconstruction on top of the ADR-021 diagonal baseline."""
from collections import Counter, defaultdict
import math

from metropogits.street_diagonals import (
    arrangement, plan_diagonals, pair, ribbon, tapered_ribbon, hull, bounds,
    buckets, overlap,
)

MAX_CHECKS = 5_000_000
MAX_PROPOSALS = 20_000


def chain_record(path, center, edges):
    distances = [0.0]
    for a, b in zip(path, path[1:]):
        distances.append(distances[-1]+math.dist(a, b))
    old, new = distances[-1], math.dist(center, path[-1])
    keys = [pair(a, b) for a, b in zip(path, path[1:])]
    width = max(edges[k]['width'] for k in keys)
    transition = min(new/3, max(6, width*3))
    stations = [0, transition/new, 1-transition/new, 1]
    widths = [edges[keys[0]]['width'], width, width, edges[keys[-1]]['width']]
    def at(t):
        return [center[j]+(path[-1][j]-center[j])*t for j in (0, 1)]
    centers = [at(t) for t in stations]
    strips = [tapered_ribbon(a, b, w0, w1) for a,b,w0,w1 in zip(centers, centers[1:], widths, widths[1:])]
    physical = [at(d/old) for d in distances]
    physical[0], physical[-1] = list(center), list(path[-1])
    return dict(path=[list(p) for p in path], physical=physical, width=width,
                polygon=hull([p for strip in strips for p in strip]), joins=[],
                beforeLength=old, afterLength=new, widthStations=stations, widths=widths)


def plan_junctions(scene, routing):
    base = plan_diagonals(scene, routing)
    edges, adjacency = arrangement(routing['streetGrid']['segments']+routing['segments'])
    pins = {tuple(p) for r in routing['routes'] for p in (r['path'][0], r['path'][-1])}
    pins.update(tuple(s[k]) for s in routing['streetGrid']['segments'] if s.get('entrance') for k in ('start', 'end'))
    terminals = {p for p, ns in adjacency.items() if len(ns) != 2} | pins
    baseline = list(base['chains'])
    base_keys = {id(c): {pair(a,b) for a,b in zip(c['path'],c['path'][1:])} for c in baseline}
    arm_baselines = {frozenset(base_keys[id(c)]):c['afterLength'] for c in baseline}
    locked = set()
    removed = {pair(a, b) for c in base['chains'] for a,b in zip(c['path'], c['path'][1:])}
    candidates = []
    for center in sorted(terminals-pins):
        if len(adjacency[center]) != 3 or center in locked:
            continue
        paths = []
        for neighbor in sorted(adjacency[center]):
            path = [center, neighbor]
            while path[-1] not in terminals:
                path.append(next(iter(adjacency[path[-1]]-{path[-2]})))
            paths.append(path)
        if len({p[-1] for p in paths}) != 3 or any(p[-1] == center for p in paths):
            continue
        keys = {pair(a,b) for p in paths for a,b in zip(p,p[1:])}
        if any(p in locked for path in paths for p in path):
            continue
        if any(not edges[k]['structural'] or edges[k]['blocked'] for k in keys):
            continue
        lengths = [sum(math.dist(a,b) for a,b in zip(p,p[1:])) for p in paths]
        for i, path in enumerate(paths):
            arm = frozenset(pair(a,b) for a,b in zip(path,path[1:]))
            lengths[i] = arm_baselines.get(arm,lengths[i])
        if not all(7 <= length <= 140 for length in lengths):
            continue
        total = sum(lengths)
        endpoints = [p[-1] for p in paths]
        centroid = [sum(p[j] for p in endpoints)/3 for j in (0, 1)]
        options = {center}
        distance = math.dist(centroid, center)
        for fraction in (.25, .5, 1):
            t = min(1, 14/max(distance, 1e-9))*fraction
            options.add(tuple(round(center[j]+(centroid[j]-center[j])*t, 8) for j in (0, 1)))
        for target in sorted(options):
            new = [math.dist(target, p) for p in endpoints]
            if sum(new) > total*.95 or any(n < 5 or n > old+1e-8 for n,old in zip(new,lengths)):
                continue
            directions = [[(p[j]-target[j])/n for j in (0, 1)] for p,n in zip(endpoints,new)]
            if any(sum(a[j]*b[j] for j in (0, 1)) > .819152 for i,a in enumerate(directions) for b in directions[i+1:]):
                continue  # minimum35 degrees, no near-parallel mouths
            candidates.append((total-sum(new), center, target, paths, keys))
            if len(candidates) > MAX_PROPOSALS:
                raise ValueError('junction proposal limit')
    index, operations = defaultdict(set), 0
    for key, edge in edges.items():
        for bucket in buckets(bounds(list(key)), edge['collisionWidth']/2+4):
            index[bucket].add(key)
            operations += 1
            if operations > MAX_CHECKS:
                raise ValueError('junction spatial index limit')
    buildings = [[[b['x'],b['z']], [b['x']+b['width'],b['z']],
                  [b['x']+b['width'],b['z']+b['depth']], [b['x'],b['z']+b['depth']]] for b in scene['buildings']]
    accepted, rejected, additions = [], Counter(), []
    for _, center, target, paths, keys in sorted(candidates, key=lambda c: (-c[0], c[1], c[2])):
        if any(p in locked for path in paths for p in path):
            rejected['reserved'] += 1
            continue
        chains = [chain_record(p, target, edges) for p in paths]
        central = hull([v for c in chains for v in ribbon(target, c['path'][-1], c['widths'][0])[:2]])
        chains[0]['joins'].append(central)
        for chain, path in zip(chains, paths):
            terminal = path[-1]
            points = []
            for other in sorted(adjacency[terminal]):
                width = edges[pair(terminal,other)]['collisionWidth']
                direction = target if other == path[-2] else other
                if other == path[-2]:
                    width = chain['widths'][-1]
                points.extend(ribbon(terminal, direction, width)[:2])
            mouth = hull(points)
            if len(mouth) >= 3:
                chain['joins'].append(mouth)
        tagged = [(p, set() if p is central else {tuple(c['path'][-1])})
                  for c in chains for p in [c['polygon'], *c['joins']]]
        polygons = [p for p,_ in tagged]
        operations += len(polygons)*len(buildings)
        if operations > MAX_CHECKS:
            raise ValueError('junction building check limit')
        if any(overlap(p,b) for p in polygons for b in buildings):
            rejected['building'] += 1
            continue
        nearby = set()
        for poly in polygons:
            for bucket in buckets(bounds(poly), 4):
                nearby.update(index[bucket])
        blocked = False
        for key in sorted(nearby-keys-removed):
            operations += len(polygons)
            if operations > MAX_CHECKS:
                raise ValueError('junction road check limit')
            if any(overlap(p, ribbon(*key, edges[key]['collisionWidth'])) for p,ends in tagged if not set(key) & ends):
                blocked = True
                break
        superseded = [c for c in baseline if base_keys[id(c)] <= keys]
        existing = [(p, {tuple(c['path'][0]),tuple(c['path'][-1])}) for c in baseline+additions
                    if c not in superseded for p in [c['polygon'], *c['joins']]]
        operations += len(existing)*len(polygons)
        if operations > MAX_CHECKS:
            raise ValueError('junction replacement check limit')
        if blocked or any(overlap(p,q) for p,ports in tagged for q,ends in existing if not ends & ports):
            rejected['street'] += 1
            continue
        locked.update(p for path in paths for p in path)
        removed.update(keys)
        baseline = [c for c in baseline if c not in superseded]
        accepted.append(dict(original=list(center), physical=list(target),
                             additionIndex=len(additions),
                             beforeLength=sum(c['beforeLength'] for c in chains)
                             -sum(c['beforeLength']-c['afterLength'] for c in superseded),
                             afterLength=sum(c['afterLength'] for c in chains)))
        additions.extend(chains)
    for junction in accepted:
        first = len(baseline)+junction.pop('additionIndex')
        junction['chainIndexes'] = list(range(first,first+3))
    return dict(base, version='street-junctions/0.1', chains=baseline+additions,
                basis='structural three-arm reconstruction; fixed outer terminals; no new semantic edges',
                junctions=accepted, junctionCandidates=len(candidates), junctionRejected=dict(sorted(rejected.items())),
                beforeLength=sum(c['beforeLength'] for c in baseline+additions),
                afterLength=sum(c['afterLength'] for c in baseline+additions))
