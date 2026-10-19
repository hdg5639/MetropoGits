"""One bounded world-space height field, shared by planning and every consumer."""

import math
from functools import lru_cache

from .geometry import area, bounds, centroid, nearest, point, q, ribbon
from .landscape import field
from .seed import derive

VERSION = "terrain/0.3"
GENERATOR_VERSION = "terrain-adaptive/0.3"
PRESET = "river-valley"
STEP = 16
MAX_CELLS = 16_384
MAX_FACES = 65_536
MAX_PROFILES = 150_000
MAX_LOT_RELIEF = 1.0
MAX_ROAD_GRADE = .16
MAX_ACCESS_GRADE = .2
COLORS = ["#33464b", "#4a4149", "#354b42", "#504835", "#3e4454", "#4e3c42", "#3b4c50"]


def generate_valley(envelope, seed):
    from .rivers import generate_river

    for attempt in range(4):
        try:
            t = generate_river(envelope,seed if attempt==0 else derive(seed,"feasible-valley-water",str(attempt)))
            break
        except ValueError as error:
            # Geometry feasibility, not extra search work after budget exhaustion.
            if "work limit" in str(error) or attempt==3:
                raise
    line = t["channel"]["centerline"]
    radius = max(math.dist(p, min((nearest(p,a,b) for a,b in zip(line,line[1:])),
                                 key=lambda v:math.dist(v,p)))
                 for f in t["features"] if f["kind"] != "HILL" for p in f["polygon"])
    scale = math.sqrt(area(envelope))
    t.update(version=VERSION,preset=PRESET,surfacePolicy="graded-ground-level-foundations",
             elevation=dict(version="surface-field/0.1",seed=derive(seed,"uplands","surface-field/0.1"),
                            spacing=STEP,amplitude=q(min(18,max(6,scale*.04))),
                            riseLength=q(max(90,scale*.18)),flatRadius=q(radius+32)))
    if attempt:
        t["elevation"]["waterAttempt"]=attempt
    return t


class Surface:
    def __init__(self, parameters, line):
        self.parameters = parameters
        self.line = line

    @lru_cache(maxsize=65_536)
    def vertex(self, i, j):
        x,z = i*STEP,j*STEP
        d = min(math.dist([x,z],nearest([x,z],a,b)) for a,b in zip(self.line,self.line[1:]))
        r = max(0,d-self.parameters["flatRadius"])
        h = self.parameters["amplitude"] * r*r/(r*r+self.parameters["riseLength"]**2)
        return q(h*(.75+.25*field(self.parameters["seed"],x*.6,z*.6)))

    def height(self, p):
        if not all(math.isfinite(v) and abs(v)<=100_000 for v in p):
            raise ValueError("elevation sample extent limit")
        i,j = math.floor(p[0]/STEP),math.floor(p[1]/STEP)
        u,v = p[0]/STEP-i,p[1]/STEP-j
        a,b,c,d = [self.vertex(x,z) for x,z in ((i,j),(i+1,j),(i,j+1),(i+1,j+1))]
        return a+(b-a)*u+(c-a)*v if u+v<=1 else d+(c-d)*(1-u)+(b-d)*(1-v)

    def pieces(self, poly):
        x0,z0,x1,z1 = bounds(poly)
        lo,hi = (math.floor(x0/STEP),math.floor(z0/STEP)),(math.floor(x1/STEP),math.floor(z1/STEP))
        if (hi[0]-lo[0]+1)*(hi[1]-lo[1]+1)>MAX_CELLS:
            raise ValueError("elevation tessellation extent limit")
        from metropogits.block_orientation import clip as intersect

        result = []
        for i in range(lo[0],hi[0]+1):
            for j in range(lo[1],hi[1]+1):
                a,b,c,d = [[x*STEP,z*STEP] for x,z in ((i,j),(i+1,j),(i,j+1),(i+1,j+1))]
                for tri in ([a,b,c],[b,d,c]):
                    p = intersect(poly,tri)
                    if len(p)>=3 and area(p)>.00001:
                        result.append(p)
                        if len(result)>MAX_FACES:
                            raise ValueError("elevation tessellation face limit")
        return result

    def range(self, poly):
        heights = [self.height(p) for face in self.pieces(poly) for p in face]
        if not heights:
            raise ValueError("empty elevation footprint")
        return min(heights),max(heights)

    def profile(self, a, b):
        cuts = {0.,1.}
        for x,y in ((a[0],b[0]),(a[1],b[1]),(sum(a),sum(b))):
            if abs(y-x)<1e-9:
                continue
            if abs(y-x)/STEP>512:
                raise ValueError("elevation road extent limit")
            for k in range(math.ceil(min(x,y)/STEP),math.floor(max(x,y)/STEP)+1):
                t=(k*STEP-x)/(y-x)
                if .000001<t<.999999:
                    cuts.add(t)
        points = [point([a[j]+t*(b[j]-a[j]) for j in (0,1)]) for t in sorted(cuts)]
        points = [p for i,p in enumerate(points) if i==0 or p!=points[i-1]]
        if len(points)>256:
            raise ValueError("elevation road profile count limit")
        return [[*p,q(self.height(p)+.08)] for p in points]


def surface(terrain):
    e = terrain["elevation"]
    return _surface(tuple(sorted(e.items())),tuple(tuple(p) for p in terrain["channel"]["centerline"]))


@lru_cache(maxsize=8)
def _surface(parameters, line):
    return Surface(dict(parameters),line)


