"""Shared physical street graph and exact source-backed trips."""

import heapq
import math
from collections import defaultdict

from metropogits.layout import _network_kind
from .geometry import bounds, nearest, point
from .seed import derive

MAX_PAIRS = 2_000_000
MAX_INDEX = 1_000_000
MAX_SEGMENTS = 50_000
MAX_TRIPS = 25_000
MAX_STATES = 10_000_000


def cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def atomic_streets(raw):
    cuts = [{tuple(s["start"]), tuple(s["end"])} for s in raw]
    cells = defaultdict(list)
    checks = entries = 0
    for i, s in enumerate(raw):
        x0, z0, x1, z1 = bounds([s["start"], s["end"]])
        if (math.floor((x1 + 0.001) / 32) - math.floor((x0 - 0.001) / 32) + 1) * (
            math.floor((z1 + 0.001) / 32) - math.floor((z0 - 0.001) / 32) + 1
        ) + entries > MAX_INDEX:
            raise ValueError("world street index limit")
        keys = [
            (x, z)
            for x in range(
                math.floor((x0 - 0.001) / 32), math.floor((x1 + 0.001) / 32) + 1
            )
            for z in range(
                math.floor((z0 - 0.001) / 32), math.floor((z1 + 0.001) / 32) + 1
            )
        ]
        entries += len(keys)
        if entries > MAX_INDEX:
            raise ValueError("world street index limit")
        others = {j for k in keys for j in cells[k]}
        for j in sorted(others):
            checks += 1
            if checks > MAX_PAIRS:
                raise ValueError("world intersection work limit")
            a, b = s["start"], s["end"]
            p, q = raw[j]["start"], raw[j]["end"]
            r = [b[k] - a[k] for k in (0, 1)]
            v = [q[k] - p[k] for k in (0, 1)]
            den = cross(r, v)
            if abs(den) > 1e-8:
                d = [p[k] - a[k] for k in (0, 1)]
                t, u = cross(d, v) / den, cross(d, r) / den
                tolerance_t = 0.0003 / math.dist(a, b)
                tolerance_u = 0.0003 / math.dist(p, q)
                if (
                    -tolerance_t <= t <= 1 + tolerance_t
                    and -tolerance_u <= u <= 1 + tolerance_u
                ):
                    hit = point([a[k] + max(0, min(1, t)) * r[k] for k in (0, 1)])
                    # Favor a stored endpoint to avoid near-duplicate graph nodes.
                    hit = min(
                        (x for x in (a, b, p, q) if math.dist(x, hit) < 0.0003),
                        key=lambda x: tuple(x),
                        default=hit,
                    )
                    cuts[i].add(tuple(hit))
                    cuts[j].add(tuple(hit))
            else:
                for endpoint in (a, b, p, q):
                    if (
                        math.dist(endpoint, nearest(endpoint, a, b)) < 0.0003
                        and math.dist(endpoint, nearest(endpoint, p, q)) < 0.0003
                    ):
                        cuts[i].add(tuple(endpoint))
                        cuts[j].add(tuple(endpoint))
        for k in keys:
            cells[k].append(i)
    segments = {}
    for i, s in enumerate(raw):
        ordered = sorted(cuts[i], key=lambda p: math.dist(s["start"], p))
        for a, b in zip(ordered, ordered[1:]):
            if math.dist(a, b) < 1e-8:
                continue
            a, b = sorted((a, b))
            key = (a, b)
            prior = segments.get(key)
            if prior:
                prior["width"] = max(prior["width"], s["width"])
                prior["access"] = prior["access"] and s["access"]
            else:
                segments[key] = dict(
                    id="world:street:" + derive(str(a), str(b)),
                    kind="STRUCTURAL",
                    start=list(a),
                    end=list(b),
                    width=s["width"],
                    access=s["access"],
                )
    if len(segments) > MAX_SEGMENTS:
        raise ValueError("world physical street limit")
    return sorted(segments.values(), key=lambda s: s["id"])


