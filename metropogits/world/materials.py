"""Presentation colours only: never mutate source roles, geometry or metrics."""

import math
from metropogits.facilities import FACILITY_COLORS

VERSION = "building-materials/0.1"
# Architectural tones, not claims about real source-code construction materials.
PALETTES = [
    ["#b9b6aa", "#717a7d"],  # limestone / slate
    ["#a6b5bb", "#586d7b"],  # cool concrete / metal
    ["#c2ae93", "#7a6c60"],  # sandstone / warm roof
    ["#ad9e94", "#665f60"],  # muted masonry
    ["#c2c6c3", "#667879"],  # light concrete
    ["#95a5ae", "#52616e"],  # blue-grey cladding
]
ROLE_COLORS = dict(
    GENERIC_BUILDING="#a2adbb", SERVICE_OFFICE="#60a5fa", GATE="#f472b6",
    STRUCTURED_WAREHOUSE="#34d399", DOCUMENT_DEPOT="#6ee7b7",
    CACHE_TOWER="#fbbf24", LIBRARY="#facc15", CONTROL_CENTER="#a78bfa",
    PORT="#38bdf8", EXCHANGE="#fb923c",
)
ROLE_COLORS.update(FACILITY_COLORS)


def policy():
    return dict(version=VERSION, palettes=[p[:] for p in PALETTES], roleColors=dict(ROLE_COLORS))


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
    role = ROLE_COLORS.get(building["archetype"], ROLE_COLORS["GENERIC_BUILDING"])
    if full_tint:
        wall = roof = role
    elif building["archetype"] in ROLE_COLORS and building["archetype"] != "GENERIC_BUILDING":
        if part["y"] + part["height"] >= top - 1e-6:
            roof = blend(roof, role, .78)
    shade = part.get("shade", 0)
    return dict(wall=blend(wall, "#ffffff", shade), roof=blend(roof, "#ffffff", shade))
