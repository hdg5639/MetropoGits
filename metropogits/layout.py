"""Deterministic directory-anchored City Scene generation."""

from __future__ import annotations

import argparse
import hashlib
import math
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


LAYOUT_ALGORITHM = "hierarchical-paged/1.10"
HINT_LAYOUT_ALGORITHMS = frozenset({LAYOUT_ALGORITHM})
DISTRICT_DEPTH = 64
DISTRICT_PADDING = 4
MIN_DISTRICT_SIZE = 14
EMPTY_DISTRICT_SIZE = 8
DISTRICT_EDGE_PADDING = 2
BUILDING_COLUMNS = 8
BUILDING_SPACING = 7
BUILDING_OFFSET = 3
BUILDING_SIZE = 6
BUILDING_PAGE_CAPACITY = BUILDING_COLUMNS * BUILDING_COLUMNS
MAX_HINT_ITEMS = 100_000
NETWORK_ZONE_CITY_THRESHOLD = 256
NETWORK_ZONE_MIN_BUILDINGS = 20
NETWORK_ZONE_MAX_BUILDINGS = 64

ROLE_STYLES = {
    "ENTRYPOINT": ("GATE", 18),
    "SERVICE": ("SERVICE_OFFICE", 16),
    "PERSISTENCE_ADAPTER": ("STRUCTURED_WAREHOUSE", 14),
    "DOCUMENT_PERSISTENCE_ADAPTER": ("DOCUMENT_DEPOT", 14),
    "CACHE_ADAPTER": ("CACHE_TOWER", 14),
    "MESSAGE_PRODUCER": ("EXCHANGE", 15),
    "MESSAGE_ADAPTER": ("EXCHANGE", 15),
    "HTTP_CLIENT": ("PORT", 15),
    "CONFIGURATION": ("CONTROL_CENTER", 15),
    "GENERAL_COMPONENT": ("GENERIC_BUILDING", 10),
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


def _allocate_local_slots(
    entity_ids: list[str], locked: dict[str, int] | None = None
) -> dict[str, int]:
    known_ids = set(entity_ids)
    result = {
        entity_id: slot
        for entity_id, slot in (locked or {}).items()
        if entity_id in known_ids
    }
    occupied = set(result.values())
    for entity_id in sorted(known_ids - set(result)):
        digest = hashlib.sha256(entity_id.encode("utf-8")).digest()
        home = int.from_bytes(digest[:8], "big") % BUILDING_PAGE_CAPACITY
        stride = (
            int.from_bytes(digest[8:16], "big") % (BUILDING_PAGE_CAPACITY // 2)
        ) * 2 + 1
        selected: int | None = None
        page = 0
        while selected is None:
            page_offset = page * BUILDING_PAGE_CAPACITY
            for probe in range(BUILDING_PAGE_CAPACITY):
                candidate = page_offset + (
                    (home + probe * stride) % BUILDING_PAGE_CAPACITY
                )
                if candidate not in occupied:
                    selected = candidate
                    break
            page += 1
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


def _layout_diagnostic(code: str, severity: str, message: str) -> dict[str, Any]:
    return {"code": code, "message": message, "severity": severity}


def _finite_number(value: Any) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _prepare_layout_hint(
    previous_scene: dict[str, Any] | None,
    diagnostics: list[dict[str, Any]] | None,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], bool]:
    if previous_scene is None:
        return {}, {}, False

    reason: str | None = None
    if previous_scene.get("schemaVersion") != "city/0.1":
        reason = "unsupported or missing scene schema"
    elif previous_scene.get("layoutAlgorithm") not in HINT_LAYOUT_ALGORITHMS:
        reason = "unsupported layout algorithm family"
    elif not isinstance(previous_scene.get("districts"), list) or not isinstance(
        previous_scene.get("buildings"), list
    ):
        reason = "districts and buildings must be arrays"
    elif (
        len(previous_scene["districts"]) > MAX_HINT_ITEMS
        or len(previous_scene["buildings"]) > MAX_HINT_ITEMS
    ):
        reason = "scene exceeds the layout hint item limit"

    district_hints: dict[str, dict[str, Any]] = {}
    building_hints: dict[str, dict[str, Any]] = {}
    if reason is None:
        for item in previous_scene["districts"]:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("id"), str)
                or not item["id"]
                or (
                    item.get("parentId") is not None
                    and not isinstance(item.get("parentId"), str)
                )
                or not all(_finite_number(item.get(key)) for key in ("x", "z"))
                or not all(
                    _finite_number(item.get(key)) and item[key] > 0
                    for key in ("width", "depth")
                )
                or item["id"] in district_hints
            ):
                reason = "district geometry or identity is malformed"
                break
            district_hints[item["id"]] = item

    if reason is None:
        for item in previous_scene["buildings"]:
            if (
                not isinstance(item, dict)
                or not isinstance(item.get("entityId"), str)
                or not item["entityId"]
                or not isinstance(item.get("districtId"), str)
                or not all(_finite_number(item.get(key)) for key in ("x", "z"))
                or not all(
                    _finite_number(item.get(key)) and item[key] > 0
                    for key in ("width", "depth")
                )
                or item["entityId"] in building_hints
            ):
                reason = "building geometry or identity is malformed"
                break
            building_hints[item["entityId"]] = item

    if reason is None:
        for district in district_hints.values():
            parent_id = district["parentId"]
            if parent_id is not None and parent_id not in district_hints:
                reason = "district parent relationship is incomplete"
                break

    if reason is None:
        for district_id in sorted(district_hints):
            chain: set[str] = set()
            current: str | None = district_id
            while current is not None:
                if current in chain:
                    reason = "district parent relationship contains a cycle"
                    break
                chain.add(current)
                current = district_hints[current]["parentId"]
            if reason is not None:
                break

    if reason is None and any(
        item["districtId"] not in district_hints
        for item in building_hints.values()
    ):
        reason = "building references a missing district"

    if reason is not None:
        if diagnostics is not None:
            diagnostics.append(
                _layout_diagnostic(
                    "LAYOUT_HINT_IGNORED",
                    "WARNING",
                    f"Previous City Scene was ignored: {reason}",
                )
            )
        return {}, {}, False
    return district_hints, building_hints, True


