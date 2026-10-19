"""Terrain-first natural reserves and shared land detours; no source guesses."""

import math

from metropogits.street_diagonals import hull, overlap
from .geometry import area, centroid, dot, inside, point, q
from .landscape import expanded
from .seed import derive, draw

VERSION = "terrain/0.1"
GENERATOR_VERSION = "terrain-adaptive/0.1"
PRESET = "lake-district"
MAX_ROADS = 24_000
MAX_WORK = 2_000_000


def generate_terrain(envelope, seed, preset=PRESET):
    """Only demand-sized land and seed are inputs. No buildings/streets exist yet."""
    if preset != PRESET:
        from .elevation import PRESET as VALLEY_PRESET, generate_valley
        if preset == VALLEY_PRESET:
            return generate_valley(envelope, seed)
        from .rivers import PRESET as RIVER_PRESET, generate_river
        if preset != RIVER_PRESET:
            raise ValueError("unsupported natural terrain preset")
        return generate_river(envelope, seed)
    seed = derive(seed, "global-terrain", VERSION)
    center = centroid(envelope)
    scale = math.sqrt(area(envelope))
    radius = max(4, min(44, scale/13))
    features = []
    for i in range(28):
        local = derive(seed, "feature", str(i))
        kind = "LAKE" if len(features) < 2 else "HILL"
        angle = draw(local)*math.tau
        distance = scale*(.08 + draw(local, 1)*.27)
        c = point([center[0]+math.cos(angle)*distance, center[1]+math.sin(angle)*distance])
        r = radius*(.85+draw(local, 2)*.35)*(1 if kind == "LAKE" else .8)
        yaw, ratio = draw(local, 3)*math.tau, .65+draw(local, 4)*.3
        ring = []
        for j in range(16):
            t = j*math.tau/16
            variation = .9 + draw(local, 10+j)*.2
            u, v = r*variation*math.cos(t), r*variation*ratio*math.sin(t)
            ring.append(point([c[0]+u*math.cos(yaw)-v*math.sin(yaw),
                               c[1]+u*math.sin(yaw)+v*math.cos(yaw)]))
        poly = list(reversed(hull(ring)))
        no_build = [point(p) for p in expanded(poly, 2)]
        road_ring = [point(p) for p in expanded(no_build, 4.5)]
        if (not all(inside(p, envelope, .5) for p in road_ring)
                or any(overlap(road_ring, expanded(f["roadPolygon"], 8)) for f in features)):
            continue
        height = q(min(15, r*.42)) if kind == "HILL" else .055
        faces = []
        if kind == "HILL":
            mid = [[q(c[0]+(p[0]-c[0])*.55), q(height*.63), q(c[1]+(p[1]-c[1])*.55)] for p in poly]
            peak = [q(c[0]+r*.09), height, q(c[1]-r*.07)]
            colors = ("#527050", "#5d7955", "#486747", "#6d7964")
            for j, (a, b) in enumerate(zip(poly, poly[1:]+poly[:1])):
                faces.append(dict(points=[[a[0], .005, a[1]], [b[0], .005, b[1]],
                                          mid[(j+1)%len(mid)], mid[j]], color=colors[j%4]))
                faces.append(dict(points=[mid[j], mid[(j+1)%len(mid)], peak],
                                  color="#7a8373" if j%4 == 0 else colors[j%4]))
        else:
            inner = [[q(c[0]+(p[0]-c[0])*.88), .04, q(c[1]+(p[1]-c[1])*.88)] for p in poly]
            for j, (a, b) in enumerate(zip(poly, poly[1:]+poly[:1])):
                faces.append(dict(points=[[a[0], .055, a[1]], [b[0], .055, b[1]],
                                          inner[(j+1)%len(inner)], inner[j]], color="#83927a"))
            faces.append(dict(points=inner, color="#397c91"))
        for face in faces:
            a, b, d = face["points"][:3]
            # Surface meshes are single-valued height fields: face upwards in Y.
            ny = (b[2]-a[2])*(d[0]-a[0]) - (b[0]-a[0])*(d[2]-a[2])
            if ny < 0:
                face["points"].reverse()
        features.append(dict(id="world:nature:"+derive(local), kind=kind, center=c,
                             polygon=poly, noBuildPolygon=no_build, roadPolygon=road_ring,
                             height=height, faces=faces))
        if len(features) >= 5:
            break
    if not features:
        raise ValueError("terrain envelope cannot hold a protected natural feature")
    return dict(version=VERSION, preset=PRESET, seed=seed, environmental=True,
                initialEnvelope=envelope, surfacePolicy="flat-buildable-plains",
                features=features, protectedArea=sum(area(f["noBuildPolygon"]) for f in features))


