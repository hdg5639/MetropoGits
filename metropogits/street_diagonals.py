"""ADR-021: reconstruct isolated orthogonal chains, not a terrain deformation.

Canonical scenes and logical routing remain unchanged. The physical map is
defined only on participating street intervals; adjacent roads never move.
"""
from collections import defaultdict, Counter
import math

MAX_CHECKS = 5_000_000
MAX_EDGES = 100_000
EPS = 1e-8


def pair(a, b):
    return tuple(sorted((tuple(a), tuple(b))))


def ribbon(a, b, width):
    length = math.dist(a, b)
    if length <= EPS:
        raise ValueError('zero length diagonal pavement')
    n = [(b[1]-a[1])*width/length/2, (a[0]-b[0])*width/length/2]
    return [[a[j]+n[j] for j in (0, 1)], [a[j]-n[j] for j in (0, 1)],
            [b[j]-n[j] for j in (0, 1)], [b[j]+n[j] for j in (0, 1)]]


def overlap(a, b):
    for poly in (a, b):
        for p, q in zip(poly, poly[1:]+poly[:1]):
            axis = (p[1]-q[1], q[0]-p[0])
            if abs(axis[0])+abs(axis[1]) < EPS:
                continue
            aa = [sum(p[j]*axis[j] for j in (0, 1)) for p in a]
            bb = [sum(p[j]*axis[j] for j in (0, 1)) for p in b]
            if max(aa) <= min(bb)+EPS or max(bb) <= min(aa)+EPS:
                return False
    return True


def hull(points):
    points = sorted(set(map(tuple, points)))
    def cross(a, b, c):
        return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    halves = []
    for ordered in (points, list(reversed(points))):
        half = []
        for p in ordered:
            while len(half) >= 2 and cross(half[-2], half[-1], p) <= EPS:
                half.pop()
            half.append(p)
        halves.extend(half[:-1])
    return [list(p) for p in reversed(halves)]


def bounds(poly):
    return [min(p[0] for p in poly), min(p[1] for p in poly),
            max(p[0] for p in poly), max(p[1] for p in poly)]


def buckets(box, margin=0):
    if not all(math.isfinite(v) for v in box) or (box[2]-box[0]+2*margin+32)*(box[3]-box[1]+2*margin+32)/1024 > MAX_EDGES:
        raise ValueError('diagonal spatial extent limit')
    for x in range(math.floor((box[0]-margin)/32), math.floor((box[2]+margin)/32)+1):
        for z in range(math.floor((box[1]-margin)/32), math.floor((box[3]+margin)/32)+1):
            yield x, z


def arrangement(segments):
    """Split collinear overlaps and crossings exactly, including off-lattice doors."""
    if len(segments) > MAX_EDGES:
        raise ValueError('diagonal input segment limit')
    index, cuts, checks = defaultdict(set), [], 0
    for i, s in enumerate(segments):
        a, b = tuple(s['start']), tuple(s['end'])
        if not all(math.isfinite(v) for v in (*a, *b, s['width'])) or s['width'] <= 0:
            raise ValueError('diagonal geometry must be finite with positive width')
        if (a[0] == b[0]) == (a[1] == b[1]):
            raise ValueError('diagonal planning requires nonzero orthogonal baseline')
        cuts.append({a, b})
        nearby = set()
        for key in buckets(bounds([a, b])):
            checks += 1
            if checks > MAX_CHECKS:
                raise ValueError('diagonal spatial index limit')
            nearby.update(index[key])
            index[key].add(i)
        for k in sorted(nearby):
            checks += 1
            if checks > MAX_CHECKS:
                raise ValueError('diagonal arrangement check limit')
            c, d = tuple(segments[k]['start']), tuple(segments[k]['end'])
            horizontal = a[1] == b[1]
            other = c[1] == d[1]
            def on(p, x, y):
                return all(min(x[j], y[j]) <= p[j] <= max(x[j], y[j]) for j in (0, 1))
            if horizontal == other:
                for p in (a, b, c, d):
                    if on(p, a, b) and on(p, c, d):
                        cuts[i].add(p)
                        cuts[k].add(p)
            else:
                p = (c[0], a[1]) if horizontal else (a[0], c[1])
                if on(p, a, b) and on(p, c, d):
                    cuts[i].add(p)
                    cuts[k].add(p)
    edges, adjacency = {}, defaultdict(set)
    for s, points in zip(segments, cuts):
        for a, b in zip(sorted(points), sorted(points)[1:]):
            edge = edges.setdefault(pair(a, b), dict(width=0, collisionWidth=0, structural=False, blocked=False))
            edge['collisionWidth'] = max(edge['collisionWidth'], s['width'])
            if s.get('semantic') is False:
                edge['width'] = max(edge['width'], s['width'])
            edge['structural'] |= s.get('semantic') is False
            edge['blocked'] |= bool(s.get('entrance') or s.get('access') or s.get('kind', 'DEPENDENCY_ROAD') != 'DEPENDENCY_ROAD')
            adjacency[a].add(b)
            adjacency[b].add(a)
            if len(edges) > MAX_EDGES:
                raise ValueError('diagonal edge limit')
    return edges, adjacency


