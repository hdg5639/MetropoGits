"""Whole-campus groups follow distinct local bearings around softer commons."""
import copy
import math

from metropogits.street_diagonals import overlap
from .geometry import inside, nearest, point, ribbon
from .seed import derive, draw

VERSION='campus-plan/0.4'
MAX_WORK=300_000


def landscape_layout(*args):
    from .campus_neighborhood import neighborhood_layout
    base=neighborhood_layout(*args)
    if base is None:return None
    zone,polygon,axis,seed,roads,terrain,pairs,stats=args
    plots,walks,site=base
    centers=[c['center'] for c in site['courts']]
    rotations=[0.0]*len(centers)
    natural=[f['noBuildPolygon'] for f in (terrain or {}).get('features',[])]
    road_polys=[ribbon(r['start'],r['end'],r['width']+.3) for r in roads]
    work=0

    def moved(p,index,angles):
        c=centers[index];a=angles[index];co,si=math.cos(a),math.sin(a)
        x,z=p[0]-c[0],p[1]-c[1]
        return point([c[0]+x*co-z*si,c[1]+x*si+z*co])

    def group(identity):
        for i in range(len(centers)):
            if f':core:{i}:' in identity:return i
        return None

    def proposal(angles):
        ps,ws,cs=copy.deepcopy(plots),copy.deepcopy(walks),copy.deepcopy(site['courts'])
        ports={}
        for r in walks:
            i=group(r['id'])
            if i is not None:
                for field in ('start','end'):ports[tuple(r[field])]=moved(r[field],i,angles)
        for r in ws:
            i=group(r['id'])
            for f in ('start','end'):
                r[f]=moved(r[f],i,angles) if i is not None else ports.get(tuple(r[f]),r[f])
        # Preserve occupied straight frontages, but replace the unused square
        # corners with real short walking arcs. Gates/promeneades attach to the
        # arc midpoint rather than remaining at an abandoned rectangular corner.
        arc_ports={};extra=[]
        for i in range(len(centers)):
            ring=sorted([r for r in ws if f':core:{i}:loop:' in r['id']],key=lambda r:r['id'])
            if len(ring)!=4:continue
            saved=copy.deepcopy(ring)
            for j,r in enumerate(ring):
                a,b=saved[j]['start'],saved[j]['end'];p=saved[j-1]['start']
                u=[(b[k]-a[k])/math.dist(a,b) for k in (0,1)]
                v=[(a[k]-p[k])/math.dist(p,a) for k in (0,1)]
                radius=3.0
                origin=[a[k]+radius*(u[k]-v[k]) for k in (0,1)]
                start=[a[k]-radius*v[k] for k in (0,1)]
                theta=math.atan2(start[1]-origin[1],start[0]-origin[0])
                arc=[point([origin[0]+radius*math.cos(theta+t*math.pi/2),
                            origin[1]+radius*math.sin(theta+t*math.pi/2)]) for t in (0,.25,.5,.75,1)]
                arc_ports[tuple(a)]=arc[2]
                r['start']=arc[-1];r['end']=point([b[k]-radius*u[k] for k in (0,1)])
                extra.extend(dict(r,id=r['id']+f':corner:{k}',start=x,end=y) for k,(x,y) in enumerate(zip(arc,arc[1:])))
        for r in ws:
            if ':loop:' in r['id']:continue
            for f in ('start','end'):r[f]=arc_ports.get(tuple(r[f]),r[f])
        ws+=extra
        for p in ps:
            i=group(p['laneId'])
            if i is None:
                old=next((r for r in walks if r['id']==p['laneId']),None)
                new=next((r for r in ws if r['id']==p['laneId']),None)
                if old is None or new is None:continue  # Existing vehicle frontage stays fixed.
                oa,ob,na,nb=old['start'],old['end'],new['start'],new['end']
                length=math.dist(oa,ob);span=math.dist(na,nb)
                u=[(ob[j]-oa[j])/length for j in (0,1)]
                v=[(nb[j]-na[j])/span for j in (0,1)]
                change=math.atan2(v[1],v[0])-math.atan2(u[1],u[0])
                def affine(at):
                    along=sum((at[j]-oa[j])*u[j] for j in (0,1))/length
                    across=-(at[0]-oa[0])*u[1]+(at[1]-oa[1])*u[0]
                    return point([na[0]+along*(nb[0]-na[0])-across*v[1],
                                  na[1]+along*(nb[1]-na[1])+across*v[0]])
                # Preserve full source dimensions: translate/rotate the plot,
                # never stretch it with a changed promenade length.
                old_center=p['center'];new_center=affine(old_center)
                co,si=math.cos(change),math.sin(change)
                def rigid(at):
                    x,z=at[0]-old_center[0],at[1]-old_center[1]
                    return point([new_center[0]+co*x-si*z,new_center[1]+si*x+co*z])
                p['polygon']=[rigid(at) for at in p['polygon']]
                p['entrance']=rigid(p['entrance']);p['streetPoint']=affine(p['streetPoint'])
                p['center']=new_center;p['angle']+=change
                continue
            for f in ('center','entrance','streetPoint'):p[f]=moved(p[f],i,angles)
            p['polygon']=[moved(v,i,angles) for v in p['polygon']]
            p['angle']+=angles[i]
        for i,c in enumerate(cs):
            # An elliptical shared lawn fits inside its former rectangular
            # reserve. No invented facility or reduced source footprint.
            yaw=axis+angles[i];co,si=math.cos(yaw),math.sin(yaw)
            c['polygon']=[point([c['center'][0]+co*10.8*math.cos(t)-si*7.8*math.sin(t),
                                c['center'][1]+si*10.8*math.cos(t)+co*7.8*math.sin(t)])
                          for t in [k*math.tau/16 for k in range(16)]]
        return ps,ws,cs

    def valid(ps,ws,cs):
        nonlocal work
        from .geometry import bounds
        def hits(a,b):
            nonlocal work
            ba,bb=bounds(a),bounds(b)
            if ba[2]<bb[0] or bb[2]<ba[0] or ba[3]<bb[1] or bb[3]<ba[1]:return False
            work+=1
            if work>MAX_WORK:raise ValueError('campus neighborhood landscape clearance work limit')
            return overlap(a,b)
        lawns=[c['polygon'] for c in cs]
        pavement=[ribbon(r['start'],r['end'],r['width']+.25) for r in ws]
        for i,p in enumerate(ps):
            if not all(inside(v,polygon,1) for v in p['polygon']):return False
            if any(hits(p['polygon'],o) for o in natural+road_polys+lawns+pavement+[p['polygon'] for p in ps[:i]]):return False
        field=None
        if terrain and 'elevation' in terrain:
            from .elevation import surface,suitable
            from .rivers import blocks_ground_connection
            field=surface(terrain)
            if any(not suitable(p,terrain) or blocks_ground_connection(p['entrance'],p['streetPoint'],terrain) for p in ps):return False
        for r in ws:
            a,b=r['start'],r['end']
            if math.dist(a,b)<.01 or not all(inside(p,polygon,-.001) for p in (a,b)):return False
            if any(hits(ribbon(a,b,1.4),p) for p in natural+lawns):return False
            if field:
                profile=field.profile(a,b)
                if blocks_ground_connection(a,b,terrain) or any(abs(v[2]-u[2])/math.dist(u[:2],v[:2])>.1598 for u,v in zip(profile,profile[1:])):return False
        return True

    # Interlocked frontage wings cannot be moved one group at a time. Test a
    # bounded set of coordinated bearings before accepting the original axes.
    import itertools
    preferred=[1 if draw(derive(seed,VERSION,str(i)))>.5 else -1 for i in range(len(centers))]
    for factor in (1,.6,.3):
        found=False
        for signs in itertools.product((1,-1),repeat=len(centers)):
            candidate=[sign*preferred[i]*factor*math.pi/9 for i,sign in enumerate(signs)]
            if valid(*proposal(candidate)):
                rotations=candidate;found=True;break
        if found:break
    ps,ws,cs=proposal(rotations)
    if not valid(ps,ws,cs):
        # Keep the full original precinct, not a successful-looking small pocket.
        stats['landscapeFallback']='NO_SAFE_GROUP_TRANSFORM'
        return base
    site=copy.deepcopy(site)
    site.update(courts=cs,walkways=ws,groupRotations=rotations)
    stats.update(groupRotations=rotations,landscapeChecks=work)
    return ps,ws,site
