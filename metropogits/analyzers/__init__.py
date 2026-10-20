"""Compose bundled, non-executing language analyzers behind the UCG contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from metropogits.analyzers.java import enrich_java_graph
from metropogits.analyzers.jsts import LANGUAGES as JSTS_LANGUAGES
from metropogits.analyzers.jsts import enrich_jsts_graph
from metropogits.analyzers.path_semantics import enrich_path_semantics
from metropogits.analyzers.python import enrich_python_graph
from metropogits.analyzers.polyglot import (
    LANGUAGES as POLYGLOT_LANGUAGES,
    enrich_polyglot_graph,
)
from metropogits.scanner import ScanLimits, ScanResult
from scripts.validate_ucg import validate_document as validate_ucg_document

SUPPORTED_LANGUAGES = (
    frozenset({"java", "python"}) | JSTS_LANGUAGES | POLYGLOT_LANGUAGES
)


def enrich_graph(
    root: Path,
    scan: ScanResult,
    graph: dict[str, Any],
    limits: ScanLimits,
) -> dict[str, Any]:
    """Run every bundled adapter and report honest aggregate coverage."""

    document = enrich_java_graph(root, scan, graph, limits)
    document = enrich_jsts_graph(root, scan, document, limits)
    document = enrich_python_graph(root, scan, document, limits)
    document = enrich_polyglot_graph(root, scan, document, limits)
    document = enrich_path_semantics(document)
    skipped_paths = {
        item["sourcePath"]
        for item in document["diagnostics"]
        if item["code"]
        in {
            "JAVA_ANALYSIS_SKIPPED",
            "JSTS_ANALYSIS_SKIPPED",
            "PYTHON_ANALYSIS_SKIPPED",
            "POLYGLOT_ANALYSIS_SKIPPED",
        }
        and "sourcePath" in item
    }
    java_count = sum(
        item.language == "java" and item.path not in skipped_paths
        for item in scan.files
    )
    jsts_count = sum(
        item.language in JSTS_LANGUAGES and item.path not in skipped_paths
        for item in scan.files
    )
    python_count = sum(
        item.language == "python" and item.path not in skipped_paths
        for item in scan.files
    )
    polyglot_count = sum(
        item.language in POLYGLOT_LANGUAGES and item.path not in skipped_paths
        for item in scan.files
    )
    structural_only = (
        len(scan.files) - java_count - jsts_count - python_count - polyglot_count
    )
    document["diagnostics"].append(
        {
            "code": "ANALYZER_COVERAGE",
            "message": (
                f"Adapters processed {java_count} Java and {jsts_count} "
                f"JavaScript/TypeScript file(s), plus {python_count} Python AST file(s); {structural_only} file(s) "
                "remain structural-only"
                f"; {polyglot_count} file(s) processed by lexical polyglot adapters"
            ),
            "severity": "INFO",
        }
    )
    document["diagnostics"].sort(
        key=lambda item: (
            item["code"],
            item.get("sourcePath", ""),
            item["message"],
        )
    )
    errors = validate_ucg_document(document)
    if errors:
        raise ValueError("analyzers generated invalid UCG: " + "; ".join(errors))
    return document


__all__ = ["enrich_graph"]
