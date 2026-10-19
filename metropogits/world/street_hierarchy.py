"""Offline physical street functions, distinct from logical dependency demand."""

import heapq
import math
from collections import Counter, defaultdict

from .geometry import bounds, nearest, point, ribbon
from .seed import derive

VERSION = "street-plan/0.1"
MAX_STREETS = 50_000
MAX_INDEX = 500_000
MAX_CHECKS = 2_000_000
MAX_STATES = 500_000
MAX_PAINT = 100_000
CLASSES = ("ARTERIAL", "COLLECTOR", "LOCAL", "SERVICE", "PEDESTRIAN")
COLORS = {
    "ARTERIAL": dict(overview="#566570", district="#53626c", detail="#4b5964"),
    "COLLECTOR": dict(overview="#45565f", district="#40515b", detail="#394a54"),
    "LOCAL": dict(overview="#39464a", district="#334149", detail="#293943"),
    "SERVICE": dict(overview="#43504d", district="#3d4b50", detail="#364955"),
    "PEDESTRIAN": dict(overview="#506053", district="#687568", detail="#758273"),
}


def derive_street_plan(world):
    """Pure bounded classification/audit; never edit physical roads or trips."""
    streets = sorted(world["streets"], key=lambda s: s["id"])
    if len(streets) > MAX_STREETS:
        raise ValueError("street hierarchy input limit")
    by_id = {s["id"]: s for s in streets}
    if len(by_id) != len(streets):
        raise ValueError("street hierarchy duplicate identity")
    adjacency, index = defaultdict(list), defaultdict(set)
    checks = entries = states = 0

    def cells(poly, pad=0.003):
        x0, z0, x1, z1 = bounds(poly)
        a, b = (
            (math.floor((x0 - pad) / 32), math.floor((z0 - pad) / 32)),
            (math.floor((x1 + pad) / 32), math.floor((z1 + pad) / 32)),
        )
        if (b[0] - a[0] + 1) * (b[1] - a[1] + 1) > MAX_INDEX:
            raise ValueError("street hierarchy spatial extent limit")
        return [(x, z) for x in range(a[0], b[0] + 1) for z in range(a[1], b[1] + 1)]

    def nearby(poly):
        nonlocal checks
        ids = sorted({k for c in cells(poly) for k in index[c]})
        checks += len(ids)
        if checks > MAX_CHECKS:
            raise ValueError("street hierarchy geometry work limit")
        return [by_id[k] for k in ids]

    for s in streets:
        a, b = tuple(s["start"]), tuple(s["end"])
        length = math.dist(a, b)
        if length <= 1e-8:
            raise ValueError("street hierarchy degenerate road")
        adjacency[a].append((b, s["id"], length))
        adjacency[b].append((a, s["id"], length))
        keys = cells([a, b])
        entries += len(keys)
        if entries > MAX_INDEX:
            raise ValueError("street hierarchy spatial index limit")
        for c in keys:
            index[c].add(s["id"])
    # Components use actual shared endpoints, never geometric proximity guesses.
    node_component, components = {}, []
    for node in sorted(adjacency):
        if node in node_component:
            continue
        key = "world:street-component:" + derive(str(node), VERSION)
        queue, ids = [node], set()
        node_component[node] = key
        while queue:
            at = queue.pop()
            for other, identity, _ in adjacency[at]:
                ids.add(identity)
                if other not in node_component:
                    node_component[other] = key
                    queue.append(other)
        components.append(
            dict(id=key, streetCount=len(ids), buildingCount=0, portCount=0)
        )
    component_records = {c["id"]: c for c in components}
    profiles = {
        s["id"]: dict(
            streetClass="SERVICE" if s["access"] else "LOCAL",
            reasons=["BUILDING_ACCESS" if s["access"] else "LOCAL_FRONTAGE"],
            componentId=node_component[tuple(s["start"])],
        )
        for s in streets
    }
    walking = set()
    for site in world.get('campusPlan',{}).get('sites',[]):
        for r in site['walkways']:
            for s in nearby([r['start'],r['end']]):
                if not s['access'] and s['width']<=r['width']+.002 and all(
                    math.dist(p,nearest(p,r['start'],r['end']))<.002 for p in (s['start'],s['end'])):
                    walking.add(s['id'])
    for identity in walking:
        profiles[identity].update(streetClass='PEDESTRIAN',reasons=['CAMPUS_WALKWAY'])

    def promote(s, cls, reason):
        p = profiles[s["id"]]
        if s["access"] or s['id'] in walking:
            return
        if CLASSES.index(cls) < CLASSES.index(p["streetClass"]):
            p["streetClass"] = cls
        p["reasons"] = sorted(set(p["reasons"] + [reason]))

    for r in world.get("zoning", {}).get("mainRoads", []):
        if r["id"].startswith(("world:permeability:","world:campus-court:")):
            continue  # A protected narrow alley is not a collector by fiat.
        for s in nearby([r["start"], r["end"]]):
            if all(
                math.dist(p, nearest(p, r["start"], r["end"])) < 0.002
                for p in (s["start"], s["end"])
            ):
                promote(s, "COLLECTOR", "RESERVED_BACKBONE")
    for r in world["topology"]["edges"]:
        if len(r["districtIds"]) != 2:
            continue  # The outer perimeter is not automatically an arterial.
        for s in nearby([r["start"], r["end"]]):
            if all(
                math.dist(p, nearest(p, r["start"], r["end"])) < 0.002
                for p in (s["start"], s["end"])
            ):
                promote(s, "ARTERIAL", "INTERDISTRICT_CORRIDOR")
    for s in streets:
        if s.get("bridgeId") or s.get("tunnelId"):
            promote(s, "COLLECTOR", "PROTECTED_CROSSING")

    # Close the coarse hierarchy along a rooted shortest-path tree of EXISTING
    # non-access streets. The subgraph stays connected without invented geometry.
    seen = set()
    for node in sorted(adjacency):
        if node in seen or not any(
            not by_id[k]["access"] and k not in walking for _, k, _ in adjacency[node]
        ):
            continue
        nodes, ids, queue = {node}, set(), [node]
        seen.add(node)
        while queue:
            at = queue.pop()
            for other, k, _ in adjacency[at]:
                if by_id[k]["access"] or k in walking:
                    continue
                ids.add(k)
                if other not in seen:
                    nodes.add(other)
                    seen.add(other)
                    queue.append(other)
        coarse = {
            k for k in ids if profiles[k]["streetClass"] in ("ARTERIAL", "COLLECTOR")
        }
        if not coarse:
            key = max(
                ids, key=lambda k: (math.dist(by_id[k]["start"], by_id[k]["end"]), k)
            )
            promote(by_id[key], "COLLECTOR", "LOCAL_CENTER")
            coarse.add(key)
        root = min(
            (tuple(p) for k in coarse for p in (by_id[k]["start"], by_id[k]["end"])),
            key=lambda p: (
                min(
                    CLASSES.index(profiles[k]["streetClass"])
                    for _, k, _ in adjacency[p]
                    if k in ids
                ),
                p,
            ),
        )
        costs, previous, heap = {root: 0.0}, {}, [(0.0, root)]
        while heap:
            cost, at = heapq.heappop(heap)
            if cost != costs[at]:
                continue
            states += 1
            if states > MAX_STATES:
                raise ValueError("street hierarchy shortest-path work limit")
            for other, k, length in sorted(adjacency[at]):
                if k not in ids:
                    continue
                value = cost + length * (
                    1.15 if profiles[k]["streetClass"] == "LOCAL" else 1
                )
                if value < costs.get(other, math.inf) - 1e-9:
                    costs[other] = value
                    previous[other] = (at, k)
                    heapq.heappush(heap, (value, other))
        joined = {root}
        for at in sorted(
            {tuple(p) for k in coarse for p in (by_id[k]["start"], by_id[k]["end"])}
        ):
            path = []
            while at not in joined:
                path.append(at)
                at, k = previous[at]
                promote(by_id[k], "COLLECTOR", "COARSE_CONNECTOR")
            joined.update(path)

    def attachment(at, *, frontage=False):
        touching = [
            s
            for s in nearby([at])
            if (not frontage or not s["access"])
            and math.dist(at, nearest(at, s["start"], s["end"])) < 0.002
        ]
        return sorted(s["id"] for s in touching), (
            profiles[touching[0]["id"]]["componentId"] if touching else None
        )

    frontages, unattached = {}, []
    for p in sorted(world["parcels"], key=lambda p: p["entityId"]):
        _, component = attachment(p["entrance"])
        roads, frontage_component = attachment(p["streetPoint"], frontage=True)
        frontages[p["entityId"]] = dict(streetIds=roads, componentId=component)
        if component is None or not roads or frontage_component != component:
            unattached.append(p["entityId"])
        if component:
            component_records[component]["buildingCount"] += 1
    ports, missing = [], []
    for z in sorted(world.get("zoning", {}).get("zones", []), key=lambda z: z["id"]):
        for at in sorted(z.get("accessPorts", [])):
            roads, component = attachment(at, frontage=True)
            key = "world:street-port:" + derive(z["id"], str(at), VERSION)
            ports.append(
                dict(
                    id=key,
                    zoneId=z["id"],
                    point=at,
                    streetIds=roads,
                    componentId=component,
                )
            )
            if component:
                component_records[component]["portCount"] += 1
            else:
                missing.append(key)
    counts = Counter(p["streetClass"] for p in profiles.values())
    return dict(
        version=VERSION,
        structural=True,
        segments=profiles,
        backboneStreetIds=sorted(
            k
            for k, p in profiles.items()
            if p["streetClass"] in ("ARTERIAL", "COLLECTOR")
        ),
        components=components,
        frontages=frontages,
        ports=ports,
        summary=dict(
            classCounts={k: counts[k] for k in CLASSES},
            componentCount=len(components),
            occupiedComponentCount=sum(c["buildingCount"] > 0 for c in components),
            unattachedEntityIds=unattached,
            unattachedPortIds=missing,
        ),
        work=dict(indexEntries=entries, geometryChecks=checks, searchStates=states),
    )


