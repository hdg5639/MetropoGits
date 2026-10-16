"""Unified MetropoGits command-line interface."""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path
from typing import Any

from metropogits import __version__
from metropogits.analyzers.java import JavaAnalysisError, enrich_java_graph
from metropogits.layout import LayoutError, generate_city
from metropogits.preview import PreviewError, render_preview
from metropogits.scanner import (
    ScanLimits,
    ScannerError,
    build_structural_ucg,
    scan_repository,
)
from metropogits.viewer import ViewerError, render_viewer
from scripts.canonical_json import (
    CanonicalJsonError,
    canonical_json_bytes,
    loads_strict_json,
)
from scripts.stable_ids import (
    normalize_repository_id,
    repository_id_from_root,
)
from scripts.validate_city import validate_document as validate_city_document
from scripts.validate_ucg import validate_document as validate_ucg_document


EXIT_SUCCESS = 0
EXIT_INVALID_INPUT = 2
DEFAULT_LIMITS = ScanLimits()
PRIVACY_WARNING = (
    "Generated metadata can reveal repository filenames and architecture; "
    "publish it only after review."
)


class CliError(ValueError):
    """Raised for an actionable command-line workflow failure."""


def _sha256_bytes(content: bytes) -> str:
    return f"sha256:{hashlib.sha256(content).hexdigest()}"


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        document = loads_strict_json(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, CanonicalJsonError) as error:
        raise CliError(f"unable to read {label}: {error}") from error
    if not isinstance(document, dict):
        raise CliError(f"{label} root must be an object")
    return document


def _write_bytes(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content)


def _repository_id(repo: Path, supplied: str | None) -> str:
    return (
        normalize_repository_id(supplied)
        if supplied is not None
        else repository_id_from_root(repo)
    )


def analyze_repository(
    repo: Path,
    repository_id: str | None = None,
    revision: str | None = None,
    source_url: str | None = None,
    limits: ScanLimits | None = None,
    excluded_paths: tuple[Path, ...] = (),
) -> dict[str, Any]:
    resolved_limits = limits or ScanLimits()
    resolved_id = _repository_id(repo, repository_id)
    scan = scan_repository(repo, resolved_limits, excluded_paths)
    structural_graph = build_structural_ucg(
        scan, resolved_id, revision, source_url
    )
    return enrich_java_graph(repo, scan, structural_graph, resolved_limits)


def _artifact_record(path: str, media_type: str, content: bytes) -> dict[str, Any]:
    return {
        "bytes": len(content),
        "mediaType": media_type,
        "path": path,
        "sha256": _sha256_bytes(content),
    }


def build_repository(
    repo: Path,
    output: Path,
    repository_id: str | None = None,
    theme: str = "minimal",
    revision: str | None = None,
    source_url: str | None = None,
    width: int = 1200,
    height: int = 675,
    limits: ScanLimits | None = None,
) -> dict[str, Any]:
    resolved_repo = repo.resolve(strict=False)
    resolved_output = output.resolve(strict=False)
    if resolved_output == resolved_repo or resolved_output in resolved_repo.parents:
        raise CliError("output directory must not be the repository root or its parent")
    graph = analyze_repository(
        repo,
        repository_id,
        revision,
        source_url,
        limits,
        excluded_paths=(output,),
    )
    scene = generate_city(graph, theme)
    preview = render_preview(scene, graph, width, height)
    viewer_artifacts = render_viewer(scene, graph)

    graph_bytes = canonical_json_bytes(graph)
    scene_bytes = canonical_json_bytes(scene)
    snippet_bytes = (
        "[![MetropoGits city preview](preview.svg)](index.html)\n"
    ).encode("utf-8")
    media_types = {
        "assets/viewer-data.js": "text/javascript",
        "assets/viewer.css": "text/css",
        "assets/viewer.js": "text/javascript",
        "index.html": "text/html",
    }
    artifacts = sorted(
        [
            _artifact_record("README_SNIPPET.md", "text/markdown", snippet_bytes),
            _artifact_record("city.json", "application/json", scene_bytes),
            _artifact_record("graph.ucg.json", "application/json", graph_bytes),
            _artifact_record("preview.svg", "image/svg+xml", preview),
        ]
        + [
            _artifact_record(path, media_types[path], content)
            for path, content in viewer_artifacts.items()
        ],
        key=lambda item: item["path"],
    )
    diagnostics = graph["diagnostics"]
    warning_count = sum(
        1 for diagnostic in diagnostics if diagnostic.get("severity") == "WARNING"
    )
    error_count = sum(
        1 for diagnostic in diagnostics if diagnostic.get("severity") == "ERROR"
    )
    manifest: dict[str, Any] = {
        "artifacts": artifacts,
        "diagnostics": {
            "count": len(diagnostics),
            "errorCount": error_count,
            "warningCount": warning_count,
        },
        "generator": {
            "catalogVersion": graph["generator"]["catalogVersion"],
            "name": "metropogits",
            "version": __version__,
        },
        "options": {
            "height": height,
            "layoutAlgorithm": scene["layoutAlgorithm"],
            "theme": theme,
            "width": width,
        },
        "privacyWarnings": [PRIVACY_WARNING],
        "repository": graph["repository"],
        "schemaVersion": "manifest/0.1",
        "status": "PARTIAL" if warning_count or error_count else "COMPLETE",
    }
    manifest_bytes = canonical_json_bytes(manifest)

    output.mkdir(parents=True, exist_ok=True)
    _write_bytes(output / "graph.ucg.json", graph_bytes)
    _write_bytes(output / "city.json", scene_bytes)
    _write_bytes(output / "preview.svg", preview)
    _write_bytes(output / "README_SNIPPET.md", snippet_bytes)
    for relative_path, content in viewer_artifacts.items():
        _write_bytes(output / relative_path, content)
    _write_bytes(output / "manifest.json", manifest_bytes)
    return manifest


