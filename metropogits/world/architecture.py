"""Source-purpose massing within existing file envelopes; presentation only."""

import math

from metropogits.building_forms import FORMS, GENERIC_FORMS
from .geometry import point
from .seed import derive
from .source_programs import file_topology

VERSION = "source-architecture/0.1"

# Normalized x,y,z,w,h,d,shade. No courtyard/roof component creates a new entity.
COURT = [
    (0, 0, 0, 0.23, 0.54, 1, 0),
    (0.77, 0, 0, 0.23, 0.72, 1, 0.08),
    (0.23, 0, 0, 0.54, 0.4, 0.24, 0.1),
    (0, 0.54, 0, 0.23, 0.08, 1, 0.22),
    (0.77, 0.72, 0, 0.23, 0.08, 1, 0.22),
]
HALL = [
    (0, 0, 0, 1, 0.42, 1, 0),
    (0.06, 0.42, 0.06, 0.88, 0.12, 0.26, 0.18),
    (0.06, 0.42, 0.37, 0.88, 0.18, 0.26, 0.22),
    (0.06, 0.42, 0.68, 0.88, 0.12, 0.26, 0.18),
]
BENCH = [
    (0, 0, 0, 0.4, 0.6, 1, 0),
    (0.6, 0, 0, 0.4, 0.42, 1, 0.08),
    (0.4, 0, 0.34, 0.2, 0.26, 0.32, 0.1),
    (0.05, 0.6, 0.08, 0.3, 0.1, 0.84, 0.24),
    (0.65, 0.42, 0.08, 0.3, 0.1, 0.84, 0.24),
]
PAVILION = [
    (0, 0, 0, 1, 0.12, 1, 0),
    (0.04, 0.12, 0.04, 0.92, 0.34, 0.6, 0.05),
    (0, 0.46, 0, 1, 0.1, 0.8, 0.25),
    (0.12, 0.12, 0.8, 0.12, 0.34, 0.12, 0.08),
    (0.76, 0.12, 0.8, 0.12, 0.34, 0.12, 0.08),
]
TOWER = [
    (0, 0, 0, 1, 0.2, 1, 0),
    (0.15, 0.2, 0.08, 0.7, 0.48, 0.84, 0.06),
    (0.25, 0.68, 0.18, 0.5, 0.28, 0.64, 0.15),
    (0.34, 0.96, 0.3, 0.32, 0.04, 0.4, 0.28),
]
STEPPED = [
    (0, 0, 0, 1, 0.24, 1, 0),
    (0, 0.24, 0, 0.7, 0.28, 0.8, 0.08),
    (0, 0.52, 0, 0.4, 0.3, 0.6, 0.15),
    (0.02, 0.82, 0.02, 0.36, 0.08, 0.56, 0.26),
]
ARCHIVE = [
    (0, 0, 0, 0.28, 0.64, 1, 0),
    (0.36, 0, 0, 0.28, 0.8, 1, 0.06),
    (0.72, 0, 0, 0.28, 0.56, 1, 0.12),
    (0, 0.64, 0.04, 0.28, 0.08, 0.92, 0.25),
    (0.36, 0.8, 0.04, 0.28, 0.08, 0.92, 0.25),
]


