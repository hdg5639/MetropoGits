"""Source-affinity campus complexes; shared physical aggregate, not new files."""

import math
from collections import Counter, defaultdict
from itertools import combinations

from .geometry import bounds, q, rectangle
from .source_programs import program_summary

VERSION = "campus-landmarks/0.1"
MAX_AFFINITY_WORK = 300_000


def source_edges(graph):
    files = {e["path"]: e["id"] for e in graph["entities"] if e["kind"] == "FILE"}
    owners = {
        e["id"]: files.get(e.get("path"))
        for e in graph["entities"]
        if e["kind"] in ("FILE", "SYMBOL")
    }
    return [
        (owners[e["from"]], owners[e["to"]], e)
        for e in graph["edges"]
        if e["type"] not in ("CONTAINS", "DECLARES", "DEPENDS_ON")
        and e["confidence"] in ("DIRECT", "RESOLVED")
        and owners.get(e["from"])
        and owners.get(e["to"])
        and owners[e["from"]] != owners[e["to"]]
    ]


def campus_affinity(graph, locations):
    """Visual affinity via real edges or a shared local target, not a new edge."""
    pairs, targets = {}, defaultdict(set)
    for a, b, _ in source_edges(graph):
        if a not in locations:
            continue
        targets[b].add(a)
        if b in locations and locations[a] == locations[b]:
            pairs[tuple(sorted((a, b)))] = 2
    work = 0
    for target, members in sorted(targets.items()):
        # Bounded presentation choices never remove original graph relations.
        if len(members) > 128:
            continue
        for a, b in combinations(sorted(members), 2):
            work += 1
            if work > MAX_AFFINITY_WORK:
                raise ValueError("role compound campus affinity work limit")
            if locations[a] == locations[b]:
                key = (a, b)
                pairs[key] = min(4, pairs.get(key, 0) + 0.75)
            if len(pairs) > 100_000:
                raise ValueError("role compound campus affinity limit")
    return pairs


def decorate(model, members, zone, graph, links, field, terrain):
    """Compile a large hall/podium and a few linked anchors in checked space."""
    from .elevation import foundation_faces

    ids = sorted(p["entityId"] for p in members)
    summary = program_summary(dict(zone, memberEntityIds=ids))
    kind = summary["kind"]
    height = q(
        min(
            36,
            max(max(p["height"] for p in members) * 1.25, 20 + math.log2(len(ids)) * 2),
        )
    )
    # Each arrangement is one inspectable compound. Wings are architectural
    # volumes representing its actual sources, never invented departments.
    if kind == "VALIDATION":
        specs = [
            (0, 0, 0, 1, 0.16, 1),
            (0.04, 0.16, 0.08, 0.92, 0.32, 0.84),
            (0.08, 0.48, 0.15, 0.2, 0.52, 0.32),
            (0.38, 0.48, 0.14, 0.54, 0.12, 0.72),
        ]
        label = "Verification hall"
    elif kind == "DATA":
        specs = [
            (0, 0, 0, 1, 0.18, 1),
            (0.06, 0.18, 0.08, 0.36, 0.72, 0.84),
            (0.57, 0.18, 0.08, 0.36, 0.52, 0.84),
            (0.4, 0.18, 0.38, 0.2, 0.28, 0.24),
        ]
        label = "Data commons"
    elif kind in ("APPLICATION", "TOOLING"):
        specs = [
            (0, 0, 0, 1, 0.18, 1),
            (0.04, 0.18, 0.1, 0.92, 0.24, 0.8),
            (0.1, 0.42, 0.15, 0.3, 0.58, 0.42),
            (0.59, 0.42, 0.4, 0.28, 0.28, 0.46),
        ]
        label = "Application hall" if kind == "APPLICATION" else "Tooling hall"
    elif kind == "INTERFACE":
        specs = [
            (0, 0, 0, 1, 0.14, 1),
            (0.04, 0.14, 0.06, 0.92, 0.38, 0.76),
            (0.04, 0.52, 0.04, 0.92, 0.1, 0.8),
            (0.7, 0.62, 0.15, 0.2, 0.38, 0.3),
        ]
        label = "Interface gallery"
    else:
        specs = [
            (0, 0, 0, 1, 0.18, 1),
            (0.08, 0.18, 0.08, 0.32, 0.68, 0.84),
            (0.6, 0.18, 0.08, 0.32, 0.46, 0.84),
            (0.4, 0.18, 0.3, 0.2, 0.28, 0.4),
        ]
        label = "Compute hall" if kind == "COMPUTE" else "Source commons"
    c, s = math.cos(model["angle"]), math.sin(model["angle"])
    parts = []
    for x, y, z, w, h, d in specs:
        u = (x + w / 2 - 0.5) * model["width"]
        v = (z + d / 2 - 0.5) * model["depth"]
        at = [model["center"][0] + c * u - s * v, model["center"][1] + s * u + c * v]
        parts.append(
            dict(
                footprint=rectangle(
                    at, model["angle"], w * model["width"], d * model["depth"]
                ),
                y=q(model["baseElevation"] + y * height),
                height=q(h * height),
            )
        )
    model["parts"] = parts
    model["foundationFaces"] = foundation_faces(model, terrain) if field else []
    anchor = min(ids, key=lambda k: (-sum(links[k].get(b, 0) for b in ids), k))
    mapped = source_edges(graph)
    targets = defaultdict(set)
    for a, b, _ in mapped:
        if a in ids and b not in ids:
            targets[b].add(a)
    shared = sorted(k for k, v in targets.items() if len(v) > 1)
    edges = [e for a, b, e in mapped if a in ids and b in [*ids, *shared]]
    counts = Counter(p["archetype"] for p in members)
    x, z, X, Z = bounds(model["footprint"])
    return dict(
        role="CAMPUS:" + kind,
        tier="landmark",
        title=label,
        version=VERSION,
        height=height,
        x=x,
        z=z,
        width=X - x,
        depth=Z - z,
        campusProgram=summary,
        anchorEntityId=anchor,
        sourceEdgeIds=sorted(e["id"] for e in edges),
        sharedTargetIds=shared,
        groupingBasis="STATIC_EDGES_AND_SHARED_LOCAL_TARGETS",
        evidenceIds=sorted(
            {ev for e in edges for ev in e["evidenceIds"]}
            | {ev for p in members for ev in p["evidenceIds"]}
        ),
        archetypeCounts=[
            dict(archetype=a, count=n)
            for a, n in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
        ],
    )
