"""CPU counterpart of the viewer's pure ADR-012 block projection.

Keep this derivation in parity with viewer-filters.js; shared scene tests compare
membership, plots, and representative geometry, not merely aggregate counts.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict

from metropogits.preview import _major_district_ids
from metropogits.territory import derive_district_territories


def _round(value):
    return math.floor(value + 0.5)


def _bucket(value):
    result = 0x811C9DC5
    for character in value:
        result = ((result ^ ord(character)) * 0x01000193) & 0xFFFFFFFF
    return result % 2147483647


def _center(item, axis):
    return item[axis] + item["width" if axis == "x" else "depth"] / 2


def _bounds(items):
    x, z = min(item["x"] for item in items), min(item["z"] for item in items)
    return dict(
        x=x,
        z=z,
        width=max(item["x"] + item["width"] for item in items) - x,
        depth=max(item["z"] + item["depth"] for item in items) - z,
    )


def _partition(members, count):
    if count <= 1 or len(members) <= 1:
        return [list(members)]
    axes = sorted(
        ("x", "z"),
        key=lambda a: (
            -(
                max(_center(b, a) for b in members)
                - min(_center(b, a) for b in members)
            ),
            a,
        ),
    )
    left_count = count // 2
    right_count = count - left_count
    ideal = _round(len(members) * left_count / count)
    selected = None
    for axis in axes:
        other = "z" if axis == "x" else "x"
        size = "width" if axis == "x" else "depth"
        ordered = sorted(
            members, key=lambda b: (_center(b, axis), _center(b, other), b["entityId"])
        )
        ends, end = [], -math.inf
        for item in ordered:
            end = max(end, item[axis] + item[size])
            ends.append(end)
        starts, start = [0] * len(ordered), math.inf
        for index in range(len(ordered) - 1, -1, -1):
            start = min(start, ordered[index][axis])
            starts[index] = start
        candidates = [
            i
            for i in range(left_count, len(ordered) - right_count + 1)
            if ends[i - 1] <= starts[i]
        ]
        if candidates:
            selected = (ordered, min(candidates, key=lambda i: (abs(i - ideal), i)))
            break
    if selected is None:
        selected = (
            sorted(members, key=lambda b: b["entityId"]),
            max(left_count, min(len(members) - right_count, ideal)),
        )
    ordered, split = selected
    return _partition(ordered[:split], left_count) + _partition(
        ordered[split:], right_count
    )


def _intersection(a, b):
    x, z = max(a["x"], b["x"]), max(a["z"], b["z"])
    width = min(a["x"] + a["width"], b["x"] + b["width"]) - x
    depth = min(a["z"] + a["depth"], b["z"] + b["depth"]) - z
    return dict(x=x, z=z, width=width, depth=depth) if width > 0 and depth > 0 else None


def _subtract(plot, blocker):
    overlap = _intersection(plot, blocker)
    if overlap is None:
        return [plot]
    x, z = overlap["x"], overlap["z"]
    end_x, end_z = x + overlap["width"], z + overlap["depth"]
    parts = [
        dict(x=plot["x"], z=plot["z"], width=plot["width"], depth=z - plot["z"]),
        dict(
            x=plot["x"],
            z=end_z,
            width=plot["width"],
            depth=plot["z"] + plot["depth"] - end_z,
        ),
        dict(x=plot["x"], z=z, width=x - plot["x"], depth=overlap["depth"]),
        dict(
            x=end_x,
            z=z,
            width=plot["x"] + plot["width"] - end_x,
            depth=overlap["depth"],
        ),
    ]
    return [part for part in parts if part["width"] > 0 and part["depth"] > 0]


def district_owners(scene, major_ids=None):
    """Nearest major ancestor, or the root's direct child for residual files."""
    major_ids = _major_district_ids(scene) if major_ids is None else major_ids
    districts = {d["id"]: d for d in scene["districts"]}
    owners = {}
    for district in scene["districts"]:
        path, current = [], district
        while current:
            path.append(current["id"])
            if current["id"] in major_ids:
                break
            current = districts.get(current["parentId"])
        owners[district["id"]] = (
            path[-1] if current else path[-2] if len(path) > 1 else path[-1]
        )
    return owners


