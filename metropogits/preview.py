"""Deterministic CPU-only SVG preview renderer."""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path
from typing import Any

from scripts.canonical_json import CanonicalJsonError, loads_strict_json
from scripts.validate_city import validate_document as validate_city_document


MIN_WIDTH = 320
MIN_HEIGHT = 240
MAX_DIMENSION = 4096
HEADER_HEIGHT = 64
PADDING = 28

ARCHETYPE_COLORS = {
    "CACHE_TOWER": ("#facc15", "#ca8a04", "#713f12"),
    "CONTROL_CENTER": ("#a78bfa", "#6d28d9", "#4c1d95"),
    "DOCUMENT_DEPOT": ("#fb923c", "#c2410c", "#7c2d12"),
    "EXCHANGE": ("#2dd4bf", "#0f766e", "#134e4a"),
    "GATE": ("#f472b6", "#be185d", "#831843"),
    "GENERIC_BUILDING": ("#94a3b8", "#475569", "#334155"),
    "LIBRARY": ("#facc15", "#a16207", "#713f12"),
    "PORT": ("#38bdf8", "#0369a1", "#0c4a6e"),
    "SERVICE_OFFICE": ("#60a5fa", "#1d4ed8", "#1e3a8a"),
    "STRUCTURED_WAREHOUSE": ("#34d399", "#047857", "#064e3b"),
}
NETWORK_COLORS = {
    "DEPENDENCY_ROAD": "#64748b",
    "HTTP_HIGHWAY": "#f97316",
    "MESSAGING_PATH": "#a855f7",
}


class PreviewError(ValueError):
    """Raised when a preview cannot be rendered safely."""


def _escape(value: Any) -> str:
    text = str(value)
    xml_safe = "".join(
        character
        if (
            ord(character) in {0x09, 0x0A, 0x0D}
            or 0x20 <= ord(character) <= 0xD7FF
            or 0xE000 <= ord(character) <= 0xFFFD
            or 0x10000 <= ord(character) <= 0x10FFFF
        )
        else "�"
        for character in text
    )
    return html.escape(xml_safe, quote=True)


def _fmt(value: float) -> str:
    if abs(value) < 0.0005:
        return "0"
    return f"{value:.3f}".rstrip("0").rstrip(".")


def _bounds(scene: dict[str, Any]) -> tuple[float, float, float, float]:
    points: list[tuple[float, float]] = []
    for district in scene["districts"]:
        x = float(district["x"])
        z = float(district["z"])
        points.extend(
            [
                (x, z),
                (x + float(district["width"]), z + float(district["depth"])),
            ]
        )
    for network in scene["networks"]:
        points.extend((float(point[0]), float(point[1])) for point in network["path"])
    if not points:
        return 0.0, 0.0, 1.0, 1.0
    xs = [point[0] for point in points]
    zs = [point[1] for point in points]
    return min(xs), min(zs), max(xs), max(zs)


def _drawable_district_ids(scene: dict[str, Any]) -> set[str]:
    districts = {item["id"]: item for item in scene["districts"]}
    children: dict[str, list[str]] = {}
    for district in scene["districts"]:
        parent_id = district["parentId"]
        if parent_id is not None:
            children.setdefault(parent_id, []).append(district["id"])
    with_buildings = {item["districtId"] for item in scene["buildings"]}
    result: set[str] = set()
    for district in scene["districts"]:
        child_ids = children.get(district["id"], [])
        if district["id"] in with_buildings or len(child_ids) != 1:
            result.add(district["id"])
            continue
        child = districts[child_ids[0]]
        geometry = tuple(district[key] for key in ("x", "z", "width", "depth"))
        child_geometry = tuple(child[key] for key in ("x", "z", "width", "depth"))
        if geometry != child_geometry:
            result.add(district["id"])
    return result


