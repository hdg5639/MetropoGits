"""Unified MetropoGits command-line interface."""

from __future__ import annotations

import argparse
import hashlib
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from metropogits import __version__
from metropogits.analyzers import enrich_graph
from metropogits.analyzers.java import JavaAnalysisError
from metropogits.history import HistorySnapshot, build_history
from metropogits.layout import LayoutError, generate_city
from metropogits.preview import PreviewError, render_preview
from metropogits.scanner import (
    ScanLimits,
    ScannerError,
    build_structural_ucg,
    scan_repository,
)
from metropogits.viewer import ViewerError, render_history_viewer, render_viewer
from scripts.canonical_json import (
    CanonicalJsonError,
    canonical_json_bytes,
    loads_strict_json,
)
from scripts.stable_ids import (
    normalize_repository_id,
    repository_id_from_root,
)
from scripts.validate_catalog import validate_document as validate_catalog_document
from scripts.validate_city import validate_document as validate_city_document
from scripts.validate_history import validate_document as validate_history_document
from scripts.validate_ucg import validate_document as validate_ucg_document


EXIT_SUCCESS = 0
EXIT_PARTIAL = 1
EXIT_INVALID_INPUT = 2
EXIT_RESOURCE_LIMIT = 3
EXIT_INTERNAL_ERROR = 4
DEFAULT_LIMITS = ScanLimits()
RESOURCE_LIMIT_DIAGNOSTICS = frozenset(
    {
        "DEPTH_LIMIT_REACHED",
        "ENTRY_LIMIT_REACHED",
        "FILE_LIMIT_REACHED",
        "FILE_SIZE_LIMIT",
        "TOTAL_SIZE_LIMIT_REACHED",
    }
)
PRIVACY_WARNING = (
    "Generated metadata can reveal repository filenames and architecture; "
    "publish it only after review."
)


class CliError(ValueError):
    """Raised for an actionable command-line workflow failure."""


class CliUsageError(CliError):
    """Raised when command-line arguments do not satisfy the CLI contract."""


class CliArgumentParser(argparse.ArgumentParser):
    """Argument parser that lets the CLI format usage failures consistently."""

    def error(self, message: str) -> None:
        raise CliUsageError(message)


@dataclass(frozen=True)
class CommandResult:
    message: str
    output: str
    status: str = "COMPLETE"
    exit_code: int = EXIT_SUCCESS
    diagnostics: dict[str, Any] | None = None


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
    structural_graph = build_structural_ucg(scan, resolved_id, revision, source_url)
    return enrich_graph(repo, scan, structural_graph, resolved_limits)


def _artifact_record(path: str, media_type: str, content: bytes) -> dict[str, Any]:
    return {
        "bytes": len(content),
        "mediaType": media_type,
        "path": path,
        "sha256": _sha256_bytes(content),
    }


def _diagnostic_summary(diagnostics: list[dict[str, Any]]) -> dict[str, Any]:
    codes = Counter(str(item.get("code", "UNKNOWN")) for item in diagnostics)
    return {
        "codes": [
            {"code": code, "count": count} for code, count in sorted(codes.items())
        ],
        "count": len(diagnostics),
        "errorCount": sum(1 for item in diagnostics if item.get("severity") == "ERROR"),
        "infoCount": sum(1 for item in diagnostics if item.get("severity") == "INFO"),
        "warningCount": sum(
            1 for item in diagnostics if item.get("severity") == "WARNING"
        ),
    }


