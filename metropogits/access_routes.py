"""Derived, provenance-preserving building access (ADR-016). No semantic edges."""
from __future__ import annotations

import hashlib
import heapq
import math
import html
from collections import defaultdict

from scripts.canonical_json import canonical_json_bytes
from metropogits.road_paint import dash_segments, junction_trims

PITCH = 3.5
MAX_NODES = 250_000
MAX_ROUTES = 20_000
MAX_EXPANSIONS = 5_000_000


def _id(prefix, value):
    return f"visual:{prefix}:" + hashlib.sha256(canonical_json_bytes(value)).hexdigest()[:20]


def _pair(a, b):
    return (a, b) if a < b else (b, a)


def _point(node):
    return [node[0] * PITCH, node[1] * PITCH]


def _heading(a, b):
    return tuple((b[i] > a[i]) - (b[i] < a[i]) for i in (0, 1))


def _compact_segments(segments, routes):
    """Coalesce straight runs only when provenance/width are identical; keep junctions."""
    incident = defaultdict(list)
    for item in segments.values():
        item["routeIds"] = sorted(set(item["routeIds"]))
        for point in (item["start"], item["end"]):
            incident[tuple(point)].append(item["id"])
    visited, replacements, compact = set(), {}, {}
    for identity, first in sorted(segments.items()):
        if identity in visited:
            continue
        chain = {identity}
        endpoints = [first["start"], first["end"]]
        for index in range(2):
            current = identity
            while not first["access"]:
                point = endpoints[index]
                links = incident[tuple(point)]
                if len(links) != 2:
                    break
                other_id = next(key for key in links if key != current)
                other = segments[other_id]
                if other_id in chain or other_id in visited or any(other[k] != first[k] for k in ("kind", "access", "width", "routeIds")):
                    break
                horizontal = first["start"][1] == first["end"][1]
                if horizontal != (other["start"][1] == other["end"][1]):
                    break
                endpoints[index] = other["end"] if other["start"] == point else other["start"]
                chain.add(other_id)
                current = other_id
        start, end = sorted(endpoints)
        key = _id("access-segment", [first["kind"], start, end])
        compact[key] = {**first, "id": key, "start": start, "end": end}
        visited.update(chain)
        replacements.update((old, key) for old in chain)
    for route in routes:
        ids, points = [], [route["path"][0]]
        for i, identity in enumerate(route["segmentIds"]):
            key = replacements[identity]
            end = route["path"][i+1]
            continues = len(points) >= 2 and sum((points[-1][axis]-points[-2][axis]) * (end[axis]-points[-1][axis]) for axis in (0,1)) > 0
            if ids and ids[-1] == key and continues:
                points[-1] = end
            else:
                ids.append(key)
                points.append(route["path"][i+1])
        route["segmentIds"], route["path"] = ids, points
    return compact


