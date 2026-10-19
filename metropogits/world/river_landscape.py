"""Open analytical river network, ridges and evidence-used tunnel candidates."""

import math

from metropogits.block_orientation import clip as intersect
from metropogits.street_diagonals import overlap
from .geometry import area, centroid, dot, inside, nearest, point, q, ribbon
from .landscape import expanded, subtract
from .seed import derive, draw

VERSION = "terrain/0.4"
GENERATOR_VERSION = "terrain-adaptive/0.4"
PRESET = "river-landscape"
MAX_WORK = 2_000_000


def _strip(line, width, identity):
    from .rivers import _feature

    sections = []
    for i,p in enumerate(line):
        a,b=line[max(0,i-1)],line[min(len(line)-1,i+1)]
        n=[-(b[1]-a[1])/math.dist(a,b),(b[0]-a[0])/math.dist(a,b)]
        sections.append([point([p[j]+side*n[j]*width/2 for j in (0,1)]) for side in (-1,1)])
    return [_feature([*a,*reversed(b)],identity+":"+str(i),"RIVER")
            for i,(a,b) in enumerate(zip(sections,sections[1:]))]


def _banks(features):
    water=[f for f in features if f["kind"]=="RIVER"]
    work=0
    for f in water:
        banks=[expanded(f["polygon"],1.4)]
        for other in water:
            work+=len(banks)*len(other["polygon"])
            if work>MAX_WORK:
                raise ValueError("open river shore work limit")
            banks=[p for bank in banks for p in subtract(bank,other["polygon"])]
            if len(banks)>63:
                raise ValueError("open river shore face limit")
        f["faces"]=[dict(points=[[q(x),.06,q(z)] for x,z in reversed(p)],color="#83927a") for p in banks]
        f["faces"].append(dict(points=[[x,.09,z] for x,z in reversed(f["polygon"])],color="#397c91"))


def _ridge(envelope, line, water, seed):
    c,scale=centroid(envelope),math.sqrt(area(envelope))
    a,b=line[3],line[7]
    u=[(b[j]-a[j])/math.dist(a,b) for j in (0,1)]
    v=[-u[1],u[0]]
    major,minor=min(88,max(17,scale*.125)),min(34,max(8,scale*.046))
    for i in range(16):
        local=derive(seed,"ridge",str(i))
        side=1 if i%2 else -1
        center=point([c[j]+v[j]*side*scale*(.22+draw(local)*.12)+u[j]*scale*(draw(local,1)-.5)*.35 for j in (0,1)])
        poly=[point([center[j]+u[j]*major*math.cos(k*math.tau/16)+v[j]*minor*math.sin(k*math.tau/16) for j in (0,1)]) for k in range(16)]
        road=[point(p) for p in expanded(poly,6.5)]
        if not all(inside(p,envelope,1) for p in road) or any(overlap(road,expanded(f["roadPolygon"],3)) for f in water):
            continue
        height=q(min(35,max(12,major*.42)))
        inner=[[q(center[0]+(p[0]-center[0])*.38),q(height*.72),q(center[1]+(p[1]-center[1])*.38)] for p in poly]
        peak=[center[0],height,center[1]]
        faces=[]
        for k,(p,r) in enumerate(zip(poly,poly[1:]+poly[:1])):
            faces.extend([dict(points=[[p[0],.005,p[1]],inner[k],inner[(k+1)%16],[r[0],.005,r[1]]],color=("#5e735a","#687a60","#586d55")[k%3]),
                          dict(points=[inner[k],peak,inner[(k+1)%16]],color=("#879080","#727f6c")[k%2])])
        return dict(id="world:ridge:"+derive(local),kind="HILL",landform="RIDGE",center=center,
                    polygon=poly,noBuildPolygon=[point(p) for p in expanded(poly,2)],roadPolygon=road,height=height,faces=faces),v
    return None,None


