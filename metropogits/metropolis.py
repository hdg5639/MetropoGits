"""Compose distinct repository cities using explicit cross-repository evidence."""

from __future__ import annotations

import copy
import hashlib
from dataclasses import dataclass
from typing import Any, Iterable

from metropogits import __version__
from metropogits.catalog import CATALOG_VERSION
from scripts.canonical_json import canonical_json_bytes, sha256_digest
from scripts.stable_ids import make_edge_id
from scripts.validate_city import validate_document as validate_city_document
from scripts.validate_metropolis import validate_document as validate_metropolis_document
from scripts.validate_ucg import validate_document as validate_ucg_document


class MetropolisError(ValueError):
    """Raised when repository cities cannot be federated safely."""


@dataclass(frozen=True)
class MetropolisMember:
    ucg: dict[str, Any]
    scene: dict[str, Any]


@dataclass(frozen=True)
class MetropolisArtifacts:
    document: dict[str, Any]
    ucg: dict[str, Any]
    scene: dict[str, Any]


def _remap_evidence_ids(value: dict[str, Any], mapping: dict[str, str]) -> None:
    for field in ("technologies", "capabilities", "roles"):
        for claim in value.get(field, []):
            claim["evidenceIds"] = sorted(mapping[item] for item in claim["evidenceIds"])


def _network_kind(edge_type: str) -> str:
    return "HTTP_HIGHWAY" if edge_type == "HTTP_CALL" else "MESSAGING_PATH"