def _hinted_local_slots(
    files_by_district: dict[str, list[dict[str, Any]]],
    district_hints: dict[str, dict[str, Any]],
    building_hints: dict[str, dict[str, Any]],
) -> dict[str, dict[str, int]]:
    result: dict[str, dict[str, int]] = {}
    for district_id in sorted(files_by_district):
        district_hint = district_hints.get(district_id)
        if district_hint is None:
            continue
        occupied: set[int] = set()
        slots: dict[str, int] = {}
        for entity in sorted(files_by_district[district_id], key=lambda item: item["id"]):
            building_hint = building_hints.get(entity["id"])
            if (
                building_hint is None
                or building_hint["districtId"] != district_id
            ):
                continue
            offset_x = building_hint["x"] - district_hint["x"]
            offset_z = building_hint["z"] - district_hint["z"]
            column_value = (offset_x - BUILDING_OFFSET) / BUILDING_SPACING
            page = math.floor(offset_z / DISTRICT_DEPTH)
            page_offset_z = offset_z - page * DISTRICT_DEPTH
            row_value = (page_offset_z - BUILDING_OFFSET) / BUILDING_SPACING
            if (
                page < 0
                or not float(column_value).is_integer()
                or not float(row_value).is_integer()
            ):
                continue
            column = int(column_value)
            row = int(row_value)
            if not (0 <= column < BUILDING_COLUMNS and 0 <= row < BUILDING_COLUMNS):
                continue
            slot = (
                page * BUILDING_PAGE_CAPACITY
                + row * BUILDING_COLUMNS
                + column
            )
            if slot in occupied:
                continue
            occupied.add(slot)
            slots[entity["id"]] = slot
        if slots:
            result[district_id] = slots
    return result


def _ordered_children(
    district_id: str, children_by_parent: dict[str, list[str]]
) -> list[str]:
    return sorted(
        children_by_parent.get(district_id, []),
        key=lambda child_id: (_hash_integer(child_id), child_id),
    )