def derive_blocks(scene, territory_data=None):
    """Return complete, disjoint file membership with viewer-compatible plots."""
    territory_data = territory_data or derive_district_territories(scene)
    territories = {t["id"]: t for t in territory_data["districts"]}
    districts = {d["id"]: d for d in scene["districts"]}
    major_ids = _major_district_ids(scene)
    owners = district_owners(scene, major_ids)
    groups = defaultdict(list)
    for building in scene["buildings"]:
        groups[owners[building["districtId"]]].append(building)

    def ancestry(district_id):
        path = []
        while district_id in districts:
            path.append(district_id)
            district_id = districts[district_id]["parentId"]
        return path[::-1]

    target_count = min(48, max(12, _round(math.sqrt(len(scene["buildings"])))))
    target_population = max(1, len(scene["buildings"]) / target_count)
    facilities = []
    for major_id, members in sorted(groups.items()):
        members.sort(key=lambda b: b["entityId"])
        count = min(len(members), max(1, _round(len(members) / target_population)))
        partitions = sorted(
            _partition(members, count),
            key=lambda group: (
                min(_center(b, "z") for b in group),
                min(_center(b, "x") for b in group),
                group[0]["entityId"],
            ),
        )
        for index, group in enumerate(partitions):
            group.sort(key=lambda b: b["entityId"])
            common = major_id
            for level in zip(*(ancestry(b["districtId"]) for b in group)):
                if len(set(level)) != 1:
                    break
                common = level[0]
            placement = _bounds(group)
            plots = [
                p
                for r in territories[major_id]["rectangles"]
                if (p := _intersection(placement, r))
            ]
            for nested_id in sorted(major_ids):
                if major_id not in ancestry(nested_id)[:-1]:
                    continue
                for blocker in territories[nested_id]["rectangles"]:
                    plots = [
                        part for plot in plots for part in _subtract(plot, blocker)
                    ]
            plots = sorted(
                plots or [placement],
                key=lambda p: (p["z"], p["x"], p["depth"], p["width"]),
            )
            bounds = _bounds(plots)
            label = min(plots, key=lambda p: (-p["width"] * p["depth"], p["z"], p["x"]))
            counts = Counter(b["archetype"] for b in group)
            facilities.append(
                {
                    **bounds,
                    "width": max(2, bounds["width"]),
                    "depth": max(2, bounds["depth"]),
                    "archetypeCounts": [
                        dict(archetype=a, count=n)
                        for a, n in sorted(counts.items(), key=lambda p: (-p[1], p[0]))
                    ],
                    "districtId": common,
                    "majorDistrictId": major_id,
                    "height": min(64, 14 + math.log2(len(group) + 1) * 4.5),
                    "id": f"visual:block:{major_id}:{index:03d}",
                    "labelX": _center(label, "x"),
                    "labelZ": _center(label, "z"),
                    "memberDistrictIds": sorted({b["districtId"] for b in group}),
                    "memberEntityIds": [b["entityId"] for b in group],
                    "plots": plots,
                }
            )
    return sorted(facilities, key=lambda f: f["id"])