def _crossing(a,b,p,water,seed):
    from .terrain import outside

    normal=[-(b[1]-a[1])/math.dist(a,b),(b[0]-a[0])/math.dist(a,b)]
    far=[point([p[j]+normal[j]*side*160 for j in (0,1)]) for side in (-1,1)]
    def gap(field):
        parts=[tuple(far)]
        for f in water:
            parts=[r for x,y in parts for r in outside(x,y,f[field])]
        return next(((x[1],y[0]) for x,y in zip(parts,parts[1:]) if math.dist(p,nearest(p,x[1],y[0]))<.001),None)
    bank,wet=gap("roadPolygon"),gap("polygon")
    if not bank or not wet:
        return None
    left=point([wet[0][j]-normal[j]*.6 for j in (0,1)])
    right=point([wet[1][j]+normal[j]*.6 for j in (0,1)])
    deck=q(min(.95,.08+.15*min(math.dist(bank[0],left),math.dist(right,bank[1]))))
    if deck<.7:
        return None
    return dict(id="world:bridge:"+derive(seed),path=[bank[0],left,right,bank[1]],
                heights=[.08,deck,deck,.08],width=4.5,maxGrade=.16,clearance=q(deck-.09),structural=True)


def _bridge_conflict(candidate, crossings):
    """Separate entire bridge approaches, not only their over-water decks."""
    return any(overlap(ribbon(a,b,candidate["width"]+.3),ribbon(c,d,other["width"]+.3))
               for other in crossings
               for a,b in zip(candidate["path"],candidate["path"][1:])
               for c,d in zip(other["path"],other["path"][1:]))


def _planned_crossing(a,b,fraction,water,seed,envelope,crossings):
    # Fixed, local alternatives preserve the water/terrain seed and earlier
    # feasible bridges. Never change heights to hide intersecting sloped ramps.
    for offset in (0,-.15,.15,-.3,.3):
        at=max(.05,min(.95,fraction+offset))
        p=point([a[j]+at*(b[j]-a[j]) for j in (0,1)])
        crossing=_crossing(a,b,p,water,seed)
        if not crossing or not all(inside(p,envelope) for p in crossing["path"]):
            if offset==0:
                return None  # Preserve prior no-crossing outcomes, not a new bridge search.
            continue
        if not _bridge_conflict(crossing,crossings):
            return crossing
    raise ValueError("river bridge approaches cannot be separated within placement budget")


def generate_landscape_terrain(envelope, seed):
    from .elevation import generate_valley, surface
    from .rivers import _feature
    from .terrain import outside

    t=generate_valley(envelope,seed)
    line=t["channel"]["centerline"]
    c=centroid(envelope)
    reach=max(math.dist(c,p) for p in envelope)*4+64  # > five bounded 1.5x area repairs
    ends=[]
    for a,b in ((line[0],line[1]),(line[-1],line[-2])):
        ends.append(point([a[j]+(a[j]-b[j])/math.dist(a,b)*reach for j in (0,1)]))
    water=[f for f in t["features"] if f["kind"]=="RIVER"]
    width=math.dist(*sorted(water[0]["polygon"],key=lambda p:math.dist(p,line[0]))[:2])
    # Extend the SAME end cross sections: no artificial lake/cap at either join.
    for i,(far,f,at) in enumerate(((ends[0],water[0],line[0]),(ends[1],water[-1],line[-1]))):
        cross=sorted(f["polygon"],key=lambda p:math.dist(p,at))[:2]
        shift=[far[j]-at[j] for j in (0,1)]
        water.append(_feature(cross+[point([p[j]+shift[j] for j in (0,1)]) for p in cross],"world:water:"+derive(seed,"open",str(i)),"RIVER"))
    join=line[4]
    u=[(line[5][j]-line[3][j])/math.dist(line[5],line[3]) for j in (0,1)]
    n=[-u[1],u[0]]
    side=1 if draw(derive(seed,"tributary"))>.5 else -1
    branch=[join,point([join[j]+n[j]*side*reach*.18+u[j]*reach*.035 for j in (0,1)]),
            point([join[j]+n[j]*side*reach+u[j]*reach*.18 for j in (0,1)])]
    water.extend(_strip(branch,max(3.2,width*.42),"world:stream:"+derive(seed)))
    _banks(water)
    # A Y-shaped barrier creates three land sectors: connect both main reaches
    # and the smaller stream, rather than losing a bridge at the confluence.
    crossings=[]
    for i,(a,b,fraction) in enumerate(((line[1],line[2],.5),(line[6],line[7],.5),(*branch[:2],.42))):
        crossing=_planned_crossing(a,b,fraction,water,derive(seed,"crossing",str(i)),envelope,crossings)
        if crossing:
            crossings.append(crossing)
    ridge,axis=_ridge(envelope,[ends[0],*line,ends[1]],water,seed)
    features=water+([ridge] if ridge else [])
    t.update(version=VERSION,preset=PRESET,features=features,crossings=crossings,
             channel=dict(t["channel"],centerline=[ends[0],*line,ends[1]],tributaries=[branch],extentPolicy="open-through-boundary/0.1"),tunnels=[])
    t["elevation"]["flatRadius"]=q(max(32,width/2+32))
    if ridge:
        center=ridge["center"]
        far=[point([center[j]+side*axis[j]*200 for j in (0,1)]) for side in (-1,1)]
        parts=outside(*far,ridge["roadPolygon"])
        if len(parts)==2:
            path=[parts[0][1],parts[1][0]]
            heights=[q(surface(t).height(p)+.08) for p in path]
            if abs(heights[1]-heights[0])/math.dist(*path)<=.16:
                t["tunnels"].append(dict(id="world:tunnel:"+derive(seed,ridge["id"]),hillId=ridge["id"],path=path,
                                         heights=heights,width=3.5,maxGrade=.16,clearance=3.2,structural=True))
    protected=[]
    for f in features:
        parts=[f["noBuildPolygon"]]
        for other in protected:
            parts=[p for s in parts for p in subtract(s,other)]
        protected.extend(parts)
    t["protectedArea"]=sum(map(area,protected))
    return t


