"""Deterministic CPU isometric showcase of the same canonical city (ADR-013)."""

from __future__ import annotations

import json
import math
from collections import Counter

from metropogits.building_forms import building_parts
from metropogits.preview import (
    ARCHETYPE_COLORS,
    MAJOR_DISTRICT_COLORS,
    MAX_DIMENSION,
    MIN_HEIGHT,
    MIN_WIDTH,
    PreviewError,
    _escape,
    _fmt,
    _major_district_ids,
    _palette,
)
from metropogits.projection import aggregate_parts, derive_blocks, district_owners
from metropogits.streets import derive_street_grid
from metropogits.access_routes import derive_access_routes, svg_access_lines
from metropogits.road_hierarchy import derive_road_hierarchy
from metropogits.territory import derive_district_territories
from scripts.canonical_json import canonical_json_bytes
from scripts.validate_city import validate_document


def _corners(rect):
    x, z, w, d = rect["x"], rect["z"], rect["width"], rect["depth"]
    return [(x, z), (x + w, z), (x + w, z + d), (x, z + d)]


def _rotate(x, z, turn):
    return ((x, z), (-z, x), (-x, -z), (z, -x))[turn]


def _iso(x, z, y=0):
    return (x - z) * math.sqrt(3) / 2, (x + z) / 2 - y


def _shade(color, factor):
    values = [int(color[i : i + 2], 16) for i in (1, 3, 5)]
    return "#" + "".join(f"{max(0, min(255, round(v * factor))):02x}" for v in values)


def _painted_occupancy(polygons, box):
    """Deterministic 160x90 center-sampled coverage, excluding text and routes."""
    columns, rows = 160, 90
    sx, sy = box["width"] / columns, box["height"] / rows
    covered = set()
    for points in polygons:
        start = max(0, math.ceil((min(y for _, y in points) - box["y"]) / sy - 0.5))
        end = min(rows, math.ceil((max(y for _, y in points) - box["y"]) / sy - 0.5))
        for row in range(start, end):
            y = box["y"] + (row + 0.5) * sy
            crossings = []
            for (x0, y0), (x1, y1) in zip(points, points[1:] + points[:1]):
                if min(y0, y1) <= y < max(y0, y1):
                    crossings.append(x0 + (x1 - x0) * (y - y0) / (y1 - y0))
            crossings.sort()
            for left, right in zip(crossings[::2], crossings[1::2]):
                first = max(0, math.ceil((left - box["x"]) / sx - 0.5))
                last = min(columns, math.ceil((right - box["x"]) / sx - 0.5))
                covered.update((column, row) for column in range(first, last))
    return len(covered) / (columns * rows)


def _selected_networks(scene, graph):
    owners = district_owners(scene)
    files = {b["entityId"]: owners[b["districtId"]] for b in scene["buildings"]}
    edges = {edge["id"]: edge for edge in graph["edges"]}

    def rank(network):
        cross = any(
            files.get(edges[e]["from"]) != files.get(edges[e]["to"])
            for e in network["edgeIds"]
        )
        return -int(cross), -len(set(network["edgeIds"])), network["id"]

    return sorted(sorted(scene["networks"], key=rank)[:24], key=lambda n: n["id"])


