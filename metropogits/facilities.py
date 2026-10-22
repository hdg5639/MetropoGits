"""Shared, bounded facility silhouettes: one real source file, one envelope.

These are architectural metaphors, not claims of deployed infrastructure.
JSON is shared by CPU, Canvas and WebGL to prevent geometry drift.
"""

import json
from importlib.resources import files

FACILITY_MODELS = json.loads(
    files("metropogits.viewer_assets")
    .joinpath("facility-models.json")
    .read_text(encoding="utf8")
)
FACILITY_COLORS = {name: model["color"] for name, model in FACILITY_MODELS.items()}


def color_triple(hex_color):
    channels = [int(hex_color[i : i + 2], 16) for i in (1, 3, 5)]
    return tuple(
        "#" + "".join(f"{round(c * scale):02x}" for c in channels)
        for scale in (1, 0.65, 0.42)
    )


FACILITY_PALETTES = {
    name: color_triple(color) for name, color in FACILITY_COLORS.items()
}
