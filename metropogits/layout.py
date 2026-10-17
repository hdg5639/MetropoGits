"""Deterministic directory-anchored City Scene generation."""

from __future__ import annotations

import argparse
import hashlib
import math
import sys
from collections import defaultdict, deque
from decimal import Decimal
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


LAYOUT_ALGORITHM = "hierarchical-paged/1.13"
HINT_LAYOUT_ALGORITHMS = frozenset({LAYOUT_ALGORITHM})
SCENE_SCHEMA_VERSION = "city/0.2"
FOOTPRINT_CELL_SIZE = 7
DISTRICT_DEPTH = 64
DISTRICT_PADDING = 4
MIN_DISTRICT_SIZE = 14
EMPTY_DISTRICT_SIZE = 8
DISTRICT_EDGE_PADDING = 2
BUILDING_COLUMNS = 8
BUILDING_SPACING = 7
BUILDING_OFFSET = 3
COMPACT_LEAF_BUILDING_OFFSET = 0.5
COMPACT_LEAF_MAX_FILES = 3
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
    if isinstance(value, bool) or not isinstance(value, (Decimal, int, float)):
        return False
    return value.is_finite() if isinstance(value, Decimal) else math.isfinite(value)


def _prepare_layout_hint(
    previous_scene: dict[str, Any] | None,
    diagnostics: list[dict[str, Any]] | None,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]], bool]:
    if previous_scene is None:
        return {}, {}, False

    reason: str | None = None
    if previous_scene.get("schemaVersion") != SCENE_SCHEMA_VERSION:
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
    compact_leaf_ids: set[str],
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
            offset_x = float(building_hint["x"]) - float(district_hint["x"])
            offset_z = float(building_hint["z"]) - float(district_hint["z"])
            building_offset = (
                COMPACT_LEAF_BUILDING_OFFSET
                if district_id in compact_leaf_ids
                else BUILDING_OFFSET
            )
            column_value = (offset_x - building_offset) / BUILDING_SPACING
            page = math.floor(offset_z / DISTRICT_DEPTH)
            page_offset_z = offset_z - page * DISTRICT_DEPTH
            row_value = (page_offset_z - building_offset) / BUILDING_SPACING
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


def _compact_leaf_groups(
    root_id: str,
    children_by_parent: dict[str, list[str]],
    files_by_district: dict[str, list[dict[str, Any]]],
) -> dict[str, tuple[str, ...]]:
    result: dict[str, tuple[str, ...]] = {}

    def visit(district_id: str, hierarchy_depth: int) -> None:
        children = _ordered_children(district_id, children_by_parent)
        for child_id in children:
            visit(child_id, hierarchy_depth + 1)
        if _street_gap_cells(hierarchy_depth) > 0:
            return
        candidates = tuple(
            child_id
            for child_id in children
            if not children_by_parent.get(child_id)
            and 1
            <= len(files_by_district.get(child_id, ()))
            <= COMPACT_LEAF_MAX_FILES
        )
        if len(candidates) >= 2:
            result[district_id] = candidates

    visit(root_id, 0)
    return result


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


Cell = tuple[int, int]


def _cell_components(cells: set[Cell]) -> list[set[Cell]]:
    unseen = set(cells)
    result: list[set[Cell]] = []
    while unseen:
        pending = [min(unseen, key=lambda cell: (cell[1], cell[0]))]
        component = {pending[0]}
        unseen.remove(pending[0])
        while pending:
            x, z = pending.pop(0)
            for neighbor in ((x + 1, z), (x, z + 1), (x - 1, z), (x, z - 1)):
                if neighbor in unseen:
                    unseen.remove(neighbor)
                    component.add(neighbor)
                    pending.append(neighbor)
        result.append(component)
    return sorted(
        result,
        key=lambda component: (
            -len(component),
            min((cell[1], cell[0]) for cell in component),
        ),
    )


def _connect_local_cells(cells: set[Cell]) -> set[Cell]:
    """Connect an orthogonal cell union with deterministic shortest corridors."""

    result = set(cells)
    while True:
        components = _cell_components(result)
        if len(components) <= 1:
            return result
        source = components[0]
        target_cells = set().union(*components[1:])
        source_cell, target_cell = min(
            (
                (first, second)
                for first in source
                for second in target_cells
            ),
            key=lambda pair: (
                abs(pair[0][0] - pair[1][0]) + abs(pair[0][1] - pair[1][1]),
                pair[0][1],
                pair[0][0],
                pair[1][1],
                pair[1][0],
            ),
        )
        x, z = source_cell
        target_x, target_z = target_cell
        step_x = 1 if target_x > x else -1
        while x != target_x:
            x += step_x
            result.add((x, z))
        step_z = 1 if target_z > z else -1
        while z != target_z:
            z += step_z
            result.add((x, z))


