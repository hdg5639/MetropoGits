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
    return dict(version=VERSION, palettes=[p[:] for p in PALETTES],
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


def part_material(building, part, top, full_tint=False):
    wall, roof = PALETTES[stable_index(building["entityId"], len(PALETTES))]
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
