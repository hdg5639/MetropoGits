"""Hardened GitHub Action entry point for the static build pipeline."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path

from metropogits.cli import build_repository
from metropogits.scanner import ScanLimits


class ActionInputError(ValueError):
    """Raised when a GitHub Action input escapes its allowed boundary."""


def _text(environment: Mapping[str, str], name: str, default: str = "") -> str:
    value = environment.get(name, default)
    if "\x00" in value or "\r" in value or "\n" in value:
        raise ActionInputError(f"{name} must be a single line without NUL")
    return value


def _integer(
    environment: Mapping[str, str], name: str, default: int, minimum: int = 1
) -> int:
    raw = _text(environment, name, str(default))
    try:
        value = int(raw)
    except ValueError as error:
        raise ActionInputError(f"{name} must be an integer") from error
    if value < minimum:
        raise ActionInputError(f"{name} must be at least {minimum}")
    return value


def _workspace_path(
    workspace: Path,
    raw_value: str,
    label: str,
    *,
    must_exist: bool,
) -> Path:
    supplied = Path(raw_value)
    if supplied.is_absolute():
        raise ActionInputError(f"{label} must be relative to GITHUB_WORKSPACE")
    try:
        resolved = (workspace / supplied).resolve(strict=must_exist)
    except OSError as error:
        raise ActionInputError(f"{label} is not accessible: {error}") from error
    if resolved != workspace and workspace not in resolved.parents:
        raise ActionInputError(f"{label} must remain inside GITHUB_WORKSPACE")
    return resolved


def _default_source_url(environment: Mapping[str, str]) -> str | None:
    supplied = _text(environment, "INPUT_SOURCE_URL")
    if supplied:
        return supplied
    server = _text(environment, "GITHUB_SERVER_URL")
    repository = _text(environment, "GITHUB_REPOSITORY")
    if server.startswith(("https://", "http://")) and repository:
        return f"{server.rstrip('/')}/{repository}"
    return None


def _write_outputs(path: Path, values: Mapping[str, str]) -> None:
    try:
        with path.open("a", encoding="utf-8", newline="\n") as stream:
            for name, value in values.items():
                if "\r" in value or "\n" in value:
                    raise ActionInputError(f"output {name} contains a newline")
                stream.write(f"{name}={value}\n")
    except OSError as error:
        raise ActionInputError(f"GITHUB_OUTPUT is not writable: {error}") from error


def run_action(environment: Mapping[str, str]) -> dict:
    workspace_raw = _text(environment, "GITHUB_WORKSPACE")
    if not workspace_raw:
        raise ActionInputError("GITHUB_WORKSPACE is required")
    workspace = Path(workspace_raw).resolve(strict=True)
    if not workspace.is_dir():
        raise ActionInputError("GITHUB_WORKSPACE must be a directory")

    repository = _workspace_path(
        workspace,
        _text(environment, "INPUT_REPOSITORY", "."),
        "repository",
        must_exist=True,
    )
    if not repository.is_dir():
        raise ActionInputError("repository must be a directory")
    output = _workspace_path(
        workspace,
        _text(environment, "INPUT_OUTPUT", "metropogits-dist"),
        "output",
        must_exist=False,
    )
    if output == workspace:
        raise ActionInputError("output must not be GITHUB_WORKSPACE")
    github_output_raw = _text(environment, "GITHUB_OUTPUT")
    if not github_output_raw:
        raise ActionInputError("GITHUB_OUTPUT is required")

    repository_id = _text(environment, "INPUT_REPO_ID") or _text(
        environment, "GITHUB_REPOSITORY"
    )
    if not repository_id:
        raise ActionInputError("repo-id or GITHUB_REPOSITORY is required")
    revision = _text(environment, "INPUT_REVISION") or _text(environment, "GITHUB_SHA")
    limits = ScanLimits(
        max_entries=_integer(environment, "INPUT_MAX_ENTRIES", ScanLimits.max_entries),
        max_files=_integer(environment, "INPUT_MAX_FILES", ScanLimits.max_files),
        max_file_bytes=_integer(
            environment, "INPUT_MAX_FILE_BYTES", ScanLimits.max_file_bytes
        ),
        max_total_bytes=_integer(
            environment, "INPUT_MAX_TOTAL_BYTES", ScanLimits.max_total_bytes
        ),
        max_depth=_integer(
            environment, "INPUT_MAX_DEPTH", ScanLimits.max_depth, minimum=0
        ),
    )
    manifest = build_repository(
        repository,
        output,
        repository_id=repository_id,
        theme=_text(environment, "INPUT_THEME", "minimal"),
        revision=revision or None,
        source_url=_default_source_url(environment),
        limits=limits,
    )

    _write_outputs(
        Path(github_output_raw),
        {
            "artifact-path": str(output),
            "manifest-path": str(output / "manifest.json"),
            "status": manifest["status"],
        },
    )
    return manifest


def main() -> int:
    try:
        manifest = run_action(os.environ)
    except (ActionInputError, OSError, ValueError) as error:
        print(f"MetropoGits Action failed: {error}", file=sys.stderr)
        return 2
    print(
        f"MetropoGits Action built {len(manifest['artifacts'])} artifacts "
        f"with status {manifest['status']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