def clip_line(a,b,polygon):
    """Intersect a segment with the convex urban domain, shared exact endpoints."""
    lo,hi=0.,1.
    for p,r in zip(polygon,polygon[1:]+polygon[:1]):
        n=[r[1]-p[1],p[0]-r[0]]
        da,db=dot(a,n)-dot(p,n),dot(b,n)-dot(p,n)
        if da>0 and db>0:
            return None
        if abs(da-db)>1e-10:
            v=da/(da-db)
            if da>db:
                lo=max(lo,v)
            else:
                hi=min(hi,v)
    return [point([a[j]+v*(b[j]-a[j]) for j in (0,1)]) for v in (lo,hi)] if hi-lo>.000001 else None


def joined_streets(roads, parcels, terrain):
    """Join quantized clipping seams, not separate nearby urban roads."""
    from collections import defaultdict

    if len(roads)>50_000:
        raise ValueError("open river junction input limit")
    fixed={tuple(p[k]) for p in parcels for k in ("entrance","streetPoint")}
    fixed.update(tuple(p) for c in terrain["crossings"] for p in c["path"])
    fixed.update(tuple(p) for c in terrain["tunnels"] for p in c["path"])
    cells=defaultdict(list)
    def bucket(p):
        return tuple(math.floor(v/.001) for v in p)
    for p in sorted(fixed):
        cells[bucket(p)].append(p)
    canonical={p:p for p in fixed}
    work=0
    for p in sorted({tuple(r[k]) for r in roads for k in ("start","end")}-fixed):
        x,z=bucket(p)
        choices=[]
        for i in range(x-1,x+2):
            for j in range(z-1,z+2):
                for other in cells[i,j]:
                    work+=1
                    if work>MAX_WORK:
                        raise ValueError("open river junction work limit")
                    if math.dist(p,other)<.0005:
                        choices.append(other)
        canonical[p]=min(choices,key=lambda v:(v not in fixed,math.dist(p,v),v)) if choices else p
        if not choices:
            cells[x,z].append(p)
    result=[]
    for r in roads:
        a,b=(list(canonical[tuple(r[k])]) for k in ("start","end"))
        if math.dist(a,b)>.00001:
            result.append(dict(r,start=a,end=b))
    return result