def render_showcase(scene, graph, width=1200, height=675, routing=None):
    """Render a traceable SVG; never execute source or mutate graph/scene."""
    errors = validate_document(scene, graph)
    if errors:
        raise PreviewError("invalid City Scene: " + "; ".join(errors))
    # Strict JSON uses Decimal; rendering uses floating-point geometry like the
    # browser. Normalize a private copy without modifying canonical input.
    scene = json.loads(canonical_json_bytes(scene))
    if not MIN_WIDTH <= width <= MAX_DIMENSION:
        raise PreviewError(f"width must be between {MIN_WIDTH} and {MAX_DIMENSION}")
    if not MIN_HEIGHT <= height <= MAX_DIMENSION:
        raise PreviewError(f"height must be between {MIN_HEIGHT} and {MAX_DIMENSION}")
    routing = routing if routing is not None else derive_access_routes(scene, graph)
    palette = _palette(scene["theme"])
    territories = derive_district_territories(scene)
    by_territory = {t["id"]: t for t in territories["districts"]}
    entities = {e["id"]: e for e in graph["entities"]}
    major_ids = sorted(_major_district_ids(scene))
    blocks = derive_blocks(scene, territories) if len(scene["buildings"]) >= 256 else []
    networks = _selected_networks(scene, graph)
    streets = derive_street_grid(scene)["rectangles"]
    mapping = {}
    models = []
    for block in blocks:
        mapping[block["id"]] = {
            k: block[k]
            for k in (
                "districtId",
                "majorDistrictId",
                "memberEntityIds",
                "memberDistrictIds",
            )
        }
        mapping[block["id"]]["kind"] = "visual-block"
        for part in aggregate_parts(block):
            models.append((part, block["id"]))
    if not blocks:
        for building in scene["buildings"]:
            mapping[building["entityId"]] = dict(
                kind="file",
                entityId=building["entityId"],
                districtId=building["districtId"],
            )
            models.append((building, building["entityId"]))
    for network in networks:
        mapping[network["id"]] = dict(kind="network", edgeIds=network["edgeIds"])
    visible_districts = sorted(
        set(major_ids) | {d["id"] for d in scene["districts"] if d["parentId"] is None}
    )
    for district_id in visible_districts:
        mapping[district_id] = dict(kind="district", districtId=district_id)
    mapping["visual:streets"] = dict(kind="structural-streets", semantic=False,
                                     basis=routing["version"], networkIds=sorted(n["id"] for n in networks))

    surfaces = [
        (r, district_id)
        for district_id in visible_districts
        for r in by_territory[district_id]["rectangles"]
    ]
    plots = [(p, b["id"]) for b in blocks for p in b["plots"]]
    cuboids = [
        (part, model["archetype"], owner)
        for model, owner in models
        for part in building_parts(model)
    ]
    ground_points = [p for rect, _ in surfaces + plots for p in _corners(rect)]
    ground_points += [p for r in streets for p in _corners(r)]
    ground_points += [tuple(p) for n in networks for p in n["path"]]
    world_points = [(x, z, 0) for x, z in ground_points]
    world_points += [
        (x, z, y)
        for part, _, _ in cuboids
        for x, z in _corners(part)
        for y in (part["y"], part["y"] + part["height"])
    ]
    # Reserve labels around geometry as well as fixed header / legend regions.
    frame = max(0.75, min(1, width / 1200, height / 675))
    box = dict(
        x=28 * frame,
        y=96 * frame,
        width=width - 56 * frame,
        height=height - 166 * frame,
    )
    cameras = []
    for turn in range(4):
        projected = [_iso(*_rotate(x, z, turn), y) for x, z, y in world_points] or [
            (0, 0),
            (1, 1),
        ]
        min_x, min_y = min(p[0] for p in projected), min(p[1] for p in projected)
        span_x = max(1, max(p[0] for p in projected) - min_x)
        span_y = max(1, max(p[1] for p in projected) - min_y)
        scale = min(box["width"] / span_x, box["height"] / span_y)
        occupancy = span_x * span_y * scale * scale / (box["width"] * box["height"])
        cameras.append((occupancy, -turn, scale, min_x, min_y, span_x, span_y))
    occupancy, negative_turn, scale, min_x, min_y, span_x, span_y = max(cameras)
    turn = -negative_turn
    origin_x = box["x"] + (box["width"] - span_x * scale) / 2
    origin_y = box["y"] + (box["height"] - span_y * scale) / 2

    def project_rotated(x, z, y=0):
        px, py = _iso(x, z, y)
        return origin_x + (px - min_x) * scale, origin_y + (py - min_y) * scale

    def project(x, z, y=0):
        return project_rotated(*_rotate(x, z, turn), y)

    def points_text(points):
        return " ".join(f"{_fmt(x)},{_fmt(y)}" for x, y in points)

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">',
        f'<title id="title">MetropoGits showcase · {_escape(graph["repository"]["id"])}</title>',
        '<desc id="description">Isometric repository city. Block masses are visual aggregates, '
        "not additional code entities. Structural streets are not dependency evidence. "
        "Relationship routes retain canonical endpoints. Open the viewer for source inspection.</desc>",
        "<defs>",
        f'<clipPath id="content-clip"><rect x="0" y="70" width="{width}" height="{height - 122}"/></clipPath>',
        "</defs>",
        f'<rect width="{width}" height="{height}" fill="{palette["background"]}"/>',
        '<g id="city" clip-path="url(#content-clip)">',
    ]
    polygons_for_occupancy = []

    def polygon(points, color, attrs="", opacity=1):
        polygons_for_occupancy.append(points)
        lines.append(
            f'<polygon points="{points_text(points)}" fill="{color}" '
            f'fill-opacity="{opacity}" stroke="{_shade(color, 1.2)}" stroke-width="0.4" {attrs}/>'
        )

    colors = {
        d: MAJOR_DISTRICT_COLORS[i % len(MAJOR_DISTRICT_COLORS)]
        for i, d in enumerate(major_ids)
    }
    # Parent ground first; major overlays retain the same canonical locations.
    for rect, district_id in sorted(
        surfaces, key=lambda pair: (pair[1] in major_ids, pair[1])
    ):
        polygon(
            [project(x, z) for x, z in _corners(rect)],
            colors.get(district_id, "#172236"),
            f'data-map-id="{_escape(district_id)}"',
        )
    for plot, owner in plots:
        polygon(
            [project(x, z, 0.05) for x, z in _corners(plot)],
            "#344154",
            f'data-map-id="{_escape(owner)}"',
            0.8,
        )
    lines.extend(svg_access_lines(routing, project, overview=bool(blocks), network_ids={n["id"] for n in networks},
                                  hierarchy=derive_road_hierarchy(scene, routing)))
    faces = []
    for part, archetype, owner in cuboids:
        rotated = [_rotate(x, z, turn) for x, z in _corners(part)]
        x0, x1 = min(p[0] for p in rotated), max(p[0] for p in rotated)
        z0, z1 = min(p[1] for p in rotated), max(p[1] for p in rotated)
        y0, y1 = part["y"], part["y"] + part["height"]
        base = ARCHETYPE_COLORS.get(archetype, ARCHETYPE_COLORS["GENERIC_BUILDING"])[0]
        for vertices, shade in [
            ([(x1, z0, y0), (x1, z1, y0), (x1, z1, y1), (x1, z0, y1)], 0.63),
            ([(x0, z1, y0), (x1, z1, y0), (x1, z1, y1), (x0, z1, y1)], 0.8),
            ([(x0, z0, y1), (x1, z0, y1), (x1, z1, y1), (x0, z1, y1)], 1.05),
        ]:
            depth = sum(x + z + y for x, z, y in vertices) / 4
            faces.append(
                (
                    depth,
                    owner,
                    vertices,
                    _shade(base, shade + part["shade"] * 0.2),
                    archetype,
                )
            )
    for _, owner, vertices, color, archetype in sorted(
        faces, key=lambda f: (f[0], f[1])
    ):
        polygon(
            [project_rotated(*p) for p in vertices],
            color,
            f'data-map-id="{_escape(owner)}" data-archetype="{_escape(archetype)}"',
        )

    labels = []
    paths = {d: entities.get(d, {}).get("path", d) for d in major_ids}
    shorts = Counter(p.rsplit("/", 1)[-1] for p in paths.values())
    for district_id in major_ids:
        path = paths[district_id]
        text = path if shorts[path.rsplit("/", 1)[-1]] > 1 else path.rsplit("/", 1)[-1]
        text = text[:36] + "…" if len(text) > 37 else text
        anchor = by_territory[district_id]["landmarkPlot"]
        px, py = project(
            anchor["x"] + anchor["width"] / 2, anchor["z"] + anchor["depth"] / 2
        )
        label_width = min(width - 40, len(text) * 7 + 16)
        for offset in (-28, -52, 8, 32, -76, 56):
            x = max(12, min(width - label_width - 12, px - label_width / 2))
            y = max(72, min(height - 80, py + offset))
            rect = dict(x=x, y=y, width=label_width, height=22)
            if any(
                x < r["x"] + r["width"] + 6
                and x + label_width + 6 > r["x"]
                and y < r["y"] + r["height"] + 4
                and y + 26 > r["y"]
                for r in labels
            ):
                continue
            labels.append({**rect, "districtId": district_id, "text": text})
            lines.append(
                f'<g data-map-id="{_escape(district_id)}"><title>{_escape(path)}</title>'
                f'<path d="M {_fmt(px)} {_fmt(py)} L {_fmt(x + label_width / 2)} {_fmt(y + 22)}" '
                'stroke="#94a3b8" stroke-width="0.7"/>'
                f'<rect x="{_fmt(x)}" y="{_fmt(y)}" width="{_fmt(label_width)}" height="22" '
                'rx="4" fill="#101c2d" stroke="#678099" stroke-width="0.7"/>'
                f'<text x="{_fmt(x + 8)}" y="{_fmt(y + 15)}" fill="#e2e8f0" '
                f'font-size="12" font-family="sans-serif">{_escape(text)}</text></g>'
            )
            break
    lines.append("</g>")
    # Always paint protected title / legend last. Long repository IDs are bounded.
    name = graph["repository"]["id"]
    max_chars = max(12, (width - 60) // 11)
    title = name if len(name) <= max_chars else name[: max_chars - 1] + "…"
    summary = (
        f"{len(scene['buildings']):,} files · {len(blocks)} visual blocks"
        if blocks
        else f"{len(models)} file buildings"
    )
    summary += f" · {len(networks)}/{len(scene['networks'])} routes"
    lines += [
        f'<text x="28" y="30" fill="{palette["text"]}" font-family="sans-serif" '
        f'font-size="20" font-weight="700">{_escape(title)}</text>',
        f'<text x="28" y="52" fill="{palette["muted"]}" font-family="sans-serif" '
        f'font-size="11">{_escape(summary)}</text>',
        f'<text x="28" y="{height - 31}" fill="{palette["text"]}" font-family="sans-serif" '
        'font-size="11">METROPOGITS · Your code is a living city</text>',
        f'<text x="28" y="{height - 14}" fill="{palette["muted"]}" font-family="sans-serif" '
        'font-size="10">Visual aggregates · Source evidence in viewer</text>',
    ]
    metadata = dict(
        projectionVersion="showcase/0.1",
        ucgDigest=scene["ucgDigest"],
        mappings=mapping,
        hiddenNetworkIds=sorted(
            n["id"] for n in scene["networks"] if n not in networks
        ),
        camera=dict(
            quarterTurn=turn,
            scale=scale,
            contentBounds=box,
            projectedBounds=dict(
                x=origin_x, y=origin_y, width=span_x * scale, height=span_y * scale
            ),
            boundingBoxOccupancy=occupancy,
            paintedAreaOccupancy=_painted_occupancy(polygons_for_occupancy, box),
            paintedAreaSampling="160x90 polygon centers; excludes labels and route strokes",
        ),
        labels=labels,
        hiddenLabelIds=sorted(
            set(major_ids) - {label["districtId"] for label in labels}
        ),
    )
    lines.append(
        '<metadata id="showcase-metadata">'
        + _escape(
            json.dumps(
                metadata, sort_keys=True, separators=(",", ":"), ensure_ascii=True
            )
        )
        + "</metadata>"
    )
    lines.append("</svg>")
    return ("\n".join(lines) + "\n").encode("utf-8")