def _diagnostic_exit_code(diagnostics: list[dict[str, Any]]) -> int:
    if any(item.get("code") in RESOURCE_LIMIT_DIAGNOSTICS for item in diagnostics):
        return EXIT_RESOURCE_LIMIT
    if any(item.get("severity") in {"WARNING", "ERROR"} for item in diagnostics):
        return EXIT_PARTIAL
    return EXIT_SUCCESS


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
    snippet_bytes = ("[![MetropoGits city preview](preview.svg)](index.html)\n").encode(
        "utf-8"
    )
    media_types = {
        "assets/viewer-data.js": "text/javascript",
        "assets/viewer.css": "text/css",
        "assets/viewer-filters.js": "text/javascript",
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
    diagnostic_summary = _diagnostic_summary(diagnostics)
    manifest: dict[str, Any] = {
        "artifacts": artifacts,
        "diagnostics": diagnostic_summary,
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
        "status": (
            "PARTIAL"
            if diagnostic_summary["warningCount"] or diagnostic_summary["errorCount"]
            else "COMPLETE"
        ),
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


def _add_json_option(
    parser: argparse.ArgumentParser, *, suppress_default: bool = False
) -> None:
    default = argparse.SUPPRESS if suppress_default else False
    parser.add_argument(
        "--json",
        action="store_true",
        default=default,
        help="emit one structured JSON result for CI",
    )


def _limits_from_args(args: argparse.Namespace) -> ScanLimits:
    return ScanLimits(
        max_entries=args.max_entries,
        max_files=args.max_files,
        max_file_bytes=args.max_file_bytes,
        max_total_bytes=args.max_total_bytes,
        max_depth=args.max_depth,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = CliArgumentParser(prog="metropogits", description=__doc__)
    parser.add_argument("--version", action="version", version=__version__)
    _add_json_option(parser)
    commands = parser.add_subparsers(dest="command", required=True)

    analyze = commands.add_parser("analyze", help="scan a repository into UCG")
    _add_json_option(analyze, suppress_default=True)
    _add_scan_options(analyze)
    analyze.add_argument("--out", type=Path, required=True)

    generate = commands.add_parser("generate", help="generate a City Scene")
    _add_json_option(generate, suppress_default=True)
    generate.add_argument("--graph", type=Path, required=True)
    generate.add_argument("--out", type=Path, required=True)
    generate.add_argument("--theme", default="minimal")

    render = commands.add_parser("render", help="render an SVG preview")
    _add_json_option(render, suppress_default=True)
    render.add_argument("--scene", type=Path, required=True)
    render.add_argument("--graph", type=Path, required=True)
    render.add_argument("--out", type=Path, required=True)
    render.add_argument("--width", type=int, default=1200)
    render.add_argument("--height", type=int, default=675)

    build = commands.add_parser("build", help="run the structural preview pipeline")
    _add_json_option(build, suppress_default=True)
    _add_scan_options(build)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--theme", default="minimal")
    build.add_argument("--width", type=int, default=1200)
    build.add_argument("--height", type=int, default=675)

    history = commands.add_parser(
        "history", help="build a timeline from ordered build directories"
    )
    _add_json_option(history, suppress_default=True)
    history.add_argument(
        "--snapshot",
        type=Path,
        action="append",
        required=True,
        help="build directory containing graph.ucg.json and city.json; repeat in order",
    )
    history.add_argument("--out", type=Path, required=True)

    validate = commands.add_parser(
        "validate", help="validate UCG, City, or catalog JSON"
    )
    _add_json_option(validate, suppress_default=True)
    validate.add_argument("--input", type=Path, required=True)
    validate.add_argument("--ucg", type=Path)
    return parser


def _run(args: argparse.Namespace) -> CommandResult:
    if args.command == "analyze":
        graph = analyze_repository(
            args.repo,
            args.repo_id,
            args.revision,
            args.source_url,
            _limits_from_args(args),
        )
        _write_bytes(args.out, canonical_json_bytes(graph))
        diagnostics = _diagnostic_summary(graph["diagnostics"])
        exit_code = _diagnostic_exit_code(graph["diagnostics"])
        return CommandResult(
            f"Wrote UCG with {len(graph['entities'])} entities: {args.out}",
            str(args.out),
            "PARTIAL" if exit_code else "COMPLETE",
            exit_code,
            diagnostics,
        )

    if args.command == "generate":
        graph = _load_json(args.graph, "UCG")
        scene = generate_city(graph, args.theme)
        _write_bytes(args.out, canonical_json_bytes(scene))
        return CommandResult(
            f"Wrote City Scene with {len(scene['buildings'])} buildings: {args.out}",
            str(args.out),
        )

    if args.command == "render":
        graph = _load_json(args.graph, "UCG")
        scene = _load_json(args.scene, "City Scene")
        preview = render_preview(scene, graph, args.width, args.height)
        _write_bytes(args.out, preview)
        return CommandResult(f"Wrote SVG preview: {args.out}", str(args.out))

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
        diagnostic_codes = {item["code"] for item in manifest["diagnostics"]["codes"]}
        exit_code = (
            EXIT_RESOURCE_LIMIT
            if diagnostic_codes & RESOURCE_LIMIT_DIAGNOSTICS
            else EXIT_PARTIAL
            if manifest["status"] == "PARTIAL"
            else EXIT_SUCCESS
        )
        return CommandResult(
            (
                f"Built {len(manifest['artifacts'])} artifacts with "
                f"status {manifest['status']}: {args.out}"
            ),
            str(args.out),
            manifest["status"],
            exit_code,
            manifest["diagnostics"],
        )

    if args.command == "history":
        snapshots: list[HistorySnapshot] = []
        viewer_snapshots: list[dict[str, dict[str, Any]]] = []
        resolved_output = args.out.resolve(strict=False)
        for snapshot_path in args.snapshot:
            resolved_snapshot = snapshot_path.resolve(strict=False)
            if (
                resolved_output == resolved_snapshot
                or resolved_output in resolved_snapshot.parents
                or resolved_snapshot in resolved_output.parents
            ):
                raise CliError("history output must not overlap a snapshot directory")
            graph = _load_json(snapshot_path / "graph.ucg.json", "history UCG")
            scene = _load_json(snapshot_path / "city.json", "history City Scene")
            snapshots.append(HistorySnapshot(graph, scene))
            viewer_snapshots.append({"scene": scene, "ucg": graph})
        timeline = build_history(snapshots)
        artifacts = render_history_viewer(timeline, viewer_snapshots)
        _write_bytes(args.out / "history.json", canonical_json_bytes(timeline))
        for path, content in artifacts.items():
            _write_bytes(args.out / path, content)
        for index, snapshot in enumerate(snapshots):
            revision_root = args.out / "revisions" / f"{index:03d}"
            _write_bytes(
                revision_root / "graph.ucg.json", canonical_json_bytes(snapshot.ucg)
            )
            _write_bytes(
                revision_root / "city.json", canonical_json_bytes(snapshot.scene)
            )
        return CommandResult(
            f"Built history with {len(snapshots)} revisions: {args.out}",
            str(args.out),
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
    elif schema_version == "catalog/0.1":
        errors = validate_catalog_document(document, args.input.parent / "fixtures")
    elif schema_version == "history/0.1":
        errors = validate_history_document(document)
    else:
        raise CliError(f"unsupported schemaVersion: {schema_version!r}")
    if errors:
        raise CliError("contract validation failed: " + "; ".join(errors))
    return CommandResult(
        f"Valid {schema_version} document: {args.input}", str(args.input)
    )


def _json_line(document: dict[str, Any]) -> str:
    return canonical_json_bytes(document).decode("utf-8")


def _command_from_arguments(arguments: list[str]) -> str | None:
    commands = {"analyze", "build", "generate", "history", "render", "validate"}
    return next((item for item in arguments if item in commands), None)


def _print_failure(
    json_output: bool,
    command: str | None,
    category: str,
    message: str,
    exit_code: int,
) -> None:
    if json_output:
        print(
            _json_line(
                {
                    "command": command,
                    "error": {"category": category, "message": message},
                    "exitCode": exit_code,
                    "status": "FAILED",
                }
            )
        )
        return
    print(f"MetropoGits failed [{category}]: {message}", file=sys.stderr)


def main(argv: list[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    json_requested = "--json" in arguments
    try:
        args = _build_parser().parse_args(arguments)
    except CliUsageError as error:
        _print_failure(
            json_requested,
            _command_from_arguments(arguments),
            "INVALID_INPUT",
            str(error),
            EXIT_INVALID_INPUT,
        )
        return EXIT_INVALID_INPUT
    try:
        result = _run(args)
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
        _print_failure(
            args.json,
            args.command,
            "INVALID_INPUT",
            str(error),
            EXIT_INVALID_INPUT,
        )
        return EXIT_INVALID_INPUT
    except Exception as error:
        message = f"Unexpected internal error ({error.__class__.__name__})"
        _print_failure(
            args.json,
            args.command,
            "INTERNAL_ERROR",
            message,
            EXIT_INTERNAL_ERROR,
        )
        return EXIT_INTERNAL_ERROR
    if args.json:
        payload: dict[str, Any] = {
            "command": args.command,
            "exitCode": result.exit_code,
            "message": result.message,
            "output": result.output,
            "status": result.status,
        }
        if result.diagnostics is not None:
            payload["diagnostics"] = result.diagnostics
        print(_json_line(payload))
    else:
        print(result.message)
    return result.exit_code


if __name__ == "__main__":
    raise SystemExit(main())