def plan_diagonals(scene, routing):
    if routing.get('streetGrid', {}).get('version') != 'structural-streets/0.2':
        raise ValueError('diagonal streets require aligned structural streets')
    if routing.get('curvePlan'):
        raise ValueError('diagonal streets cannot also use corner curves')
    structural = routing['streetGrid']['segments']
    edges, adjacency = arrangement(structural+list(routing['segments']))
    pins = {tuple(p) for r in routing['routes'] for p in (r['path'][0], r['path'][-1])}
    pins.update(tuple(s[k]) for s in structural if s.get('entrance') for k in ('start', 'end'))
    terminals = {p for p, ns in adjacency.items() if len(ns) != 2} | pins
    visited, candidates = set(), []
    for start in sorted(terminals):
        for nxt in sorted(adjacency[start]):
            if pair(start, nxt) in visited:
                continue
            path, previous, current = [start], start, nxt
            while True:
                visited.add(pair(previous, current))
                path.append(current)
                if current in terminals:
                    break
                previous, current = current, next(iter(adjacency[current]-{previous}))
            keys = [pair(a, b) for a, b in zip(path, path[1:])]
            old = sum(math.dist(a, b) for a, b in keys)
            new = math.dist(path[0], path[-1])
            if (len(path) < 3 or not 7 <= new <= 280 or new > old*.9
                    or any(abs(path[0][j]-path[-1][j]) < 2 for j in (0, 1))
                    or any(not edges[k]['structural'] or edges[k]['blocked'] for k in keys)):
                continue
            candidates.append((old-new, path, keys, old, new))
    buildings = [[[b['x'], b['z']], [b['x']+b['width'], b['z']],
                  [b['x']+b['width'], b['z']+b['depth']], [b['x'], b['z']+b['depth']]] for b in scene['buildings']]
    index, spatial_entries = defaultdict(set), 0
    for key, e in edges.items():
        for bucket in buckets(bounds(list(key)), e['collisionWidth']/2+4):
            spatial_entries += 1
            if spatial_entries > MAX_CHECKS:
                raise ValueError('diagonal clearance index limit')
            index[bucket].add(key)
    accepted, removed, reasons, checks = [], set(), Counter(), 0
    def certify(path, keys, new, width):
        nonlocal checks
        a, b = path[0], path[-1]
        throat = [min(width, edges[keys[0]]['width']), min(width, edges[keys[-1]]['width'])]
        transition = min(new/3, max(6, width*3))
        stations = [0, transition, new-transition, new]
        widths = [throat[0], width, width, throat[1]]
        centers = [[a[j]+(b[j]-a[j])*d/new for j in (0, 1)] for d in stations]
        strips = [tapered_ribbon(p, q, w0, w1) for p, q, w0, w1 in zip(centers, centers[1:], widths, widths[1:])]
        poly = hull([p for strip in strips for p in strip])
        # Certify the entire new strip plus junction mouths. The latter are the
        # convex hull of the incident cross-sections, not a disk decoration.
        joins = []
        for p, other, chain_neighbor, mouth in ((a, b, path[1], throat[0]), (b, a, path[-2], throat[1])):
            points = [list(p)]
            for q in sorted(adjacency[p]):
                w = mouth if q == chain_neighbor else edges[pair(p, q)]['collisionWidth']
                direction = other if q == chain_neighbor else q
                r = ribbon(p, direction, w)
                points.extend(r[:2])
            joins.append(hull(points))
        checks += len(buildings)*3
        if checks > MAX_CHECKS:
            raise ValueError('diagonal clearance check limit')
        if any(overlap(p, rect) for p in [poly, *joins] for rect in buildings):
            return None, 'building'
        nearby = set()
        for polygon in [poly, *joins]:
            for bucket in buckets(bounds(polygon), 4):
                nearby.update(index[bucket])
        blocked = False
        for key in sorted(nearby-set(keys)-removed):
            checks += 1
            if checks > MAX_CHECKS:
                raise ValueError('diagonal road check limit')
            if {a, b} & set(key):
                continue  # shared terminal is an intentional junction
            if any(overlap(p, ribbon(*key, edges[key]['collisionWidth'])) for p in [poly, *joins]):
                blocked = True
                break
        checks += sum((1+len(c['joins']))*(1+len(joins)) for c in accepted)
        if checks > MAX_CHECKS:
            raise ValueError('diagonal accepted-road check limit')
        if blocked or any(overlap(p, q) for c in accepted for p in [poly, *joins] for q in [c['polygon'], *c['joins']]):
            return None, 'street'
        return dict(polygon=poly, joins=joins, widthStations=[d/new for d in stations], widths=widths), None

    for _, path, keys, old, new in sorted(candidates, key=lambda c: (-c[0], c[1])):
        # Prefer a full connector, tapering at its original mouths. If blocked,
        # try narrower existing-width envelopes, never widening past the source
        # streets or relaxing obstacle checks to make a candidate pass.
        low, high = min(edges[k]['width'] for k in keys), max(edges[k]['width'] for k in keys)
        geometry = None
        for width in sorted({low, (low+high)/2, high}, reverse=True):
            geometry, reason = certify(path, keys, new, width)
            if geometry:
                break
        if not geometry:
            reasons[reason] += 1
            continue
        a, b = path[0], path[-1]
        distances = [0.0]
        for p, q in zip(path, path[1:]):
            distances.append(distances[-1]+math.dist(p, q))
        physical = [[a[j]+(b[j]-a[j])*d/old for j in (0, 1)] for d in distances]
        physical[0], physical[-1] = list(a), list(b)
        accepted.append(dict(path=[list(p) for p in path], physical=physical, width=width,
                             beforeLength=old, afterLength=new, **geometry))
        removed.update(keys)
    return dict(version='street-diagonals/0.1', chains=accepted, candidates=len(candidates),
                rejected=dict(sorted(reasons.items())),
                beforeLength=sum(c['beforeLength'] for c in accepted),
                afterLength=sum(c['afterLength'] for c in accepted),
                basis='structural chain chords; fixed terminals; no new semantic edges')