def marking_surfaces(world):
    """Sparse physical center paint; arbitrary bearings, existing pavement only."""
    plan = world.get("streetPlan")
    if not plan:
        return []
    adjacency = defaultdict(list)
    for s in world["streets"]:
        if not s["access"]:
            for p in (s["start"], s["end"]):
                adjacency[tuple(p)].append(s)
    result = []
    for s in sorted(world["streets"], key=lambda s: s["id"]):
        cls = plan["segments"][s["id"]]["streetClass"]
        if cls not in ("ARTERIAL", "COLLECTOR") or s["width"] < 2.5:
            continue
        a, b = sorted((s["start"], s["end"]))
        length = math.dist(a, b)
        unit = [(b[j] - a[j]) / length for j in (0, 1)]
        trim = [
            max(x["width"] for x in adjacency[tuple(p)]) / 2 + 0.2
            if len(adjacency[tuple(p)]) >= 3
            else 0.15
            for p in (a, b)
        ]
        phase = sum(a[j] * unit[j] for j in (0, 1))
        for i in range(
            math.floor((phase + trim[0]) / 6), math.ceil((phase + length - trim[1]) / 6)
        ):
            lo, hi = (
                max(trim[0], i * 6 - phase),
                min(length - trim[1], i * 6 + 2 - phase),
            )
            if hi - lo < 0.15:
                continue
            start, end = [point([a[j] + u * unit[j] for j in (0, 1)]) for u in (lo, hi)]
            poly = list(reversed(ribbon(start, end, 0.12)))
            if "surface" in world:
                from .elevation import pavement

                # A narrow ribbon follows the same height mesh as the road.
                road = dict(s, start=start, end=end, width=0.12)
                if s.get("bridgeId") or s.get("tunnelId"):
                    from .rivers import height_at

                    pieces = [
                        dict(
                            points=poly,
                            pointHeights=[height_at(s, p) + 0.04 for p in poly],
                            color="#b8b9a6",
                        )
                    ]
                else:
                    pieces = pavement(road, world["terrain"], "#b8b9a6", 0.12)
            else:
                pieces = [dict(points=poly, color="#b8b9a6", elevation=0.12)]
            result.extend(
                dict(p, physicalId=s["id"], streetClass=cls, structuralMarking=True)
                for p in pieces
            )
            if len(result) > MAX_PAINT:
                raise ValueError("street hierarchy paint work limit")
    return result
