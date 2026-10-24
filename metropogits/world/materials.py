"""Presentation colours only: never mutate source roles, geometry or metrics."""

import math
from metropogits.facilities import FACILITY_COLORS

VERSION = "building-materials/0.1"
# Architectural tones, not claims about real source-code construction materials.
PALETTES = [
    ["#d8dcdc", "#59656c"],  # white ceramic / graphite roof
    ["#8fa7b3", "#3f5666"],  # blue-grey glass cladding
    ["#cdbfa8", "#6a625a"],  # champagne stone
    ["#6f7f89", "#38464f"],  # graphite metal panel
    ["#e3e6e4", "#7b878c"],  # pale concrete
    ["#7e9aa6", "#34505f"],  # teal curtain wall
    # Warmer and more saturated tones, used only through REGIONS below.
    ["#b4533e", "#4d2d27"],  # red brick
    ["#c98a63", "#62402f"],  # terracotta
    ["#d9c299", "#7a6a52"],  # sandstone
    ["#ece5d6", "#8c8a82"],  # white stucco
    ["#5f9ea0", "#2c5a63"],  # green-teal glass
    ["#6e93c2", "#2f4c72"],  # blue glass
    ["#40526e", "#212c42"],  # navy metal
    ["#d2a44c", "#6e5424"],  # ochre cladding
    ["#9db487", "#4d5e3d"],  # sage patina
    ["#d2a8a0", "#7a5650"],  # dusty rose render
    ["#8a6a52", "#43332a"],  # timber and copper
]
# Quarter styles. A planning neighbourhood picks one region from a stable hash of its
# id and its buildings pick within it, so a city reads as distinct quarters instead of
# one uniform grey mix. Purely presentational: roles stay on roof accents and in the
# inspector, and no region claims anything about the source.
REGIONS = [
    [10, 11, 12, 5, 4],  # glass downtown
    [6, 7, 8, 16, 2],    # brick quarter
    [8, 2, 9, 15, 4],    # stone civic quarter
    [14, 9, 10, 13, 16], # garden quarter
    [3, 12, 13, 4, 6],   # industrial works
    [0, 1, 2, 3, 4, 5],  # original ceramic and graphite mix
]
# Presentation-only entrance glazing, roller shutter and canopy cladding.
DETAIL_COLORS = {2: ["#6a93aa", "#c4d0d6"], 12: ["#354e59", "#566771"], 13: ["#56616a", "#728087"],
                 14: ["#77838a", "#9ba5a9"]}
ROLE_COLORS = dict(
    GENERIC_BUILDING="#a2adbb", SERVICE_OFFICE="#60a5fa", GATE="#f472b6",
    STRUCTURED_WAREHOUSE="#34d399", DOCUMENT_DEPOT="#6ee7b7",
    CACHE_TOWER="#fbbf24", LIBRARY="#facc15", CONTROL_CENTER="#a78bfa",
    PORT="#38bdf8", EXCHANGE="#fb923c",
)
ROLE_COLORS.update(FACILITY_COLORS)


def policy():
    return dict(version=VERSION, palettes=[p[:] for p in PALETTES], regions=[r[:] for r in REGIONS],
                detailColors={str(k): v[:] for k, v in DETAIL_COLORS.items()},
                roleColors=dict(ROLE_COLORS))


def stable_index(identity, count):
    """FNV-1a over Unicode code points, matching the viewer's for-of iteration."""
    value = 2166136261
    for character in str(identity):
        value = ((value ^ ord(character)) * 16777619) & 0xFFFFFFFF
    return value % count


def blend(left, right, amount):
    return "#" + "".join(
        f"{math.floor(int(left[i:i+2], 16)*(1-amount)+int(right[i:i+2], 16)*amount+.5):02x}"
        for i in (1, 3, 5)
    )


def palette_for(building):
    quarter = building.get("zoneId") or building.get("districtId")
    if quarter:
        region = REGIONS[stable_index(quarter, len(REGIONS))]
        return PALETTES[region[stable_index(building["entityId"], len(region))]]
    return PALETTES[stable_index(building["entityId"], len(PALETTES))]


def part_material(building, part, top, full_tint=False):
    wall, roof = palette_for(building)
    if part.get("materialKind") in DETAIL_COLORS:
        wall, roof = DETAIL_COLORS[part["materialKind"]]
    role = ROLE_COLORS.get(building["archetype"], ROLE_COLORS["GENERIC_BUILDING"])
    if full_tint:
        wall = roof = role
    elif building["archetype"] in ROLE_COLORS and building["archetype"] != "GENERIC_BUILDING":
        if part["y"] + part["height"] >= top - 1e-6:
            roof = blend(roof, role, .42)
    shade = part.get("shade", 0)
    return dict(wall=blend(wall, "#ffffff", shade), roof=blend(roof, "#ffffff", shade))
