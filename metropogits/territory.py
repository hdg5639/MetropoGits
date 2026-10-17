"""Deterministic visual district territories derived from City buildings."""

from __future__ import annotations

import math
from collections import deque
from typing import Any


TERRITORY_CELL_SIZE = 14
_NEIGHBORS = ((1, 0), (0, 1), (-1, 0), (0, -1))


Cell = tuple[int, int]


def _components(cells: set[Cell]) -> list[set[Cell]]:
    unseen = set(cells)
    result: list[set[Cell]] = []
    while unseen:
        start = min(unseen, key=lambda cell: (cell[1], cell[0]))
        component = {start}
        unseen.remove(start)
        queue = deque([start])
        while queue:
            x, z = queue.popleft()
            for dx, dz in _NEIGHBORS:
                neighbor = (x + dx, z + dz)
                if neighbor not in unseen:
                    continue
                unseen.remove(neighbor)
                component.add(neighbor)
                queue.append(neighbor)
        result.append(component)
    return sorted(
        result,
        key=lambda component: (
            -len(component),
            min((cell[1], cell[0]) for cell in component),
        ),
    )


def _connect_cells(cells: set[Cell], columns: int, rows: int) -> set[Cell]:
    result = set(cells)
    while True:
        components = _components(result)
        if len(components) <= 1:
            return result
        source = components[0]
        targets = set().union(*components[1:])
        queue = deque(sorted(source, key=lambda cell: (cell[1], cell[0])))
        previous: dict[Cell, Cell | None] = {cell: None for cell in source}
        found: Cell | None = None
        while queue and found is None:
            current = queue.popleft()
            for dx, dz in _NEIGHBORS:
                neighbor = (current[0] + dx, current[1] + dz)
                if (
                    not 0 <= neighbor[0] < columns
                    or not 0 <= neighbor[1] < rows
                    or neighbor in previous
                ):
                    continue
                previous[neighbor] = current
                if neighbor in targets:
                    found = neighbor
                    break
                queue.append(neighbor)
        if found is None:
            return result
        cursor: Cell | None = found
        while cursor is not None:
            result.add(cursor)
            cursor = previous[cursor]


def _dilate_cells(cells: set[Cell], columns: int, rows: int) -> set[Cell]:
    return {
        (column + dx, row + dz)
        for column, row in cells
        for dx in (-1, 0, 1)
        for dz in (-1, 0, 1)
        if 0 <= column + dx < columns and 0 <= row + dz < rows
    }


def _landmark_plot(
    district: dict[str, Any], cells: set[Cell], columns: int, rows: int, cell_size: int
) -> dict[str, float]:
    heights = [0] * columns
    best: tuple[tuple[int, int, int, int, int], tuple[int, int, int, int]] | None = None
    for row in range(rows):
        for column in range(columns):
            heights[column] = heights[column] + 1 if (column, row) in cells else 0
        stack: list[int] = []
        for column in range(columns + 1):
            height = heights[column] if column < columns else 0
            while stack and heights[stack[-1]] > height:
                index = stack.pop()
                rectangle_height = heights[index]
                start_column = stack[-1] + 1 if stack else 0
                rectangle_width = column - start_column
                start_row = row - rectangle_height + 1
                score = (
                    rectangle_width * rectangle_height,
                    min(rectangle_width, rectangle_height),
                    -abs(rectangle_width - rectangle_height),
                    -start_row,
                    -start_column,
                )
                candidate = (
                    start_column,
                    start_row,
                    rectangle_width,
                    rectangle_height,
                )
                if best is None or score > best[0]:
                    best = (score, candidate)
            stack.append(column)
    assert best is not None
    start_column, start_row, rectangle_width, rectangle_height = best[1]
    x = float(district["x"] + start_column * cell_size)
    z = float(district["z"] + start_row * cell_size)
    right = min(
        float(district["x"] + district["width"]),
        float(district["x"] + (start_column + rectangle_width) * cell_size),
    )
    bottom = min(
        float(district["z"] + district["depth"]),
        float(district["z"] + (start_row + rectangle_height) * cell_size),
    )
    return {"depth": bottom - z, "width": right - x, "x": x, "z": z}