def tunnel_piece(street, terrain):
    from .elevation import surface
    for t in terrain.get("tunnels",[]):
        a,b=t["path"]
        if all(math.dist(p,nearest(p,a,b))<.0003 for p in (street["start"],street["end"])):
            if street["access"] or abs(street["width"]-t["width"])>.0001:
                raise ValueError("tunnel has invalid access or width")
            return dict(tunnelId=t["id"],heights=[q(surface(terrain).height(p)+.08) for p in (street["start"],street["end"])])
    return {}


def validate_landscape(world):
    from .elevation import surface
    t=world["terrain"]
    line=t["channel"]["centerline"]
    for path in [line,*t["channel"]["tributaries"]]:
        if inside(path[-1],world["envelope"],-8) or (path is line and inside(path[0],world["envelope"],-8)):
            raise ValueError("open river endpoint trapped inside urban land")
    if not any(inside(p,world["envelope"]) for p in line[1:-1]):
        raise ValueError("open river does not pass through city")
    used={s["physicalId"] for s in world["routing"]["segments"]}
    for street in world["streets"]:
        expected=tunnel_piece(street,t)
        if street.get("tunnelId")!=expected.get("tunnelId"):
            raise ValueError("forged or missing tunnel permit")
    for tunnel in t["tunnels"]:
        pieces=[s for s in world["streets"] if s.get("tunnelId")==tunnel["id"]]
        if not pieces:
            continue
        if not any(s["id"] in used for s in pieces):
            raise ValueError("constructed tunnel has no evidenced trip")
        if abs(sum(math.dist(s["start"],s["end"]) for s in pieces)-math.dist(*tunnel["path"]))>.003:
            raise ValueError("tunnel lost complete physical span")
        mountain=next(f for f in t["features"] if f["id"]==tunnel["hillId"])
        if mountain["height"]<tunnel["clearance"]+2:
            raise ValueError("tunnel has inadequate mountain cover")
        a,b=tunnel["path"]
        n=[-(b[1]-a[1])/math.dist(a,b),(b[0]-a[0])/math.dist(a,b)]
        for distance in (.35,.5,.65):
            for side in (-1,0,1):
                p=[a[j]+distance*(b[j]-a[j])+side*n[j]*(tunnel["width"]/2+.18) for j in (0,1)]
                if _mountain_height(mountain,p,t)-surface(t).height(p)-.08<tunnel["clearance"]:
                    raise ValueError("tunnel core lacks actual full-width mountain cover")
        if any(overlap(ribbon(*tunnel["path"],tunnel["width"]),f["noBuildPolygon"]) for f in t["features"] if f["kind"]=="RIVER"):
            raise ValueError("mountain tunnel intersects water")


def _mountain_height(mountain,p,terrain):
    from .elevation import lifted_faces

    heights=[]
    for face in lifted_faces(mountain["faces"],terrain):
        for i in range(1,len(face["points"])-1):
            a,b,c=(face["points"][j] for j in (0,i,i+1))
            x,z=p[0]-a[0],p[1]-a[2]
            ux,uz,vx,vz=b[0]-a[0],b[2]-a[2],c[0]-a[0],c[2]-a[2]
            den=ux*vz-uz*vx
            if abs(den)<1e-9:
                continue
            u,v=(x*vz-z*vx)/den,(ux*z-uz*x)/den
            if min(u,v)>=-.00001 and u+v<=1.00001:
                heights.append(a[1]+u*(b[1]-a[1])+v*(c[1]-a[1]))
    return max(heights,default=-math.inf)


def clip_face(points,normal,limit):
    out=[]
    for a,b in zip(points,points[1:]+points[:1]):
        da=sum(a[j]*normal[j] for j in range(3))-limit
        db=sum(b[j]*normal[j] for j in range(3))-limit
        if da<=.000001:
            out.append(a)
        if (da<=.000001)!=(db<=.000001):
            u=da/(da-db)
            out.append([a[j]+u*(b[j]-a[j]) for j in range(3)])
    return out


