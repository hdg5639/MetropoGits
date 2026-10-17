"""Deterministic directory-anchored City Scene generation."""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections import defaultdict
from pathlib import Path, PurePosixPath
from typing import Any

from scripts.canonical_json import (
    CanonicalJsonError,
    canonical_json_bytes,
    loads_strict_json,
    sha256_digest,
)
from scripts.validate_city import validate_document as validate_city_document
from scripts.validate_ucg import validate_document as validate_ucg_document


LAYOUT_ALGORITHM = "hierarchical-paged/1.0"
DISTRICT_WIDTH = 64
DISTRICT_DEPTH = 64
DISTRICT_PADDING = 16
BUILDING_COLUMNS = 8
BUILDING_SPACING = 7
BUILDING_OFFSET = 6
BUILDING_PAGE_CAPACITY = BUILDING_COLUMNS * BUILDING_COLUMNS

ROLE_STYLES = {
    "ENTRYPOINT": ("GATE", 14),
    "SERVICE": ("SERVICE_OFFICE", 12),
    "PERSISTENCE_ADAPTER": ("STRUCTURED_WAREHOUSE", 10),
    "DOCUMENT_PERSISTENCE_ADAPTER": ("DOCUMENT_DEPOT", 10),
    "CACHE_ADAPTER": ("CACHE_TOWER", 10),
    "MESSAGE_PRODUCER": ("EXCHANGE", 11),
    "MESSAGE_ADAPTER": ("EXCHANGE", 11),
    "HTTP_CLIENT": ("PORT", 11),
    "CONFIGURATION": ("CONTROL_CENTER", 11),
    "GENERAL_COMPONENT": ("GENERIC_BUILDING", 8),
}
ROLE_PRIORITY = {
    "ENTRYPOINT": 0,
    "SERVICE": 1,
    "PERSISTENCE_ADAPTER": 2,
    "DOCUMENT_PERSISTENCE_ADAPTER": 2,
    "CACHE_ADAPTER": 2,
    "MESSAGE_PRODUCER": 3,
    "MESSAGE_ADAPTER": 3,
    "HTTP_CLIENT": 4,
    "CONFIGURATION": 5,
    "GENERAL_COMPONENT": 6,
}


class LayoutError(ValueError):
    """Raised when a UCG cannot be transformed into a valid City Scene."""


def _hash_integer(value: str) -> int:
    return int.from_bytes(hashlib.sha256(value.encode("utf-8")).digest()[:8], "big")


