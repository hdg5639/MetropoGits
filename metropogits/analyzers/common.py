"""Bounded source reads and canonical evidence emission for bundled adapters."""

from __future__ import annotations

import copy
import hashlib
import os
import stat
from pathlib import Path, PurePosixPath

from metropogits.catalog import CatalogFact, resolve_catalog_claims
from scripts.canonical_json import canonical_json_bytes
from scripts.stable_ids import make_edge_id, make_entity_id

MAX_ITEMS = 250_000


class AnalysisError(ValueError):
    """Explicit bounded-analysis failure, never a reason to execute the target."""


def read_source(root, scanned, limit):
    root = Path(root).resolve(strict=True)
    path = root.joinpath(*PurePosixPath(scanned.path).parts)
    if root not in path.resolve(strict=True).parents:
        raise AnalysisError("source path escapes root")
    metadata = path.stat(follow_symlinks=False)
    if path.is_symlink() or not stat.S_ISREG(metadata.st_mode):
        raise AnalysisError("source is not a regular file")
    if metadata.st_size > limit:
        raise AnalysisError("source byte limit")
    descriptor = os.open(
        path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        opened = os.fstat(descriptor)
        if not stat.S_ISREG(opened.st_mode) or opened.st_size > limit:
            raise AnalysisError("opened source violates limits")
        if (opened.st_dev, opened.st_ino) != (metadata.st_dev, metadata.st_ino):
            raise AnalysisError("source changed during open")
        with os.fdopen(descriptor, "rb") as stream:
            descriptor = -1
            content = stream.read(limit + 1)
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    if len(content) > limit:
        raise AnalysisError("source byte limit")
    return content.decode("utf-8-sig")


class GraphWriter:
    def __init__(self, graph, extractor):
        self.document = copy.deepcopy(graph)
        self.extractor = extractor
        self.repo = graph["repository"]["id"]
        self.entities = {e["id"]: e for e in self.document["entities"]}
        self.files = {
            e["path"]: e for e in self.entities.values() if e["kind"] == "FILE"
        }
        self.edges = {e["id"]: e for e in self.document["edges"]}
        self.evidence = {e["evidenceId"]: e for e in self.document["evidence"]}
        self.inferred_proofs = set()

    def diagnostic(self, code, message, path=None, severity="INFO", **details):
        item = dict(code=code, severity=severity, message=message, **details)
        if path:
            item["sourcePath"] = path
        self.document["diagnostics"].append(item)

    def proof(self, path, line, kind, identity, end=None):
        identity = identity[:240]
        key = [self.extractor, path, line, end or line, kind, identity]
        digest = hashlib.sha256(canonical_json_bytes(key)).hexdigest()
        evidence_id = f"evidence:sha256:{digest}"
        self.evidence[evidence_id] = dict(
            evidenceId=evidence_id,
            sourcePath=path,
            startLine=line,
            endLine=end or line,
            extractor=self.extractor,
            kind=kind,
            ruleId=f"{self.extractor.split('/')[0]}.{kind.lower()}",
            summary=f"Explicit {kind.lower()} identity: {identity}",
        )
        self._bounded()
        return evidence_id

    def external(self, ecosystem, name):
        # Only identifiers/module paths, never dependency URLs or credential values.
        path = f"{ecosystem}/{name}"
        if not name or any(x in name for x in ("..", "\\", "://", "\x00")):
            raise AnalysisError("unsafe external module identity")
        entity_id = make_entity_id(self.repo, "EXTERNAL_PACKAGE", path)
        self.entities.setdefault(
            entity_id, dict(id=entity_id, kind="EXTERNAL_PACKAGE", path=path)
        )
        self._bounded()
        return entity_id

    def edge(self, source, target, kind, proof, identity, confidence="RESOLVED"):
        if source == target:
            return
        edge_id = make_edge_id(source, kind, target, identity)
        item = self.edges.setdefault(
            edge_id,
            dict(
                id=edge_id,
                type=kind,
                **{
                    "from": source,
                    "to": target,
                    "confidence": confidence,
                    "evidenceIds": [],
                },
            ),
        )
        item["evidenceIds"] = sorted(set(item["evidenceIds"]) | {proof})
        self._bounded()

    def symbol(self, path, name, line, end):
        entity_id = make_entity_id(self.repo, "SYMBOL", path, name)
        self.entities.setdefault(
            entity_id, dict(id=entity_id, kind="SYMBOL", path=path)
        )
        proof = self.proof(path, line, "AST", "declaration:" + name, end)
        self.edge(self.files[path]["id"], entity_id, "DECLARES", proof, name)

    def claims(self, path, facts):
        entity = self.files[path]
        for field, values in resolve_catalog_claims(facts).items():
            for claim in values:
                if self.inferred_proofs.intersection(claim["evidenceIds"]):
                    claim["confidence"] = "INFERRED"
                identities = [
                    f.value for f in facts if f.evidence_id in claim["evidenceIds"]
                ]
                import_proofs = {
                    f.evidence_id
                    for f in facts
                    if f.kind == "IMPORT"
                    and any(
                        identity == f.value or identity.startswith(f.value + ".")
                        for identity in identities
                    )
                }
                claim["evidenceIds"] = sorted(set(claim["evidenceIds"]) | import_proofs)
                existing = next(
                    (
                        c
                        for c in entity.setdefault(field, [])
                        if (c["value"], c["confidence"])
                        == (claim["value"], claim["confidence"])
                    ),
                    None,
                )
                if existing:
                    existing["evidenceIds"] = sorted(
                        set(existing["evidenceIds"]) | set(claim["evidenceIds"])
                    )
                else:
                    entity[field].append(claim)
            if field in entity:
                entity[field].sort(key=lambda c: (c["value"], c["confidence"]))

    def fact(self, path, line, kind, identity, inferred=False):
        proof = self.proof(path, line, kind, identity)
        if inferred:
            self.inferred_proofs.add(proof)
            self.evidence[proof]["summary"] = (
                f"Imported-namespace candidate identity: {identity[:240]}"
            )
        return CatalogFact(kind, identity, proof)

    def _bounded(self):
        if max(len(self.entities), len(self.edges), len(self.evidence)) > MAX_ITEMS:
            raise AnalysisError("adapter graph item limit exceeded")

    def finish(self):
        self.document["entities"] = sorted(
            self.entities.values(), key=lambda e: e["id"]
        )
        self.document["edges"] = sorted(self.edges.values(), key=lambda e: e["id"])
        self.document["evidence"] = sorted(
            self.evidence.values(), key=lambda e: e["evidenceId"]
        )
        self.document["diagnostics"].sort(
            key=lambda e: (e["code"], e.get("sourcePath", ""), e["message"])
        )
        return self.document
