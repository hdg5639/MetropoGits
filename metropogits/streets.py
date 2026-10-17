"""Derive non-semantic street surfaces from canonical City geometry."""

from __future__ import annotations

import math
from collections import defaultdict
from typing import Any


STREET_CELL_SIZE = 7
Cell = tuple[int, int]


def _rectangle_cells(rectangle: dict[str, Any]) -> set[Cell]:
    start_x = math.floor(float(rectangle["x"]) / STREET_CELL_SIZE)
    start_z = math.floor(float(rectangle["z"]) / STREET_CELL_SIZE)
    end_x = math.ceil(
        (float(rectangle["x"]) + float(rectangle["width"])) / STREET_CELL_SIZE
    )
    end_z = math.ceil(
        (float(rectangle["z"]) + float(rectangle["depth"])) / STREET_CELL_SIZE
    )
    return {
        (x, z)
        for z in range(start_z, end_z)
        for x in range(start_x, end_x)
    }


def _district_cells(district: dict[str, Any]) -> set[Cell]:
    rectangles = district.get("footprint") or [district]
    return set().union(*(_rectangle_cells(item) for item in rectangles))


def _path_cells(path: list[list[float]]) -> set[Cell]:
    result: set[Cell] = set()
    for start, end in zip(path, path[1:]):
        start_cell = (
            round((float(start[0]) - STREET_CELL_SIZE / 2) / STREET_CELL_SIZE),
            round((float(start[1]) - STREET_CELL_SIZE / 2) / STREET_CELL_SIZE),
        )
        end_cell = (
            round((float(end[0]) - STREET_CELL_SIZE / 2) / STREET_CELL_SIZE),
            round((float(end[1]) - STREET_CELL_SIZE / 2) / STREET_CELL_SIZE),
        )
        if start_cell[0] == end_cell[0]:
            result.update(
                (start_cell[0], z)
                for z in range(
                    min(start_cell[1], end_cell[1]),
                    max(start_cell[1], end_cell[1]) + 1,
                )
            )
        elif start_cell[1] == end_cell[1]:
            result.update(
                (x, start_cell[1])
                for x in range(
                    min(start_cell[0], end_cell[0]),
                    max(start_cell[0], end_cell[0]) + 1,
                )
            )
    return result


def _merged_rectangles(
    cells: set[Cell], tier: str
) -> list[dict[str, float | str]]:
    rows: dict[int, list[int]] = defaultdict(list)
    for x, z in cells:
        rows[z].append(x)
    active: dict[tuple[int, int], tuple[int, int]] = {}
    merged: list[tuple[int, int, int, int]] = []
    for z in range(min(rows, default=0), max(rows, default=-1) + 1):
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
            "depth": float((end_z - start_z) * STREET_CELL_SIZE),
            "tier": tier,
            "width": float((end_x - start_x) * STREET_CELL_SIZE),
            "x": float(start_x * STREET_CELL_SIZE),
            "z": float(start_z * STREET_CELL_SIZE),
        }
        for start_x, start_z, end_x, end_z in sorted(
            merged, key=lambda item: (item[1], item[0], item[3], item[2])
        )
    ]


def derive_street_grid(scene: dict[str, Any]) -> dict[str, Any]:
    """Return neutral street surfaces without creating semantic relationships."""

    districts = {item["id"]: item for item in scene["districts"]}
    children: dict[str, list[str]] = defaultdict(list)
    direct_buildings: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for district in scene["districts"]:
        if district["parentId"] in districts:
            children[district["parentId"]].append(district["id"])
    for child_ids in children.values():
        child_ids.sort()
    for building in scene["buildings"]:
        direct_buildings[building["districtId"]].append(building)

    depths: dict[str, int] = {}

    def depth(district_id: str) -> int:
        if district_id in depths:
            return depths[district_id]
        parent_id = districts[district_id]["parentId"]
        result = 0 if parent_id is None else depth(parent_id) + 1
        depths[district_id] = result
        return result

    tier_cells: dict[str, set[Cell]] = {
        "BOULEVARD": set(),
        "STREET": set(),
        "ALLEY": set(),
        "ROUTE_ACCESS": set(),
    }
    district_cell_cache = {
        district_id: _district_cells(district)
        for district_id, district in districts.items()
    }
    for district_id in sorted(districts):
        child_ids = children[district_id]
        if not child_ids and not direct_buildings[district_id]:
            continue
        child_cells = [district_cell_cache[child_id] for child_id in child_ids]
        owned = set().union(*child_cells) if child_cells else set()
        for building in direct_buildings[district_id]:
            owned.update(_rectangle_cells(building))
        district_depth = depth(district_id)
        gap = 2 if district_depth == 0 else 1 if district_depth <= 2 else 0
        reserved = {
            (x + dx, z + dz)
            for cells in child_cells
            for x, z in cells
            for dx in range(-gap, gap + 1)
            for dz in range(-gap, gap + 1)
        }
        parent_bounds = _rectangle_cells(districts[district_id])
        street_cells = (district_cell_cache[district_id] | reserved) & parent_bounds
        street_cells -= owned
        tier = (
            "BOULEVARD"
            if district_depth == 0
            else "STREET"
            if district_depth <= 2
            else "ALLEY"
        )
        tier_cells[tier].update(street_cells)

    tier_cells["STREET"] -= tier_cells["BOULEVARD"]
    tier_cells["ALLEY"] -= tier_cells["BOULEVARD"] | tier_cells["STREET"]
    routed_cells = set().union(
        *(_path_cells(network["path"]) for network in scene["networks"])
    ) if scene["networks"] else set()
    structural_cells = set().union(
        tier_cells["BOULEVARD"], tier_cells["STREET"], tier_cells["ALLEY"]
    )
    tier_cells["ROUTE_ACCESS"] = routed_cells - structural_cells

    rectangles = [
        rectangle
        for tier in ("BOULEVARD", "STREET", "ALLEY", "ROUTE_ACCESS")
        for rectangle in _merged_rectangles(tier_cells[tier], tier)
    ]
    return {
        "cellSize": STREET_CELL_SIZE,
        "rectangles": rectangles,
        "semantic": False,
        "surfaces": [part for rectangle in rectangles for part in street_surfaces(rectangle)],
    }


def street_surfaces(rectangle: dict[str, Any]) -> list[dict[str, Any]]:
    """Shared curb/asphalt/paint geometry. Never represents a dependency edge."""
    x, z, width, depth = (float(rectangle[key]) for key in ("x", "z", "width", "depth"))
    parts = [dict(x=x, z=z, width=width, depth=depth, color="#526176", elevation=0.12)]
    inset = min(0.45, width / 6, depth / 6)
    parts.append(dict(x=x + inset, z=z + inset, width=width - 2 * inset,
                      depth=depth - 2 * inset, color="#253141", elevation=0.13))
    length = max(width, depth)
    if min(width, depth) >= 7 and length >= 21:
        for offset in range(3, int(length) - 3, 8):
            parts.append(dict(x=x + offset if width >= depth else x + width / 2 - 0.10,
                              z=z + depth / 2 - 0.10 if width >= depth else z + offset,
                              width=min(3, length - offset - 1) if width >= depth else 0.20,
                              depth=0.20 if width >= depth else min(3, length - offset - 1),
                              color="#a2a996", elevation=0.145))
    return parts