def _fill_enclosed_cells(cells: set[Cell]) -> set[Cell]:
    """Fill internal voids while preserving concave exterior boundaries."""

    max_x = max(x for x, _ in cells)
    max_z = max(z for _, z in cells)
    exterior: set[Cell] = set()
    pending = [
        (x, z)
        for z in range(max_z + 1)
        for x in range(max_x + 1)
        if (x in {0, max_x} or z in {0, max_z}) and (x, z) not in cells
    ]
    exterior.update(pending)
    while pending:
        x, z = pending.pop()
        for neighbor in ((x + 1, z), (x, z + 1), (x - 1, z), (x, z - 1)):
            if (
                0 <= neighbor[0] <= max_x
                and 0 <= neighbor[1] <= max_z
                and neighbor not in cells
                and neighbor not in exterior
            ):
                exterior.add(neighbor)
                pending.append(neighbor)
    return cells | {
        (x, z)
        for z in range(max_z + 1)
        for x in range(max_x + 1)
        if (x, z) not in exterior
    }


def _street_gap_cells(parent_depth: int) -> int:
    if parent_depth == 0:
        return 2
    if parent_depth <= 2:
        return 1
    return 0


def _reserved_cells(cells: set[Cell], gap_cells: int) -> set[Cell]:
    return {
        (x + dx, z + dz)
        for x, z in cells
        for dx in range(-gap_cells, gap_cells + 1)
        for dz in range(-gap_cells, gap_cells + 1)
    }


def _translated_cells(cells: set[Cell], offset: Cell) -> set[Cell]:
    return {(x + offset[0], z + offset[1]) for x, z in cells}


def _normalized_cells(cells: set[Cell]) -> set[Cell]:
    min_x = min(x for x, _ in cells)
    min_z = min(z for _, z in cells)
    return {(x - min_x, z - min_z) for x, z in cells}


def _pack_shape(
    shape: set[Cell],
    occupied: set[Cell],
    gap_cells: int,
    preferred: Cell | None = None,
    prefer_density: bool = False,
) -> Cell:
    normalized = _normalized_cells(shape)
    forbidden = _reserved_cells(occupied, gap_cells) if occupied else set()

    def available(offset: Cell) -> bool:
        return offset[0] >= 0 and offset[1] >= 0 and not any(
            (x + offset[0], z + offset[1]) in forbidden for x, z in normalized
        )

    if preferred is not None and available(preferred):
        return preferred
    if not occupied:
        return (0, 0)

    shape_width = max(x for x, _ in normalized) + 1
    shape_depth = max(z for _, z in normalized) + 1
    occupied_width = max((x for x, _ in occupied), default=-1) + 1
    occupied_depth = max((z for _, z in occupied), default=-1) + 1
    limit_x = max(shape_width, occupied_width + shape_width + 2)
    limit_z = max(shape_depth, occupied_depth + shape_depth + 2)
    candidates: list[tuple[tuple[int, ...], Cell]] = []
    density_candidates: list[tuple[int, int, Cell]] = []
    for z in range(limit_z):
        for x in range(limit_x):
            offset = (x, z)
            if not available(offset):
                continue
            width = max(occupied_width, x + shape_width)
            depth = max(occupied_depth, z + shape_depth)
            if prefer_density:
                density_candidates.append((width, depth, offset))
            else:
                score = (max(width, depth), width * depth, abs(width - depth), z, x)
                candidates.append((score, offset))
    if prefer_density and density_candidates:
        shortest_long_side = min(
            max(width, depth) for width, depth, _ in density_candidates
        )
        permitted_long_side = math.ceil(shortest_long_side * 1.12)
        return min(
            (
                (
                    width * depth,
                    max(width, depth),
                    abs(width - depth),
                    offset[1],
                    offset[0],
                ),
                offset,
            )
            for width, depth, offset in density_candidates
            if max(width, depth) <= permitted_long_side
        )[1]
    if not candidates:
        raise LayoutError("unable to place district footprint")
    return min(candidates)[1]