class AccessGrid:
    def __init__(self, buildings):
        self.boxes = {}
        self.buckets = defaultdict(set)
        for building in buildings:
            x, z, w, d = (float(building[k]) for k in ("x", "z", "width", "depth"))
            box = (x, z, x + w, z + d)
            self.boxes[building["entityId"]] = box
            for key in self.bucket_keys(box, 3):
                self.buckets[key].add(building["entityId"])
        self.bounds = (math.floor(min(b[0] for b in self.boxes.values()) / PITCH) - 4,
                       math.floor(min(b[1] for b in self.boxes.values()) / PITCH) - 4,
                       math.ceil(max(b[2] for b in self.boxes.values()) / PITCH) + 4,
                       math.ceil(max(b[3] for b in self.boxes.values()) / PITCH) + 4)
        self.clearances = {}
        self.expansions = 0

    @staticmethod
    def bucket_keys(box, margin=0):
        x0, z0, x1, z1 = box
        for x in range(math.floor((x0 - margin) / 7), math.floor((x1 + margin) / 7) + 1):
            for z in range(math.floor((z0 - margin) / 7), math.floor((z1 + margin) / 7) + 1):
                yield x, z

    def clearance(self, a, b, ignored=None):
        x0, x1 = sorted((a[0], b[0]))
        z0, z1 = sorted((a[1], b[1]))
        nearby = set().union(*(self.buckets.get(key, set()) for key in self.bucket_keys((x0, z0, x1, z1))))
        result = 3.0
        for entity_id in nearby:
            if entity_id == ignored:
                continue
            left, top, right, bottom = self.boxes[entity_id]
            result = min(result, max(left - x1, x0 - right, top - z1, z0 - bottom, 0))
        return result

    def neighbors(self, node):
        x, z = node
        lo_x, lo_z, hi_x, hi_z = self.bounds
        for other in ((x - 1, z), (x, z - 1), (x, z + 1), (x + 1, z)):
            if not (lo_x <= other[0] <= hi_x and lo_z <= other[1] <= hi_z):
                continue
            key = _pair(node, other)
            if key not in self.clearances:
                self.clearances[key] = self.clearance(_point(node), _point(other))
            if self.clearances[key] > 0.12:
                yield other, self.clearances[key]

    def access(self, building, toward):
        left, top, right, bottom = self.boxes[building["entityId"]]
        mid_x, mid_z = (left + right) / 2, (top + bottom) / 2
        candidates = [
            ((math.floor(left / PITCH), round(mid_z / PITCH)), [left, round(mid_z / PITCH) * PITCH]),
            ((math.ceil(right / PITCH), round(mid_z / PITCH)), [right, round(mid_z / PITCH) * PITCH]),
            ((round(mid_x / PITCH), math.floor(top / PITCH)), [round(mid_x / PITCH) * PITCH, top]),
            ((round(mid_x / PITCH), math.ceil(bottom / PITCH)), [round(mid_x / PITCH) * PITCH, bottom]),
        ]
        eligible = []
        for node, door in candidates:
            if not (left <= door[0] <= right and top <= door[1] <= bottom):
                continue
            port = _point(node)
            if self.clearance(door, port, building["entityId"]) <= 0.36 or not list(self.neighbors(node)):
                continue
            distance = abs(port[0] - toward[0]) + abs(port[1] - toward[1])
            eligible.append((distance, node, door))
        if not eligible:
            return None
        _, node, door = min(eligible)
        return node, door

    def route(self, start, end, usage, start_heading=(0, 0), end_heading=(0, 0)):
        if start == end:
            return [start]
        def heuristic(node):
            return 90 * (abs(node[0] - end[0]) + abs(node[1] - end[1]))
        # Arrival direction is part of the state: two visits to a junction may
        # have different continuation costs. Never discard one just by node.
        initial = (start, start_heading)
        queue = [(heuristic(start), 0, 0, initial)]
        costs, previous = {initial: (0, 0)}, {initial: None}
        while queue:
            if self.expansions >= MAX_EXPANSIONS:
                return None
            _, bends, cost, state = heapq.heappop(queue)
            if (cost, bends) != costs[state]:
                continue
            self.expansions += 1
            current, heading = state
            if current == end:
                path = []
                while state is not None:
                    path.append(state[0])
                    state = previous[state]
                return list(reversed(path))
            for other, clearance in self.neighbors(current):
                direction = (other[0] - current[0], other[1] - current[1])
                turn = int(heading != (0, 0) and direction != heading)
                turn += int(other == end and end_heading != (0, 0) and direction != end_heading)
                # Including the turn, every transition stays in [90, 100].
                # Thus continuity/sharing retain ADR-016's 100/90 detour bound.
                weight = min(100, 98 - (2 if clearance >= 1.5 else 0) - min(6, usage.get(_pair(current, other), 0)) + 2 * turn)
                candidate = (cost + weight, bends + turn)
                next_state = (other, direction)
                if candidate < costs.get(next_state, (math.inf, math.inf)):
                    costs[next_state], previous[next_state] = candidate, state
                    heapq.heappush(queue, (candidate[0] + heuristic(other), candidate[1], candidate[0], next_state))
        return None


