"""Package a dependency-free interactive city viewer for static hosting."""

from __future__ import annotations

from importlib.resources import files
from typing import Any

from scripts.canonical_json import canonical_json_bytes, sha256_digest
from scripts.validate_city import validate_document as validate_city_document
from scripts.validate_history import validate_document as validate_history_document
from scripts.validate_metropolis import (
    validate_document as validate_metropolis_document,
)


ASSET_PACKAGE = "metropogits.viewer_assets"


class ViewerError(ValueError):
    """Raised when viewer artifacts cannot be generated safely."""


def _javascript_assignment(name: str, document: Any) -> bytes:
    payload = canonical_json_bytes(document).decode("utf-8")
    safe_payload = (
        payload.replace("<", r"\u003c")
        .replace(">", r"\u003e")
        .replace("&", r"\u0026")
        .replace("\u2028", r"\u2028")
        .replace("\u2029", r"\u2029")
    )
    return f"globalThis.{name}={safe_payload};\n".encode("utf-8")


def _javascript_data(scene: dict[str, Any], ucg: dict[str, Any]) -> bytes:
    return _javascript_assignment("METROPOGITS_DATA", {"scene": scene, "ucg": ucg})


def render_viewer(scene: dict[str, Any], ucg: dict[str, Any]) -> dict[str, bytes]:
    """Return deterministic, file://-compatible viewer artifacts."""

    errors = validate_city_document(scene, ucg)
    if errors:
        raise ViewerError("invalid City Scene: " + "; ".join(errors))

    resources = files(ASSET_PACKAGE)
    result = {
        "index.html": resources.joinpath("index.html").read_bytes(),
        "assets/viewer.css": resources.joinpath("viewer.css").read_bytes(),
        "assets/viewer-activity.js": resources.joinpath(
            "viewer-activity.js"
        ).read_bytes(),
        "assets/viewer-filters.js": resources.joinpath(
            "viewer-filters.js"
        ).read_bytes(),
        "assets/viewer-3d.js": resources.joinpath("viewer-3d.js").read_bytes(),
        "assets/viewer.js": resources.joinpath("viewer.js").read_bytes(),
        "assets/viewer-data.js": _javascript_data(scene, ucg),
    }
    return dict(sorted(result.items()))


def render_history_viewer(
    timeline: dict[str, Any], snapshots: list[dict[str, dict[str, Any]]]
) -> dict[str, bytes]:
    """Return a deterministic static viewer with revision selection."""

    history_errors = validate_history_document(timeline)
    if history_errors:
        raise ViewerError("invalid history timeline: " + "; ".join(history_errors))
    if len(snapshots) != len(timeline["frames"]):
        raise ViewerError("history snapshot count does not match timeline frames")
    frames: list[dict[str, Any]] = []
    for index, (snapshot, frame) in enumerate(zip(snapshots, timeline["frames"])):
        ucg = snapshot["ucg"]
        scene = snapshot["scene"]
        errors = validate_city_document(scene, ucg)
        if errors:
            raise ViewerError(
                f"invalid history snapshot {index}: " + "; ".join(errors)
            )
        if (
            ucg["repository"]["revision"] != frame["revision"]
            or sha256_digest(ucg) != frame["ucgDigest"]
            or sha256_digest(scene) != frame["cityDigest"]
        ):
            raise ViewerError(f"history snapshot {index} does not match its frame")
        frames.append(
            {"revision": frame["revision"], "scene": scene, "ucg": ucg}
        )

    resources = files(ASSET_PACKAGE)
    html = resources.joinpath("index.html").read_text(encoding="utf-8")
    history_bar = """    <section class="historybar" aria-label="Repository history">
      <label for="history-revision">Revision</label>
      <select id="history-revision"></select>
      <span id="history-summary" aria-live="polite"></span>
    </section>

"""
    html = html.replace("<body>", '<body class="history-mode">', 1)
    html = html.replace(
        '    <section class="filterbar"',
        history_bar + '    <section class="filterbar"',
        1,
    )
    html = html.replace(
        '    <script src="assets/viewer-filters.js" defer></script>',
        '    <script src="assets/viewer-history.js" defer></script>\n'
        '    <script src="assets/viewer-filters.js" defer></script>',
        1,
    )
    payload = {"frames": frames, "timeline": timeline}
    result = {
        "index.html": html.encode("utf-8"),
        "assets/viewer.css": resources.joinpath("viewer.css").read_bytes(),
        "assets/viewer-activity.js": resources.joinpath(
            "viewer-activity.js"
        ).read_bytes(),
        "assets/viewer-filters.js": resources.joinpath(
            "viewer-filters.js"
        ).read_bytes(),
        "assets/viewer-3d.js": resources.joinpath("viewer-3d.js").read_bytes(),
        "assets/viewer-history.js": resources.joinpath(
            "viewer-history.js"
        ).read_bytes(),
        "assets/viewer.js": resources.joinpath("viewer.js").read_bytes(),
        "assets/viewer-data.js": _javascript_assignment(
            "METROPOGITS_HISTORY", payload
        ),
    }
    return dict(sorted(result.items()))


def render_metropolis_viewer(
    document: dict[str, Any], scene: dict[str, Any], ucg: dict[str, Any]
) -> dict[str, bytes]:
    """Return a static viewer for a validated multi-repository metropolis."""

    metropolis_errors = validate_metropolis_document(document)
    if metropolis_errors:
        raise ViewerError(
            "invalid metropolis document: " + "; ".join(metropolis_errors)
        )
    scene_errors = validate_city_document(scene, ucg)
    if scene_errors:
        raise ViewerError("invalid merged City Scene: " + "; ".join(scene_errors))
    if (
        sha256_digest(ucg) != document["mergedUcgDigest"]
        or sha256_digest(scene) != document["mergedCityDigest"]
    ):
        raise ViewerError("metropolis digests do not match merged artifacts")

    resources = files(ASSET_PACKAGE)
    html = resources.joinpath("index.html").read_text(encoding="utf-8")
    metropolis_bar = """    <section class="metropolisbar" aria-label="Repository federation">
      <strong id="metropolis-repositories"></strong>
      <label for="metropolis-link">Cross-repository link</label>
      <select id="metropolis-link"></select>
      <span id="metropolis-link-summary" aria-live="polite"></span>
    </section>

"""
    html = html.replace("<body>", '<body class="metropolis-mode">', 1)
    html = html.replace(
        '    <section class="filterbar"',
        metropolis_bar + '    <section class="filterbar"',
        1,
    )
    html = html.replace(
        '    <script src="assets/viewer-filters.js" defer></script>',
        '    <script src="assets/viewer-metropolis.js" defer></script>\n'
        '    <script src="assets/viewer-filters.js" defer></script>',
        1,
    )
    data = _javascript_data(scene, ucg) + _javascript_assignment(
        "METROPOGITS_METROPOLIS", document
    )
    result = {
        "index.html": html.encode("utf-8"),
        "assets/viewer.css": resources.joinpath("viewer.css").read_bytes(),
        "assets/viewer-activity.js": resources.joinpath(
            "viewer-activity.js"
        ).read_bytes(),
        "assets/viewer-filters.js": resources.joinpath(
            "viewer-filters.js"
        ).read_bytes(),
        "assets/viewer-3d.js": resources.joinpath("viewer-3d.js").read_bytes(),
        "assets/viewer-metropolis.js": resources.joinpath(
            "viewer-metropolis.js"
        ).read_bytes(),
        "assets/viewer.js": resources.joinpath("viewer.js").read_bytes(),
        "assets/viewer-data.js": data,
    }
    return dict(sorted(result.items()))
