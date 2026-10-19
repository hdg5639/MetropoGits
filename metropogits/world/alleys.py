"""Sparse structural cross-links through real gaps in long frontage rows."""

import heapq
import math
from collections import defaultdict

from metropogits.street_diagonals import overlap
from .geometry import bounds, inside, nearest, point, rectangle, ribbon
from .infrastructure import cross
from .seed import derive

GENERATOR_VERSION = "flat-adaptive-neighborhoods/0.5"
WIDTH = 1.6
MAX_LENGTH = 44
MIN_SPACING = 58
MAX_ALLEYS = 24
MAX_CANDIDATES = 6000
MAX_INDEX = 200_000
MAX_CHECKS = 500_000
MAX_STATES = 100_000


def add_alleys(streets, parcels, districts):
    """Return extra raw streets and an audit note; never move or mutate inputs."""
    note = dict(reason="sparse long-row alleys", version="frontage-alleys/0.1",
                corridors=[], candidates=0, geometryChecks=0, searchStates=0,
                budgetExhausted=None)
    index = defaultdict(set)
    objects = {}
    entries = 0
    roads = {s["id"]: s for s in streets}
    lots = {p["entityId"]: p for p in parcels}
    owners = {d["id"]: d["polygon"] for d in districts}
    adjacency = defaultdict(list)
    junctions = defaultdict(int)
    accepted, counts = [], defaultdict(int)
    zone_sizes = defaultdict(int)
    for p in parcels:
        zone_sizes[p.get("zoneId", p["districtId"])] += 1

    def cells(poly):
        x0, z0, x1, z1 = bounds(poly)
        nx, nz = math.floor(x1/24)-math.floor(x0/24)+1, math.floor(z1/24)-math.floor(z0/24)+1
        if nx*nz > MAX_INDEX:
            raise ValueError("alley spatial extent budget")
        return [(x, z) for x in range(math.floor(x0/24), math.floor(x1/24)+1)
                for z in range(math.floor(z0/24), math.floor(z1/24)+1)]

    def reserve(kind, key, poly):
        nonlocal entries
        keys = cells(poly)
        entries += len(keys)
        if entries > MAX_INDEX:
            raise ValueError("alley spatial index budget")
        objects[kind, key] = poly
        for cell in keys:
            index[cell].add((kind, key))

    def query(poly, kind):
        identities = sorted({key for cell in cells(poly) for key in index[cell] if key[0] == kind})
        note["geometryChecks"] += len(identities)
        if note["geometryChecks"] > MAX_CHECKS:
            raise ValueError("alley geometry budget")
        return [key for _, key in identities]

    def nearby(at, radius, kind):
        return query([[at[0]-radius, at[1]-radius], [at[0]+radius, at[1]+radius]], kind)

    def existing_shortcut(a, b, source, target, limit):
        # Endpoints may be interior to atomic pieces. Include their exact offsets.
        costs, heap = {}, []
        for p in (source["start"], source["end"]):
            key = tuple(p)
            costs[key] = math.dist(a, p)
            heapq.heappush(heap, (costs[key], key))
        goals = {tuple(p): math.dist(p, b) for p in (target["start"], target["end"])}
        while heap:
            cost, at = heapq.heappop(heap)
            if cost != costs[at] or cost > limit:
                continue
            note["searchStates"] += 1
            if note["searchStates"] > MAX_STATES:
                raise ValueError("alley shortcut search budget")
            if at in goals and cost + goals[at] <= limit:
                return True
            for other, length in adjacency[at]:
                value = cost + length
                if value <= limit and value < costs.get(other, math.inf)-1e-9:
                    costs[other] = value
                    heapq.heappush(heap, (value, other))
        return False

    try:
        for s in sorted(streets, key=lambda s: s["id"]):
            reserve("road", s["id"], ribbon(s["start"], s["end"], s["width"]+.4))
            a, b = tuple(s["start"]), tuple(s["end"])
            length = math.dist(a, b)
            adjacency[a].append((b, length))
            adjacency[b].append((a, length))
            if not s["access"]:
                junctions[a] += 1
                junctions[b] += 1
        for p in sorted(parcels, key=lambda p: p["entityId"]):
            reserve("lot", p["entityId"], p["parcel"])

        candidates = []
        for p in sorted(parcels, key=lambda p: p["entityId"]):
            tangent = [math.cos(p["angle"]), math.sin(p["angle"])]
            normal = [-tangent[1], tangent[0]]
            row = []
            for key in nearby(p["center"], 65, "lot"):
                other = lots[key]
                delta = [other["center"][j]-p["center"][j] for j in (0, 1)]
                along = sum(delta[j]*tangent[j] for j in (0, 1))
                across = sum(delta[j]*normal[j] for j in (0, 1))
                if (other.get("zoneId", other["districtId"]) == p.get("zoneId", p["districtId"])
                        and math.cos(other["angle"]-p["angle"]) > math.cos(math.radians(10))
                        and abs(across) < 1.2 and abs(along) <= 65):
                    row.append((along, key))
            row.sort()
            for (left, first), (right, second) in zip(row, row[1:]):
                if first != p["entityId"] or not 9 <= right-left <= 30:
                    continue
                mid = (left+right)/2
                support = [(t, k) for t, k in row if abs(t-mid) <= 55]
                if (len(support) < 6 or support[-1][0]-support[0][0] < 54
                        or sum(t < mid for t, _ in support) < 2
                        or sum(t > mid for t, _ in support) < 2):
                    continue
                a = point([(p["streetPoint"][j]+lots[second]["streetPoint"][j])/2 for j in (0, 1)])
                candidates.append((derive(first, second, "alley-gap"), a, normal, p,
                                   sorted(k for _, k in support)))
                if len(candidates) > MAX_CANDIDATES:
                    raise ValueError("alley candidate budget")

        for _, center, normal, p, row_ids in sorted(candidates, key=lambda item: item[0]):
            if len(accepted) >= MAX_ALLEYS:
                break
            note["candidates"] += 1
            zone = p.get("zoneId", p["districtId"])
            cap = min(2, max(1, zone_sizes[zone]//80))
            if counts[zone] >= cap or any(math.dist(center, s["center"]) < MIN_SPACING for s in accepted):
                continue
            near_roads = [roads[key] for key in nearby(center, MAX_LENGTH+5, "road")]
            sources = [(math.dist(center, nearest(center, s["start"], s["end"])), s["id"], s)
                       for s in near_roads if not s["access"] and abs(cross(normal,
                           [s["end"][j]-s["start"][j] for j in (0, 1)]))/math.dist(s["start"], s["end"]) > .9]
            if not sources:
                continue
            distance, _, source = min(sources)
            if distance > 1:
                continue
            a = point(nearest(center, source["start"], source["end"]))
            hits = []
            for s in near_roads:
                if s["access"]:
                    continue
                v = [s["end"][j]-s["start"][j] for j in (0, 1)]
                delta = [s["start"][j]-a[j] for j in (0, 1)]
                den = cross(normal, v)
                if abs(den)/math.dist(s["start"], s["end"]) < .5:
                    continue
                t, u = cross(delta, v)/den, cross(delta, normal)/den
                if 0.01 < t <= MAX_LENGTH and -.00001 <= u <= 1.00001:
                    hits.append((t, s["id"], s, point([a[j]+t*normal[j] for j in (0, 1)])))
            if not hits:
                continue
            length, _, target, b = min(hits)
            if length < 10 or any(
                junctions[tuple(v)] >= 3 and math.dist(at, v) < 7
                for at, s in ((a, source), (b, target)) for v in (s["start"], s["end"])
            ):
                continue
            center = point([(a[j]+b[j])/2 for j in (0, 1)])
            if any(math.dist(center, s["center"]) < MIN_SPACING for s in accepted):
                continue
            clearance = rectangle(center, math.atan2(b[1]-a[1], b[0]-a[0]), length+.4, WIDTH+.4)
            if not all(inside(v, owners[p["districtId"]], margin=.2) for v in clearance):
                continue
            if any(overlap(clearance, objects["lot", key]) for key in query(clearance, "lot")):
                continue
            if any(roads[key]["access"] and overlap(clearance, objects["road", key])
                   for key in query(clearance, "road")):
                continue
            trim_a, trim_b = source["width"]/2+1, target["width"]/2+1
            body = ribbon([a[j]+trim_a*normal[j] for j in (0, 1)],
                          [b[j]-trim_b*normal[j] for j in (0, 1)], WIDTH+.4)
            if any(not roads[key]["access"] and overlap(body, objects["road", key])
                   for key in query(body, "road")):
                continue
            # Reject a local shortcut already available nearby; no road for its own sake.
            if existing_shortcut(a, b, source, target, max(length*1.65, length+16)):
                continue
            identity = "world:alley:"+derive(str(a), str(b))
            record = dict(id=identity, start=a, end=b, center=center, width=WIDTH,
                          districtId=p["districtId"], zoneId=zone, rowEntityIds=row_ids,
                          connectsStreetIds=[source["id"], target["id"]])
            accepted.append(record)
            counts[zone] += 1
            # Wide spatial separation prevents interacting cuts before atomization.
        note["corridors"] = accepted
    except ValueError as error:
        note["budgetExhausted"] = str(error)
        note["corridors"] = accepted
    return [dict(start=s["start"], end=s["end"], width=WIDTH, access=False) for s in accepted], note