def derive_access_routes(scene, graph):
    buildings = {b["entityId"]: b for b in scene["buildings"]}
    edges = {e["id"]: e for e in graph["edges"]}
    grouped = defaultdict(lambda: dict(edgeIds=set(), networkIds=set()))
    for network in scene["networks"]:
        for edge_id in network["edgeIds"]:
            edge = edges[edge_id]
            if edge["from"] in buildings and edge["to"] in buildings:
                group = grouped[(network["kind"], edge["from"], edge["to"])]
                group["edgeIds"].add(edge_id)
                group["networkIds"].add(network["id"])
    result = dict(version="visual-access/0.2", routes=[], segments=[], junctions=[],
                  unresolvedEdgeIds=[], diagnostics=[], status="COMPLETE")
    if not grouped:
        return result
    extent_x = max(float(b["x"])+float(b["width"]) for b in buildings.values()) - min(float(b["x"]) for b in buildings.values())
    extent_z = max(float(b["z"])+float(b["depth"]) for b in buildings.values()) - min(float(b["z"]) for b in buildings.values())
    if (math.ceil(extent_x / PITCH)+10) * (math.ceil(extent_z / PITCH)+10) > MAX_NODES or len(grouped) > MAX_ROUTES:
        result.update(status="PARTIAL", unresolvedEdgeIds=sorted({e for g in grouped.values() for e in g["edgeIds"]}),
                      diagnostics=["Access routing resource limit; no fabricated fallback paths"])
        return result
    grid = AccessGrid(list(buildings.values()))
    neighbors = defaultdict(set)
    for _, source, target in grouped:
        neighbors[source].add(target)
        neighbors[target].add(source)
    ports = {}
    for entity_id, targets in sorted(neighbors.items()):
        centers = [(float(buildings[t]["x"]) + float(buildings[t]["width"]) / 2,
                    float(buildings[t]["z"]) + float(buildings[t]["depth"]) / 2) for t in sorted(targets)]
        toward = (sum(p[0] for p in centers) / len(centers), sum(p[1] for p in centers) / len(centers))
        ports[entity_id] = grid.access(buildings[entity_id], toward)
    segments, usage = {}, defaultdict(int)

    def segment(kind, a, b, width, route_id, access=False):
        if a == b:
            return None
        start, end = sorted((a, b))
        identity = _id("access-segment", [kind, start, end])
        if identity not in segments:
            segments[identity] = dict(id=identity, kind=kind, start=start, end=end,
                                      width=round(width, 4), access=access, routeIds=[])
        segments[identity]["routeIds"].append(route_id)
        return identity

    for (kind, source, target), group in sorted(grouped.items()):
        if ports[source] is None or ports[target] is None:
            result["unresolvedEdgeIds"].extend(group["edgeIds"])
            continue
        start, source_door = ports[source]
        end, target_door = ports[target]
        path = grid.route(start, end, usage, _heading(source_door, _point(start)),
                          _heading(_point(end), target_door))
        if path is None:
            result["unresolvedEdgeIds"].extend(group["edgeIds"])
            continue
        identity = _id("access-route", [kind, source, target])
        segment_ids = [segment(kind, source_door, _point(start), 0.7, identity, True)]
        for a, b in zip(path, path[1:]):
            key = _pair(a, b)
            width = min(5.5, 2 * (grid.clearances[key] - 0.12))
            segment_ids.append(segment(kind, _point(a), _point(b), width, identity))
            usage[key] += 1
        segment_ids.append(segment(kind, _point(end), target_door, 0.7, identity, True))
        points = [source_door, *map(_point, path), target_door]
        points = [p for i, p in enumerate(points) if i == 0 or p != points[i - 1]]
        result["routes"].append(dict(id=identity, kind=kind, source=source, target=target,
                                     edgeIds=sorted(group["edgeIds"]), networkIds=sorted(group["networkIds"]),
                                     path=points, segmentIds=[s for s in segment_ids if s], latticeSteps=len(path)-1))
    segments = _compact_segments(segments, result["routes"])
    incidence = defaultdict(list)
    for item in sorted(segments.values(), key=lambda s: s["id"]):
        item["routeIds"] = sorted(set(item["routeIds"]))
        result["segments"].append(item)
        for point in (item["start"], item["end"]):
            incidence[(item["kind"], *point)].append(item["id"])
    for (kind, x, z), incident in sorted(incidence.items()):
        if len(incident) >= 3:
            result["junctions"].append(dict(id=_id("access-junction", [kind, x, z]), kind=kind,
                                            point=[x, z], segmentIds=sorted(incident)))
    result["unresolvedEdgeIds"] = sorted(set(result["unresolvedEdgeIds"]))
    if result["unresolvedEdgeIds"]:
        result["status"] = "PARTIAL"
        result["diagnostics"].append("Some evidenced endpoints could not be reached without crossing buildings")
    result["searchExpansions"] = grid.expansions
    return result


