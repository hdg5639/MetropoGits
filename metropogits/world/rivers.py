"""Bounded connected water topology and certified, shared physical crossings.

The channel is analytical, not simulated hydrology. No source facts are inputs.
"""

import math

from metropogits.street_diagonals import hull, overlap
from .geometry import area, centroid, inside, nearest, point, q, ribbon
from .landscape import expanded, subtract
from .seed import derive, draw

VERSION = "terrain/0.2"
GENERATOR_VERSION = "terrain-adaptive/0.2"
PRESET = "river-corridor"
MAX_FEATURES = 24
MAX_WORK = 2_000_000


def _feature(poly, identity, kind):
    poly = list(reversed(hull(poly)))
    # Water and bank faces share actual vertices, including between reaches.
    outer = [point(p) for p in expanded(poly, 1.4)]
    faces = [dict(points=[[x, .06, z] for x, z in reversed(outer)], color="#83927a"),
             dict(points=[[x, .09, z] for x, z in reversed(poly)], color="#397c91")]
    return dict(id=identity, kind=kind, center=point(centroid(poly)), polygon=poly,
                noBuildPolygon=[point(p) for p in expanded(poly, 2)],
                roadPolygon=[point(p) for p in expanded(poly, 6.5)], height=.09, faces=faces)


def generate_river(envelope, seed):
    from .terrain import generate_terrain, outside

    seed = derive(seed, "global-terrain", VERSION)
    c, scale = centroid(envelope), math.sqrt(area(envelope))
    yaw = draw(seed)*math.tau
    u, v = [math.cos(yaw), math.sin(yaw)], [-math.sin(yaw), math.cos(yaw)]
    width = max(7, min(20, scale*.033))
    phase = draw(seed, 1)*math.tau
    for attempt in range(12):
        length = scale*.86*.9**attempt
        centers = [point([c[j]+u[j]*(t-.5)*length + v[j]*length*.085*
                          (math.sin(t*math.tau+phase)+.3*math.sin(t*math.tau*2))
                          for j in (0, 1)]) for t in [i/8 for i in range(9)]]
        cross_sections = []
        for i, p in enumerate(centers):
            a, b = centers[max(0,i-1)], centers[min(8,i+1)]
            tangent = [(b[j]-a[j])/math.dist(a,b) for j in (0,1)]
            n = [-tangent[1], tangent[0]]
            r = width/2*(.92+.16*draw(seed,20+i))
            cross_sections.append([point([p[j]+side*n[j]*r for j in (0,1)]) for side in (-1,1)])
        features = [_feature([*cross_sections[i], *reversed(cross_sections[i+1])],
                             "world:water:"+derive(seed,str(i)), "RIVER") for i in range(8)]
        for i in (0,8):
            p = centers[i]
            pool = [point([p[j]+width*(u[j]*math.cos(k*math.tau/16)*1.1+
                                       v[j]*math.sin(k*math.tau/16)*.8) for j in (0,1)]) for k in range(16)]
            features.append(_feature(pool,"world:water:"+derive(seed,"pool",str(i)),"LAKE"))
        if all(inside(p,envelope,1) for f in features for p in f["roadPolygon"]):
            break
    else:
        raise ValueError("river corridor cannot fit demand envelope")
    # Preserve hills only where independent initial terrain leaves safe room.
    for f in generate_terrain(envelope, seed)["features"]:
        if f["kind"] == "HILL" and not any(overlap(f["roadPolygon"], expanded(o["roadPolygon"],5)) for o in features):
            features.append(f)
    # Subtract the WHOLE water union from shore faces. A depth buffer hides the
    # overlap, but painter-based CPU/Canvas must not show false transverse dams.
    water_features = [f for f in features if f["kind"] != "HILL"]
    work = 0
    for f in water_features:
        banks = [[point(p) for p in expanded(f["polygon"],1.4)]]
        for o in water_features:
            work += len(banks)*len(o["polygon"])
            if work > MAX_WORK:
                raise ValueError("river shore geometry work limit")
            banks = [p for bank in banks for p in subtract(bank,o["polygon"])]
            if len(banks) > 63:
                raise ValueError("river shore face limit")
        f["faces"] = [dict(points=[[q(x),.06,q(z)] for x,z in reversed(p)],color="#83927a") for p in banks]
        f["faces"].append(dict(points=[[x,.09,z] for x,z in reversed(f["polygon"])],color="#397c91"))
    crossings = []
    indices = (1,4,6) if length > 250 else (2,5) if length > 110 else (3,)
    for i in indices:
        a, b = centers[i], centers[i+1]
        p = [(a[j]+b[j])/2 for j in (0,1)]
        n = [-(b[1]-a[1])/math.dist(a,b), (b[0]-a[0])/math.dist(a,b)]
        far = [point([p[j]+side*n[j]*width*8 for j in (0,1)]) for side in (-1,1)]

        def interval(field):
            parts = [tuple(far)]
            for f in features:
                if f["kind"] != "HILL":
                    parts = [s for x,y in parts for s in outside(x,y,f[field])]
            gaps = [(a[1],b[0]) for a,b in zip(parts,parts[1:])
                    if math.dist(a[1],b[0]) > .001 and math.dist(p,nearest(p,a[1],b[0])) < .001]
            if len(gaps) != 1:
                raise ValueError("river crossing cannot bind two exposed banks")
            return gaps[0]

        start, end = interval("roadPolygon")
        water_start, water_end = interval("polygon")
        left = point([water_start[j]-n[j]*.6 for j in (0,1)])
        right = point([water_end[j]+n[j]*.6 for j in (0,1)])
        deck = q(min(.95,.08+.15*min(math.dist(start,left),math.dist(right,end))))
        if deck < .7:
            raise ValueError("river bridge cannot meet bank grade and clearance")
        path = [start,left,right,end]
        crossing = dict(id="world:bridge:"+derive(seed,str(i)), path=path,
                        heights=[.08,deck,deck,.08], width=4.5, maxGrade=.16,
                        clearance=q(deck-.09), structural=True)
        # Adjacent channel reaches share water; hills are never bridge permits.
        if any(overlap(ribbon(start,end,5.3),f["noBuildPolygon"])
               for f in features if f["kind"] == "HILL"):
            continue
        crossings.append(crossing)
    if not crossings:
        raise ValueError("river has no feasible shared crossing")
    # Actual union area, not the sum of overlapping bank tiles.
    protected = []
    for f in features:
        parts = [f["noBuildPolygon"]]
        for o in protected:
            parts = [p for s in parts for p in subtract(s,o)]
        protected.extend(parts)
    return dict(version=VERSION,preset=PRESET,seed=seed,environmental=True,
                initialEnvelope=envelope,surfacePolicy="flat-buildable-plains",features=features,
                protectedArea=sum(map(area,protected)),
                channel=dict(centerline=centers, waterLevel=.09,
                             policy="analytical-connected-channel-not-drainage-simulation"),
                crossings=crossings)