def _direct_footprint_cells(
    slots: dict[str, int], building_offset: float = BUILDING_OFFSET
) -> set[Cell]:
    cells: set[Cell] = set()
    for slot in slots.values():
        page, page_slot = divmod(slot, BUILDING_PAGE_CAPACITY)
        row, column = divmod(page_slot, BUILDING_COLUMNS)
        x = building_offset + column * BUILDING_SPACING
        z = page * DISTRICT_DEPTH + building_offset + row * BUILDING_SPACING
        start_x = math.floor(x / FOOTPRINT_CELL_SIZE)
        start_z = math.floor(z / FOOTPRINT_CELL_SIZE)
        end_x = math.ceil((x + BUILDING_SIZE) / FOOTPRINT_CELL_SIZE)
        end_z = math.ceil((z + BUILDING_SIZE) / FOOTPRINT_CELL_SIZE)
        cells.update(
            (cell_x, cell_z)
            for cell_z in range(start_z, end_z)
            for cell_x in range(start_x, end_x)
        )
    return cells


def _pack_compact_leaf_block(
    member_ids: tuple[str, ...],
    footprint_cells: dict[str, set[Cell]],
    district_hints: dict[str, dict[str, Any]],
    parent_id: str,
) -> tuple[set[Cell], dict[str, Cell], Cell | None]:
    parent_hint = district_hints.get(parent_id)
    relative_hints: dict[str, Cell] = {}
    if parent_hint is not None:
        for member_id in member_ids:
            member_hint = district_hints.get(member_id)
            if member_hint is None or member_hint["parentId"] != parent_id:
                continue
            relative_x = (
                float(member_hint["x"]) - float(parent_hint["x"])
            ) / FOOTPRINT_CELL_SIZE
            relative_z = (
                float(member_hint["z"]) - float(parent_hint["z"])
            ) / FOOTPRINT_CELL_SIZE
            if float(relative_x).is_integer() and float(relative_z).is_integer():
                relative_hints[member_id] = (int(relative_x), int(relative_z))

    block_preferred: Cell | None = None
    internal_hints: dict[str, Cell] = {}
    if relative_hints:
        block_preferred = (
            min(cell[0] for cell in relative_hints.values()),
            min(cell[1] for cell in relative_hints.values()),
        )
        internal_hints = {
            member_id: (
                cell[0] - block_preferred[0],
                cell[1] - block_preferred[1],
            )
            for member_id, cell in relative_hints.items()
        }

    hinted = sorted(
        internal_hints,
        key=lambda member_id: (
            internal_hints[member_id][1],
            internal_hints[member_id][0],
            member_id,
        ),
    )
    unhinted = sorted(
        set(member_ids) - set(hinted),
        key=lambda member_id: (
            -len(footprint_cells[member_id]),
            _hash_integer(member_id),
            member_id,
        ),
    )
    occupied: set[Cell] = set()
    offsets: dict[str, Cell] = {}
    for member_id in hinted + unhinted:
        offset = _pack_shape(
            footprint_cells[member_id],
            occupied,
            0,
            internal_hints.get(member_id),
        )
        offsets[member_id] = offset
        occupied.update(
            _translated_cells(footprint_cells[member_id], offset)
        )

    width = max(x for x, _ in occupied) + 1
    depth = max(z for _, z in occupied) + 1
    block_cells = {
        (x, z)
        for z in range(depth)
        for x in range(width)
    }
    return block_cells, offsets, block_preferred


def _cells_to_footprint(
    cells: set[Cell], origin_x: float, origin_z: float
) -> list[dict[str, float]]:
    rows: dict[int, list[int]] = defaultdict(list)
    for x, z in cells:
        rows[z].append(x)
    active: dict[tuple[int, int], tuple[int, int]] = {}
    merged: list[tuple[int, int, int, int]] = []
    for z in range(max(rows) + 1):
        runs: list[tuple[int, int]] = []
        for x in sorted(rows.get(z, [])):
            if runs and x == runs[-1][1]:
                runs[-1] = (runs[-1][0], x + 1)
            else:
                runs.append((x, x + 1))
        current = set(runs)
        for run in sorted(set(active) - current):
            start_z, end_z = active.pop(run)
            merged.append((run[0], start_z, run[1], end_z))
        for run in runs:
            active[run] = (active[run][0], z + 1) if run in active else (z, z + 1)
    for run in sorted(active):
        start_z, end_z = active[run]
        merged.append((run[0], start_z, run[1], end_z))
    return [
        {
            "depth": float((end_z - start_z) * FOOTPRINT_CELL_SIZE),
            "width": float((end_x - start_x) * FOOTPRINT_CELL_SIZE),
            "x": float(origin_x + start_x * FOOTPRINT_CELL_SIZE),
            "z": float(origin_z + start_z * FOOTPRINT_CELL_SIZE),
        }
        for start_x, start_z, end_x, end_z in sorted(
            merged, key=lambda item: (item[1], item[0], item[3], item[2])
        )
    ]


