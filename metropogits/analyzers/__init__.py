"""Compose bundled, non-executing language analyzers behind the UCG contract."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from metropogits.analyzers.java import enrich_java_graph
from metropogits.analyzers.jsts import LANGUAGES as JSTS_LANGUAGES
from metropogits.analyzers.jsts import enrich_jsts_graph
from metropogits.scanner import ScanLimits, ScanResult
from scripts.validate_ucg import validate_document as validate_ucg_document


def enrich_graph(
    root: Path,
    scan: ScanResult,
    graph: dict[str, Any],
    limits: ScanLimits,
) -> dict[str, Any]:
    """Run every bundled adapter and report honest aggregate coverage."""

    document = enrich_java_graph(root, scan, graph, limits)
    document = enrich_jsts_graph(root, scan, document, limits)
    skipped_paths = {
        item["sourcePath"]
        for item in document["diagnostics"]
        if item["code"] in {"JAVA_ANALYSIS_SKIPPED", "JSTS_ANALYSIS_SKIPPED"}
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
    structural_only = len(scan.files) - java_count - jsts_count
    document["diagnostics"].append(
        {
            "code": "ANALYZER_COVERAGE",
            "message": (
                f"Adapters processed {java_count} Java and {jsts_count} "
                f"JavaScript/TypeScript file(s); {structural_only} file(s) "
                "remain structural-only"
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