def aggregate_parts(facility):
    """Balanced representative masses, with exact population accounting."""
    counts = facility["archetypeCounts"]
    target = min(
        16, max(len(counts), math.ceil(math.sqrt(len(facility["memberEntityIds"]))))
    )
    allocations = {item["archetype"]: 1 for item in counts[:target]}
    while sum(allocations.values()) < target:
        selected = min(
            (item for item in counts if item["archetype"] in allocations),
            key=lambda item: (
                -item["count"] / (allocations[item["archetype"]] + 1),
                item["archetype"],
            ),
        )
        allocations[selected["archetype"]] += 1
    parts = []
    for item in counts:
        count = allocations.get(item["archetype"], 0)
        for index in range(count):
            parts.append(
                dict(
                    archetype=item["archetype"],
                    entityId=f"{facility['id']}:{item['archetype']}:{index}",
                    representedCount=item["count"] // count
                    + (index < item["count"] % count),
                )
            )
    parts.sort(key=lambda p: (_bucket(p["entityId"]), p["entityId"]))
    source = facility.get("plots", [facility])
    usable = [p for p in source if p["width"] >= 2 and p["depth"] >= 2]
    candidates = usable if len(usable) >= min(len(parts), len(source)) else source
    largest_area = max(p["width"] * p["depth"] for p in candidates)
    span_x, span_z = max(1, facility["width"]), max(1, facility["depth"])
    selected = []

    def score(plot):
        area_bonus = math.sqrt(plot["width"] * plot["depth"] / largest_area) * 0.08
        nx = (_center(plot, "x") - facility["x"]) / span_x
        nz = (_center(plot, "z") - facility["z"]) / span_z
        if not selected:
            return -math.hypot(nx - 0.5, nz - 0.5) + area_bonus
        separation = min(
            math.hypot(
                (_center(plot, "x") - _center(p, "x")) / span_x,
                (_center(plot, "z") - _center(p, "z")) / span_z,
            )
            for p in selected
        )
        cx = (
            nx + sum((_center(p, "x") - facility["x"]) / span_x for p in selected)
        ) / (len(selected) + 1)
        cz = (
            nz + sum((_center(p, "z") - facility["z"]) / span_z for p in selected)
        ) / (len(selected) + 1)
        return separation + area_bonus - math.hypot(cx - 0.5, cz - 0.5) * 0.85

    while len(selected) < min(len(parts), len(candidates)):
        remaining = [p for p in candidates if p not in selected]
        selected.append(
            min(
                remaining,
                key=lambda p: (
                    -score(p),
                    -p["width"] * p["depth"],
                    _bucket(f"{facility['id']}:{p['x']:g}:{p['z']:g}"),
                    p["z"],
                    p["x"],
                ),
            )
        )
    selected.sort(key=lambda p: (p["z"], p["x"], -p["width"] * p["depth"]))
    plot_counts = [dict(count=1, plot=p) for p in selected]
    while sum(item["count"] for item in plot_counts) < len(parts):
        plot_counts.sort(
            key=lambda item: (
                -item["plot"]["width"] * item["plot"]["depth"] / (item["count"] + 1),
                item["plot"]["z"],
                item["plot"]["x"],
            )
        )
        plot_counts[0]["count"] += 1
    slots = []
    for item in plot_counts:
        count, plot = item["count"], item["plot"]
        columns = max(
            1, math.ceil(math.sqrt(count * plot["width"] / max(1, plot["depth"])))
        )
        rows = math.ceil(count / columns)
        mx, mz, gx, gz = (
            plot["width"] * 0.07,
            plot["depth"] * 0.07,
            plot["width"] * 0.035,
            plot["depth"] * 0.035,
        )
        width = (plot["width"] - mx * 2 - gx * max(0, columns - 1)) / columns
        depth = (plot["depth"] - mz * 2 - gz * max(0, rows - 1)) / rows
        for index in range(count):
            row, column = divmod(index, columns)
            items_in_row = min(columns, count - row * columns)
            occupied_width = items_in_row * width + max(0, items_in_row - 1) * gx
            slots.append(
                dict(
                    width=width,
                    depth=depth,
                    x=plot["x"]
                    + (plot["width"] - occupied_width) / 2
                    + column * (width + gx),
                    z=plot["z"] + mz + row * (depth + gz),
                )
            )
    largest = max(p["representedCount"] for p in parts)
    return [
        {
            **part,
            **slot,
            "height": facility["height"]
            * (0.48 + math.sqrt(part["representedCount"] / largest) * 0.52),
        }
        for part, slot in zip(parts, slots)
    ]