def _measure_districts(
    district_id: str,
    children_by_parent: dict[str, list[str]],
    files_by_district: dict[str, list[dict[str, Any]]],
    district_hints: dict[str, dict[str, Any]],
    allocated_slots: dict[str, dict[str, int]],
    dimensions: dict[str, tuple[float, float]],
    child_offsets: dict[str, dict[str, tuple[float, float]]],
    footprint_cells: dict[str, set[Cell]],
    compact_leaf_groups: dict[str, tuple[str, ...]],
    compact_leaf_ids: set[str],
    hierarchy_depth: int = 0,
) -> tuple[float, float]:
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
            footprint_cells,
            compact_leaf_groups,
            compact_leaf_ids,
            hierarchy_depth + 1,
        )
    local_slots = allocated_slots.get(district_id, {})
    building_offset = (
        COMPACT_LEAF_BUILDING_OFFSET
        if district_id in compact_leaf_ids
        else BUILDING_OFFSET
    )
    direct_cells = _direct_footprint_cells(local_slots, building_offset)
    if not direct_cells and not children:
        direct_cells = {(0, 0)}

    # Empty directory chains carry hierarchy but need no dedicated city block.
    # Sharing the child's footprint keeps the full parent graph without turning
    # paths such as src/main/java/com/example into a diagonal runway.
    if not local_slots and len(children) == 1:
        child_id = children[0]
        child_offsets[district_id] = {child_id: (0, 0)}
        dimensions[district_id] = dimensions[child_id]
        footprint_cells[district_id] = set(footprint_cells[child_id])
        return dimensions[district_id]
    hint = district_hints.get(district_id)
    offsets: dict[str, tuple[float, float]] = {}
    occupied = set(direct_cells)
    compact_members = set(compact_leaf_groups.get(district_id, ()))
    regular_children = [
        child_id for child_id in children if child_id not in compact_members
    ]
    hinted = []
    unhinted = []
    for child_id in regular_children:
        child_hint = district_hints.get(child_id)
        if (
            hint is not None
            and child_hint is not None
            and child_hint["parentId"] == district_id
        ):
            hinted.append(child_id)
        else:
            unhinted.append(child_id)
    hinted.sort(
        key=lambda child_id: (
            district_hints[child_id]["z"] - hint["z"],
            district_hints[child_id]["x"] - hint["x"],
            child_id,
        )
    )
    unhinted.sort(
        key=lambda child_id: (
            -len(footprint_cells[child_id]),
            -max(dimensions[child_id]),
            _hash_integer(child_id),
            child_id,
        ),
    )
    for child_id in hinted + unhinted:
        preferred: Cell | None = None
        child_hint = district_hints.get(child_id)
        if (
            hint is not None
            and child_hint is not None
            and child_hint["parentId"] == district_id
        ):
            relative_x = (child_hint["x"] - hint["x"]) / FOOTPRINT_CELL_SIZE
            relative_z = (child_hint["z"] - hint["z"]) / FOOTPRINT_CELL_SIZE
            if float(relative_x).is_integer() and float(relative_z).is_integer():
                preferred = (int(relative_x), int(relative_z))
        offset_cells = _pack_shape(
            footprint_cells[child_id],
            occupied,
            _street_gap_cells(hierarchy_depth),
            preferred,
            prefer_density=hierarchy_depth == 0,
        )
        offsets[child_id] = (
            float(offset_cells[0] * FOOTPRINT_CELL_SIZE),
            float(offset_cells[1] * FOOTPRINT_CELL_SIZE),
        )
        occupied.update(_translated_cells(footprint_cells[child_id], offset_cells))

    if compact_members:
        member_ids = compact_leaf_groups[district_id]
        block_cells, member_offsets, block_preferred = _pack_compact_leaf_block(
            member_ids,
            footprint_cells,
            district_hints,
            district_id,
        )
        block_offset = _pack_shape(
            block_cells,
            occupied,
            _street_gap_cells(hierarchy_depth),
            block_preferred,
            prefer_density=hierarchy_depth == 0,
        )
        for member_id in member_ids:
            member_offset = member_offsets[member_id]
            offsets[member_id] = (
                float((block_offset[0] + member_offset[0]) * FOOTPRINT_CELL_SIZE),
                float((block_offset[1] + member_offset[1]) * FOOTPRINT_CELL_SIZE),
            )
        occupied.update(_translated_cells(block_cells, block_offset))

    occupied = _fill_enclosed_cells(_connect_local_cells(occupied))
    occupied = _normalized_cells(occupied)
    width = float((max(x for x, _ in occupied) + 1) * FOOTPRINT_CELL_SIZE)
    depth = float((max(z for _, z in occupied) + 1) * FOOTPRINT_CELL_SIZE)
    child_offsets[district_id] = offsets
    footprint_cells[district_id] = occupied
    dimensions[district_id] = (width, depth)
    return dimensions[district_id]