def massing(building, topology, anchor=False):
    """Same role can have different observed responsibilities and silhouettes."""
    archetype = building["archetype"]
    incoming, outgoing = topology["incoming"], topology["outgoing"]
    variant = int(derive(building["entityId"], VERSION), 16) % 3
    base = FORMS.get(archetype, GENERIC_FORMS[variant])
    name = "Role facility"
    if archetype == "GENERIC_BUILDING":
        base = GENERIC_FORMS[variant]
        name = "Unclassified source / neutral massing"
    elif archetype == "SERVICE_OFFICE":
        if outgoing >= 3 and outgoing > incoming:
            base, name = COURT, "Multi-target service court"
        elif incoming >= 3 or anchor:
            base, name = TOWER, "Shared service tower"
        else:
            base, name = (STEPPED if variant else COURT), "Service wings"
    elif archetype == "LIBRARY":
        if outgoing >= 3:
            base, name = (
                (BENCH, HALL, COURT)[variant],
                "Multi-target validation benches",
            )
        elif outgoing:
            base, name = (
                (PAVILION, BENCH, HALL)[variant],
                "Target-linked verification pavilion",
            )
        else:
            base, name = (
                (HALL if variant else COURT),
                "Validation halls / local targets unresolved",
            )
    elif archetype in ("UI_PAVILION", "API_HUB", "PORT"):
        if archetype == "UI_PAVILION":
            base, name = (
                ((PAVILION, HALL, COURT)[variant] if outgoing < 3 else COURT),
                "Interface galleries",
            )
        elif archetype == "API_HUB":
            base, name = (COURT if outgoing >= 3 else base), "API access hall"
        else:
            name = "Outbound adapter terminal"
    elif archetype in ("MODEL_ARCHIVE", "DOCUMENT_DEPOT", "SEARCH_LIBRARY"):
        base, name = (
            (
                (ARCHIVE, STEPPED, BENCH)[variant]
                if archetype == "MODEL_ARCHIVE"
                else (COURT if variant else base)
            ),
            "Schema / document archive wings",
        )
    elif archetype in ("STRUCTURED_WAREHOUSE", "STORAGE_SILOS", "WORKER_WORKSHOP"):
        base, name = (
            (HALL if archetype != "STORAGE_SILOS" and variant else base),
            "Storage or task-work bays",
        )
    elif archetype == "COMPUTE_LAB":
        base, name = (BENCH if variant else base), "Compute research blocks"
    elif archetype == "DATA_LAB":
        base, name = (
            (ARCHIVE if incoming > outgoing else BENCH),
            "Data processing benches",
        )
    elif archetype in ("GATE", "SECURITY_STATION"):
        name = "Source access / security gateway"
    elif archetype == "CLI_TERMINAL":
        name = "Command concourse"
    elif archetype in (
        "CONFIGURATION",
        "CONTROL_CENTER",
        "STATE_HUB",
        "CACHE_TOWER",
        "EXCHANGE",
    ):
        name = "Shared state / coordination facility"
    # Real source anchors keep a legible tall volume; not an extra invented tower.
    # Neighbours are purposefully lower where their existing role form permits it.
    if anchor and archetype not in ("GATE", "SECURITY_STATION", "GENERIC_BUILDING"):
        base = TOWER if incoming >= outgoing else base
        name = "Activity anchor / " + name
    # Stable architectural wing handedness, within the same source footprint.
    if variant == 2 and archetype not in ("GATE", "PORT", "CLI_TERMINAL"):
        base = [(1 - x - w, y, z, w, h, d, shade) for x, y, z, w, h, d, shade in base]
    return base, name


def purpose_world(world, graph):
    topology = file_topology(graph)
    anchors = {
        k
        for site in world.get("campusPlan", {}).get("sites", [])
        for k in site["anchorEntityIds"]
    }
    entities = {e["id"]: e for e in graph["entities"] if e["kind"] == "FILE"}
    parcels, programs = [], {}
    for p in world["parcels"]:
        record = topology[p["entityId"]]
        form, name = massing(p, record, p["entityId"] in anchors)
        c, s = math.cos(p["angle"]), math.sin(p["angle"])
        w, h, d = p["width"], p["height"], p["depth"]

        def place(x, z):
            return point(
                [p["center"][0] + c * x - s * z, p["center"][1] + s * x + c * z]
            )

        parts = []
        for x, y, z, pw, ph, pd, shade in form:
            lx, lz = (x - 0.5) * w, (z - 0.5) * d
            parts.append(
                dict(
                    x=lx,
                    y=y * h,
                    z=lz,
                    width=pw * w,
                    height=ph * h,
                    depth=pd * d,
                    shade=shade,
                    footprint=[
                        place(a, b)
                        for a, b in (
                            (lx, lz),
                            (lx + pw * w, lz),
                            (lx + pw * w, lz + pd * d),
                            (lx, lz + pd * d),
                        )
                    ],
                )
            )
        parcels.append(dict(p, parts=parts))
        programs[p["entityId"]] = dict(
            version=VERSION,
            label=name,
            derived=True,
            anchor=p["entityId"] in anchors,
            incomingFiles=record["incoming"],
            outgoingFiles=record["outgoing"],
            declarations=record["declarations"],
            roleEvidenceIds=sorted(
                {
                    ev
                    for r in entities[p["entityId"]].get("roles", [])
                    for ev in r["evidenceIds"]
                }
            ),
            relationEvidenceIds=record["evidenceIds"],
        )
    return dict(world, parcels=parcels), programs
