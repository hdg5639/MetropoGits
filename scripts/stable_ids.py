#!/usr/bin/env python3
"""Generate MetropoGits stable repository, entity, and edge identifiers."""

from __future__ import annotations

import argparse
import hashlib
import os
import re
import sys
import unicodedata
from pathlib import Path
from urllib.parse import quote

if __package__:
    from .canonical_json import canonical_json_bytes
else:
    from canonical_json import canonical_json_bytes


ENTITY_KINDS = {
    "REPOSITORY": "repository",
    "MODULE": "module",
    "DIRECTORY": "directory",
    "FILE": "file",
    "SYMBOL": "symbol",
    "EXTERNAL_PACKAGE": "external-package",
    "EXTERNAL_SYSTEM": "external-system",
}
EDGE_KINDS = {
    "CONTAINS",
    "IMPORTS",
    "DECLARES",
    "EXTENDS",
    "IMPLEMENTS",
    "REFERENCES",
    "CALLS",
    "DEPENDS_ON",
    "HTTP_CALL",
    "PUBLISHES",
    "SUBSCRIBES",
    "READS",
    "WRITES",
}
REPOSITORY_SEGMENT = re.compile(r"^[A-Za-z0-9._~-]+$")


class StableIdError(ValueError):
    """Raised when identifier input violates the v0.1 identity policy."""


def _require_unicode_scalars(value: str, label: str) -> None:
    try:
        value.encode("utf-8")
    except UnicodeEncodeError as error:
        raise StableIdError(f"{label} contains an unpaired Unicode surrogate") from error


def _normalized_segments(value: str, label: str) -> list[str]:
    if not isinstance(value, str) or not value:
        raise StableIdError(f"{label} must be a non-empty string")
    if "\x00" in value:
        raise StableIdError(f"{label} must not contain NUL")
    _require_unicode_scalars(value, label)

    slash_path = unicodedata.normalize("NFC", value).replace("\\", "/")
    if slash_path.startswith("/") or re.match(r"^[A-Za-z]:", slash_path):
        raise StableIdError(f"{label} must be relative")

    segments: list[str] = []
    for segment in slash_path.split("/"):
        if segment in {"", "."}:
            continue
        if segment == "..":
            raise StableIdError(f"{label} must not contain traversal")
        segments.append(segment)
    if not segments:
        raise StableIdError(f"{label} must contain at least one segment")
    return segments


def normalize_repository_id(namespace: str) -> str:
    segments = _normalized_segments(namespace, "repository namespace")
    for segment in segments:
        if not REPOSITORY_SEGMENT.fullmatch(segment):
            raise StableIdError(
                "repository namespace segments may contain only ASCII letters, "
                "digits, '.', '_', '~', and '-'"
            )
    return "/".join(segments)


def repository_id_from_root(root: str | Path) -> str:
    resolved = Path(root).resolve(strict=False)
    host_normalized = unicodedata.normalize(
        "NFC", os.path.normcase(str(resolved)).replace("\\", "/")
    )
    digest = hashlib.sha256(host_normalized.encode("utf-8")).hexdigest()[:16]
    return f"local-sha256-{digest}"


def normalize_relative_path(path: str) -> str:
    return "/".join(_normalized_segments(path, "relative path"))


def _encode_path(path: str) -> str:
    normalized = normalize_relative_path(path)
    return "/".join(quote(segment, safe="-._~") for segment in normalized.split("/"))


def make_entity_id(
    repository_id: str,
    kind: str,
    relative_path: str,
    qualified_symbol: str | None = None,
) -> str:
    canonical_repository_id = normalize_repository_id(repository_id)
    if not isinstance(kind, str) or kind not in ENTITY_KINDS:
        raise StableIdError(f"unsupported entity kind: {kind}")
    if kind == "SYMBOL" and (
        not isinstance(qualified_symbol, str) or not qualified_symbol
    ):
        raise StableIdError("SYMBOL entity requires a qualified symbol")
    if kind != "SYMBOL" and qualified_symbol is not None:
        raise StableIdError("qualified symbol is valid only for SYMBOL entities")

    entity_id = (
        f"{canonical_repository_id}:{ENTITY_KINDS[kind]}:{_encode_path(relative_path)}"
    )
    if qualified_symbol is not None:
        normalized_symbol = unicodedata.normalize("NFC", qualified_symbol)
        if not normalized_symbol or "\x00" in normalized_symbol:
            raise StableIdError("qualified symbol must be non-empty and contain no NUL")
        _require_unicode_scalars(normalized_symbol, "qualified symbol")
        entity_id += "#" + quote(normalized_symbol, safe="-._~")
    return entity_id


def make_edge_id(
    source_id: str,
    edge_type: str,
    target_id: str,
    discriminator: str = "",
) -> str:
    if not isinstance(source_id, str) or not isinstance(target_id, str):
        raise StableIdError("edge endpoints must be strings")
    if not source_id or not target_id:
        raise StableIdError("edge endpoints must be non-empty")
    if not isinstance(edge_type, str) or edge_type not in EDGE_KINDS:
        raise StableIdError(f"unsupported edge kind: {edge_type}")
    if not isinstance(discriminator, str):
        raise StableIdError("edge discriminator must be a string")
    _require_unicode_scalars(source_id, "edge source")
    _require_unicode_scalars(target_id, "edge target")
    _require_unicode_scalars(discriminator, "edge discriminator")

    payload = [source_id, edge_type, target_id, discriminator]
    digest = hashlib.sha256(canonical_json_bytes(payload)).hexdigest()
    return f"edge:sha256:{digest}"


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)

    repository = commands.add_parser("repository", help="generate a repository ID")
    repository_source = repository.add_mutually_exclusive_group(required=True)
    repository_source.add_argument("--namespace")
    repository_source.add_argument("--root", type=Path)

    entity = commands.add_parser("entity", help="generate an entity ID")
    entity.add_argument("--repo-id", required=True)
    entity.add_argument("--kind", required=True, choices=sorted(ENTITY_KINDS))
    entity.add_argument("--path", required=True)
    entity.add_argument("--symbol")

    edge = commands.add_parser("edge", help="generate an edge ID")
    edge.add_argument("--from-id", required=True)
    edge.add_argument("--type", required=True, choices=sorted(EDGE_KINDS))
    edge.add_argument("--to-id", required=True)
    edge.add_argument("--discriminator", default="")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    try:
        if args.command == "repository":
            result = (
                normalize_repository_id(args.namespace)
                if args.namespace is not None
                else repository_id_from_root(args.root)
            )
        elif args.command == "entity":
            result = make_entity_id(args.repo_id, args.kind, args.path, args.symbol)
        else:
            result = make_edge_id(
                args.from_id, args.type, args.to_id, args.discriminator
            )
    except StableIdError as error:
        print(f"Unable to generate stable ID: {error}", file=sys.stderr)
        return 2

    print(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