def _compact_cold_slots(slots: dict[str, int]) -> dict[str, int]:
    """Remove unused rows and columns without changing their relative order."""

    page_rows: dict[int, set[int]] = defaultdict(set)
    page_columns: dict[int, set[int]] = defaultdict(set)
    for slot in slots.values():
        page, page_slot = divmod(slot, BUILDING_PAGE_CAPACITY)
        row, column = divmod(page_slot, BUILDING_COLUMNS)
        page_rows[page].add(row)
        page_columns[page].add(column)

    row_ranks = {
        page: {row: rank for rank, row in enumerate(sorted(rows))}
        for page, rows in page_rows.items()
    }
    column_ranks = {
        page: {column: rank for rank, column in enumerate(sorted(columns))}
        for page, columns in page_columns.items()
    }

    compacted: dict[str, int] = {}
    for entity_id, slot in slots.items():
        page, page_slot = divmod(slot, BUILDING_PAGE_CAPACITY)
        row, column = divmod(page_slot, BUILDING_COLUMNS)
        compacted[entity_id] = (
            page * BUILDING_PAGE_CAPACITY
            + row_ranks[page][row] * BUILDING_COLUMNS
            + column_ranks[page][column]
        )
    return compacted


def _local_rectangles_overlap(
    first: tuple[float, float, float, float],
    second: tuple[float, float, float, float],
) -> bool:
    first_x, first_z, first_width, first_depth = first
    second_x, second_z, second_width, second_depth = second
    return (
        first_x < second_x + second_width
        and second_x < first_x + first_width
        and first_z < second_z + second_depth
        and second_z < first_z + first_depth
    )