def _allocate_local_slots(entity_ids: list[str]) -> dict[str, int]:
    occupied: set[int] = set()
    result: dict[str, int] = {}
    for entity_id in sorted(entity_ids):
        digest = hashlib.sha256(entity_id.encode("utf-8")).digest()
        home = int.from_bytes(digest[:8], "big") % BUILDING_PAGE_CAPACITY
        stride = (
            int.from_bytes(digest[8:16], "big") % (BUILDING_PAGE_CAPACITY // 2)
        ) * 2 + 1
        page = len(occupied) // BUILDING_PAGE_CAPACITY
        page_offset = page * BUILDING_PAGE_CAPACITY
        selected: int | None = None
        for probe in range(BUILDING_PAGE_CAPACITY):
            candidate = page_offset + (
                (home + probe * stride) % BUILDING_PAGE_CAPACITY
            )
            if candidate not in occupied:
                selected = candidate
                break
        if selected is None:
            raise LayoutError("building page allocation exhausted unexpectedly")
        occupied.add(selected)
        result[entity_id] = selected
    return result


def _root_district_id(repository_id: str) -> str:
    return f"{repository_id}:directory:."


def _district_parent_id(
    path: str, directory_ids: dict[str, str], root_id: str
) -> str:
    parent_path = str(PurePosixPath(path).parent)
    return directory_ids.get(parent_path, root_id)


def _ordered_children(
    district_id: str, children_by_parent: dict[str, list[str]]
) -> list[str]:
    return sorted(
        children_by_parent.get(district_id, []),
        key=lambda child_id: (_hash_integer(child_id), child_id),
    )


def _building_page_count(file_count: int) -> int:
    return max(
        1,
        (file_count + BUILDING_PAGE_CAPACITY - 1) // BUILDING_PAGE_CAPACITY,
    )


def _measure_districts(
    district_id: str,
    children_by_parent: dict[str, list[str]],
    files_by_district: dict[str, list[dict[str, Any]]],
    dimensions: dict[str, tuple[int, int, int]],
) -> tuple[int, int, int]:
    children = _ordered_children(district_id, children_by_parent)
    child_dimensions = [
        _measure_districts(
            child_id,
            children_by_parent,
            files_by_district,
            dimensions,
        )
        for child_id in children
    ]
    direct_depth = DISTRICT_DEPTH * _building_page_count(
        len(files_by_district.get(district_id, []))
    )
    width = DISTRICT_WIDTH
    depth = direct_depth
    if child_dimensions:
        width = max(
            width,
            max(child_width for child_width, _, _ in child_dimensions)
            + 2 * DISTRICT_PADDING,
        )
        depth += DISTRICT_PADDING + sum(
            child_depth + DISTRICT_PADDING
            for _, child_depth, _ in child_dimensions
        )
    dimensions[district_id] = (width, depth, direct_depth)
    return dimensions[district_id]


def _place_districts(
    district_id: str,
    parent_id: str | None,
    x: int,
    z: int,
    children_by_parent: dict[str, list[str]],
    dimensions: dict[str, tuple[int, int, int]],
    districts: list[dict[str, Any]],
) -> None:
    width, depth, direct_depth = dimensions[district_id]
    districts.append(
        {
            "depth": depth,
            "id": district_id,
            "parentId": parent_id,
            "width": width,
            "x": x,
            "z": z,
        }
    )
    child_z = z + direct_depth + DISTRICT_PADDING
    for child_id in _ordered_children(district_id, children_by_parent):
        _place_districts(
            child_id,
            district_id,
            x + DISTRICT_PADDING,
            child_z,
            children_by_parent,
            dimensions,
            districts,
        )
        child_z += dimensions[child_id][1] + DISTRICT_PADDING


def _building_style(entity: dict[str, Any]) -> tuple[str, int, list[str]]:
    roles = entity.get("roles", [])
    recognized = [role for role in roles if role["value"] in ROLE_STYLES]
    if not recognized:
        return "GENERIC_BUILDING", 8, []
    selected = min(
        recognized,
        key=lambda role: (ROLE_PRIORITY[role["value"]], role["value"]),
    )
    archetype, height = ROLE_STYLES[selected["value"]]
    evidence_ids = sorted(
        {evidence_id for role in recognized for evidence_id in role["evidenceIds"]}
    )
    return archetype, height, evidence_ids


def _network_kind(edge_type: str) -> str:
    if edge_type == "HTTP_CALL":
        return "HTTP_HIGHWAY"
    if edge_type in {"PUBLISHES", "SUBSCRIBES"}:
        return "MESSAGING_PATH"
    return "DEPENDENCY_ROAD"


def _network_id(
    kind: str, source_district: str, target_district: str, edge_ids: list[str]
) -> str:
    payload = [kind, source_district, target_district, edge_ids]
    digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return f"network:sha256:{digest}"


def generate_city(ucg: dict[str, Any], theme: str = "minimal") -> dict[str, Any]:
    ucg_errors = validate_ucg_document(ucg)
    if ucg_errors:
        raise LayoutError("invalid UCG: " + "; ".join(ucg_errors))
    if not theme:
        raise LayoutError("theme must be non-empty")

    repository_id = ucg["repository"]["id"]
    root_id = _root_district_id(repository_id)
    directory_entities = [
        entity
        for entity in ucg["entities"]
        if entity["kind"] == "DIRECTORY" and "path" in entity
    ]
    directory_ids = {entity["path"]: entity["id"] for entity in directory_entities}

    file_entities = [
        entity
        for entity in ucg["entities"]
        if entity["kind"] == "FILE" and "path" in entity
    ]
    files_by_district: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for entity in file_entities:
        parent_path = str(PurePosixPath(entity["path"]).parent)
        district_id = directory_ids.get(parent_path, root_id)
        files_by_district[district_id].append(entity)

    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for entity in directory_entities:
        parent_id = _district_parent_id(entity["path"], directory_ids, root_id)
        children_by_parent[parent_id].append(entity["id"])
    dimensions: dict[str, tuple[int, int, int]] = {}
    _measure_districts(
        root_id,
        children_by_parent,
        files_by_district,
        dimensions,
    )
    districts: list[dict[str, Any]] = []
    _place_districts(
        root_id,
        None,
        0,
        0,
        children_by_parent,
        dimensions,
        districts,
    )
    districts.sort(key=lambda item: item["id"])
    districts_by_id = {item["id"]: item for item in districts}

    buildings: list[dict[str, Any]] = []
    entity_districts: dict[str, str] = {}
    for district_id in sorted(files_by_district):
        district = districts_by_id[district_id]
        entities = files_by_district[district_id]
        local_slots = _allocate_local_slots([entity["id"] for entity in entities])
        for entity in sorted(entities, key=lambda item: item["id"]):
            slot = local_slots[entity["id"]]
            page, page_slot = divmod(slot, BUILDING_PAGE_CAPACITY)
            column = page_slot % BUILDING_COLUMNS
            row = page_slot // BUILDING_COLUMNS
            archetype, height, evidence_ids = _building_style(entity)
            buildings.append(
                {
                    "archetype": archetype,
                    "depth": 4,
                    "districtId": district_id,
                    "entityId": entity["id"],
                    "evidenceIds": evidence_ids,
                    "height": height,
                    "styleVariant": entity.get("language") or "unknown",
                    "width": 4,
                    "x": district["x"] + BUILDING_OFFSET + column * BUILDING_SPACING,
                    "z": (
                        district["z"]
                        + page * DISTRICT_DEPTH
                        + BUILDING_OFFSET
                        + row * BUILDING_SPACING
                    ),
                }
            )
            entity_districts[entity["id"]] = district_id
    buildings.sort(key=lambda item: item["entityId"])

    grouped_edges: dict[tuple[str, str, str], list[str]] = defaultdict(list)
    for edge in ucg["edges"]:
        if edge["type"] == "CONTAINS":
            continue
        source_district = entity_districts.get(edge["from"])
        target_district = entity_districts.get(edge["to"])
        if source_district is None or target_district is None:
            continue
        grouped_edges[
            (_network_kind(edge["type"]), source_district, target_district)
        ].append(edge["id"])

    networks: list[dict[str, Any]] = []
    for (kind, source_id, target_id), unsorted_edge_ids in grouped_edges.items():
        edge_ids = sorted(unsorted_edge_ids)
        source = districts_by_id[source_id]
        target = districts_by_id[target_id]
        start = [source["x"] + source["width"] / 2, source["z"] + source["depth"] / 2]
        end = [target["x"] + target["width"] / 2, target["z"] + target["depth"] / 2]
        if start == end:
            path = [
                start,
                [start[0] + 12, start[1]],
                [start[0] + 12, start[1] + 12],
                [start[0], start[1] + 12],
            ]
        else:
            path = [start, [end[0], start[1]], end]
        networks.append(
            {
                "edgeIds": edge_ids,
                "id": _network_id(kind, source_id, target_id, edge_ids),
                "kind": kind,
                "path": path,
            }
        )
    networks.sort(key=lambda item: item["id"])

    scene: dict[str, Any] = {
        "buildings": buildings,
        "decorations": [],
        "districts": districts,
        "layoutAlgorithm": LAYOUT_ALGORITHM,
        "networks": networks,
        "schemaVersion": "city/0.1",
        "theme": theme,
        "ucgDigest": sha256_digest(ucg),
    }
    scene_errors = validate_city_document(scene, ucg)
    if scene_errors:
        raise LayoutError("generated invalid City Scene: " + "; ".join(scene_errors))
    return scene


def _load_ucg(path: Path) -> dict[str, Any]:
    try:
        document = loads_strict_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, CanonicalJsonError) as error:
        raise LayoutError(f"unable to read UCG: {error}") from error
    if not isinstance(document, dict):
        raise LayoutError("UCG root must be an object")
    return document


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--theme", default="minimal")
    args = parser.parse_args()

    try:
        scene = generate_city(_load_ucg(args.graph), args.theme)
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(canonical_json_bytes(scene))
    except (OSError, LayoutError, ValueError) as error:
        print(f"City generation failed: {error}", file=sys.stderr)
        return 2

    print(f"Wrote City Scene with {len(scene['buildings'])} buildings: {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