class PhysicalMap:
    def __init__(self, plan):
        self.lines = defaultdict(list)
        self.checks = 0
        for chain in plan['chains']:
            accumulated = 0
            for i, (a, b) in enumerate(zip(chain['path'], chain['path'][1:])):
                axis = 0 if a[1] == b[1] else 1
                length = math.dist(a, b)
                fractions = [0, 1]
                fractions += [(t*chain['beforeLength']-accumulated)/length for t in chain['widthStations']
                              if accumulated < t*chain['beforeLength'] < accumulated+length]
                def at(t):
                    if t == 0:
                        return list(a), chain['physical'][i]
                    if t == 1:
                        return list(b), chain['physical'][i+1]
                    return ([a[j]+(b[j]-a[j])*t for j in (0, 1)],
                            [chain['physical'][i][j]+(chain['physical'][i+1][j]-chain['physical'][i][j])*t for j in (0, 1)])
                def width_at(t):
                    fraction = (accumulated+t*length)/chain['beforeLength']
                    for lo, hi, w0, w1 in zip(chain['widthStations'], chain['widthStations'][1:], chain['widths'], chain['widths'][1:]):
                        if fraction <= hi+EPS:
                            return w0+(w1-w0)*max(0, min(1, (fraction-lo)/(hi-lo)))
                    return chain['widths'][-1]
                fractions = sorted(set(fractions))
                for start, end in zip(fractions, fractions[1:]):
                    p, pp = at(start)
                    q, qq = at(end)
                    self.lines[axis, a[1-axis]].append((p, q, pp, qq, (width_at(start), width_at(end))))
                accumulated += length

    def spans(self, a, b):
        axis = 0 if a[1] == b[1] else 1
        entries = self.lines.get((axis, a[1-axis]), [])
        self.checks += len(entries)
        if self.checks > MAX_CHECKS:
            raise ValueError('diagonal mapping check limit')
        low, high = sorted((a[axis], b[axis]))
        cuts = {a[axis], b[axis]}
        entries = [e for e in entries if min(e[0][axis], e[1][axis]) < high and max(e[0][axis], e[1][axis]) > low]
        for e in entries:
            cuts.update(p[axis] for p in e[:2] if low < p[axis] < high)
        ordered = sorted(cuts, reverse=b[axis] < a[axis])
        for x, y in zip(ordered, ordered[1:]):
            points = [[v, a[1]] if axis == 0 else [a[0], v] for v in (x, y)]
            width = None
            for p, q, pp, qq, w in entries:
                if min(p[axis], q[axis]) <= (x+y)/2 <= max(p[axis], q[axis]):
                    def at(v):
                        if v == p[axis]:
                            return list(pp)
                        if v == q[axis]:
                            return list(qq)
                        t = (v-p[axis])/(q[axis]-p[axis])
                        return [pp[j]+t*(qq[j]-pp[j]) for j in (0, 1)]
                    def width_at(v):
                        t = (v-p[axis])/(q[axis]-p[axis])
                        return w[0]+t*(w[1]-w[0])
                    points, width = [at(x), at(y)], (width_at(x), width_at(y))
                    break
            yield x, y, points[0], points[1], width


