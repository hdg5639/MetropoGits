"""Purpose-specific massing for certified campus groups, not new facilities.

Keep the reserved footprint, source membership and access network unchanged.
The volumes below are architectural metaphors, never counts of runtime rooms,
servers, laboratories or departments. Unknown groups retain neutral massing.
"""

from .architecture_catalog import part
from .seed import derive
from .source_programs import ROLE_PROGRAM

VERSION = "campus-massing/0.1"


def campus_massing(source):
    summary = source.get("campusProgram", {})
    kind = summary.get("kind")
    # Only an already source-certified program can activate a special silhouette.
    # Names, group size and attractive prototype labels are not role evidence.
    if not summary.get("evidenceIds") or not summary.get("classifiedMemberCount"):
        return None
    roles = summary.get("roleCounts", {})
    if not any(n > 0 and ROLE_PROGRAM.get(r) == kind for r, n in roles.items()):
        return None
    b = part
    mirror = int(derive(source["id"], VERSION), 16) % 2
    if kind == "VALIDATION":
        # A low connecting spine with three unequal roof-lit halls. Open fingers
        # are visible in grayscale, unlike the old full-lot podium plus tower.
        specs = [b(0.04, 0, 0.05, 0.92, 0.22, 0.18, "ROUNDED", 2)]
        for x, h, d, shape in ((0.05, 0.44, 0.67, "WEDGE"), (0.38, 0.57, 0.75, "ROUNDED"), (0.71, 0.38, 0.60, "WEDGE")):
            specs.append(b(x, 0, 0.23, 0.24, h, d, shape, 2))
        specs.append(b(0.05, 0, 0.78, 0.24, 0.16, 0.19, "DOME", 2))
        layout, label, proportion = (
            "COMB_HALLS",
            "Verification halls / shared spine",
            0.95,
        )
    elif kind == "DATA":
        storage = any(
            roles.get(r, 0)
            for r in (
                "PERSISTENCE_ADAPTER",
                "DOCUMENT_PERSISTENCE_ADAPTER",
                "OBJECT_STORAGE_ADAPTER",
                "CACHE_ADAPTER",
            )
        )
        if storage:
            specs = [
                b(0.05, 0, 0.08, 0.39, 0.40, 0.80, "ROUNDED", 4),
                b(0.56, 0, 0.08, 0.39, 0.40, 0.80, "ROUNDED", 4),
                b(0.44, 0, 0.15, 0.12, 0.20, 0.25, "ROUNDED", 2),
                b(0.26, 0, 0.79, 0.48, 0.15, 0.18),
            ]
            layout, label = "LINKED_STORAGE_HALLS", "Data access halls"
        else:
            # Data models alone do NOT establish a database/data center.
            specs = [
                b(0.05, 0, 0.08, 0.22, 0.58, 0.84, "TAPER", 2),
                b(0.39, 0, 0.08, 0.22, 0.76, 0.66, "TAPER", 2),
                b(0.73, 0, 0.08, 0.22, 0.46, 0.84, "ROUNDED", 2),
                b(0.27, 0, 0.08, 0.46, 0.18, 0.19, "ROUNDED", 2),
                b(0.27, 0, 0.76, 0.46, 0.13, 0.16, "ROUNDED", 2),
            ]
            layout, label = "ARCHIVE_FINGERS", "Model archive wings"
        proportion = 1.15
    elif kind == "APPLICATION":
        specs = [
            b(0.05, 0, 0.07, 0.31, 0.80, 0.40, "TAPER", 2),
            b(0.14, 0.80, 0.16, 0.13, 0.20, 0.13, "SPIRE", 4),
            b(0.36, 0, 0.10, 0.58, 0.26, 0.26, "ROUNDED", 2),
            b(0.72, 0, 0.36, 0.22, 0.38, 0.51, "WEDGE", 2),
            b(0.12, 0, 0.58, 0.24, 0.23, 0.32, "ROUNDED", 1),
            b(0.36, 0, 0.72, 0.36, 0.12, 0.15, "ROUNDED", 2),
        ]
        layout, label, proportion = (
            "TOWER_AND_OPEN_WINGS",
            "Application tower / shared court",
            2.4,
        )
    elif kind == "INTERFACE":
        specs = [
            b(0.05, 0, 0.09, 0.90, 0.21, 0.38, "ROUNDED", 2),
            b(0.05, 0.21, 0.09, 0.68, 0.19, 0.26, "ROUNDED", 2),
            b(0.05, 0.40, 0.09, 0.40, 0.16, 0.19, "ROUNDED", 1),
            b(0.02, 0.21, 0.07, 0.96, 0.025, 0.62, "ROUNDED", 4),
            b(0.09, 0, 0.68, 0.24, 0.17, 0.25, "DOME", 2),
            b(0.67, 0, 0.68, 0.24, 0.17, 0.25, "DOME", 2),
            b(0.43, 0, 0.47, 0.14, 0.10, 0.35, "ROUNDED", 2),
        ]
        layout, label, proportion = (
            "TERRACED_GALLERY",
            "Interface galleries / sheltered forecourt",
            1.1,
        )
    elif kind == "COMPUTE":
        specs = [
            b(0.06, 0, 0.08, 0.34, 0.56, 0.36, "TAPER", 2),
            b(0.59, 0, 0.10, 0.34, 0.38, 0.32, "ROUNDED", 2),
            b(0.22, 0, 0.63, 0.60, 0.26, 0.30, "ROUNDED", 4),
            b(0.40, 0.07, 0.19, 0.19, 0.12, 0.12, "ROUNDED", 2),
            b(0.31, 0.07, 0.44, 0.12, 0.12, 0.19, "ROUNDED", 2),
            b(0.69, 0.07, 0.42, 0.12, 0.12, 0.21, "ROUNDED", 2),
        ]
        layout, label, proportion = (
            "LINKED_PODS",
            "Compute pavilions / linked volumes",
            1.25,
        )
    elif kind == "TOOLING":
        specs = [
            b(0.04, 0, 0.09, 0.65, 0.36, 0.78, "SAWTOOTH", 4),
            b(0.75, 0, 0.10, 0.20, 0.63, 0.31, "TAPER", 4),
            b(0.69, 0, 0.22, 0.06, 0.16, 0.19, "ROUNDED", 2),
            b(0.75, 0, 0.60, 0.20, 0.20, 0.28, "WEDGE", 2),
        ]
        layout, label, proportion = (
            "WORKSHOP_AND_BAR",
            "Tooling workshops / access wing",
            1.0,
        )
    else:
        return None
    model = source["physicalModel"]
    physical = source.get('physicalProgramVersion') == 'capacity-replan/0.2'
    if physical:
        # The same evidenced purpose admits several genuinely different
        # compositions. This changes volumes/voids, not role classifications.
        # No research/data-center claim is inferred from an attractive shape.
        from .modern_massing import modern_grammar
        choice = int(derive(source['id'], 'program-composition/0.2'), 16) % 4
        alternatives = {
            'APPLICATION': ('bar', 'tower', 'atrium', 'bar'),
            'VALIDATION': ('verification', 'pavilions', 'court', 'bar'),
            'INTERFACE': ('bar', 'atrium', 'court', 'bar'),
            'COMPUTE': ('pods', 'pavilions', 'bar', 'atrium'),
            'TOOLING': ('warehouse', 'sawtooth', 'hall', 'bar'),
            'DATA': ('warehouse', 'hall', 'sawtooth', 'court') if kind == 'DATA' and storage else ('bar', 'atrium', 'court', 'bar'),
        }
        # Keep one original, purpose-specific system in the population.
        if choice:
            specs, layout = modern_grammar(alternatives[kind][choice], model, source['id'])
        if kind == 'APPLICATION' and choice != 1:
            proportion = 1.05  # Horizontal offices are not stretched towers.
    # Deep sites use the long axis for halls, not a stretched monumental roof.
    # This rotates only architectural masses; the real footprint/yaw and road
    # entrances stay fixed. Frontage dressing is resolved AFTER the transform.
    transpose = model["depth"] > model["width"] * 1.25
    capacity = min(model['width'], model['depth']) * proportion
    height = capacity if physical else min(source['height'], capacity)
    for p in specs:
        if transpose:
            p["x"], p["z"] = p["z"], p["x"]
            p["width"], p["depth"] = p["depth"], p["width"]
        if mirror:
            p["x"] = 1 - p["x"] - p["width"]
    return (
        specs,
        height,
        dict(
            version='campus-massing/0.2' if physical else VERSION,
            layout=layout,
            label=label,
            programKind=kind,
            roleEvidenceIds=sorted(summary["evidenceIds"]),
            derived=True,
            presentationOnly=True,
            longAxisAdapted=transpose,
            volumesAreNotSourceCounts=True,
        ),
    )
