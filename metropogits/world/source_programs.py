"""Architectural programs derived from source roles, never new source claims."""

from collections import Counter, defaultdict

ROLE_PROGRAM = {
    "TEST": "VALIDATION",
    "UI_COMPONENT": "INTERFACE",
    "UI_PAGE": "INTERFACE",
    "API_ENDPOINT": "APPLICATION",
    "ENTRYPOINT": "APPLICATION",
    "SERVICE": "APPLICATION",
    "AUTH_CONFIGURATION": "APPLICATION",
    "TASK_WORKER": "APPLICATION",
    "PERSISTENCE_ADAPTER": "DATA",
    "DOCUMENT_PERSISTENCE_ADAPTER": "DATA",
    "DATA_MODEL": "DATA",
    "CACHE_ADAPTER": "DATA",
    "STATE_STORE": "DATA",
    "SEARCH_ADAPTER": "DATA",
    "OBJECT_STORAGE_ADAPTER": "DATA",
    "ML_COMPONENT": "COMPUTE",
    "DATA_PROCESSOR": "COMPUTE",
    "CLI_ENTRYPOINT": "TOOLING",
}
LABELS = dict(
    VALIDATION="Verification commons",
    INTERFACE="Interface precinct",
    APPLICATION="Application works",
    DATA="Data services precinct",
    COMPUTE="Compute commons",
    TOOLING="Tooling works",
    COLLABORATION="Source collaboration precinct",
)


def member_programs(zone):
    members = set(zone["memberEntityIds"])
    result = {}
    for member in zone.get("memberClaims", []):
        if member["entityId"] not in members:
            continue
        valid = [
            r
            for r in member["roles"]
            if r["value"] in ROLE_PROGRAM
            and r["confidence"] in ("DIRECT", "RESOLVED")
            and r["evidenceIds"]
        ]
        result[member["entityId"]] = dict(
            kinds=sorted({ROLE_PROGRAM[r["value"]] for r in valid}),
            roles=sorted({r["value"] for r in valid}),
            evidenceIds=sorted({e for r in valid for e in r["evidenceIds"]}),
        )
    return result


def program_summary(zone):
    members = member_programs(zone)
    counts = Counter(k for m in members.values() for k in m["kinds"])
    kind = min(counts, key=lambda k: (-counts[k], k)) if counts else "COLLABORATION"
    return dict(
        version="source-program/0.1",
        kind=kind,
        label=LABELS[kind],
        derived=True,
        memberCount=len(zone["memberEntityIds"]),
        classifiedMemberCount=sum(bool(m["kinds"]) for m in members.values()),
        roleCounts=dict(
            sorted(Counter(r for m in members.values() for r in m["roles"]).items())
        ),
        evidenceIds=sorted({e for m in members.values() for e in m["evidenceIds"]}),
    )


def file_topology(graph):
    """Unique observed local file neighbours, not a simulated runtime call graph."""
    files = {e["path"]: e["id"] for e in graph["entities"] if e["kind"] == "FILE"}
    owners = {
        e["id"]: files.get(e.get("path"))
        for e in graph["entities"]
        if e["kind"] in ("FILE", "SYMBOL")
    }
    incoming, outgoing, proofs = defaultdict(set), defaultdict(set), defaultdict(set)
    declarations = Counter()
    for edge in graph["edges"]:
        if edge["type"] == "DECLARES":
            if edge["from"] in owners:
                declarations[owners[edge["from"]]] += 1
            continue
        if edge["type"] in ("CONTAINS", "DEPENDS_ON"):
            continue
        a, b = owners.get(edge["from"]), owners.get(edge["to"])
        if a and b and a != b:
            outgoing[a].add(b)
            incoming[b].add(a)
            proofs[a].update(edge["evidenceIds"])
            proofs[b].update(edge["evidenceIds"])
    return {
        identity: dict(
            incoming=len(incoming[identity]),
            outgoing=len(outgoing[identity]),
            declarations=declarations[identity],
            evidenceIds=sorted(proofs[identity]),
        )
        for identity in sorted(files.values())
    }
