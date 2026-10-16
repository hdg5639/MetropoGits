"""Package a dependency-free interactive city viewer for static hosting."""

from __future__ import annotations

from importlib.resources import files
from typing import Any

from scripts.canonical_json import canonical_json_bytes
from scripts.validate_city import validate_document as validate_city_document


ASSET_PACKAGE = "metropogits.viewer_assets"


class ViewerError(ValueError):
    """Raised when viewer artifacts cannot be generated safely."""


def _javascript_data(scene: dict[str, Any], ucg: dict[str, Any]) -> bytes:
    payload = canonical_json_bytes({"scene": scene, "ucg": ucg}).decode("utf-8")
    safe_payload = (
        payload.replace("<", r"\u003c")
        .replace(">", r"\u003e")
        .replace("&", r"\u0026")
        .replace("\u2028", r"\u2028")
        .replace("\u2029", r"\u2029")
    )
    return f"globalThis.METROPOGITS_DATA={safe_payload};\n".encode("utf-8")


def render_viewer(
    scene: dict[str, Any], ucg: dict[str, Any]
) -> dict[str, bytes]:
    """Return deterministic, file://-compatible viewer artifacts."""

    errors = validate_city_document(scene, ucg)
    if errors:
        raise ViewerError("invalid City Scene: " + "; ".join(errors))

    resources = files(ASSET_PACKAGE)
    result = {
        "index.html": resources.joinpath("index.html").read_bytes(),
        "assets/viewer.css": resources.joinpath("viewer.css").read_bytes(),
        "assets/viewer.js": resources.joinpath("viewer.js").read_bytes(),
        "assets/viewer-data.js": _javascript_data(scene, ucg),
    }
    return dict(sorted(result.items()))