def _merged_rectangles(
    district: dict[str, Any], cells: set[Cell], cell_size: int
) -> list[dict[str, float]]:
    rows: dict[int, list[int]] = {}
    for column, row in cells:
        rows.setdefault(row, []).append(column)

    active: dict[tuple[int, int], tuple[int, int]] = {}
    merged: list[tuple[int, int, int, int]] = []
    for row in range(max(rows, default=-1) + 1):
        columns = sorted(rows.get(row, []))
        runs: list[tuple[int, int]] = []
        for column in columns:
            if runs and column == runs[-1][1]:
                runs[-1] = (runs[-1][0], column + 1)
            else:
                runs.append((column, column + 1))
        current = set(runs)
        for run in sorted(set(active) - current):
            start_row, end_row = active.pop(run)
            merged.append((run[0], start_row, run[1], end_row))
        for run in runs:
            if run in active:
                active[run] = (active[run][0], row + 1)
            else:
                active[run] = (row, row + 1)
    for run in sorted(active):
        start_row, end_row = active[run]
        merged.append((run[0], start_row, run[1], end_row))

    max_x = float(district["x"] + district["width"])
    max_z = float(district["z"] + district["depth"])
    rectangles = []
    for start_column, start_row, end_column, end_row in sorted(
        merged, key=lambda item: (item[1], item[0], item[3], item[2])
    ):
        x = float(district["x"] + start_column * cell_size)
        z = float(district["z"] + start_row * cell_size)
        right = min(max_x, float(district["x"] + end_column * cell_size))
        bottom = min(max_z, float(district["z"] + end_row * cell_size))
        rectangles.append(
            {"depth": bottom - z, "width": right - x, "x": x, "z": z}
        )
    return rectangles


def _boundary_segments(
    district: dict[str, Any], cells: set[Cell], cell_size: int
) -> list[list[list[float]]]:
    horizontal: dict[int, list[tuple[int, int]]] = {}
    vertical: dict[int, list[tuple[int, int]]] = {}
    for column, row in cells:
        if (column, row - 1) not in cells:
            horizontal.setdefault(row, []).append((column, column + 1))
        if (column, row + 1) not in cells:
            horizontal.setdefault(row + 1, []).append((column, column + 1))
        if (column - 1, row) not in cells:
            vertical.setdefault(column, []).append((row, row + 1))
        if (column + 1, row) not in cells:
            vertical.setdefault(column + 1, []).append((row, row + 1))

    def merge(intervals: list[tuple[int, int]]) -> list[tuple[int, int]]:
        result: list[tuple[int, int]] = []
        for start, end in sorted(intervals):
            if result and start == result[-1][1]:
                result[-1] = (result[-1][0], end)
            else:
                result.append((start, end))
        return result

    origin_x = float(district["x"])
    origin_z = float(district["z"])
    max_x = origin_x + float(district["width"])
    max_z = origin_z + float(district["depth"])
    segments: list[list[list[float]]] = []
    for row in sorted(horizontal):
        z = min(max_z, origin_z + row * cell_size)
        for start, end in merge(horizontal[row]):
            segments.append(
                [
                    [min(max_x, origin_x + start * cell_size), z],
                    [min(max_x, origin_x + end * cell_size), z],
                ]
            )
    for column in sorted(vertical):
        x = min(max_x, origin_x + column * cell_size)
        for start, end in merge(vertical[column]):
            segments.append(
                [
                    [x, min(max_z, origin_z + start * cell_size)],
                    [x, min(max_z, origin_z + end * cell_size)],
                ]
            )
    return segments