def river_roads(terrain, polygon=None):
    """Exposed union banks only: no internal tile loops or per-road bridges."""
    from .terrain import outside

    roads, work = [], 0
    for f in terrain["features"]:
        poly = f["roadPolygon"]
        for a,b in zip(poly,poly[1:]+poly[:1]):
            pieces = [(a,b)]
            for o in terrain["features"]:
                if o is f:
                    continue
                work += len(pieces)*len(o["roadPolygon"])
                if work > MAX_WORK:
                    raise ValueError("river bank union work limit")
                pieces = [s for x,y in pieces for s in outside(x,y,o["roadPolygon"])]
            roads.extend(dict(start=a,end=b,width=3.5,access=False) for a,b in pieces)
    roads.extend(dict(start=a,end=b,width=c["width"],access=False)
                 for c in terrain["crossings"] for a,b in zip(c["path"],c["path"][1:]))
    if polygon is not None:
        from .river_landscape import clip_line
        roads=[dict(r,start=p[0],end=p[1]) for r in roads
               if (p:=clip_line(r["start"],r["end"],polygon))]
    return roads


def crossing_piece(street, terrain):
    """Certify geometry, not caller-provided bridge labels. End heights follow it."""
    for c in terrain.get("crossings", []):
        for i,(a,b) in enumerate(zip(c["path"],c["path"][1:])):
            if all(math.dist(p,nearest(p,a,b)) < .0003 for p in (street["start"],street["end"])):
                if street["access"] or abs(street["width"]-c["width"]) > .0001:
                    raise ValueError("bridge has invalid access or pavement width")
                heights = [q(c["heights"][i]+(c["heights"][i+1]-c["heights"][i])*
                             math.dist(a,nearest(p,a,b))/math.dist(a,b))
                           for p in (street["start"],street["end"])]
                return dict(bridgeId=c["id"],heights=heights)
    return {}


