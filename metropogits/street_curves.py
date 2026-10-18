"""Geography-only, bounded bend smoothing for the opt-in street experiment.

The compact-support map is shared by pavement, paint and complete trajectories.
It cannot move anything outside a certified building-free square. A branch is
never replaced with a bend or an invented roundabout.
"""
from collections import defaultdict
import math

MAX_PIECES = 500_000


def plan_curves(scene, routing):
    if routing.get('streetGrid', {}).get('version') != 'structural-streets/0.2':
        raise ValueError('curved streets require aligned structural streets')
    adjacency = defaultdict(set)
    samples = 0
    for segment in routing['streetGrid']['segments']:
        a, b = segment['start'], segment['end']
        count = max(1, math.ceil(math.dist(a, b)/3.5))
        samples += count+1
        if samples > MAX_PIECES:
            raise ValueError('curve planning sample limit')
        points = [tuple(round(a[j]+(b[j]-a[j])*i/count, 6) for j in (0, 1)) for i in range(count+1)]
        for p, q in zip(points, points[1:]):
            adjacency[p].add(q)
            adjacency[q].add(p)
        if len(adjacency) > MAX_PIECES:
            raise ValueError('curve planning node limit')
    candidates, checks = [], 0
    for p, neighbors in sorted(adjacency.items()):
        if len(neighbors) != 2:
            continue
        a, b = sorted(neighbors)
        vectors = [[q[j]-p[j] for j in (0, 1)] for q in (a, b)]
        if any(v[0] and v[1] for v in vectors) or sum(vectors[0][j]*vectors[1][j] for j in (0, 1)) != 0:
            continue
        directions = [[v[j]/math.hypot(*v) for j in (0, 1)] for v in vectors]
        lengths = []
        for q, direction in zip((a, b), directions):
            previous, current = p, q
            for _ in range(16):
                choices = adjacency[current] - {previous}
                if len(choices) != 1:
                    break
                nxt = next(iter(choices))
                delta = [nxt[j]-current[j] for j in (0, 1)]
                if any(abs(delta[j]-direction[j]*math.hypot(*delta)) > 1e-7 for j in (0, 1)):
                    break
                previous, current = current, nxt
            lengths.append(math.dist(p, current))
        checks += len(scene['buildings'])
        if checks > 5_000_000:
            raise ValueError('curve clearance check limit')
        clearance = min((max(b['x']-p[0], p[0]-b['x']-b['width'],
                             b['z']-p[1], p[1]-b['z']-b['depth'], 0)
                         for b in scene['buildings']), default=14)
        radius = min(14, min(lengths)*.45, clearance-.2)
        if radius >= 1.5:
            candidates.append(dict(point=list(p), radius=round(radius, 6),
                direction=[sum(v[j] for v in directions) for j in (0, 1)]))
    accepted = []
    for c in sorted(candidates, key=lambda c:(-c['radius'], c['point'])):
        checks += len(accepted)
        if checks > 5_000_000:
            raise ValueError('curve clearance check limit')
        if all(max(abs(c['point'][j]-a['point'][j]) for j in (0, 1)) >= c['radius']+a['radius']+.1 for a in accepted):
            accepted.append(c)
    return dict(version='street-curves/0.1', corners=sorted(accepted,key=lambda c:c['point']),
                candidates=len(candidates), roundabouts=0,
                basis='geography-only degree-two bends; no junction or relationship changes')


class CurveMap:
    def __init__(self, plan):
        self.corners = (plan or {}).get('corners', [])
        self.pieces = 0
        self.buckets = defaultdict(list)
        for corner in self.corners:
            p, r = corner['point'], corner['radius']
            for x in range(math.floor((p[0]-r)/32), math.floor((p[0]+r)/32)+1):
                for z in range(math.floor((p[1]-r)/32), math.floor((p[1]+r)/32)+1):
                    self.buckets[x,z].append(corner)

    def point(self, point):
        for c in self.buckets.get((math.floor(point[0]/32),math.floor(point[1]/32)), []):
            p, r = c['point'], c['radius']
            x, z = (abs(point[j]-p[j])/r for j in (0, 1))
            if x < 1 and z < 1:
                delta = r/4*((1-x)*(1-z))**2
                return [point[j]+c['direction'][j]*delta for j in (0, 1)]
        return list(point)

    def affected(self, points):
        lo = [min(p[j] for p in points) for j in (0, 1)]
        hi = [max(p[j] for p in points) for j in (0, 1)]
        return any(all(lo[j] < c['point'][j]+c['radius'] and hi[j] > c['point'][j]-c['radius']
                       for j in (0, 1)) for c in self.corners)

    def count(self, count):
        self.pieces += count
        if self.pieces > MAX_PIECES:
            raise ValueError('curved street presentation limit')

    def line(self, a, b):
        if not self.affected([a,b]):
            return [list(a),list(b)]
        n = max(1, math.ceil(math.dist(a,b)/.75))
        self.count(n)
        return [self.point([a[j]+(b[j]-a[j])*i/n for j in (0,1)]) for i in range(n+1)]

    def polygon(self, points):
        if not self.affected(points):
            return [points]
        # Bilinear subdivision before the common map keeps all consumers on the
        # same physical footprint rather than bending only four distant corners.
        a,b,c,d = points
        nx=max(1,math.ceil(max(math.dist(a,b),math.dist(c,d))/.75))
        nz=max(1,math.ceil(max(math.dist(a,d),math.dist(b,c))/.75))
        self.count(nx*nz)
        def at(i,k):
            u,v=i/nx,k/nz
            return self.point([(1-v)*((1-u)*a[j]+u*b[j])+v*((1-u)*d[j]+u*c[j]) for j in (0,1)])
        return [[at(i,k),at(i+1,k),at(i+1,k+1),at(i,k+1)] for i in range(nx) for k in range(nz)]