def suitable(slot, terrain):
    s = surface(terrain)
    low,high = s.range(slot["polygon"])
    length = math.dist(slot["entrance"],slot["streetPoint"])
    return (high-low <= MAX_LOT_RELIEF and length>.001
            and abs(high+.04-s.height(slot["streetPoint"]))/length <= MAX_ACCESS_GRADE)


def foundation(parcel, terrain):
    low,high = surface(terrain).range(parcel["footprint"])
    return dict(baseElevation=q(high+.04),foundationLow=q(low))


def annotate(streets, parcels, terrain):
    from .rivers import crossing_piece

    s = surface(terrain)
    entrances = {}
    for p in parcels:
        p.update(foundation(p,terrain))
        entrances[tuple(p["entrance"])] = p["baseElevation"]+.08
    count = 0
    for road in streets:
        bridge = crossing_piece(road,terrain)
        if bridge:
            road.update(bridge)
            profile = [[*p,y] for p,y in zip((road["start"],road["end"]),bridge["heights"])]
        else:
            profile = s.profile(road["start"],road["end"])
            if road["access"]:
                a,b = road["start"],road["end"]
                ya,yb = [entrances.get(tuple(p),s.height(p)+.08) for p in (a,b)]
                profile = [[*p[:2],q(ya+(yb-ya)*math.dist(a,p[:2])/math.dist(a,b))] for p in profile]
            road["heights"] = [profile[0][2],profile[-1][2]]
        road["heightProfile"] = profile
        count += len(profile)
        if count>MAX_PROFILES:
            raise ValueError("elevation road profile limit")


def validate_profiles(streets, parcels, terrain):
    expected = [dict(s) for s in streets]
    copies = [dict(p) for p in parcels]
    annotate(expected,copies,terrain)
    for a,b in zip(expected,streets):
        if any(a.get(k)!=b.get(k) for k in ("bridgeId","heights","heightProfile")):
            raise ValueError("street elevation differs from certified field/profile")
        limit = MAX_ACCESS_GRADE if a["access"] else MAX_ROAD_GRADE
        for p,r in zip(a["heightProfile"],a["heightProfile"][1:]):
            if abs(r[2]-p[2])/math.dist(p[:2],r[:2]) > limit+.0002:
                raise ValueError("physical street grade exceeded")
    for a,b in zip(copies,parcels):
        if any(a.get(k)!=b.get(k) for k in ("baseElevation","foundationLow")):
            raise ValueError("source foundation differs from protected ground")
        if a["baseElevation"]-a["foundationLow"]>MAX_LOT_RELIEF+.041:
            raise ValueError("source foundation relief exceeded")
    joints = {}
    for road in streets:
        for p in road["heightProfile"][::len(road["heightProfile"])-1]:
            key = tuple(p[:2])
            if key in joints and abs(joints[key]-p[2])>.001:
                raise ValueError("street elevation junction discontinuity")
            joints[key]=p[2]


def build_surface(terrain, districts):
    s=surface(terrain)
    faces=[]
    for i,d in enumerate(districts):
        for p in s.pieces(d["polygon"]):
            faces.append(dict(points=[[q(x),q(s.height([x,z])),q(z)] for x,z in reversed(p)],
                              color=COLORS[i%len(COLORS)]))
            if len(faces)>MAX_FACES:
                raise ValueError("world surface mesh limit")
    x0,z0,x1,z1=bounds([p for d in districts for p in d["polygon"]])
    ix,iz=math.floor(x0/STEP)-1,math.floor(z0/STEP)-1
    nx,nz=math.ceil(x1/STEP)-ix+2,math.ceil(z1/STEP)-iz+2
    if nx*nz>MAX_CELLS:
        raise ValueError("world surface grid limit")
    return dict(version="surface/0.1",spacing=STEP,origin=[ix*STEP,iz*STEP],
                values=[[s.vertex(ix+i,iz+j) for i in range(nx)] for j in range(nz)],faces=faces)


def lifted_faces(faces, terrain, *, rigid=False):
    s=surface(terrain)
    center=centroid([[x,z] for f in faces for x,y,z in f["points"]]) if rigid else None
    return [dict(f,points=[[x,q(y+s.height(center or [x,z])),z] for x,y,z in f["points"]]) for f in faces]


def foundation_faces(parcel, terrain):
    s=surface(terrain)
    faces=[]
    p=parcel["footprint"]
    for a,b in zip(p,p[1:]+p[:1]):
        path=s.profile(a,b)
        for a,b in zip(path,path[1:]):
            faces.append(dict(points=[[a[0],parcel["baseElevation"]+.2,a[1]],
                                      [b[0],parcel["baseElevation"]+.2,b[1]],
                                      [b[0],q(b[2]-.08),b[1]],[a[0],q(a[2]-.08),a[1]]],color="#87928c"))
    return faces


def pavement(road, terrain, color, offset=.08):
    s=surface(terrain)
    pieces=[]
    if road.get("bridgeId") or road["access"]:
        from .rivers import height_at
        for a,b in zip(road["heightProfile"],road["heightProfile"][1:]):
            poly=list(reversed(ribbon(a[:2],b[:2],road["width"])))
            pieces.append(dict(points=poly,pointHeights=[height_at(dict(road,start=a[:2],end=b[:2],heights=[a[2],b[2]]),p)+offset-.08 for p in poly],
                               width=road["width"],color=color))
        return pieces
    for poly in s.pieces(ribbon(road["start"],road["end"],road["width"])):
        for i in range(1,len(poly)-1):
            p=[poly[0],poly[i+1],poly[i],poly[i]]
            pieces.append(dict(points=[point(v) for v in p],pointHeights=[q(s.height(v)+offset) for v in p],width=road["width"],color=color))
    return pieces