def outside(a, b, polygon):
    """Subtract a convex protected interior from one line, preserving endpoints."""
    lo, hi = 0., 1.
    for p, r in zip(polygon, polygon[1:]+polygon[:1]):
        n = [r[1]-p[1], p[0]-r[0]]
        da, db = dot(a, n)-dot(p, n), dot(b, n)-dot(p, n)
        if da > .00015 and db > .00015:
            return [(a, b)]
        if abs(da-db) > 1e-10:
            t = da/(da-db)
            if da > db:
                lo = max(lo, t)
            else:
                hi = min(hi, t)
    if hi <= lo+.000001:
        return [(a, b)]
    result = []
    if lo > .000001:
        result.append((a, point([a[j]+lo*(b[j]-a[j]) for j in (0, 1)])))
    if hi < 1-.000001:
        result.append((point([a[j]+hi*(b[j]-a[j]) for j in (0, 1)]), b))
    return [(p, r) for p, r in result if math.dist(p, r) > .001]


def adapt_roads(roads, terrain):
    if len(roads) > MAX_ROADS:
        raise ValueError("terrain road input limit")
    output = []
    work = 0
    for road in roads:
        pieces = [(road["start"], road["end"])]
        for f in terrain["features"]:
            work += len(pieces)*len(f["roadPolygon"])
            if work > MAX_WORK:
                raise ValueError("terrain road clipping work limit")
            pieces = [part for a, b in pieces for part in outside(a, b, f["roadPolygon"])]
        for i, (a, b) in enumerate(pieces):
            output.append(dict(road, start=a, end=b,
                               id=road.get("id", "terrain-road")+":land:"+str(i)))
        if len(output) > MAX_ROADS:
            raise ValueError("terrain adapted road limit")
    return output


def terrain_plan(plans, main, boundary, ports, pattern, polygon, terrain):
    """Alter the street/slot supply before ANY source-to-address assignment."""
    from .adaptive import clear_frontage
    from .geometry import nearest

    adapted_main = adapt_roads(main+boundary, terrain)
    if terrain.get("crossings"):
        from .rivers import river_roads
        for i, r in enumerate(river_roads(terrain)):
            from .geometry import ribbon
            if overlap(ribbon(r["start"], r["end"], r["width"]), polygon):
                adapted_main.append(dict(r, id="world:river-road:"+derive(pattern["id"],str(i)),
                                         structural=True,patternId=pattern["id"]))
    else:
        for f in terrain["features"]:
            if not overlap(f["roadPolygon"], polygon):
                continue
            adapted_main.extend(dict(id=f["id"]+":contour:"+derive(pattern["id"], str(i)), start=a, end=b,
                                     width=3.5, access=False, structural=True, patternId=pattern["id"])
                                for i, (a, b) in enumerate(zip(f["roadPolygon"],
                                                               f["roadPolygon"][1:]+f["roadPolygon"][:1])))
    adapted = {key: (p[0], adapt_roads(p[1], terrain), *p[2:]) for key, p in plans.items()}
    physical = adapted_main + [r for p in adapted.values() for r in p[1]]
    candidates = [s for p in adapted.values() for s in p[0] if not any(
        overlap(s["polygon"], f["noBuildPolygon"]) or inside(s["streetPoint"], f["roadPolygon"])
        for f in terrain["features"])]
    if "elevation" in terrain:
        from .elevation import suitable
        if len(candidates)>100_000:
            raise ValueError("elevation candidate limit")
        before=len(candidates)
        candidates=[s for s in candidates if suitable(s,terrain)]
        pattern=dict(pattern,elevationRejectedSlots=before-len(candidates))
    valid = {s["id"] for s in clear_frontage(candidates, physical)}
    adapted = {key: ([s for s in p[0] if s["id"] in valid], *p[1:]) for key, p in adapted.items()}
    if sum(map(len, ports.values()))*len(adapted_main) > MAX_WORK:
        raise ValueError("terrain portal projection work limit")
    actual_ports = {key: {tuple(point(min((nearest(at, r["start"], r["end"]) for r in adapted_main),
                                         key=lambda v: math.dist(at, v)))) for at in values}
                    for key, values in ports.items()} if adapted_main else {key:set() for key in ports}
    pattern = dict(pattern, terrainVersion=terrain.get("version", VERSION), protectedStreetIds=sorted(r["id"] for r in adapted_main),
                   roadCount=len(adapted_main))
    return adapted, adapted_main, [], actual_ports, pattern


def validate_terrain(terrain, seed):
    from .rivers import VERSION as RIVER_VERSION, MAX_FEATURES
    from .elevation import VERSION as VALLEY_VERSION

    if (not isinstance(terrain, dict) or terrain.get("version") != VERSION
            or not 3 <= len(terrain.get("initialEnvelope", [])) <= 512
            or not 1 <= len(terrain.get("features", [])) <= 5):
        if (not isinstance(terrain, dict) or terrain.get("version") not in (RIVER_VERSION, VALLEY_VERSION)
                or not 3 <= len(terrain.get("initialEnvelope", [])) <= 512
                or not 1 <= len(terrain.get("features", [])) <= MAX_FEATURES
                or not 1 <= len(terrain.get("crossings", [])) <= 3):
            raise ValueError("invalid terrain payload or resource limit")
    expected = generate_terrain(terrain["initialEnvelope"], seed, terrain.get("preset"))
    if expected != terrain:
        raise ValueError("terrain differs from its original global field/reserves")