def presentation(routing, surfaces, pavement, hierarchy):
    mapper = PhysicalMap(routing['diagonalPlan'])
    structural = {s['id']: s for s in routing['streetGrid']['segments']}
    output = []
    for s in surfaces:
        original = structural[s['segmentId']]
        axis = 0 if original['start'][1] == original['end'][1] else 1
        lo, hi = min(p[axis] for p in s['points']), max(p[axis] for p in s['points'])
        a = [lo, original['start'][1]] if axis == 0 else [original['start'][0], lo]
        b = [hi, original['start'][1]] if axis == 0 else [original['start'][0], hi]
        spans = list(mapper.spans(a, b))
        if not any(w is not None for _, _, _, _, w in spans):
            output.append(s)
            continue
        for x, y, p, q, w in spans:
            def side(v):
                first = max(abs(t[1-axis]-a[1-axis])*2 for t in s['points'] if t[axis] == lo)
                last = max(abs(t[1-axis]-a[1-axis])*2 for t in s['points'] if t[axis] == hi)
                return first+(last-first)*(v-lo)/(hi-lo)
            # The entire chord width was certified. Unchanged partial spans
            # preserve the original taper rather than flattening all streets.
            polygon = tapered_ribbon(p, q, *w) if w is not None else tapered_ribbon(p, q, side(x), side(y))
            output.append(dict(s, points=polygon))
    for i, c in enumerate(routing['diagonalPlan']['chains']):
        for j, h in enumerate(c['joins']):
            if len(h) < 3:
                continue
            for n in range(1, len(h)-1):
                p = [h[0], h[n], h[n+1], h[n+1]]
                box = bounds(p)
                output.append(dict(id=f'diagonal-join-{i}-{j}-{n}', points=p, x=box[0], z=box[1],
                    width=box[2]-box[0], depth=box[3]-box[1], color='#43515d', semantic=False, elevation=.1))
    paths, pieces, paints = {}, dict(pavement['segments']), {}
    for s in routing['segments']:
        spans = list(mapper.spans(s['start'], s['end']))
        paths[s['id']] = [spans[0][2]]+[v[3] for v in spans]
        if not any(w is not None for _, _, _, _, w in spans):
            continue
        profile = (hierarchy or {}).get('segments', {}).get(s['id'], {})
        width = min(s['width'], profile.get('width', s['width']))
        pieces[s['id']], paints[s['id']] = [], []
        old_pieces = pavement['segments'].get(s['id'], [dict(start=s['start'], end=s['end'],
                    points=ribbon(s['start'], s['end'], width), width=width, maxWidth=width)])
        for piece in old_pieces:
            a, b = piece['start'], piece['end']
            axis = 0 if a[1] == b[1] else 1
            def side(v):
                first = max(abs(t[1-axis]-a[1-axis])*2 for t in piece['points'] if t[axis] == a[axis])
                last = max(abs(t[1-axis]-b[1-axis])*2 for t in piece['points'] if t[axis] == b[axis])
                return first+(last-first)*(v-a[axis])/(b[axis]-a[axis])
            for x, y, p, q, w in mapper.spans(a, b):
                w0, w1 = side(x), side(y)
                if w is not None:
                    w0, w1 = min(w0, w[0]), min(w1, w[1])
                pieces[s['id']].append(dict(piece, points=tapered_ribbon(p, q, w0, w1), start=p, end=q,
                                           width=min(w0, w1), maxWidth=max(w0, w1)))
        for piece in pieces[s['id']]:
            a, b, safe = piece['start'], piece['end'], piece['width']
            if s['kind'] != 'DEPENDENCY_ROAD':
                paints[s['id']].append(dict(start=a, end=b))
            elif not s.get('access') and safe >= 1.25 and profile.get('lanePattern') == 'DASHED':
                length = math.dist(a, b)
                # Keep junction mouths clear. Phase is deterministic per span.
                if math.ceil(length/4) > 512:
                    raise ValueError('diagonal paint sample limit')
                for k in range(math.ceil(length/4)):
                    start, end = max(1.8, k*4), min(length-1.8, k*4+1.6)
                    if end > start:
                        def point(d):
                            return [a[j]+(b[j]-a[j])*d/length for j in (0, 1)]
                        paints[s['id']].append(dict(start=point(start), end=point(end)))
    return output, dict(segments=pieces), dict(version=routing['diagonalPlan']['version'], segments=paths,
                                               corners=[], paintSegments=paints)


def tapered_ribbon(a, b, w0, w1):
    first, last = ribbon(a, b, w0), ribbon(a, b, w1)
    return first[:2]+last[2:]
