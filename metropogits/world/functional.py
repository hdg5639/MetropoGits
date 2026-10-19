"""Bounded source-anchored dependency neighborhoods, never role-exclusive bins."""

import heapq
import math
import posixpath
from collections import Counter, defaultdict

from .affinity import dependency_pairs
from .seed import derive

VERSION = "functional-neighborhoods/0.1"
TARGET_FILES = 112
MAX_ZONES = 7
MAX_GROWTH_WORK = 500_000


def functional_candidates(members, entities, district_id, graph):
    identities = sorted(b["entityId"] for b in members)
    owners = dict.fromkeys(identities, district_id)
    pairs = dependency_pairs(graph, owners)
    links = defaultdict(dict)
    for (a, b), weight in pairs.items():
        links[a][b] = links[b][a] = weight
    files = {e["path"]: e["id"] for e in entities.values() if e["kind"] == "FILE"}
    edge_index = defaultdict(list)
    for edge in graph["edges"]:
        if edge["type"] in ("CONTAINS", "DECLARES") or edge["confidence"] not in (
            "DIRECT",
            "RESOLVED",
        ):
            continue
        a, b = (files.get(entities[edge[k]].get("path")) for k in ("from", "to"))
        if a in owners and b in owners and a != b:
            edge_index[tuple(sorted((a, b)))].append(edge)
    pending, batches, work = set(identities), [], 0
    target = max(TARGET_FILES, math.ceil(len(identities) / MAX_ZONES))
    while pending:
        selected, scores, queue, components = [], defaultdict(float), [], 0
        while pending and len(selected) < target:
            if not queue:
                heapq.heappush(queue, (0, min(pending)))
                components += 1
            negative, key = heapq.heappop(queue)
            work += 1
            if work > MAX_GROWTH_WORK:
                raise ValueError("functional neighborhood growth work limit")
            if key not in pending or -negative < scores[key]:
                continue
            pending.remove(key)
            selected.append(key)
            for neighbor, weight in sorted(links[key].items()):
                if neighbor in pending:
                    scores[neighbor] += weight
                    heapq.heappush(queue, (-scores[neighbor], neighbor))
        batches.append((sorted(selected), components))
    # Avoid a tiny last administrative wedge. This packs existing source files;
    # it does not assert a relationship between disconnected components.
    if len(batches) > 1 and len(batches[-1][0]) < 24:
        tail, components = batches.pop()
        choices = []
        for i, (group, _) in enumerate(batches):
            group_set = set(group)
            affinity = sum(
                w
                for key in tail
                for other, w in links[key].items()
                if other in group_set
            )
            choices.append((-affinity, len(group), group[0], i))
        i = min(choices)[-1]
        group, count = batches[i]
        batches[i] = (sorted(group + tail), count + components)
    records = []
    for keys, components in batches:
        selected = set(keys)
        claims = [
            dict(entityId=k, roles=entities[k]["roles"])
            for k in keys
            if entities[k].get("roles")
        ]
        cores = [
            dict(
                entityId=k,
                roles=[
                    r
                    for r in entities[k].get("roles", [])
                    if r["confidence"] in ("DIRECT", "RESOLVED") and r["evidenceIds"]
                ],
            )
            for k in keys
        ]
        cores = [c for c in cores if c["roles"]]
        core_ids = {c["entityId"] for c in cores}
        role_counts = Counter(r["value"] for c in cores for r in c["roles"])
        internal = [
            e
            for (a, b), edges in edge_index.items()
            if a in selected and b in selected
            for e in edges
        ]
        supporters = []
        for key in keys:
            if key in core_ids:
                continue
            connected = [other for other in links[key] if other in core_ids]
            score = sum(links[key][other] for other in connected)
            if score >= 2:
                supporters.append(
                    dict(
                        entityId=key,
                        affinity=score,
                        coreEdgeIds=sorted(
                            {
                                e["id"]
                                for other in connected
                                for e in edge_index[tuple(sorted((key, other)))]
                            }
                        ),
                    )
                )
        dominant = role_counts.most_common()
        names = {
            "SERVICE": "service",
            "PERSISTENCE_ADAPTER": "persistence",
            "ENTRYPOINT": "entrypoint",
            "UI_PAGE": "frontend",
            "TEST": "test",
            "CONFIGURATION": "configuration",
            "GENERAL_COMPONENT": "component",
        }
        basis = posixpath.commonpath(
            [posixpath.dirname(entities[k].get("path", "")) for k in keys]
        )
        label = posixpath.basename(basis) or "Root"
        label += " · " + (
            " + ".join(names.get(role, role.lower()) for role, _ in dominant[:2])
            if dominant
            else "unclassified"
        )
        total = sum(role_counts.values()) or 1
        profile = "GRID"
        if role_counts["PERSISTENCE_ADAPTER"] >= max(8, total * 0.45):
            profile = "INDUSTRIAL"
        elif role_counts["TEST"] >= max(8, total * 0.45):
            profile = "ORGANIC"
        elif role_counts["ENTRYPOINT"] >= max(12, total * 0.55):
            profile = "RADIAL"
        elif len(role_counts) > 1:
            profile = "HYBRID"
        records.append(
            dict(
                id="world:zone:" + derive(district_id, keys[0], VERSION),
                parentId=district_id,
                clusterKey="FUNCTIONAL:" + keys[0],
                label=label,
                classification=dict(
                    status="INFERRED" if cores else "UNKNOWN",
                    ruleIds=["planning:dependency-region-growth/1"] if cores else [],
                    evidenceIds=sorted(
                        {v for c in cores for r in c["roles"] for v in r["evidenceIds"]}
                    ),
                ),
                memberEntityIds=keys,
                memberClaims=claims,
                coreEntityIds=sorted(core_ids),
                coreClaims=cores,
                supportingMembers=supporters,
                internalEdgeIds=sorted(e["id"] for e in internal),
                structuralMemberEntityIds=sorted(
                    selected - core_ids - {s["entityId"] for s in supporters}
                ),
                roleCounts=dict(sorted(role_counts.items())),
                growthRestarts=components,
                requestedProfile=profile,
            )
        )
    return sorted(records, key=lambda z: z["id"])
