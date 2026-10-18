"""Source cores, explicit supporting edges and bounded neighborhood ownership."""

import copy
from collections import defaultdict

from .affinity import dependency_pairs
from .zoning import candidates

VERSION = "neighborhoods/0.1"


def neighborhood_candidates(members, entities, district_id, graph):
    clusters = copy.deepcopy(candidates(members, entities, district_id))
    owners = {b["entityId"]: district_id for b in members}
    pairs = dependency_pairs(graph, owners)
    files = {e["path"]: e["id"] for e in entities.values() if e["kind"] == "FILE"}
    edge_ids = defaultdict(set)
    for edge in graph["edges"]:
        if edge["type"] in ("CONTAINS", "DECLARES") or edge["confidence"] not in (
            "DIRECT",
            "RESOLVED",
        ):
            continue
        a, b = (files.get(entities[edge[k]].get("path")) for k in ("from", "to"))
        if a in owners and b in owners and a != b:
            edge_ids[tuple(sorted((a, b)))].add(edge["id"])
    cores = {
        identity: z["id"]
        for z in clusters
        if z["clusterKey"] != "GENERAL_MIXED"
        for identity in z["memberEntityIds"]
    }
    scores, evidence = (
        defaultdict(lambda: defaultdict(float)),
        defaultdict(lambda: defaultdict(set)),
    )
    mixed = next((z for z in clusters if z["clusterKey"] == "GENERAL_MIXED"), None)
    eligible = set(mixed["memberEntityIds"]) if mixed else set()
    # Ambiguous/tiny verified roles stay explicitly mixed, not somebody else's
    # generic support. Only actual unclassified files can be recruited.
    eligible = {key for key in eligible if not entities[key].get("roles")}
    for (a, b), weight in pairs.items():
        for supporter, core in ((a, b), (b, a)):
            if supporter in eligible and core in cores:
                zone = cores[core]
                scores[supporter][zone] += weight
                evidence[supporter][zone].update(edge_ids[(a, b)])
    proposals = []
    for key, values in scores.items():
        ordered = sorted(values, key=lambda zone: (-values[zone], zone))
        best = ordered[0]
        runner_up = values[ordered[1]] if len(ordered) > 1 else 0
        if values[best] >= 2 and values[best] > runner_up * 1.5:
            proposals.append((-values[best], key, best))
    by_id = {z["id"]: z for z in clusters}
    for z in clusters:
        z["coreEntityIds"] = (
            list(z["memberEntityIds"]) if z["clusterKey"] != "GENERAL_MIXED" else []
        )
        z["coreClaims"] = copy.deepcopy(z["memberClaims"])
        z["supportingMembers"] = []
    moved = set()
    for negative_score, key, zone in sorted(proposals):
        z = by_id[zone]
        if len(z["supportingMembers"]) >= len(z["coreEntityIds"]) // 2:
            continue
        z["memberEntityIds"].append(key)
        z["supportingMembers"].append(
            dict(
                entityId=key,
                coreEdgeIds=sorted(evidence[key][zone]),
                affinity=-negative_score,
            )
        )
        moved.add(key)
    for z in clusters:
        if z["clusterKey"] == "GENERAL_MIXED":
            z["memberEntityIds"] = sorted(set(z["memberEntityIds"]) - moved)
        else:
            z["memberEntityIds"].sort()
        z["memberClaims"] = [
            dict(entityId=key, roles=copy.deepcopy(entities[key].get("roles", [])))
            for key in z["memberEntityIds"]
            if entities[key].get("roles")
        ]
        z["supportingMembers"].sort(key=lambda item: item["entityId"])
    return [z for z in clusters if z["memberEntityIds"]]
