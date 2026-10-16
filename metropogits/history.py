"""Build deterministic, evidence-preserving repository history timelines."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any, Iterable

from scripts.canonical_json import canonical_json_bytes, sha256_digest
from scripts.validate_city import validate_document as validate_city_document
from scripts.validate_history import validate_document as validate_history_document
from scripts.validate_ucg import validate_document as validate_ucg_document


class HistoryError(ValueError):
    """Raised when snapshots cannot form a valid history timeline."""


@dataclass(frozen=True)
class HistorySnapshot:
    ucg: dict[str, Any]
    scene: dict[str, Any]


def _lineage_id(repository_id: str, entity_id: str) -> str:
    digest = hashlib.sha256(
        canonical_json_bytes([repository_id, entity_id])
    ).hexdigest()
    return f"lineage:sha256:{digest}"


def _building_states(snapshot: HistorySnapshot) -> dict[str, dict[str, str]]:
    entities = {
        entity["id"]: entity
        for entity in snapshot.ucg["entities"]
        if entity["kind"] == "FILE" and "path" in entity
    }
    edges_by_entity: dict[str, list[dict[str, Any]]] = {
        entity_id: [] for entity_id in entities
    }
    for edge in snapshot.ucg["edges"]:
        if edge["type"] == "CONTAINS":
            continue
        for endpoint in ("from", "to"):
            if edge[endpoint] in edges_by_entity:
                edges_by_entity[edge[endpoint]].append(edge)
    buildings = {item["entityId"]: item for item in snapshot.scene["buildings"]}
    states: dict[str, dict[str, str]] = {}
    for entity_id, entity in entities.items():
        building = buildings.get(entity_id)
        if building is None:
            continue
        semantic_building = {
            key: building[key]
            for key in ("archetype", "height", "styleVariant")
        }
        related_edges = sorted(
            edges_by_entity[entity_id], key=lambda item: item["id"]
        )
        state = {
            "building": semantic_building,
            "edges": related_edges,
            "entity": entity,
        }
        states[entity_id] = {
            "path": entity["path"],
            "stateDigest": sha256_digest(state),
        }
    return states


def build_history(snapshots: Iterable[HistorySnapshot]) -> dict[str, Any]:
    """Create a canonical timeline from ordered, already-generated snapshots."""

    ordered = list(snapshots)
    if not 2 <= len(ordered) <= 256:
        raise HistoryError("history requires between 2 and 256 snapshots")

    repository_id: str | None = None
    revisions: list[str] = []
    states_by_revision: list[dict[str, dict[str, str]]] = []
    frames: list[dict[str, Any]] = []
    for index, snapshot in enumerate(ordered):
        ucg_errors = validate_ucg_document(snapshot.ucg)
        if ucg_errors:
            raise HistoryError(
                f"snapshot {index} has invalid UCG: " + "; ".join(ucg_errors)
            )
        current_repository = snapshot.ucg["repository"]["id"]
        if repository_id is None:
            repository_id = current_repository
        elif current_repository != repository_id:
            raise HistoryError("all snapshots must belong to the same repository")
        revision = snapshot.ucg["repository"]["revision"]
        if not revision:
            raise HistoryError(f"snapshot {index} must include a revision")
        if revision in revisions:
            raise HistoryError(f"duplicate history revision: {revision!r}")
        scene_errors = validate_city_document(snapshot.scene, snapshot.ucg)
        if scene_errors:
            raise HistoryError(
                f"snapshot {index} has invalid City Scene: "
                + "; ".join(scene_errors)
            )
        revisions.append(revision)
        states = _building_states(snapshot)
        states_by_revision.append(states)
        frames.append(
            {
                "buildingCount": len(states),
                "cityDigest": sha256_digest(snapshot.scene),
                "index": index,
                "revision": revision,
                "ucgDigest": sha256_digest(snapshot.ucg),
            }
        )

    transitions: list[dict[str, Any]] = []
    for index in range(1, len(ordered)):
        previous = states_by_revision[index - 1]
        current = states_by_revision[index]
        previous_ids = set(previous)
        current_ids = set(current)
        common = previous_ids & current_ids
        transitions.append(
            {
                "addedEntityIds": sorted(current_ids - previous_ids),
                "changedEntityIds": sorted(
                    entity_id
                    for entity_id in common
                    if previous[entity_id]["stateDigest"]
                    != current[entity_id]["stateDigest"]
                ),
                "fromRevision": revisions[index - 1],
                "removedEntityIds": sorted(previous_ids - current_ids),
                "toRevision": revisions[index],
                "unchangedEntityIds": sorted(
                    entity_id
                    for entity_id in common
                    if previous[entity_id]["stateDigest"]
                    == current[entity_id]["stateDigest"]
                ),
            }
        )

    all_entity_ids = sorted(
        {entity_id for states in states_by_revision for entity_id in states}
    )
    lineages: list[dict[str, Any]] = []
    assert repository_id is not None
    for entity_id in all_entity_ids:
        paths = {
            states[entity_id]["path"]
            for states in states_by_revision
            if entity_id in states
        }
        if len(paths) != 1:
            raise HistoryError(
                f"entity ID {entity_id!r} maps to multiple paths across snapshots"
            )
        appearances = [
            {
                "entityId": entity_id,
                "revision": revisions[index],
                "stateDigest": states[entity_id]["stateDigest"],
            }
            for index, states in enumerate(states_by_revision)
            if entity_id in states
        ]
        path = next(iter(paths))
        lineages.append(
            {
                "firstRevision": appearances[0]["revision"],
                "lastRevision": appearances[-1]["revision"],
                "lineageId": _lineage_id(repository_id, entity_id),
                "path": path,
                "revisions": appearances,
            }
        )
    lineages.sort(key=lambda item: item["lineageId"])

    timeline = {
        "frames": frames,
        "lineages": lineages,
        "repositoryId": repository_id,
        "schemaVersion": "history/0.1",
        "transitions": transitions,
    }
    errors = validate_history_document(timeline)
    if errors:
        raise HistoryError("generated invalid history: " + "; ".join(errors))
    return timeline