def derive_district_territories(scene: dict[str, Any]) -> dict[str, Any]:
    """Return a bounded visual territory mask for every canonical district."""

    districts = {item["id"]: item for item in scene["districts"]}
    children: dict[str, list[str]] = {district_id: [] for district_id in districts}
    direct_buildings: dict[str, list[dict[str, Any]]] = {
        district_id: [] for district_id in districts
    }
    for district in scene["districts"]:
        parent_id = district["parentId"]
        if parent_id in children:
            children[parent_id].append(district["id"])
    for child_ids in children.values():
        child_ids.sort()
    for building in scene["buildings"]:
        if building["districtId"] in direct_buildings:
            direct_buildings[building["districtId"]].append(building)
    for buildings in direct_buildings.values():
        buildings.sort(key=lambda item: item["entityId"])

    descendant_buildings: dict[str, tuple[dict[str, Any], ...]] = {}

    def collect(district_id: str) -> tuple[dict[str, Any], ...]:
        if district_id in descendant_buildings:
            return descendant_buildings[district_id]
        result = list(direct_buildings[district_id])
        for child_id in children[district_id]:
            result.extend(collect(child_id))
        descendant_buildings[district_id] = tuple(result)
        return descendant_buildings[district_id]

    territories: list[dict[str, Any]] = []
    for district_id in sorted(districts):
        district = districts[district_id]
        columns = max(1, math.ceil(float(district["width"]) / TERRITORY_CELL_SIZE))
        rows = max(1, math.ceil(float(district["depth"]) / TERRITORY_CELL_SIZE))
        cells: set[Cell] = set()
        for building in collect(district_id):
            start_column = max(
                0,
                math.floor(
                    (float(building["x"]) - float(district["x"]))
                    / TERRITORY_CELL_SIZE
                ),
            )
            start_row = max(
                0,
                math.floor(
                    (float(building["z"]) - float(district["z"]))
                    / TERRITORY_CELL_SIZE
                ),
            )
            end_column = min(
                columns,
                max(
                    start_column + 1,
                    math.ceil(
                        (
                            float(building["x"])
                            + float(building["width"])
                            - float(district["x"])
                        )
                        / TERRITORY_CELL_SIZE
                    ),
                ),
            )
            end_row = min(
                rows,
                max(
                    start_row + 1,
                    math.ceil(
                        (
                            float(building["z"])
                            + float(building["depth"])
                            - float(district["z"])
                        )
                        / TERRITORY_CELL_SIZE
                    ),
                ),
            )
            for row in range(start_row, end_row):
                for column in range(start_column, end_column):
                    cells.add((column, row))
        if not cells:
            rectangles = [
                {
                    "depth": float(district["depth"]),
                    "width": float(district["width"]),
                    "x": float(district["x"]),
                    "z": float(district["z"]),
                }
            ]
            boundary = [
                [[rectangles[0]["x"], rectangles[0]["z"]], [rectangles[0]["x"] + rectangles[0]["width"], rectangles[0]["z"]]],
                [[rectangles[0]["x"] + rectangles[0]["width"], rectangles[0]["z"]], [rectangles[0]["x"] + rectangles[0]["width"], rectangles[0]["z"] + rectangles[0]["depth"]]],
                [[rectangles[0]["x"] + rectangles[0]["width"], rectangles[0]["z"] + rectangles[0]["depth"]], [rectangles[0]["x"], rectangles[0]["z"] + rectangles[0]["depth"]]],
                [[rectangles[0]["x"], rectangles[0]["z"] + rectangles[0]["depth"]], [rectangles[0]["x"], rectangles[0]["z"]]],
            ]
            landmark_plot = rectangles[0]
        else:
            cells = _connect_cells(cells, columns, rows)
            cells = _dilate_cells(cells, columns, rows)
            rectangles = _merged_rectangles(district, cells, TERRITORY_CELL_SIZE)
            boundary = _boundary_segments(district, cells, TERRITORY_CELL_SIZE)
            landmark_plot = _landmark_plot(
                district, cells, columns, rows, TERRITORY_CELL_SIZE
            )
        min_x = min(item["x"] for item in rectangles)
        min_z = min(item["z"] for item in rectangles)
        max_x = max(item["x"] + item["width"] for item in rectangles)
        max_z = max(item["z"] + item["depth"] for item in rectangles)
        territories.append(
            {
                "boundary": boundary,
                "bounds": {
                    "maxX": max_x,
                    "maxZ": max_z,
                    "minX": min_x,
                    "minZ": min_z,
                },
                "id": district_id,
                "labelAnchor": [min_x + 2, min_z + 2],
                "landmarkPlot": landmark_plot,
                "rectangles": rectangles,
            }
        )
    return {"cellSize": TERRITORY_CELL_SIZE, "districts": territories}