def _add_scan_options(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--repo-id")
    parser.add_argument("--revision")
    parser.add_argument("--source-url")
    parser.add_argument("--max-entries", type=int, default=DEFAULT_LIMITS.max_entries)
    parser.add_argument("--max-files", type=int, default=DEFAULT_LIMITS.max_files)
    parser.add_argument(
        "--max-file-bytes", type=int, default=DEFAULT_LIMITS.max_file_bytes
    )
    parser.add_argument(
        "--max-total-bytes", type=int, default=DEFAULT_LIMITS.max_total_bytes
    )
    parser.add_argument("--max-depth", type=int, default=DEFAULT_LIMITS.max_depth)


def _limits_from_args(args: argparse.Namespace) -> ScanLimits:
    return ScanLimits(
        max_entries=args.max_entries,
        max_files=args.max_files,
        max_file_bytes=args.max_file_bytes,
        max_total_bytes=args.max_total_bytes,
        max_depth=args.max_depth,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="metropogits", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    commands = parser.add_subparsers(dest="command", required=True)

    analyze = commands.add_parser("analyze", help="scan a repository into UCG")
    _add_scan_options(analyze)
    analyze.add_argument("--out", type=Path, required=True)

    generate = commands.add_parser("generate", help="generate a City Scene")
    generate.add_argument("--graph", type=Path, required=True)
    generate.add_argument("--out", type=Path, required=True)
    generate.add_argument("--theme", default="minimal")

    render = commands.add_parser("render", help="render an SVG preview")
    render.add_argument("--scene", type=Path, required=True)
    render.add_argument("--graph", type=Path, required=True)
    render.add_argument("--out", type=Path, required=True)
    render.add_argument("--width", type=int, default=1200)
    render.add_argument("--height", type=int, default=675)

    build = commands.add_parser("build", help="run the structural preview pipeline")
    _add_scan_options(build)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--theme", default="minimal")
    build.add_argument("--width", type=int, default=1200)
    build.add_argument("--height", type=int, default=675)

    validate = commands.add_parser("validate", help="validate UCG or City JSON")
    validate.add_argument("--input", type=Path, required=True)
    validate.add_argument("--ucg", type=Path)
    return parser


def _run(args: argparse.Namespace) -> str:
    if args.command == "analyze":
        graph = analyze_repository(
            args.repo,
            args.repo_id,
            args.revision,
            args.source_url,
            _limits_from_args(args),
        )
        _write_bytes(args.out, canonical_json_bytes(graph))
        return f"Wrote UCG with {len(graph['entities'])} entities: {args.out}"

    if args.command == "generate":
        graph = _load_json(args.graph, "UCG")
        scene = generate_city(graph, args.theme)
        _write_bytes(args.out, canonical_json_bytes(scene))
        return f"Wrote City Scene with {len(scene['buildings'])} buildings: {args.out}"

    if args.command == "render":
        graph = _load_json(args.graph, "UCG")
        scene = _load_json(args.scene, "City Scene")
        preview = render_preview(scene, graph, args.width, args.height)
        _write_bytes(args.out, preview)
        return f"Wrote SVG preview: {args.out}"

    if args.command == "build":
        manifest = build_repository(
            args.repo,
            args.out,
            args.repo_id,
            args.theme,
            args.revision,
            args.source_url,
            args.width,
            args.height,
            _limits_from_args(args),
        )
        return (
            f"Built {len(manifest['artifacts'])} artifacts with "
            f"status {manifest['status']}: {args.out}"
        )

    document = _load_json(args.input, "contract document")
    schema_version = document.get("schemaVersion")
    if schema_version == "ucg/0.1":
        errors = validate_ucg_document(document)
    elif schema_version == "city/0.1":
        if args.ucg is None:
            raise CliError("--ucg is required when validating a City Scene")
        graph = _load_json(args.ucg, "UCG")
        errors = validate_city_document(document, graph)
    else:
        raise CliError(f"unsupported schemaVersion: {schema_version!r}")
    if errors:
        raise CliError("contract validation failed: " + "; ".join(errors))
    return f"Valid {schema_version} document: {args.input}"


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        message = _run(args)
    except (
        OSError,
        CliError,
        JavaAnalysisError,
        LayoutError,
        PreviewError,
        ScannerError,
        ViewerError,
        ValueError,
    ) as error:
        print(f"MetropoGits failed: {error}", file=sys.stderr)
        return EXIT_INVALID_INPUT
    print(message)
    return EXIT_SUCCESS


if __name__ == "__main__":
    raise SystemExit(main())
