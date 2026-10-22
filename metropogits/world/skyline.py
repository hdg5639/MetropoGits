"""Bounded static-reference centers; presentation, not runtime/business centers."""

import math
from collections import defaultdict

from .campus_landmarks import source_edges
from .seed import derive

VERSION = "reference-skyline/0.1"
RADIUS = 48
MAX_WORK = 300_000


def reference_centers(world, graph, eligible):
    """Find existing local hubs, without moving files or inventing relations.

    Fixed thresholds/local distances avoid global percentile reshuffles. Campus
    source layers are excluded: their certified complexes retain their identity.
    A center needs six distinct evidenced incoming files and eight nearby lots.
    At most three spatially separated centers are selected per directory owner.
    """
    campus = {
        k
        for s in world.get("campusPlan", {}).get("sites", [])
        for k in s["memberEntityIds"]
    }
    parcels = {p["entityId"]: p for p in world["parcels"]}
    eligible = set(eligible) & parcels.keys() - campus
    incoming, neighbours, proofs = defaultdict(set), defaultdict(set), defaultdict(set)
    for a, b, edge in source_edges(graph):
        if a not in parcels or b not in parcels:
            continue
        incoming[b].add(a)
        neighbours[a].add(b)
        neighbours[b].add(a)
        proofs[b].update(edge["evidenceIds"])
    grid = defaultdict(list)
    for k in sorted(eligible):
        p = parcels[k]
        x, z = p["center"]
        grid[p["districtId"], math.floor(x / RADIUS), math.floor(z / RADIUS)].append(k)
    work = 0

    def nearby(k):
        nonlocal work
        p = parcels[k]
        x, z = p["center"]
        i, j = math.floor(x / RADIUS), math.floor(z / RADIUS)
        result = []
        for a in range(i - 1, i + 2):
            for b in range(j - 1, j + 2):
                for other in grid[p["districtId"], a, b]:
                    work += 1
                    if work > MAX_WORK:
                        raise ValueError("reference skyline spatial work limit")
                    if math.dist(p["center"], parcels[other]["center"]) <= RADIUS:
                        result.append(other)
        return sorted(result)

    centers = defaultdict(list)
    profiles = {}
    for k in sorted(eligible, key=lambda k: (-len(incoming[k]), k)):
        if len(incoming[k]) < 6:
            break
        p = parcels[k]
        owner = p["districtId"]
        if len(centers[owner]) >= 3 or any(
            math.dist(p["center"], parcels[c]["center"]) < RADIUS * 2
            for c in centers[owner]
        ):
            continue
        local = nearby(k)
        if len(local) < 8 or sum(other in neighbours[k] for other in local) < 2:
            continue
        centers[owner].append(k)
        for other in local:
            tier = (
                "CORE"
                if other == k
                else "LINKED"
                if other in neighbours[k]
                else "CONTEXT"
            )
            profiles[other] = dict(
                version=VERSION,
                tier=tier,
                centerEntityId=k,
                observedIncomingFiles=len(incoming[other]),
                centerIncomingFiles=len(incoming[k]),
                centerDistance=round(
                    math.dist(p["center"], parcels[other]["center"]), 4
                ),
                relationEvidenceIds=sorted(proofs[k]) if other == k else [],
                basis="DIRECT_RESOLVED_LOCAL_FILE_REFERENCES",
                contextIsNotARelationship=tier == "CONTEXT",
                derived=True,
                presentationOnly=True,
            )
    return profiles


def skyline_massing(profile, source, specs):
    """Use existing source height capacity; no unvalidated skyscraper envelope."""
    from .architecture_catalog import grammar

    tier = profile["tier"]
    if tier == "CORE":
        specs, scale, layout = grammar("tower"), 1.0, "SETBACK_TOWER"
    elif tier == "LINKED":
        form = "terrace" if int(derive(source["entityId"], VERSION), 16) % 2 else "bar"
        specs, scale, layout = grammar(form), 0.78, "LINKED_" + form.upper()
    else:
        # Surroundings remain neutral/supporting buildings, not fake offices.
        # A source with many other incoming users retains midrise capacity.
        scale = 0.66 if profile["observedIncomingFiles"] >= 6 else 0.42
        layout = "CONTEXT_EXISTING_MASSING"
    budget = min(source["height"], min(source["width"], source["depth"]) * 2.8)
    return specs, budget * scale, dict(profile, layout=layout)