def _place_districts(
    district_id: str,
    parent_id: str | None,
    x: float,
    z: float,
    children_by_parent: dict[str, list[str]],
    dimensions: dict[str, tuple[float, float]],
    child_offsets: dict[str, dict[str, tuple[float, float]]],
    footprint_cells: dict[str, set[Cell]],
    districts: list[dict[str, Any]],
) -> None:
    width, depth = dimensions[district_id]
    districts.append(
        {
            "depth": depth,
            "footprint": _cells_to_footprint(footprint_cells[district_id], x, z),
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
            footprint_cells,
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


def _network_walkable_cells(
    districts: list[dict[str, Any]], buildings: list[dict[str, Any]]
) -> set[Cell]:
    min_x = math.floor(min(item["x"] for item in districts) / FOOTPRINT_CELL_SIZE) - 3
    min_z = math.floor(min(item["z"] for item in districts) / FOOTPRINT_CELL_SIZE) - 3
    max_x = (
        math.ceil(
            max(item["x"] + item["width"] for item in districts)
            / FOOTPRINT_CELL_SIZE
        )
        + 3
    )
    max_z = (
        math.ceil(
            max(item["z"] + item["depth"] for item in districts)
            / FOOTPRINT_CELL_SIZE
        )
        + 3
    )
    blocked: set[Cell] = set()
    for building in buildings:
        start_x = math.floor(float(building["x"]) / FOOTPRINT_CELL_SIZE)
        start_z = math.floor(float(building["z"]) / FOOTPRINT_CELL_SIZE)
        end_x = math.ceil(
            (float(building["x"]) + float(building["width"]))
            / FOOTPRINT_CELL_SIZE
        )
        end_z = math.ceil(
            (float(building["z"]) + float(building["depth"]))
            / FOOTPRINT_CELL_SIZE
        )
        blocked.update(
            (x, z)
            for z in range(start_z, end_z)
            for x in range(start_x, end_x)
        )
    available = {
        (x, z)
        for z in range(min_z, max_z + 1)
        for x in range(min_x, max_x + 1)
        if (x, z) not in blocked
    }
    boundary = deque(
        sorted(
            (
                cell
                for cell in available
                if cell[0] in {min_x, max_x} or cell[1] in {min_z, max_z}
            ),
            key=lambda cell: (cell[1], cell[0]),
        )
    )
    exterior = set(boundary)
    while boundary:
        x, z = boundary.popleft()
        for neighbor in ((x + 1, z), (x, z + 1), (x - 1, z), (x, z - 1)):
            if neighbor in available and neighbor not in exterior:
                exterior.add(neighbor)
                boundary.append(neighbor)
    return exterior


def _mean_building_center(items: dict[str, dict[str, Any]]) -> tuple[float, float]:
    ordered = [items[entity_id] for entity_id in sorted(items)]
    return (
        sum(float(item["x"]) + float(item["width"]) / 2 for item in ordered)
        / len(ordered),
        sum(float(item["z"]) + float(item["depth"]) / 2 for item in ordered)
        / len(ordered),
    )


def _nearest_walkable_cell(cells: set[Cell], point: tuple[float, float]) -> Cell:
    target_x = (point[0] - FOOTPRINT_CELL_SIZE / 2) / FOOTPRINT_CELL_SIZE
    target_z = (point[1] - FOOTPRINT_CELL_SIZE / 2) / FOOTPRINT_CELL_SIZE
    return min(
        cells,
        key=lambda cell: (
            abs(cell[0] - target_x) + abs(cell[1] - target_z),
            (cell[0] - target_x) ** 2 + (cell[1] - target_z) ** 2,
            cell[1],
            cell[0],
        ),
    )


def _shortest_cell_path(cells: set[Cell], start: Cell, end: Cell) -> list[Cell]:
    if start == end:
        neighbor = min(
            (
                cell
                for cell in (
                    (start[0] + 1, start[1]),
                    (start[0], start[1] + 1),
                    (start[0] - 1, start[1]),
                    (start[0], start[1] - 1),
                )
                if cell in cells
            ),
            key=lambda cell: (cell[1], cell[0]),
        )
        return [start, neighbor]
    pending = deque([start])
    previous: dict[Cell, Cell | None] = {start: None}
    while pending:
        current = pending.popleft()
        neighbors = (
            (current[0] + 1, current[1]),
            (current[0], current[1] + 1),
            (current[0] - 1, current[1]),
            (current[0], current[1] - 1),
        )
        for neighbor in neighbors:
            if neighbor not in cells or neighbor in previous:
                continue
            previous[neighbor] = current
            if neighbor == end:
                pending.clear()
                break
            pending.append(neighbor)
    if end not in previous:
        raise LayoutError("unable to route dependency through the street grid")
    path = []
    current: Cell | None = end
    while current is not None:
        path.append(current)
        current = previous[current]
    return list(reversed(path))


def _simplify_cell_path(path: list[Cell]) -> list[Cell]:
    if len(path) <= 2:
        return path
    result = [path[0]]
    previous_direction = (
        path[1][0] - path[0][0],
        path[1][1] - path[0][1],
    )
    for index in range(1, len(path) - 1):
        direction = (
            path[index + 1][0] - path[index][0],
            path[index + 1][1] - path[index][1],
        )
        if direction != previous_direction:
            result.append(path[index])
        previous_direction = direction
    result.append(path[-1])
    return result


def _route_network(
    walkable: set[Cell],
    source_buildings: dict[str, dict[str, Any]],
    target_buildings: dict[str, dict[str, Any]],
) -> list[list[float]]:
    start = _nearest_walkable_cell(
        walkable, _mean_building_center(source_buildings)
    )
    end = _nearest_walkable_cell(
        walkable, _mean_building_center(target_buildings)
    )
    return [
        [
            float(cell[0] * FOOTPRINT_CELL_SIZE + FOOTPRINT_CELL_SIZE / 2),
            float(cell[1] * FOOTPRINT_CELL_SIZE + FOOTPRINT_CELL_SIZE / 2),
        ]
        for cell in _simplify_cell_path(
            _shortest_cell_path(walkable, start, end)
        )
    ]


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

    children_by_parent: dict[str, list[str]] = defaultdict(list)
    for entity in directory_entities:
        parent_id = _district_parent_id(entity["path"], directory_ids, root_id)
        children_by_parent[parent_id].append(entity["id"])
    compact_leaf_groups = _compact_leaf_groups(
        root_id, children_by_parent, files_by_district
    )
    compact_leaf_ids = {
        child_id
        for member_ids in compact_leaf_groups.values()
        for child_id in member_ids
    }
    locked_slots = _hinted_local_slots(
        files_by_district,
        district_hints,
        building_hints,
        compact_leaf_ids,
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

    dimensions: dict[str, tuple[float, float]] = {}
    child_offsets: dict[str, dict[str, tuple[float, float]]] = {}
    footprint_cells: dict[str, set[Cell]] = {}
    _measure_districts(
        root_id,
        children_by_parent,
        files_by_district,
        district_hints,
        allocated_slots,
        dimensions,
        child_offsets,
        footprint_cells,
        compact_leaf_groups,
        compact_leaf_ids,
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
        footprint_cells,
        districts,
    )
    districts.sort(key=lambda item: item["id"])
    districts_by_id = {item["id"]: item for item in districts}

    buildings: list[dict[str, Any]] = []
    for district_id in sorted(files_by_district):
        district = districts_by_id[district_id]
        entities = files_by_district[district_id]
        local_slots = allocated_slots[district_id]
        building_offset = (
            COMPACT_LEAF_BUILDING_OFFSET
            if district_id in compact_leaf_ids
            else BUILDING_OFFSET
        )
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
                    "x": district["x"] + building_offset + column * BUILDING_SPACING,
                    "z": (
                        district["z"]
                        + page * DISTRICT_DEPTH
                        + building_offset
                        + row * BUILDING_SPACING
                    ),
                }
            )
    buildings.sort(key=lambda item: item["entityId"])

    buildings_by_entity = {item["entityId"]: item for item in buildings}
    network_walkable = _network_walkable_cells(districts, buildings)
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

        path = _route_network(
            network_walkable, source_buildings, target_buildings
        )
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
        "schemaVersion": SCENE_SCHEMA_VERSION,
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