def _measure_districts(
    district_id: str,
    children_by_parent: dict[str, list[str]],
    files_by_district: dict[str, list[dict[str, Any]]],
    district_hints: dict[str, dict[str, Any]],
    allocated_slots: dict[str, dict[str, int]],
    dimensions: dict[str, tuple[float, float, int]],
    child_offsets: dict[str, dict[str, tuple[float, float]]],
) -> tuple[float, float, int]:
    children = _ordered_children(district_id, children_by_parent)
    for child_id in children:
        _measure_districts(
            child_id,
            children_by_parent,
            files_by_district,
            district_hints,
            allocated_slots,
            dimensions,
            child_offsets,
        )
    local_slots = allocated_slots.get(district_id, {})
    direct_width = 0
    direct_depth = 0
    for slot in local_slots.values():
        page, page_slot = divmod(slot, BUILDING_PAGE_CAPACITY)
        row, column = divmod(page_slot, BUILDING_COLUMNS)
        direct_width = max(
            direct_width,
            BUILDING_OFFSET
            + column * BUILDING_SPACING
            + BUILDING_SIZE
            + DISTRICT_EDGE_PADDING,
        )
        direct_depth = max(
            direct_depth,
            page * DISTRICT_DEPTH
            + BUILDING_OFFSET
            + row * BUILDING_SPACING
            + BUILDING_SIZE
            + DISTRICT_EDGE_PADDING,
        )
    if local_slots:
        direct_width = max(MIN_DISTRICT_SIZE, direct_width)
        direct_depth = max(MIN_DISTRICT_SIZE, direct_depth)
    elif not children:
        direct_width = EMPTY_DISTRICT_SIZE
        direct_depth = EMPTY_DISTRICT_SIZE

    # Empty directory chains carry hierarchy but need no dedicated city block.
    # Sharing the child's footprint keeps the full parent graph without turning
    # paths such as src/main/java/com/example into a diagonal runway.
    if not local_slots and len(children) == 1:
        child_id = children[0]
        child_offsets[district_id] = {child_id: (0, 0)}
        dimensions[district_id] = dimensions[child_id]
        return dimensions[district_id]

    hint = district_hints.get(district_id)
    width = max(direct_width, hint["width"] if hint is not None else 0)
    depth = direct_depth
    if hint is not None:
        depth = max(depth, hint["depth"])

    offsets: dict[str, tuple[float, float]] = {}
    occupied: list[tuple[float, float, float, float]] = []
    hinted_children: list[tuple[float, float, str]] = []
    for child_id in children:
        child_hint = district_hints.get(child_id)
        if hint is None or child_hint is None or child_hint["parentId"] != district_id:
            continue
        hinted_children.append(
            (
                child_hint["z"] - hint["z"],
                child_hint["x"] - hint["x"],
                child_id,
            )
        )
    for offset_z, offset_x, child_id in sorted(hinted_children):
        child_width, child_depth, _ = dimensions[child_id]
        rectangle = (offset_x, offset_z, child_width, child_depth)
        if (
            offset_x < DISTRICT_PADDING
            or offset_z < direct_depth + DISTRICT_PADDING
            or any(_local_rectangles_overlap(rectangle, item) for item in occupied)
        ):
            continue
        offsets[child_id] = (offset_x, offset_z)
        occupied.append(rectangle)

    unplaced = sorted(
        (child_id for child_id in children if child_id not in offsets),
        key=lambda child_id: (
            -(dimensions[child_id][0] * dimensions[child_id][1]),
            -max(dimensions[child_id][0], dimensions[child_id][1]),
            _hash_integer(child_id),
            child_id,
        ),
    )
    for child_id in unplaced:
        child_width, child_depth, _ = dimensions[child_id]
        candidate_xs = {DISTRICT_PADDING}
        candidate_zs = {direct_depth + DISTRICT_PADDING}
        for occupied_x, occupied_z, occupied_width, occupied_depth in occupied:
            candidate_xs.add(occupied_x + occupied_width + DISTRICT_PADDING)
            candidate_zs.add(occupied_z + occupied_depth + DISTRICT_PADDING)
        candidates: list[tuple[tuple[float, ...], tuple[float, float]]] = []
        for candidate_z in sorted(candidate_zs):
            for candidate_x in sorted(candidate_xs):
                rectangle = (
                    candidate_x,
                    candidate_z,
                    child_width,
                    child_depth,
                )
                if any(
                    _local_rectangles_overlap(rectangle, item)
                    for item in occupied
                ):
                    continue
                content_width = max(
                    direct_width,
                    candidate_x + child_width + DISTRICT_PADDING,
                    *(x + item_width + DISTRICT_PADDING for x, _, item_width, _ in occupied),
                )
                content_depth = max(
                    direct_depth,
                    candidate_z + child_depth + DISTRICT_PADDING,
                    *(z + item_depth + DISTRICT_PADDING for _, z, _, item_depth in occupied),
                )
                score = (
                    max(content_width, content_depth),
                    content_width * content_depth,
                    abs(content_width - content_depth),
                    candidate_z,
                    candidate_x,
                )
                candidates.append((score, (candidate_x, candidate_z)))
        _, offset = min(candidates)
        offsets[child_id] = offset
        occupied.append((offset[0], offset[1], child_width, child_depth))

    for child_id, (offset_x, offset_z) in offsets.items():
        child_width, child_depth, _ = dimensions[child_id]
        width = max(width, offset_x + child_width + DISTRICT_PADDING)
        depth = max(depth, offset_z + child_depth + DISTRICT_PADDING)
    child_offsets[district_id] = offsets
    dimensions[district_id] = (width, depth, direct_depth)
    return dimensions[district_id]


