"""Source-first urban planning inputs, independent of layout and individual heights.

Profiles are derived planning advice, not additional UCG roles or a claim that
master plans have already been built. Edges are indexed once; scopes visit only
their incident records. No all-pairs centrality or stochastic community solver.
"""

import math
from collections import Counter, defaultdict
from pathlib import PurePosixPath

from scripts.canonical_json import sha256_digest
from .geometry import q
from .source_programs import ROLE_PROGRAM

VERSION = "urban-character/0.1"
DEMAND_VERSION = "spatial-demand/0.1"
MAX_FILES = 10_000
MAX_EDGES = 200_000


def verified_claims(entity, field, evidence, *, usage=False):
    return [
        c for c in entity.get(field, [])
        if c.get("confidence") in ("DIRECT", "RESOLVED")
        and c.get("evidenceIds")
        and all(k in evidence for k in c["evidenceIds"])
        and (not usage or any(evidence[k]["kind"] not in ("PATH", "MANIFEST")
                              for k in c["evidenceIds"]))
    ]


class CharacterEngine:
    """Reusable before land allocation; directory/zone membership is explicit."""

    def __init__(self, graph):
        self.files = {e["id"]: e for e in graph["entities"] if e["kind"] == "FILE"}
        if len(self.files) > MAX_FILES or len(graph["edges"]) > MAX_EDGES:
            raise ValueError("urban character input limit")
        self.evidence = {e["evidenceId"]: e for e in graph["evidence"]}
        entities = {e["id"]: e for e in graph["entities"]}
        paths = {e["path"]: k for k, e in self.files.items()}
        owners = {k: paths.get(e.get("path")) for k, e in entities.items()
                  if e["kind"] in ("FILE", "SYMBOL")}
        self.records, self.incident = {}, defaultdict(set)
        for edge in graph["edges"]:
            if (edge["type"] in ("CONTAINS", "DECLARES")
                    or edge.get("confidence") not in ("DIRECT", "RESOLVED")
                    or not edge.get("evidenceIds")
                    or not all(k in self.evidence for k in edge["evidenceIds"])):
                continue
            a, b = owners.get(edge["from"]), owners.get(edge["to"])
            external = entities[edge["to"]]["kind"] in ("EXTERNAL_PACKAGE", "EXTERNAL_SYSTEM")
            if a == b and a or not a and not b:
                continue
            record = dict(a=a, b=b, external=edge["to"] if a and external else None,
                          declared=edge["type"] == "DEPENDS_ON", edge=edge)
            self.records[edge["id"]] = record
            for owner in (a, b):
                if owner:
                    self.incident[owner].add(edge["id"])

    def profile(self, identity, members, *, kind="repository"):
        members = sorted(members)
        if len(set(members)) != len(members) or not set(members) <= self.files.keys():
            raise ValueError("urban character source membership")
        own, count = set(members), len(members)
        local, boundary, used, declared = set(), set(), set(), set()
        edge_ids, relation_proof = set(), set()
        for key in sorted({k for f in members for k in self.incident[f]}):
            r = self.records[key]
            a, b = r["a"], r["b"]
            if a and b and not r["declared"]:
                (local if a in own and b in own else boundary).add((a, b))
            elif a in own and r["external"]:
                (declared if r["declared"] else used).add((a, r["external"]))
            else:
                continue
            edge_ids.add(key)
            relation_proof.update(r["edge"]["evidenceIds"])
        incoming, outgoing = Counter(b for a, b in local), Counter(a for a, b in local)
        degree_histogram = Counter((incoming[k], outgoing[k]) for k in members)
        roles, languages, tech, caps, proof = Counter(), Counter(), Counter(), Counter(), set()
        classified = 0
        programs = Counter()
        modules = Counter()
        for k in members:
            entity = self.files[k]
            languages[entity.get("language") or "unknown"] += 1
            modules[str(PurePosixPath(entity["path"]).parent)] += 1
            claims = verified_claims(entity, "roles", self.evidence)
            classified += bool(claims)
            roles.update({c["value"] for c in claims})
            programs.update({ROLE_PROGRAM[c["value"]] for c in claims if c["value"] in ROLE_PROGRAM})
            for field, counter in (("technologies", tech), ("capabilities", caps)):
                verified = verified_claims(entity, field, self.evidence, usage=True)
                counter.update({c["value"] for c in verified})
                claims += verified
            proof.update(e for c in claims for e in c["evidenceIds"])
        # Deterministic weak components describe observed connectivity only;
        # isolated/unsupported files remain isolated, never invented relations.
        parent = {k: k for k in members}

        def find(k):
            while parent[k] != k:
                parent[k] = parent[parent[k]]
                k = parent[k]
            return k

        for a, b in sorted(local):
            a, b = find(a), find(b)
            if a != b:
                parent[max(a, b)] = min(a, b)
        components = sorted(Counter(find(k) for k in members).values(), reverse=True)
        within_module = sum(PurePosixPath(self.files[a]["path"]).parent ==
                            PurePosixPath(self.files[b]["path"]).parent for a, b in local)
        connectivity = min(1, len(local) / max(1, count * math.log2(count + 1)))
        service = programs["APPLICATION"] / max(1, count)
        testing = programs["VALIDATION"] / max(1, count)
        compute = programs["COMPUTE"] / max(1, count)
        interface = programs["INTERFACE"] / max(1, count)
        data = programs["DATA"] / max(1, count)
        cohesion = len(local) / max(1, len(local) + len(boundary))
        centralization = (count * max(incoming.values(), default=0) - len(local)) / max(1, (count - 1) ** 2)
        # Every score below is aesthetic planning inference, not code quality,
        # observed traffic, actual floor area or a per-file height multiplier.
        density = 0.2 + 0.45 * connectivity + 0.2 * service + 0.15 * cohesion
        vertical = density * (0.4 + 0.6 * max(service, 0.7 * interface))
        campus = min(1, testing + compute + 0.25 * service)
        role_total = sum(roles.values()) + count - classified
        diversity = -sum((n / role_total) * math.log2(n / role_total)
                         for n in [*roles.values(), count - classified] if n) if role_total else 0
        effective_modules = count ** 2 / max(1, sum(n * n for n in modules.values()))
        preferred, rationale = "CONVENTIONAL_MIXED_USE", ["NEUTRAL_STRUCTURAL_FALLBACK"]
        if service >= 0.25 and testing + compute >= 0.15:
            preferred, rationale = "TECHNOLOGY_BUSINESS", ["VERIFIED_APPLICATION_AND_SUPPORT_ROLES"]
        elif service >= 0.3 and density >= 0.5:
            preferred, rationale = "METROPOLITAN_CORE", ["DENSE_VERIFIED_APPLICATION_FABRIC"]
        elif service >= 0.2 and density >= 0.4:
            preferred, rationale = "DENSE_BUSINESS", ["CONNECTED_VERIFIED_APPLICATION_FABRIC"]
        elif interface >= 0.4:
            preferred, rationale = "COMMERCIAL_CULTURAL", ["VERIFIED_INTERFACE_FACING_SOURCE_ROLES"]
        elif effective_modules >= 3 and centralization < 0.35 and within_module / max(1, len(local)) >= 0.55 and local:
            preferred, rationale = "POLYCENTRIC", ["DISTRIBUTED_COHESIVE_SOURCE_MODULES"]
        # Relative program-equivalent units; a later land allocator must convert
        # them to world units and admit/replan them against terrain/capacity.
        equivalent = count + 1.5 * programs["VALIDATION"] + programs["COMPUTE"] + data * count * 0.8
        return dict(
            version=VERSION, id=identity, scope=kind, memberEntityIds=members,
            facts=dict(
                sourceCount=count, classifiedSourceCount=classified,
                languages=dict(sorted(languages.items())), roleCounts=dict(sorted(roles.items())),
                usedTechnologies=dict(sorted(tech.items())), usedCapabilities=dict(sorted(caps.items())),
                localDirectedPairs=len(local), boundaryDirectedPairs=len(boundary),
                externalUsagePairs=len(used), declaredExternalPairs=len(declared),
                internalDependencyDensity=q(len(local) / max(1, count * (count - 1))),
                incomingCentralization=q(centralization),
                degreeHistogram=[dict(incoming=a, outgoing=b, files=n) for (a, b), n in sorted(degree_histogram.items())],
                weakComponentSizes=components, sourceModuleCount=len(modules),
                moduleSizes=dict(sorted(modules.items())), withinModulePairs=within_module,
                relationEdgeIds=sorted(edge_ids), relationEvidenceIds=sorted(relation_proof),
                semanticEvidenceIds=sorted(proof)),
            planning=dict(
                derived=True, interpretation="AESTHETIC_PLANNING_NOT_RUNTIME_OR_CODE_QUALITY",
                centralization=q(centralization), connectivity=q(connectivity), cohesion=q(cohesion),
                functionalDiversityBits=q(diversity), densityDemand=q(density),
                verticalPotential=q(vertical), campusPotential=q(campus),
                industrialPotential=q(data), interfacePotential=q(interface), preferredTypology=preferred, rationale=rationale,
                effectiveModuleCount=q(effective_modules),
                centerCountHint=max(1, min(4, round(effective_modules))) if preferred == "POLYCENTRIC" else int(count > 0)),
            spatialDemand=dict(
                version=DEMAND_VERSION, status="RELATIVE_UNALLOCATED",
                programEquivalentUnits=q(equivalent),
                perSourceUnits=q(equivalent / max(1, count)),
                publicSpaceFraction=q(0.14 + 0.18 * campus),
                growthReserveFraction=0.15, terrainPolicy="NATURE_FIRST",
                basis="SOURCE_PROGRAM_NOT_FIXED_PARCEL_OR_COMMITTED_FLOOR_AREA"))


def character_document(world, graph):
    engine = CharacterEngine(graph)
    profiles = [engine.profile(graph["repository"]["id"], engine.files)]
    districts = defaultdict(list)
    zones = defaultdict(list)
    for p in world["parcels"]:
        districts[p["districtId"]].append(p["entityId"])
        if p.get("zoneId"):
            zones[p["zoneId"]].append(p["entityId"])
    for kind, scopes in (("district", districts), ("zone", zones)):
        profiles.extend(engine.profile(k, v, kind=kind) for k, v in sorted(scopes.items()))
    return dict(schemaVersion=VERSION, ucgDigest=sha256_digest(graph),
                profiles=profiles, limits=dict(files=MAX_FILES, edges=MAX_EDGES),
                limitations=["Weak connectivity is not semantic community detection.",
                             "Typology preferences and relative demand are not constructed master plans.",
                             "No import count assigns a building height or corporate identity."])