def _district_label_candidates(
    scene: dict[str, Any],
    drawable_ids: set[str],
    labels: dict[str, str],
    root_ids: set[str],
    repository_id: str,
    project: Any,
    width: int,
    height: int,
) -> dict[str, str]:
    districts = {item["id"]: item for item in scene["districts"]}
    depths: dict[str, int] = {}

    def district_depth(district_id: str) -> int:
        if district_id in depths:
            return depths[district_id]
        parent_id = districts[district_id]["parentId"]
        depth = 0 if parent_id is None else district_depth(parent_id) + 1
        depths[district_id] = depth
        return depth

    populated = {item["districtId"] for item in scene["buildings"]}
    candidates: list[dict[str, Any]] = []
    for district in scene["districts"]:
        if district["id"] not in drawable_ids:
            continue
        x, y = project(district["x"], district["z"])
        right, bottom = project(
            district["x"] + district["width"],
            district["z"] + district["depth"],
        )
        full_label = (
            repository_id
            if district["id"] in root_ids
            else labels.get(district["id"], district["id"])
        )
        canvas_label = full_label.rsplit("/", 1)[-1] or full_label
        available_width = max(0, right - x - 12)
        max_characters = int(available_width // 6)
        if max_characters < 3 or bottom - y < 18:
            continue
        if len(canvas_label) > max_characters:
            canvas_label = canvas_label[: max_characters - 1] + "…"
        label_width = len(canvas_label) * 6 + 4
        candidates.append(
            {
                "height": 14,
                "id": district["id"],
                "label": canvas_label,
                "priority": (1000 if district["id"] in populated else 0)
                + district_depth(district["id"]),
                "width": label_width,
                "x": x + 4,
                "y": y + 3,
            }
        )

    accepted: list[dict[str, Any]] = []
    for candidate in sorted(
        candidates, key=lambda item: (-item["priority"], item["id"])
    ):
        if (
            candidate["x"] < 0
            or candidate["y"] < HEADER_HEIGHT
            or candidate["x"] + candidate["width"] > width
            or candidate["y"] + candidate["height"] > height
        ):
            continue
        overlaps = any(
            candidate["x"] < item["x"] + item["width"] + 3
            and item["x"] < candidate["x"] + candidate["width"] + 3
            and candidate["y"] < item["y"] + item["height"] + 3
            and item["y"] < candidate["y"] + candidate["height"] + 3
            for item in accepted
        )
        if not overlaps:
            accepted.append(candidate)
    return {item["id"]: item["label"] for item in accepted}


def _palette(theme: str) -> dict[str, str]:
    if theme == "cyberpunk":
        return {
            "background": "#090414",
            "district": "#17112b",
            "districtBorder": "#5b21b6",
            "grid": "#2e1065",
            "muted": "#c4b5fd",
            "text": "#f5f3ff",
        }
    return {
        "background": "#0f172a",
        "district": "#1e293b",
        "districtBorder": "#475569",
        "grid": "#334155",
        "muted": "#94a3b8",
        "text": "#f8fafc",
    }


def render_preview(
    scene: dict[str, Any],
    ucg: dict[str, Any],
    width: int = 1200,
    height: int = 675,
) -> bytes:
    errors = validate_city_document(scene, ucg)
    if errors:
        raise PreviewError("invalid City Scene: " + "; ".join(errors))
    if not MIN_WIDTH <= width <= MAX_DIMENSION:
        raise PreviewError(f"width must be between {MIN_WIDTH} and {MAX_DIMENSION}")
    if not MIN_HEIGHT <= height <= MAX_DIMENSION:
        raise PreviewError(f"height must be between {MIN_HEIGHT} and {MAX_DIMENSION}")

    palette = _palette(scene["theme"])
    min_x, min_z, max_x, max_z = _bounds(scene)
    world_width = max(max_x - min_x, 1.0)
    world_depth = max(max_z - min_z, 1.0)
    drawing_width = width - PADDING * 2
    drawing_height = height - HEADER_HEIGHT - PADDING * 2
    scale = min(drawing_width / world_width, drawing_height / world_depth)
    content_width = world_width * scale
    content_height = world_depth * scale
    origin_x = PADDING + (drawing_width - content_width) / 2
    origin_y = HEADER_HEIGHT + PADDING + (drawing_height - content_height) / 2

    def project(x: Any, z: Any) -> tuple[float, float]:
        projected_x = origin_x + (float(x) - min_x) * scale
        projected_y = origin_y + (float(z) - min_z) * scale
        return projected_x, projected_y

    entities = {entity["id"]: entity for entity in ucg["entities"]}
    district_labels = {
        entity["id"]: entity.get("path", entity["id"])
        for entity in ucg["entities"]
        if entity["kind"] == "DIRECTORY"
    }
    root_ids = {
        district["id"] for district in scene["districts"] if district["parentId"] is None
    }
    repository_id = ucg["repository"]["id"]
    drawable_district_ids = _drawable_district_ids(scene)
    visible_district_labels = _district_label_candidates(
        scene,
        drawable_district_ids,
        district_labels,
        root_ids,
        repository_id,
        project,
        width,
        height,
    )

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
            f'height="{height}" viewBox="0 0 {width} {height}" role="img" '
            'aria-labelledby="preview-title preview-description">'
        ),
        f"  <title id=\"preview-title\">MetropoGits preview · {_escape(repository_id)}</title>",
        (
            "  <desc id=\"preview-description\">"
            f"{len(scene['districts'])} districts, {len(scene['buildings'])} buildings, "
            f"and {len(scene['networks'])} networks.</desc>"
        ),
        "  <defs>",
        (
            "    <pattern id=\"city-grid\" width=\"16\" height=\"16\" "
            "patternUnits=\"userSpaceOnUse\">"
        ),
        f"      <path d=\"M 16 0 L 0 0 0 16\" fill=\"none\" stroke=\"{palette['grid']}\" stroke-width=\"0.5\"/>",
        "    </pattern>",
        "  </defs>",
        f"  <rect width=\"{width}\" height=\"{height}\" fill=\"{palette['background']}\"/>",
        (
            f"  <rect y=\"{HEADER_HEIGHT}\" width=\"{width}\" "
            f"height=\"{height - HEADER_HEIGHT}\" fill=\"url(#city-grid)\" "
            "opacity=\"0.35\"/>"
        ),
        (
            f"  <text x=\"{PADDING}\" y=\"30\" fill=\"{palette['text']}\" "
            "font-family=\"system-ui, sans-serif\" font-size=\"20\" "
            f"font-weight=\"700\">MetropoGits · {_escape(repository_id)}</text>"
        ),
        (
            f"  <text x=\"{PADDING}\" y=\"50\" fill=\"{palette['muted']}\" "
            "font-family=\"system-ui, sans-serif\" font-size=\"12\">"
            f"{len(scene['buildings'])} buildings · {len(scene['districts'])} districts · "
            f"{len(scene['networks'])} networks</text>"
        ),
        "  <g id=\"districts\">",
    ]

    for district in scene["districts"]:
        if district["id"] not in drawable_district_ids:
            continue
        x, y = project(district["x"], district["z"])
        district_width = max(float(district["width"]) * scale, 1.0)
        district_depth = max(float(district["depth"]) * scale, 1.0)
        label = (
            repository_id
            if district["id"] in root_ids
            else district_labels.get(district["id"], district["id"])
        )
        lines.extend(
            [
                f"    <g data-district-id=\"{_escape(district['id'])}\">",
                f"      <title>{_escape(label)}</title>",
                (
                    f"      <rect x=\"{_fmt(x)}\" y=\"{_fmt(y)}\" "
                    f"width=\"{_fmt(district_width)}\" height=\"{_fmt(district_depth)}\" "
                    f"rx=\"4\" fill=\"{palette['district']}\" fill-opacity=\"0.82\" "
                    f"stroke=\"{palette['districtBorder']}\" stroke-width=\"1.5\"/>"
                ),
            ]
        )
        canvas_label = visible_district_labels.get(district["id"])
        if canvas_label is not None:
            lines.append(
                f"      <text x=\"{_fmt(x + 6)}\" y=\"{_fmt(y + 15)}\" "
                f"fill=\"{palette['muted']}\" font-family=\"system-ui, sans-serif\" "
                f"font-size=\"10\">{_escape(canvas_label)}</text>"
            )
        lines.append("    </g>")
    lines.append("  </g>")

    lines.append("  <g id=\"networks\" fill=\"none\">")
    for network in scene["networks"]:
        projected = [project(point[0], point[1]) for point in network["path"]]
        points = " ".join(f"{_fmt(x)},{_fmt(y)}" for x, y in projected)
        color = NETWORK_COLORS.get(network["kind"], NETWORK_COLORS["DEPENDENCY_ROAD"])
        edge_summary = ", ".join(network["edgeIds"])
        lines.extend(
            [
                (
                    f"    <polyline data-network-id=\"{_escape(network['id'])}\" "
                    f"points=\"{points}\" stroke=\"#0f172a\" stroke-width=\"6\" "
                    "stroke-linejoin=\"round\" stroke-linecap=\"round\" "
                    "opacity=\"0.75\"/>"
                ),
                (
                    f"    <polyline points=\"{points}\" stroke=\"{color}\" "
                    "stroke-width=\"2.5\" stroke-linejoin=\"round\" "
                    "stroke-linecap=\"round\"><title>"
                    f"{_escape(network['kind'])}: {_escape(edge_summary)}"
                    "</title></polyline>"
                ),
            ]
        )
    lines.append("  </g>")

    lines.append("  <g id=\"buildings\">")
    for building in scene["buildings"]:
        x, y = project(building["x"], building["z"])
        building_width = max(float(building["width"]) * scale, 2.0)
        building_depth = max(float(building["depth"]) * scale, 2.0)
        extrusion = max(3.0, min(16.0, float(building["height"]) * 0.8))
        offset_x = extrusion * 0.45
        top_x = x - offset_x
        top_y = y - extrusion
        top_color, right_color, front_color = ARCHETYPE_COLORS.get(
            building["archetype"], ARCHETYPE_COLORS["GENERIC_BUILDING"]
        )
        entity = entities.get(building["entityId"], {})
        label = entity.get("path", building["entityId"])
        title = f"{label} · {building['archetype']}"
        right_points = " ".join(
            [
                f"{_fmt(top_x + building_width)},{_fmt(top_y)}",
                f"{_fmt(x + building_width)},{_fmt(y)}",
                f"{_fmt(x + building_width)},{_fmt(y + building_depth)}",
                f"{_fmt(top_x + building_width)},{_fmt(top_y + building_depth)}",
            ]
        )
        front_points = " ".join(
            [
                f"{_fmt(top_x)},{_fmt(top_y + building_depth)}",
                f"{_fmt(top_x + building_width)},{_fmt(top_y + building_depth)}",
                f"{_fmt(x + building_width)},{_fmt(y + building_depth)}",
                f"{_fmt(x)},{_fmt(y + building_depth)}",
            ]
        )
        lines.extend(
            [
                (
                    f"    <g data-entity-id=\"{_escape(building['entityId'])}\" "
                    f"data-archetype=\"{_escape(building['archetype'])}\">"
                ),
                f"      <title>{_escape(title)}</title>",
                (
                    f"      <polygon points=\"{right_points}\" fill=\"{right_color}\" "
                    'stroke="#0f172a" stroke-width="0.75"/>'
                ),
                (
                    f"      <polygon points=\"{front_points}\" fill=\"{front_color}\" "
                    'stroke="#0f172a" stroke-width="0.75"/>'
                ),
                (
                    f"      <rect x=\"{_fmt(top_x)}\" y=\"{_fmt(top_y)}\" "
                    f"width=\"{_fmt(building_width)}\" height=\"{_fmt(building_depth)}\" "
                    f"rx=\"1\" fill=\"{top_color}\" stroke=\"#0f172a\" "
                    'stroke-width="0.75"/>'
                ),
                "    </g>",
            ]
        )
    lines.extend(["  </g>", "</svg>"])
    return ("\n".join(lines) + "\n").encode("utf-8")


def _load_document(path: Path, label: str) -> dict[str, Any]:
    try:
        document = loads_strict_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, CanonicalJsonError) as error:
        raise PreviewError(f"unable to read {label}: {error}") from error
    if not isinstance(document, dict):
        raise PreviewError(f"{label} root must be an object")
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scene", type=Path, required=True)
    parser.add_argument("--ucg", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--width", type=int, default=1200)
    parser.add_argument("--height", type=int, default=675)
    args = parser.parse_args()

    try:
        scene = _load_document(args.scene, "City Scene")
        ucg = _load_document(args.ucg, "UCG")
        preview = render_preview(scene, ucg, args.width, args.height)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(preview)
    except (OSError, PreviewError, ValueError) as error:
        print(f"Preview rendering failed: {error}", file=sys.stderr)
        return 2

    print(f"Wrote deterministic SVG preview: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