def curved_presentation(routing, surfaces, pavement, hierarchy=None):
    if routing.get('diagonalPlan'):
        from metropogits.street_diagonals import presentation
        result = presentation(routing, surfaces, pavement, hierarchy)
        if routing.get('blockPlan'):
            from metropogits.block_orientation import presentation as block_presentation
            return block_presentation(routing, *result)
        return result
    plan = routing.get('curvePlan')
    if not plan:
        return surfaces, pavement, None
    mapper = CurveMap(plan)
    def joint(center, half):
        # A round join, not a square miter: the latter leaves a visible spike
        # after bending, even though the centerline itself is tangent-continuous.
        x,z=center
        for i in range(16):
            angles=[-2*math.pi*(i+t)/16 for t in (0,.5,1)]
            polygon=[center]+[[x+half*math.cos(a),z+half*math.sin(a)] for a in angles]
            yield from mapper.polygon(polygon)
    curved_surfaces = [dict(s, points=p) for s in surfaces for p in mapper.polygon(s['points'])]
    curved_pavement = dict(pavement, segments={key:[dict(piece,points=p) for piece in pieces
        for p in mapper.polygon(piece['points'])] for key,pieces in pavement['segments'].items()})
    for s in routing['segments']:
        if s['id'] in curved_pavement['segments']:
            continue
        width=min(s['width'], (hierarchy or {}).get('segments',{}).get(s['id'],{}).get('width',s['width']))
        a,b=s['start'],s['end']
        dx,dz=(0,width/2) if a[1]==b[1] else (width/2,0)
        polygon=[[a[0]-dx,a[1]-dz],[b[0]-dx,b[1]-dz],[b[0]+dx,b[1]+dz],[a[0]+dx,a[1]+dz]]
        if sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(polygon,polygon[1:]+polygon[:1]))>0:
            polygon.reverse()
        curved_pavement['segments'][s['id']]=[dict(points=p,start=a,end=b,width=width,maxWidth=width,structural=False)
            for p in mapper.polygon(polygon)]
    paths = {s['id']:mapper.line(s['start'],s['end']) for s in routing['segments']}
    # Butt-ended orthogonal strips lack the outside quarter of their corner.
    # Complete that joint inside the already certified empty support square,
    # then map it with the same transformation (not a decorative junction slab).
    for index, corner in enumerate(plan['corners']):
        center=corner['point']
        widths=[]
        for surface in surfaces:
            points=surface['points']
            for axis in (0,1):
                cross=[p[1-axis] for p in points if abs(p[axis]-center[axis])<1e-7]
                if len(cross)==2 and min(cross)<=center[1-axis]<=max(cross):
                    widths.append(max(cross)-min(cross))
        if not widths:
            continue
        half=min(min(widths)/2,corner['radius']*.8)
        x,z=center
        for points in joint(center,half):
            curved_surfaces.append(dict(id=f'curve-joint-{index}',points=points,x=x-half,z=z-half,
                width=half*2,depth=half*2,color='#43515d',elevation=.1,semantic=False))
        for segment in routing['segments']:
            if center not in (segment['start'],segment['end']):
                continue
            pieces=pavement['segments'].get(segment['id'],[])
            incident=[p['width'] for p in pieces if center in (p['start'],p['end'])]
            if not incident:
                continue
            h=min(half,min(incident)/2)
            for points in joint(center,h):
                curved_pavement['segments'][segment['id']].append(dict(points=points,start=center,end=center,
                    width=2*h,maxWidth=2*h,structural=True))
    paints={key:[{k:p[k] for k in ('start','end','width')} for p in pieces]
            for key,pieces in pavement['segments'].items()}
    return curved_surfaces, curved_pavement, dict(version=plan['version'], segments=paths, corners=plan['corners'], paintPieces=paints)