def route_world(graph, parcels, streets):
    buildings = {p["entityId"]: p for p in parcels}
    entities = {e["id"]: e for e in graph["entities"]}
    by_path = {e["path"]: e["id"] for e in graph["entities"] if e["kind"] == "FILE"}

    def owner(key):
        if key in buildings:
            return key
        return (
            by_path.get(entities[key].get("path"))
            if entities[key]["kind"] == "SYMBOL"
            else None
        )

    grouped = defaultdict(list)
    internal = []
    outside = []
    for e in sorted(graph["edges"], key=lambda e: e["id"]):
        if e["type"] == "CONTAINS":
            continue
        a, b = owner(e["from"]), owner(e["to"])
        if a is None or b is None:
            outside.append(e["id"])
            continue
        if a == b:
            internal.append(e["id"])
            continue
        grouped[(_network_kind(e["type"]), a, b)].append(e["id"])
    if len(grouped) > MAX_TRIPS:
        raise ValueError("world semantic trip limit")
    adjacency = defaultdict(list)
    pairs = {}
    for s in streets:
        a, b = tuple(s["start"]), tuple(s["end"])
        length = math.dist(a, b)
        adjacency[a].append((b, length))
        adjacency[b].append((a, length))
        pairs[tuple(sorted((a, b)))] = s
    for neighbors in adjacency.values():
        neighbors.sort()
    endpoints = {p["entityId"]: tuple(p["entrance"]) for p in parcels}
    destinations = defaultdict(set)
    for _, a, b in grouped:
        destinations[a].add(endpoints[b])
    trees = {}
    expansions = 0
    for key, targets in sorted(destinations.items()):
        start = endpoints[key]
        distance = {start: 0.0}
        previous = {start: None}
        heap = [(0.0, start)]
        remaining = set(targets)
        while heap and remaining:
            cost, node = heapq.heappop(heap)
            if cost != distance.get(node):
                continue
            expansions += 1
            if expansions > MAX_STATES:
                raise ValueError("world routing work limit")
            remaining.discard(node)
            for other, length in adjacency[node]:
                candidate = cost + length
                if candidate < distance.get(other, math.inf) - 1e-9:
                    distance[other] = candidate
                    previous[other] = node
                    heapq.heappush(heap, (candidate, other))
        if remaining:
            raise ValueError(f"world infrastructure disconnected at {key}")
        trees[key] = previous
    networks = {}
    routes = []
    render_segments = {}
    for (kind, a, b), edge_ids in sorted(grouped.items()):
        network_key = (kind, buildings[a]["districtId"], buildings[b]["districtId"])
        network_id = "world:network:" + derive(*network_key)
        network = networks.setdefault(
            network_key, dict(id=network_id, kind=kind, edgeIds=[], path=[])
        )
        identity = "world:route:" + derive(kind, a, b)
        path = []
        node = endpoints[b]
        while node is not None:
            path.append(list(node))
            node = trees[a][node]
        path.reverse()
        segment_ids = []
        for start, end in zip(path, path[1:]):
            physical = pairs[tuple(sorted((tuple(start), tuple(end))))]
            sid = "world:route-segment:" + derive(kind, physical["id"])
            item = render_segments.setdefault(
                sid,
                dict(
                    physical, id=sid, physicalId=physical["id"], kind=kind, routeIds=[]
                ),
            )
            item["routeIds"].append(identity)
            segment_ids.append(sid)
        routes.append(
            dict(
                id=identity,
                kind=kind,
                source=a,
                target=b,
                edgeIds=edge_ids,
                networkIds=[network_id],
                path=path,
                segmentIds=segment_ids,
            )
        )
        network["edgeIds"] += edge_ids
        if not network["path"]:
            network["path"] = path
    for n in networks.values():
        n["edgeIds"] = sorted(n["edgeIds"])
    for s in render_segments.values():
        s["routeIds"] = sorted(s["routeIds"])
    incident = defaultdict(list)
    for s in render_segments.values():
        for p in (s["start"], s["end"]):
            incident[(s["kind"], *p)].append(s["id"])
    junctions = [
        dict(
            id="world:junction:" + derive(str(k)),
            kind=k[0],
            point=list(k[1:]),
            segmentIds=sorted(ids),
        )
        for k, ids in sorted(incident.items())
        if len(ids) >= 3
    ]
    routing = dict(
        version="visual-access/0.2",
        status="COMPLETE",
        routes=routes,
        segments=sorted(render_segments.values(), key=lambda s: s["id"]),
        junctions=junctions,
        unresolvedEdgeIds=[],
        diagnostics=[],
    )
    return (
        routing,
        sorted(networks.values(), key=lambda n: n["id"]),
        dict(
            internalEdgeIds=internal,
            nonLocalEdgeIds=outside,
            searchExpansions=expansions,
        ),
    )