def natural_faces(world):
    """One shared clipped/portal-cut natural mesh for CPU, Canvas and WebGL."""
    from .elevation import lifted_faces

    t=world["terrain"]
    built={s["tunnelId"] for s in world["streets"] if "tunnelId" in s}
    result=[]
    for feature in t["features"]:
        faces=[]
        for face in lifted_faces(feature["faces"],t):
            p=face["points"]
            for a,b in zip(world["envelope"],world["envelope"][1:]+world["envelope"][:1]):
                p=clip_face(p,[b[1]-a[1],0,a[0]-b[0]],dot(a,[b[1]-a[1],a[0]-b[0]]))
            pieces=[p] if len(p)>=3 else []
            for tunnel in t["tunnels"]:
                if tunnel["id"] not in built or tunnel["hillId"]!=feature["id"]:
                    continue
                a,b=tunnel["path"]
                n=[-(b[1]-a[1])/math.dist(a,b),(b[0]-a[0])/math.dist(a,b)]
                # Remove the actual passage prism, not a painted closed arch.
                roof=max(p[2] for p in _tunnel_profile(tunnel,t))+tunnel["clearance"]
                planes=[([n[0],0,n[1]],dot(a,n)+tunnel["width"]/2+.18),
                        ([-n[0],0,-n[1]],-dot(a,n)+tunnel["width"]/2+.18),
                        ([0,1,0],roof)]
                remaining=[]
                for p in pieces:
                    for normal,limit in planes:
                        outside=clip_face(p,[-v for v in normal],-limit)
                        if len(outside)>=3:
                            remaining.append(outside)
                        p=clip_face(p,normal,limit)
                        if len(p)<3:
                            break
                pieces=remaining
            faces.extend(dict(face,points=p) for p in pieces)
        if faces:
            for tunnel in t["tunnels"]:
                if tunnel["id"] in built and tunnel["hillId"]==feature["id"]:
                    faces.extend(_lining(tunnel,t,faces))
            poly=intersect(feature["polygon"],world["envelope"])
            result.append(dict(feature,center=point(centroid(poly)) if poly else feature["center"],faces=faces))
    return result


def _tunnel_profile(tunnel, terrain):
    from .elevation import surface

    return surface(terrain).profile(*tunnel["path"])


def _lining(tunnel, terrain, cut_faces):
    """Open portal frames and bore lining; never a solid cap across the entrance."""
    from .elevation import surface

    a,b=tunnel["path"]
    u=[(b[j]-a[j])/math.dist(a,b) for j in (0,1)]
    n=[-u[1],u[0]]
    roof=max(p[2] for p in _tunnel_profile(tunnel,terrain))+tunnel["clearance"]
    hits=[p for f in cut_faces for p in f["points"] if abs(p[1]-roof)<.0001 and abs(dot([p[0]-a[0],p[2]-a[1]],n))<tunnel["width"]/2+.181]
    if len(hits)<4:
        raise ValueError("tunnel has no actual cut portal openings")
    lo,hi=min(dot([p[0]-a[0],p[2]-a[1]],u) for p in hits),max(dot([p[0]-a[0],p[2]-a[1]],u) for p in hits)
    points=[point([a[j]+distance*u[j] for j in (0,1)]) for distance in (lo,hi)]
    out=[]
    def face(vertices,color):
        out.extend([dict(points=vertices,color=color,surface="tunnel"),dict(points=list(reversed(vertices)),color=color,surface="tunnel")])
    half=tunnel["width"]/2+.16
    p,r=points
    for side in (-1,1):
        x,z=[point([v[j]+n[j]*half*side for j in (0,1)]) for v in (p,r)]
        face([[x[0],surface(terrain).height(x),x[1]],[z[0],surface(terrain).height(z),z[1]],
              [z[0],roof,z[1]],[x[0],roof,x[1]]],"#65716f")
    face([[v[0]+side*n[0]*half,roof,v[1]+side*n[1]*half] for v,side in ((p,-1),(r,-1),(r,1),(p,1))],"#7f8b84")
    # Portal lintels follow the actual cut hillside instead of a sealed face.
    for v in points:
        face([[v[0]+side*n[0]*(half+.22),y,v[1]+side*n[1]*(half+.22)]
              for side,y in ((-1,roof),(1,roof),(1,roof+.28),(-1,roof+.28))],"#acb6ad")
    return out
