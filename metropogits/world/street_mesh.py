"""Shared bounded pavement mesh: joined bends and curb-clipped walking surfaces."""
import math
from collections import defaultdict

from metropogits.street_diagonals import overlap, hull
from .geometry import area, bounds, nearest, point, ribbon
from .landscape import subtract
from .street_hierarchy import COLORS

VERSION = "world-street-mesh/0.1"
MAX_WORK = 2_000_000
MAX_INDEX = 500_000
MAX_PIECES = 250_000


def street_mesh(world):
    if len(world['streets'])>50_000:raise ValueError('street mesh input limit')
    streets=sorted(world['streets'],key=lambda s:s['id'])
    profiles=world.get('streetPlan',{}).get('segments',{})
    graded='surface' in world
    paths=[];adj=defaultdict(list);index=defaultdict(set);obstacles=[]
    work=entries=0

    def cells(poly):
        x0,z0,x1,z1=bounds(poly)
        a,b,c,d=math.floor(x0/16),math.floor(x1/16),math.floor(z0/16),math.floor(z1/16)
        if (b-a+1)*(d-c+1)>MAX_INDEX:raise ValueError('street mesh extent limit')
        return [(x,z) for x in range(a,b+1) for z in range(c,d+1)]

    def reserve(poly,kind):
        nonlocal entries
        keys=cells(poly);entries+=len(keys)
        if entries>MAX_INDEX:raise ValueError('street mesh index limit')
        for k in keys:index[k].add(len(obstacles))
        obstacles.append((poly,kind))

    def nearby(poly,kind):
        nonlocal work
        ids=sorted({i for k in cells(poly) for i in index[k] if obstacles[i][1]==kind})
        work+=len(ids)
        if work>MAX_WORK:raise ValueError('street mesh clearance work limit')
        return [obstacles[i][0] for i in ids]

    for p in world['parcels']:reserve(p['parcel'],'clearance')
    for f in world.get('terrain',{}).get('features',[]):reserve(f['noBuildPolygon'],'clearance')
    for site in world.get('campusPlan',{}).get('sites',[]):
        for c in site['courts']:reserve(c['polygon'],'clearance')
    for s in streets:
        cls=profiles.get(s['id'],{}).get('streetClass','SERVICE' if s['access'] else 'LOCAL')
        poly=ribbon(s['start'],s['end'],s['width'])
        walking=cls in ('PEDESTRIAN','SERVICE')
        paths.append((s,cls,poly,walking))
        if not walking:
            reserve(poly,'vehicle')
        if not s['access']:
            for p in (s['start'],s['end']):adj[(tuple(p),walking)].append(s)
    joints=[]
    # Cross-section hulls give bevel joins with no unbounded miter spikes.
    # Do not sew a bridge ramp to ground-level pavement or invent a road link.
    for (at,walking),incident in sorted(adj.items()):
        if len(incident)<2 or any(s.get('bridgeId') or s.get('tunnelId') for s in incident):continue
        tips=[]
        for s in incident:
            other=s['end'] if tuple(s['start'])==at else s['start']
            d=math.dist(at,other);r=s['width']/2
            normal=[-(other[1]-at[1])/d,(other[0]-at[0])/d]
            tips.extend([point([at[j]+side*normal[j]*r for j in (0,1)]) for side in (-1,1)])
        poly=list(reversed(hull(tips)))
        if len(poly)<3 or area(poly)<.0001:continue
        if any(overlap(poly,p) for p in nearby(poly,'clearance')):continue
        s=max(incident,key=lambda s:(s['width'],s['id']))
        cls=profiles.get(s['id'],{}).get('streetClass','LOCAL')
        joints.append((s,cls,poly,walking))
        if not walking:reserve(poly,'vehicle')
    result=[]
    def emit(base,poly,height=None):
        # Both browser renderers consume quads; encode convex faces as explicit
        # triangles (duplicate fourth corner), never silently discard vertices.
        for i in range(1,len(poly)-1):
            vertices=[poly[0],poly[i+1],poly[i],poly[i]]
            if area(vertices)<.000001:continue
            result.append(dict(base,points=[point(p) for p in vertices],
                               **(dict(pointHeights=[height(p) for p in vertices]) if height else {})))
            if len(result)>MAX_PIECES:raise ValueError('street mesh output limit')
    from .elevation import surface
    field=surface(world['terrain']) if graded else None
    from .rivers import height_at
    for s,cls,poly,walking in paths+joints:
        pieces=[poly]
        if walking:
            for obstacle in nearby(poly,'vehicle'):
                pieces=[p for p in pieces for p in subtract(p,obstacle)]
                if len(pieces)>128:raise ValueError('street mesh clipping piece limit')
        for poly in pieces:
            base=dict(physicalId=s['id'],streetClass=cls,width=s['width'],
                      color=COLORS[cls]['detail'],kind='STRUCTURAL',access=s['access'])
            if field:
                if s['access'] or s.get('bridgeId') or s.get('tunnelId'):
                    # Clip along each original elevation interval so access ramps
                    # and certified bridge grades retain their exact height law.
                    for a,b in zip(s['heightProfile'],s['heightProfile'][1:]):
                        from metropogits.block_orientation import clip
                        part=clip(poly,list(reversed(ribbon(a[:2],b[:2],s['width']))))
                        if len(part)<3 or area(part)<.000001:continue
                        road=dict(s,start=a[:2],end=b[:2],heights=[a[2],b[2]])
                        emit(base,part,lambda p:height_at(road,p))
                else:
                    for part in field.pieces(poly):
                        emit(base,part,lambda p:field.height(p)+.08)
            else:
                emit(base,poly)
    return result
