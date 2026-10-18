"""Road-cut development blocks planned before local frontage grammars."""

import math
from collections import deque

from .geometry import area, centroid, inside, partition, point, shared_boundaries
from .seed import derive
from .zone_access import access_corridors

VERSION = "road-cut-blocks/0.1"
TARGET_FILES = 64
MAX_BLOCKS = 256


def block_members(identities, pairs, zone_id, previous=()):
    pending = set(identities)
    if previous and all(pending.issuperset(b["memberEntityIds"]) for b in previous):
        records = [
            dict(b, memberEntityIds=list(b["memberEntityIds"])) for b in previous
        ]
        for b in records:
            pending.difference_update(b["memberEntityIds"])
        for identity in sorted(pending):
            options = [b for b in records if len(b["memberEntityIds"]) < b["capacity"]]
            if not options:
                break
            b = min(options, key=lambda b: (len(b["memberEntityIds"]), b["id"]))
            b["memberEntityIds"].append(identity)
        else:
            for b in records:
                b["memberEntityIds"].sort()
            return records, True
    links = {key: {} for key in identities}
    for (a, b), weight in pairs.items():
        if a in links and b in links:
            links[a][b] = links[b][a] = weight
    pending = set(identities)
    result = []
    # BFS provides a bounded, explainable dependency locality heuristic, not a
    # new semantic role or an unconstrained community-layout replacement.
    ordered = iter(sorted(identities))
    target = math.ceil(len(identities) / math.ceil(len(identities) / TARGET_FILES))
    while pending:
        while (start := next(ordered)) not in pending:
            pass
        selected, queue = [], deque([start])
        enqueued = {start}
        while len(selected) < target and (queue or pending):
            if not queue:
                queue.append(min(pending))
            key = queue.popleft()
            if key not in pending:
                continue
            pending.remove(key)
            selected.append(key)
            for neighbor in sorted(links[key], key=lambda k: (-links[key][k], k)):
                if neighbor in pending and neighbor not in enqueued:
                    queue.append(neighbor)
                    enqueued.add(neighbor)
        result.append(
            dict(
                id="world:block:" + derive(zone_id, start, VERSION),
                zoneId=zone_id,
                memberEntityIds=sorted(selected),
            )
        )
    if len(result) > MAX_BLOCKS:
        raise ValueError("road-cut block count limit")
    return sorted(result, key=lambda b: b["id"]), False


def road_block_plan(zones, polygons, members, pairs, seed, parent, previous=()):
    """No grammar parameter: changing a local pattern cannot change this plan."""
    if len(previous) > MAX_BLOCKS:
        raise ValueError("road-cut block hint count limit")
    by_old = {}
    for block in previous:
        by_old.setdefault(block["zoneId"], []).append(block)
    blocks, cuts = [], {}
    for zone in zones:
        key = zone["id"]
        records, reused = block_members(
            zone["memberEntityIds"], pairs, key, by_old.get(key, ())
        )
        if reused:
            parts = {b["id"]: b["polygon"] for b in records}
        else:
            parts = partition(
                polygons[key],
                [(b["id"], len(b["memberEntityIds"]) + 8) for b in records],
                derive(seed, key, VERSION),
            )
            parts, _ = shared_boundaries(parts, polygons[key])
        edges = {}
        for b in records:
            poly = parts[b["id"]]
            b.update(
                polygon=poly,
                anchor=point(centroid(poly)),
                areaAllocated=area(poly),
                reused=reused,
            )
            blocks.append(b)
            for a, c in zip(poly, poly[1:] + poly[:1]):
                edges.setdefault(tuple(sorted((tuple(a), tuple(c)))), []).append(
                    b["id"]
                )
        cuts[key] = [
            dict(start=list(a), end=list(b), width=3.5, access=False)
            for (a, b), owners in sorted(edges.items())
            if len(owners) == 2 and math.dist(a, b) > 0.001
        ]
    backbone = [r for roads in cuts.values() for r in roads]
    owner = {key: z["id"] for z in zones for key in z["memberEntityIds"]}
    affinity = {}
    for (a, b), weight in pairs.items():
        if a in owner and b in owner and owner[a] != owner[b]:
            key = tuple(sorted((owner[a], owner[b])))
            affinity[key] = affinity.get(key, 0) + weight
    connections, ports = access_corridors(
        polygons, cuts, parent, return_ports=True, affinity=affinity
    )
    backbone += connections
    for key, points in ports.items():
        center = centroid(polygons[key])
        for p in sorted(points):
            length = math.dist(p, center)
            if length > 0.001:
                end = point(
                    [p[j] + (center[j] - p[j]) * min(3 / length, 1) for j in (0, 1)]
                )
                backbone.append(dict(start=list(p), end=end, width=3.5, access=False))
    roads = [
        dict(
            r,
            id="world:backbone:" + derive(str(r["start"]), str(r["end"]), VERSION),
            structural=True,
        )
        for r in backbone
    ]
    vertex_work = sum(
        sum(len(b["polygon"]) for b in blocks if b["zoneId"] == z["id"]) ** 2
        for z in zones
    )
    if vertex_work > 5_000_000:
        raise ValueError("road-cut boundary classification work limit")
    for block in blocks:
        block["boundaryTypes"] = [
            "ROAD_CUT"
            if any(
                inside(point([(a[j] + b[j]) / 2 for j in (0, 1)]), other["polygon"])
                for other in blocks
                if other["zoneId"] == block["zoneId"] and other["id"] != block["id"]
            )
            else "NEIGHBORHOOD_BOUNDARY"
            for a, b in zip(
                block["polygon"], block["polygon"][1:] + block["polygon"][:1]
            )
        ]
    return (
        blocks,
        sorted(roads, key=lambda r: r["id"]),
        {key: [list(p) for p in sorted(points)] for key, points in ports.items()},
    )