def build_metropolis(
    members: Iterable[MetropolisMember], link_manifest: dict[str, Any]
) -> MetropolisArtifacts:
    """Merge repository scenes and only explicitly evidenced inter-repo links."""

    ordered = list(members)
    if not 2 <= len(ordered) <= 64:
        raise MetropolisError("metropolis requires between 2 and 64 repositories")
    link_errors = validate_metropolis_document(link_manifest)
    if link_errors:
        raise MetropolisError("invalid link manifest: " + "; ".join(link_errors))
    if link_manifest.get("schemaVersion") != "metropolis-links/0.1":
        raise MetropolisError("a metropolis-links/0.1 manifest is required")

    validated: list[tuple[str, MetropolisMember]] = []
    for index, member in enumerate(ordered):
        ucg_errors = validate_ucg_document(member.ucg)
        if ucg_errors:
            raise MetropolisError(
                f"member {index} has invalid UCG: " + "; ".join(ucg_errors)
            )
        scene_errors = validate_city_document(member.scene, member.ucg)
        if scene_errors:
            raise MetropolisError(
                f"member {index} has invalid City Scene: " + "; ".join(scene_errors)
            )
        validated.append((member.ucg["repository"]["id"], member))
    validated.sort(key=lambda item: item[0])
    repository_ids = [item[0] for item in validated]
    if len(set(repository_ids)) != len(repository_ids):
        raise MetropolisError("repository IDs must be unique")

    members_by_id = {repository_id: member for repository_id, member in validated}
    entities_by_repository = {
        repository_id: {entity["id"]: entity for entity in member.ucg["entities"]}
        for repository_id, member in validated
    }
    evidence_by_repository = {
        repository_id: {
            evidence["evidenceId"] for evidence in member.ucg["evidence"]
        }
        for repository_id, member in validated
    }
    for link in link_manifest["links"]:
        source = link["from"]
        source_repository = source["repositoryId"]
        if source_repository not in members_by_id:
            raise MetropolisError(
                f"link {link['id']!r} references missing source repository"
            )
        source_entity = entities_by_repository[source_repository].get(
            source["entityId"]
        )
        if source_entity is None or source_entity["kind"] != "FILE":
            raise MetropolisError(
                f"link {link['id']!r} source must resolve to a FILE entity"
            )
        if link["status"] == "VERIFIED":
            target = link["to"]
            target_repository = target["repositoryId"]
            if target_repository not in members_by_id:
                raise MetropolisError(
                    f"link {link['id']!r} references missing target repository"
                )
            target_entity = entities_by_repository[target_repository].get(
                target["entityId"]
            )
            if target_entity is None or target_entity["kind"] != "FILE":
                raise MetropolisError(
                    f"link {link['id']!r} target must resolve to a FILE entity"
                )
        for evidence_ref in link["evidenceRefs"]:
            repository_id = evidence_ref["repositoryId"]
            if (
                repository_id not in evidence_by_repository
                or evidence_ref["evidenceId"]
                not in evidence_by_repository[repository_id]
            ):
                raise MetropolisError(
                    f"link {link['id']!r} references missing evidence"
                )

    all_entity_ids = [
        entity["id"]
        for _, member in validated
        for entity in member.ucg["entities"]
    ]
    if len(set(all_entity_ids)) != len(all_entity_ids):
        raise MetropolisError("member entity IDs collide across repositories")

    evidence_mappings: dict[str, dict[str, str]] = {}
    merged_entities: list[dict[str, Any]] = []
    merged_edges: list[dict[str, Any]] = []
    merged_evidence: list[dict[str, Any]] = []
    merged_diagnostics: list[dict[str, Any]] = []
    repository_records: list[dict[str, Any]] = []

    bounds: list[tuple[float, float, float, float]] = []
    for _, member in validated:
        xs = [district["x"] for district in member.scene["districts"]]
        zs = [district["z"] for district in member.scene["districts"]]
        max_xs = [
            district["x"] + district["width"]
            for district in member.scene["districts"]
        ]
        max_zs = [
            district["z"] + district["depth"]
            for district in member.scene["districts"]
        ]
        bounds.append((min(xs), min(zs), max(max_xs), max(max_zs)))
    cell_width = max(max_x - min_x for min_x, _, max_x, _ in bounds) + 120
    cell_depth = max(max_z - min_z for _, min_z, _, max_z in bounds) + 120

    merged_districts: list[dict[str, Any]] = []
    merged_buildings: list[dict[str, Any]] = []
    merged_networks: list[dict[str, Any]] = []
    building_positions: dict[str, tuple[float, float]] = {}

    for index, ((repository_id, member), bound) in enumerate(zip(validated, bounds)):
        mapping = {
            evidence["evidenceId"]: f"member:{index:03d}:{evidence['evidenceId']}"
            for evidence in member.ucg["evidence"]
        }
        evidence_mappings[repository_id] = mapping
        root_districts = [
            district
            for district in member.scene["districts"]
            if district["parentId"] is None
        ]
        if len(root_districts) != 1:
            raise MetropolisError(
                f"repository {repository_id!r} must have exactly one root district"
            )
        root_district_id = root_districts[0]["id"]
        for entity in member.ucg["entities"]:
            cloned = copy.deepcopy(entity)
            _remap_evidence_ids(cloned, mapping)
            merged_entities.append(cloned)
        for edge in member.ucg["edges"]:
            cloned = copy.deepcopy(edge)
            cloned["evidenceIds"] = sorted(
                mapping[evidence_id] for evidence_id in edge["evidenceIds"]
            )
            merged_edges.append(cloned)
        for evidence in member.ucg["evidence"]:
            cloned = copy.deepcopy(evidence)
            cloned["evidenceId"] = mapping[evidence["evidenceId"]]
            cloned["sourcePath"] = f"members/{index:03d}/{evidence['sourcePath']}"
            merged_evidence.append(cloned)
        for diagnostic in member.ucg["diagnostics"]:
            cloned = copy.deepcopy(diagnostic)
            if "sourcePath" in cloned:
                cloned["sourcePath"] = f"members/{index:03d}/{cloned['sourcePath']}"
            merged_diagnostics.append(cloned)

        min_x, min_z, _, _ = bound
        column = index % 4
        row = index // 4
        shift_x = column * cell_width - min_x
        shift_z = row * cell_depth - min_z
        for district in member.scene["districts"]:
            cloned = copy.deepcopy(district)
            cloned["x"] += shift_x
            cloned["z"] += shift_z
            if "footprint" in cloned:
                for rectangle in cloned["footprint"]:
                    rectangle["x"] += shift_x
                    rectangle["z"] += shift_z
            else:
                cloned["footprint"] = [
                    {
                        "depth": cloned["depth"],
                        "width": cloned["width"],
                        "x": cloned["x"],
                        "z": cloned["z"],
                    }
                ]
            merged_districts.append(cloned)
        for building in member.scene["buildings"]:
            cloned = copy.deepcopy(building)
            cloned["x"] += shift_x
            cloned["z"] += shift_z
            cloned["evidenceIds"] = sorted(
                mapping[evidence_id] for evidence_id in building["evidenceIds"]
            )
            merged_buildings.append(cloned)
            building_positions[cloned["entityId"]] = (
                cloned["x"] + cloned["width"] / 2,
                cloned["z"] + cloned["depth"] / 2,
            )
        for network in member.scene["networks"]:
            cloned = copy.deepcopy(network)
            cloned["path"] = [
                [point[0] + shift_x, point[1] + shift_z]
                for point in network["path"]
            ]
            merged_networks.append(cloned)
        repository_records.append(
            {
                "buildingCount": len(member.scene["buildings"]),
                "cityDigest": sha256_digest(member.scene),
                "id": repository_id,
                "revision": member.ucg["repository"]["revision"],
                "rootDistrictId": root_district_id,
                "sourceUrl": member.ucg["repository"]["sourceUrl"],
                "ucgDigest": sha256_digest(member.ucg),
            }
        )

    for link in link_manifest["links"]:
        if link["status"] == "UNRESOLVED":
            merged_diagnostics.append(
                {
                    "code": "FEDERATION_LINK_UNRESOLVED",
                    "message": f"Cross-repository link remains unresolved: {link['to']['label']}",
                    "severity": "INFO",
                }
            )
            continue
        source_id = link["from"]["entityId"]
        target_id = link["to"]["entityId"]
        edge_id = make_edge_id(source_id, link["type"], target_id, link["id"])
        evidence_ids = sorted(
            evidence_mappings[item["repositoryId"]][item["evidenceId"]]
            for item in link["evidenceRefs"]
        )
        merged_edges.append(
            {
                "confidence": "DIRECT",
                "evidenceIds": evidence_ids,
                "from": source_id,
                "id": edge_id,
                "to": target_id,
                "type": link["type"],
            }
        )
        start = building_positions[source_id]
        end = building_positions[target_id]
        network_digest = hashlib.sha256(
            canonical_json_bytes(["metropolis", link["id"], edge_id])
        ).hexdigest()
        merged_networks.append(
            {
                "edgeIds": [edge_id],
                "id": f"network:sha256:{network_digest}",
                "kind": _network_kind(link["type"]),
                "path": [list(start), [end[0], start[1]], list(end)],
            }
        )

    identity_digest = hashlib.sha256(canonical_json_bytes(repository_ids)).hexdigest()
    merged_ucg: dict[str, Any] = {
        "diagnostics": sorted(
            merged_diagnostics,
            key=lambda item: (
                item.get("code", ""),
                item.get("sourcePath", ""),
                item.get("message", ""),
            ),
        ),
        "edges": sorted(merged_edges, key=lambda item: item["id"]),
        "entities": sorted(merged_entities, key=lambda item: item["id"]),
        "evidence": sorted(merged_evidence, key=lambda item: item["evidenceId"]),
        "generator": {
            "catalogVersion": CATALOG_VERSION,
            "name": "metropogits",
            "version": __version__,
        },
        "repository": {
            "id": f"metropolis-{identity_digest[:16]}",
            "revision": f"sha256:{identity_digest}",
            "sourceUrl": None,
        },
        "schemaVersion": "ucg/0.1",
    }
    ucg_errors = validate_ucg_document(merged_ucg)
    if ucg_errors:
        raise MetropolisError("generated invalid merged UCG: " + "; ".join(ucg_errors))

    merged_scene: dict[str, Any] = {
        "buildings": sorted(merged_buildings, key=lambda item: item["entityId"]),
        "decorations": [],
        "districts": sorted(merged_districts, key=lambda item: item["id"]),
        "layoutAlgorithm": "metropolis-grid/0.2",
        "networks": sorted(merged_networks, key=lambda item: item["id"]),
        "schemaVersion": "city/0.2",
        "theme": "metropolis",
        "ucgDigest": sha256_digest(merged_ucg),
    }
    scene_errors = validate_city_document(merged_scene, merged_ucg)
    if scene_errors:
        raise MetropolisError(
            "generated invalid merged City Scene: " + "; ".join(scene_errors)
        )

    document = {
        "links": copy.deepcopy(link_manifest["links"]),
        "mergedCityDigest": sha256_digest(merged_scene),
        "mergedUcgDigest": sha256_digest(merged_ucg),
        "repositories": sorted(repository_records, key=lambda item: item["id"]),
        "schemaVersion": "metropolis/0.1",
    }
    document_errors = validate_metropolis_document(document)
    if document_errors:
        raise MetropolisError(
            "generated invalid metropolis: " + "; ".join(document_errors)
        )
    return MetropolisArtifacts(document, merged_ucg, merged_scene)