def annotate_crossings(streets, routing, terrain):
    for s in streets:
        s.update(crossing_piece(s,terrain))
    physical = {s["id"]:s for s in streets}
    for s in routing["segments"]:
        s.update(crossing_piece(physical[s["physicalId"]],terrain))


def validate_crossings(streets, terrain):
    """Full span/grade continuity, including bridges carrying no source traffic."""
    junction_heights = {}
    for s in streets:
        expected = crossing_piece(s,terrain)
        fields = ("bridgeId",) if "elevation" in terrain and not expected else ("bridgeId","heights")
        if {k:s[k] for k in fields if k in s} != expected:
            raise ValueError("physical crossing certificate/height mismatch")
        for p,y in zip((s["start"],s["end"]),s.get("heights",[.08,.08])):
            key=tuple(p)
            if key in junction_heights and abs(junction_heights[key]-y) > .001:
                raise ValueError("bridge junction has discontinuous elevation")
            junction_heights[key]=y
    for c in terrain["crossings"]:
        for i,(a,b) in enumerate(zip(c["path"],c["path"][1:])):
            if abs(c["heights"][i+1]-c["heights"][i])/math.dist(a,b) > c["maxGrade"]:
                raise ValueError("bridge approach grade exceeded")
            pieces = [s for s in streets if s.get("bridgeId") == c["id"] and all(
                math.dist(p,nearest(p,a,b)) < .0003 for p in (s["start"],s["end"]))]
            if abs(sum(math.dist(s["start"],s["end"]) for s in pieces)-math.dist(a,b)) > .003:
                raise ValueError("bridge lost a continuous physical span")


def height_at(street, p):
    a,b = street["start"],street["end"]
    heights = street.get("heights",[.08,.08])
    return q(heights[0]+(heights[1]-heights[0])*math.dist(a,nearest(p,a,b))/math.dist(a,b))


def blocks_ground_connection(start, end, terrain):
    """A ground alley may not join/cross an elevated bridge approach."""
    crossings=terrain.get("crossings",[])
    if len(crossings)>(8 if terrain.get('version') in ('terrain/0.5','terrain/0.6','terrain/0.7','terrain/0.8') else 4) or any(len(c["path"])!=4 for c in crossings):
        raise ValueError("ground crossing certificate limit")
    from .elevation import surface

    field=surface(terrain)
    u=[end[j]-start[j] for j in (0,1)]
    for c in crossings:
        for i,(a,b) in enumerate(zip(c["path"],c["path"][1:])):
            v=[b[j]-a[j] for j in (0,1)]
            d=[a[j]-start[j] for j in (0,1)]
            den=u[0]*v[1]-u[1]*v[0]
            hits=[]
            if abs(den)>1e-8:
                t=(d[0]*v[1]-d[1]*v[0])/den
                r=(d[0]*u[1]-d[1]*u[0])/den
                if -.0003/math.dist(start,end)<=t<=1+.0003/math.dist(start,end) and -.0003/math.dist(a,b)<=r<=1+.0003/math.dist(a,b):
                    hits=[point([start[j]+max(0,min(1,t))*u[j] for j in (0,1)])]
            else:
                hits=[p for p in (start,end,a,b) if math.dist(p,nearest(p,start,end))<.0003 and math.dist(p,nearest(p,a,b))<.0003]
            certificate=dict(start=a,end=b,heights=c["heights"][i:i+2])
            if any(abs(height_at(certificate,p)-field.height(p)-.08)>.001 for p in hits):
                return True
    return False


def bridge_faces(terrain):
    """Shared thin deck fascia and parapets; no fake source entity/hit ID."""
    faces = []
    for c in terrain.get("crossings",[]):
        for i,(a,b) in enumerate(zip(c["path"],c["path"][1:])):
            poly = ribbon(a,b,c["width"])
            heights = [c["heights"][i],c["heights"][i+1],c["heights"][i+1],c["heights"][i]]
            faces.append(dict(points=[[p[0],y,p[1]] for p,y in reversed(list(zip(poly,heights)))],color="#6b7880",surface="deck"))
            for j,k in ((0,1),(2,3)):
                p,r,y,z = poly[j],poly[k],heights[j],heights[k]
                # Two-sided parapet, visible from either river bank.
                vertices = [[p[0],y+.26,p[1]],[r[0],z+.26,r[1]],
                            [r[0],z-.18,r[1]],[p[0],y-.18,p[1]]]
                faces.extend([dict(points=vertices,color="#a6b2b4",surface="parapet"),
                              dict(points=list(reversed(vertices)),color="#8b9b9e",surface="parapet")])
    return faces