def svg_access_lines(routing, project, overview=False, network_ids=None, hierarchy=None):
    """Traceable SVG polygons from the same shared segments used by the viewer."""
    routes = routing["routes"]
    indices = {route["id"]: i for i, route in enumerate(routes)}
    allowed = {r["id"] for r in routes if network_ids is None or set(r["networkIds"]) & network_ids}
    metadata = dict(version=routing["version"], status=routing["status"],
                    unresolvedEdgeIds=routing["unresolvedEdgeIds"],
                    routes=[{k: r[k] for k in ("id", "kind", "source", "target", "edgeIds", "networkIds")} for r in routes])
    lines = ['<metadata id="access-routing">' + html.escape(canonical_json_bytes(metadata).decode()) + '</metadata>',
             '<g id="shared-access-roads" aria-label="Shared geometry, not additional relationships">']
    structural = routing.get('streetGrid')
    if structural:
        from metropogits.structural_streets import street_rectangles
        assigned = set(structural['assignment']['assignedRouteIds'])
        allowed &= assigned
        lines.append('<metadata id="street-assignment">' + html.escape(canonical_json_bytes(
            structural['assignment']).decode()) + '</metadata>')
        lines.append('<g id="civic-infrastructure" aria-label="Structural streets: visual, not source relationships">')
        for rect in street_rectangles(routing):
            x, z, w, d = (rect[k] for k in ('x', 'z', 'width', 'depth'))
            polygon = rect.get('points', [[x,z], [x+w,z], [x+w,z+d], [x,z+d]])
            points = [project(a,b) for a,b in polygon]
            encoded = ' '.join(f'{float(a):.3f},{float(b):.3f}' for a,b in points)
            lines.append(f'<polygon points="{encoded}" fill="{rect["color"]}" data-civic-street="{rect["id"]}"/>')
        lines.append('</g>')
    visible, widths, paints = [], {}, []
    for segment in routing["segments"]:
        active = [r for r in segment["routeIds"] if r in allowed]
        if not active or (not structural and overview and (segment["access"] or len(active) < 4)):
            continue
        a, b = segment["start"], segment["end"]
        width = min(segment["width"], 0.7 + math.log2(len(active)+1)*0.5)
        profile = (hierarchy or {}).get('segments', {}).get(segment['id'])
        if profile:
            width = profile['width']
        visible.append(segment)
        widths[segment['id']] = width
        horizontal = a[1] == b[1]
        dx, dz = (0, width/2) if horizontal else (width/2, 0)
        points = [project(a[0]-dx,a[1]-dz), project(b[0]-dx,b[1]-dz),
                  project(b[0]+dx,b[1]+dz), project(a[0]+dx,a[1]+dz)]
        encoded = " ".join(f"{float(x):.3f},{float(y):.3f}" for x,y in points)
        references = " ".join(str(indices[r]) for r in active)
        shared = not segment["access"] and len(active) >= 4
        surface = profile['surface'] if profile else ("#52677b" if shared else "#33465a")
        color = {"HTTP_HIGHWAY": "#f97316", "MESSAGING_PATH": "#a855f7"}.get(segment["kind"], surface)
        grade = f' data-road-grade="{profile["grade"]}"' if profile else ''
        summary = (f'{profile["label"]}; {profile["edgeCount"]} unique edges, '
                   f'{profile["buildingCount"]} files, {profile["crossDistrictEdgeCount"]} cross-major edges; '
                   'full-road static demand; ') if profile else ''
        visibility = 'visible ' if profile else ''
        lines.append(f'<polygon data-access-segment-id="{segment["id"]}" data-route-indexes="{references}" '
                     f'points="{encoded}" fill="{color}"{grade}><title>{summary}{len(active)} {visibility}evidenced relation paths; shared geometry only</title></polygon>')
        if profile and segment['kind'] == 'DEPENDENCY_ROAD' and profile.get('lanePattern') == 'DASHED' and width >= 1.25:
            paints.append((segment, profile.get('marking', '#d4c6a5')))
    trims = junction_trims(routing, visible, widths)
    for segment, color in paints:
        for paint in dash_segments(segment['start'], segment['end'], trims.get(segment['id'], (0, 0))):
            a, b = paint['start'], paint['end']
            dx, dz = (0, .065) if a[1] == b[1] else (.065, 0)
            points = [project(a[0]-dx, a[1]-dz), project(b[0]-dx, b[1]-dz),
                      project(b[0]+dx, b[1]+dz), project(a[0]+dx, a[1]+dz)]
            encoded = ' '.join(f'{float(x):.3f},{float(y):.3f}' for x, y in points)
            lines.append(f'<polygon data-road-paint="arterial-dash" points="{encoded}" fill="{color}" aria-hidden="true"/>')
    lines.append('</g>')
    return lines