def _place_districts(
    district_id: str,
    parent_id: str | None,
    x: float,
    z: float,
    children_by_parent: dict[str, list[str]],
    dimensions: dict[str, tuple[float, float, int]],
    child_offsets: dict[str, dict[str, tuple[float, float]]],
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
    for child_id in _ordered_children(district_id, children_by_parent):
        offset_x, offset_z = child_offsets[district_id][child_id]
        _place_districts(
            child_id,
            district_id,
            x + offset_x,
            z + offset_z,
            children_by_parent,
            dimensions,
            child_offsets,
            districts,
        )


def _building_style(entity: dict[str, Any]) -> tuple[str, int, list[str]]:
    roles = entity.get("roles", [])
    recognized = [role for role in roles if role["value"] in ROLE_STYLES]
    if not recognized:
        return "GENERIC_BUILDING", 10, []
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


def _network_zones(
    districts: list[dict[str, Any]], buildings: list[dict[str, Any]]
) -> dict[str, str]:
    if len(buildings) < NETWORK_ZONE_CITY_THRESHOLD:
        return {item["entityId"]: item["districtId"] for item in buildings}

    children: dict[str, list[str]] = defaultdict(list)
    direct_entities: dict[str, list[str]] = defaultdict(list)
    for district in districts:
        if district["parentId"] is not None:
            children[district["parentId"]].append(district["id"])
    for child_ids in children.values():
        child_ids.sort()
    for building in buildings:
        direct_entities[building["districtId"]].append(building["entityId"])
    for entity_ids in direct_entities.values():
        entity_ids.sort()

    roots = sorted(
        district["id"] for district in districts if district["parentId"] is None
    )
    subtree_counts: dict[str, int] = {}

    def count(district_id: str) -> int:
        result = len(direct_entities[district_id]) + sum(
            count(child_id) for child_id in children[district_id]
        )
        subtree_counts[district_id] = result
        return result

    for root_id in roots:
        count(root_id)

    result: dict[str, str] = {}

    def assign_subtree(district_id: str, zone_id: str) -> None:
        for entity_id in direct_entities[district_id]:
            result[entity_id] = zone_id
        for child_id in children[district_id]:
            assign_subtree(child_id, zone_id)

    def partition(district_id: str) -> None:
        for entity_id in direct_entities[district_id]:
            result[entity_id] = district_id
        for child_id in children[district_id]:
            child_count = subtree_counts[child_id]
            if child_count < NETWORK_ZONE_MIN_BUILDINGS:
                assign_subtree(child_id, district_id)
            elif child_count <= NETWORK_ZONE_MAX_BUILDINGS:
                assign_subtree(child_id, child_id)
            else:
                partition(child_id)

    for root_id in roots:
        partition(root_id)
    return result


def generate_city(
    ucg: dict[str, Any],
    theme: str = "minimal",
    previous_scene: dict[str, Any] | None = None,
    diagnostics: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    ucg_errors = validate_ucg_document(ucg)
    if ucg_errors:
        raise LayoutError("invalid UCG: " + "; ".join(ucg_errors))
    if not theme:
        raise LayoutError("theme must be non-empty")

    district_hints, building_hints, hint_valid = _prepare_layout_hint(
        previous_scene, diagnostics
    )

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
    locked_slots = _hinted_local_slots(
        files_by_district, district_hints, building_hints
    )
    allocated_slots: dict[str, dict[str, int]] = {}
    for district_id, entities in files_by_district.items():
        slots = _allocate_local_slots(
            [entity["id"] for entity in entities],
            locked_slots.get(district_id),
        )
        allocated_slots[district_id] = (
            slots if locked_slots.get(district_id) else _compact_cold_slots(slots)
        )

    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for entity in directory_entities:
        parent_id = _district_parent_id(entity["path"], directory_ids, root_id)
        children_by_parent[parent_id].append(entity["id"])
    dimensions: dict[str, tuple[float, float, int]] = {}
    child_offsets: dict[str, dict[str, tuple[float, float]]] = {}
    _measure_districts(
        root_id,
        children_by_parent,
        files_by_district,
        district_hints,
        allocated_slots,
        dimensions,
        child_offsets,
    )
    districts: list[dict[str, Any]] = []
    _place_districts(
        root_id,
        None,
        0,
        0,
        children_by_parent,
        dimensions,
        child_offsets,
        districts,
    )
    districts.sort(key=lambda item: item["id"])
    districts_by_id = {item["id"]: item for item in districts}

    buildings: list[dict[str, Any]] = []
    for district_id in sorted(files_by_district):
        district = districts_by_id[district_id]
        entities = files_by_district[district_id]
        local_slots = allocated_slots[district_id]
        for entity in sorted(entities, key=lambda item: item["id"]):
            slot = local_slots[entity["id"]]
            page, page_slot = divmod(slot, BUILDING_PAGE_CAPACITY)
            column = page_slot % BUILDING_COLUMNS
            row = page_slot // BUILDING_COLUMNS
            archetype, height, evidence_ids = _building_style(entity)
            buildings.append(
                {
                    "archetype": archetype,
                    "depth": BUILDING_SIZE,
                    "districtId": district_id,
                    "entityId": entity["id"],
                    "evidenceIds": evidence_ids,
                    "height": height,
                    "styleVariant": entity.get("language") or "unknown",
                    "width": BUILDING_SIZE,
                    "x": district["x"] + BUILDING_OFFSET + column * BUILDING_SPACING,
                    "z": (
                        district["z"]
                        + page * DISTRICT_DEPTH
                        + BUILDING_OFFSET
                        + row * BUILDING_SPACING
                    ),
                }
            )
    buildings.sort(key=lambda item: item["entityId"])

    buildings_by_entity = {item["entityId"]: item for item in buildings}
    network_zones = _network_zones(districts, buildings)
    grouped_edges: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for edge in ucg["edges"]:
        if edge["type"] == "CONTAINS":
            continue
        source_district = network_zones.get(edge["from"])
        target_district = network_zones.get(edge["to"])
        if source_district is None or target_district is None:
            continue
        grouped_edges[
            (_network_kind(edge["type"]), source_district, target_district)
        ].append(edge)

    networks: list[dict[str, Any]] = []
    for (kind, source_id, target_id), grouped in grouped_edges.items():
        edge_ids = sorted(edge["id"] for edge in grouped)
        source_buildings = {
            edge["from"]: buildings_by_entity[edge["from"]]
            for edge in grouped
        }
        target_buildings = {
            edge["to"]: buildings_by_entity[edge["to"]]
            for edge in grouped
        }

        def center(items: dict[str, dict[str, Any]]) -> list[float]:
            ordered = [items[entity_id] for entity_id in sorted(items)]
            return [
                sum(item["x"] + item["width"] / 2 for item in ordered)
                / len(ordered),
                sum(item["z"] + item["depth"] / 2 for item in ordered)
                / len(ordered),
            ]

        start = center(source_buildings)
        end = center(target_buildings)
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
    if hint_valid and previous_scene is not None and diagnostics is not None:
        previous_districts = {
            item["id"]: item for item in previous_scene["districts"]
        }
        previous_buildings = {
            item["entityId"]: item for item in previous_scene["buildings"]
        }
        moved_districts = sum(
            1
            for item in districts
            if item["id"] in previous_districts
            and (item["x"], item["z"])
            != (
                previous_districts[item["id"]]["x"],
                previous_districts[item["id"]]["z"],
            )
        )
        moved_buildings = sum(
            1
            for item in buildings
            if item["entityId"] in previous_buildings
            and (item["x"], item["z"])
            != (
                previous_buildings[item["entityId"]]["x"],
                previous_buildings[item["entityId"]]["z"],
            )
        )
        compared_districts = sum(
            item["id"] in previous_districts for item in districts
        )
        compared_buildings = sum(
            item["entityId"] in previous_buildings for item in buildings
        )
        moved = moved_districts + moved_buildings
        diagnostics.append(
            _layout_diagnostic(
                "LAYOUT_HINT_PARTIAL" if moved else "LAYOUT_HINT_APPLIED",
                "WARNING" if moved else "INFO",
                (
                    "Previous City Scene compared "
                    f"{compared_districts} district(s) and "
                    f"{compared_buildings} building(s); moved "
                    f"{moved_districts} district(s) and "
                    f"{moved_buildings} building(s)"
                ),
            )
        )
    return scene


def _load_document(path: Path, label: str) -> dict[str, Any]:
    try:
        document = loads_strict_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, CanonicalJsonError) as error:
        raise LayoutError(f"unable to read {label}: {error}") from error
    if not isinstance(document, dict):
        raise LayoutError(f"{label} root must be an object")
    return document


def _load_ucg(path: Path) -> dict[str, Any]:
    return _load_document(path, "UCG")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--graph", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--theme", default="minimal")
    parser.add_argument("--previous-scene", type=Path)
    args = parser.parse_args()

    try:
        diagnostics: list[dict[str, Any]] = []
        previous_scene = (
            _load_document(args.previous_scene, "previous City Scene")
            if args.previous_scene is not None
            else None
        )
        scene = generate_city(
            _load_ucg(args.graph), args.theme, previous_scene, diagnostics
        )
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_bytes(canonical_json_bytes(scene))
    except (OSError, LayoutError, ValueError) as error:
        print(f"City generation failed: {error}", file=sys.stderr)
        return 2

    print(f"Wrote City Scene with {len(scene['buildings'])} buildings: {args.out}")
    for diagnostic in diagnostics:
        print(
            f"{diagnostic['severity']}: {diagnostic['code']}: "
            f"{diagnostic['message']}",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
