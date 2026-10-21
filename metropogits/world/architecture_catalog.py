"""Evidence-gated, export-only architecture grammar. Never new source entities.

Recipes use a small primitive kit inside the original rotated file/compound
envelope. Meshes are compiled once offline and shared by SVG, Canvas and WebGL.
The proposed catalog names are presentation IDs, not new City archetype enums.
"""

import math
from collections import Counter

from .geometry import point, q
from .seed import derive
from .source_programs import file_topology

VERSION = "architecture/0.2"
# Presentation revisions must not reshuffle existing source silhouettes.
MASSING_SEED_VERSION = "architecture/0.1"
MAX_PARTS = 18
MAX_FACES = 240


def part(x, y, z, w, h, d, shape="BOX", material=1):
    return dict(
        x=x,
        y=y,
        z=z,
        width=w,
        height=h,
        depth=d,
        primitive=shape,
        materialKind=material,
    )


def grammar(form, variant=0):
    """Unit-envelope massing, with intentional low halls and open negative space."""
    b = part
    if form == "bar":
        return [
            b(0.06, 0, 0.08, 0.88, 0.12, 0.84),
            b(0.1, 0.12, 0.12, 0.8, 0.64, 0.62, material=2),
            b(0.1, 0.76, 0.12, 0.8, 0.045, 0.62),
            b(0.3, 0.12, 0.74, 0.4, 0.13, 0.23, material=2),
        ]
    if form == "terrace":
        return [
            b(0.04, 0, 0.04, 0.92, 0.18, 0.92),
            b(0.04, 0.18, 0.04, 0.76, 0.23, 0.76, material=2),
            b(0.04, 0.41, 0.04, 0.56, 0.25, 0.56, material=2),
            b(0.04, 0.66, 0.04, 0.34, 0.22, 0.36, material=2),
            b(0.62, 0.19, 0.78, 0.28, 0.025, 0.12, material=4),
        ]
    if form == "twin":
        return [
            b(0.03, 0, 0.06, 0.94, 0.15, 0.88),
            b(0.08, 0.15, 0.12, 0.32, 0.77, 0.64, material=2),
            b(0.6, 0.15, 0.28, 0.3, 0.6, 0.62, material=2),
            b(0.4, 0.4, 0.4, 0.2, 0.08, 0.22, material=2),
        ]
    if form == "court":
        return [
            b(0.04, 0, 0.05, 0.23, 0.54, 0.9),
            b(0.73, 0, 0.05, 0.23, 0.66, 0.9),
            b(0.27, 0, 0.05, 0.46, 0.38, 0.24, material=2),
            b(0.27, 0, 0.85, 0.46, 0.1, 0.1, material=2),
        ]
    if form == "pavilions":
        return [
            b(0.03, 0, 0.06, 0.42, 0.3, 0.38, "GABLE"),
            b(0.55, 0, 0.05, 0.42, 0.4, 0.4, "GABLE"),
            b(0.12, 0, 0.62, 0.76, 0.26, 0.32, "GABLE"),
            b(0.42, 0.04, 0.38, 0.16, 0.1, 0.32, material=2),
        ]
    if form == "tower":
        return [
            b(0.02, 0, 0.02, 0.96, 0.14, 0.96),
            b(0.22, 0.14, 0.18, 0.56, 0.7, 0.58, "CHAMFER", 2),
            b(0.28, 0.84, 0.24, 0.44, 0.09, 0.46),
            b(0.44, 0.93, 0.4, 0.12, 0.07, 0.12, material=4),
        ]
    if form == "gate":
        return [
            b(0.04, 0, 0.17, 0.24, 0.58, 0.66, "CHAMFER"),
            b(0.72, 0, 0.17, 0.24, 0.58, 0.66, "CHAMFER"),
            b(0.04, 0.54, 0.17, 0.92, 0.09, 0.66, material=4),
            b(0.29, 0.05, 0.76, 0.42, 0.04, 0.2),
        ]
    if form == "atrium":
        return [
            b(0.04, 0, 0.06, 0.92, 0.12, 0.86),
            b(0.06, 0.12, 0.1, 0.25, 0.45, 0.72),
            b(0.69, 0.12, 0.1, 0.25, 0.45, 0.72),
            b(0.31, 0.12, 0.12, 0.38, 0.34, 0.56, material=2),
            b(0.04, 0.57, 0.07, 0.92, 0.05, 0.8, material=4),
        ]
    if form == "terminal":
        return [
            b(0.02, 0, 0.1, 0.96, 0.27, 0.68),
            b(0.01, 0.27, 0.08, 0.98, 0.045, 0.82, material=4),
            b(0.12, 0.08, 0.8, 0.08, 0.18, 0.14),
            b(0.4, 0.08, 0.8, 0.08, 0.18, 0.14),
            b(0.68, 0.08, 0.8, 0.08, 0.18, 0.14),
            b(0.76, 0.31, 0.14, 0.12, 0.42, 0.22, material=2),
        ]
    if form == "hall":
        return [
            b(0.04, 0, 0.06, 0.92, 0.36, 0.88, "GABLE"),
            b(0.13, 0, 0.76, 0.74, 0.12, 0.21, material=2),
            b(0.36, 0.05, 0.92, 0.28, 0.04, 0.07),
        ]
    if form == "vault":
        return [
            b(0.08, 0, 0.08, 0.84, 0.32, 0.84, "CHAMFER", 3),
            b(0.25, 0.32, 0.22, 0.5, 0.15, 0.56, "CHAMFER"),
            b(0.38, 0, 0.84, 0.24, 0.17, 0.15, material=4),
        ]
    if form == "warehouse":
        return [
            b(0.03, 0, 0.05, 0.28, 0.34, 0.9, "GABLE", 4),
            b(0.36, 0, 0.05, 0.28, 0.34, 0.9, "GABLE", 4),
            b(0.69, 0, 0.05, 0.28, 0.34, 0.9, "GABLE", 4),
            b(0.03, 0, 0.82, 0.94, 0.12, 0.16, material=4),
        ]
    if form == "sawtooth":
        return [
            b(0.04, 0, 0.06, 0.92, 0.28, 0.84, material=4),
            b(0.04, 0.28, 0.06, 0.92, 0.14, 0.84, "SAWTOOTH", 4),
            b(0.35, 0, 0.9, 0.3, 0.12, 0.08, material=2),
        ]
    if form == "archive":
        return [
            b(0.04, 0, 0.08, 0.92, 0.35, 0.84),
            b(0.08, 0.35, 0.12, 0.18, 0.12, 0.76),
            b(0.3, 0.35, 0.12, 0.18, 0.25, 0.76),
            b(0.52, 0.35, 0.12, 0.18, 0.12, 0.76),
            b(0.74, 0.35, 0.12, 0.18, 0.1, 0.76),
            b(0.07, 0.04, 0.88, 0.86, 0.08, 0.1, material=4),
        ]
    if form == "pods":
        return [
            b(0.06, 0, 0.08, 0.4, 0.36, 0.36, "CHAMFER"),
            b(0.52, 0, 0.13, 0.4, 0.51, 0.42, "CHAMFER"),
            b(0.15, 0, 0.63, 0.68, 0.27, 0.32, "CHAMFER"),
            b(0.4, 0.04, 0.35, 0.2, 0.12, 0.4, material=2),
        ]
    if form == "hub":
        return [
            b(0.25, 0, 0.25, 0.5, 0.4, 0.5, "DRUM", 2),
            b(0.04, 0, 0.34, 0.21, 0.2, 0.32, material=4),
            b(0.75, 0, 0.34, 0.21, 0.2, 0.32, material=4),
            b(0.34, 0, 0.04, 0.32, 0.2, 0.21, material=4),
            b(0.34, 0, 0.75, 0.32, 0.2, 0.21, material=4),
        ]
    if form == "silos":
        return [
            b(0.02, 0, 0.05, 0.96, 0.09, 0.9),
            b(0.07, 0.09, 0.1, 0.34, 0.5, 0.34, "DRUM", 4),
            b(0.57, 0.09, 0.1, 0.34, 0.65, 0.34, "DRUM", 4),
            b(0.08, 0.09, 0.58, 0.34, 0.4, 0.34, "DRUM", 4),
            b(0.57, 0.09, 0.58, 0.34, 0.4, 0.34, "DRUM", 4),
        ]
    if form == "dome":
        return [
            b(0.08, 0, 0.1, 0.84, 0.14, 0.8, "CHAMFER"),
            b(0.14, 0.14, 0.16, 0.72, 0.38, 0.68, "DOME", 4),
            b(0.36, 0, 0.82, 0.28, 0.12, 0.16, material=2),
        ]
    if form == "mast":
        return [
            b(0.06, 0, 0.09, 0.88, 0.23, 0.76),
            b(0.35, 0.23, 0.3, 0.3, 0.48, 0.32, material=2),
            b(0.22, 0.71, 0.2, 0.56, 0.055, 0.52),
            b(0.47, 0.765, 0.44, 0.06, 0.235, 0.07, material=4),
        ]
    if form == "gantry":
        return [
            b(0.04, 0, 0.3, 0.66, 0.26, 0.62, "SAWTOOTH", 4),
            b(0.78, 0, 0.08, 0.12, 0.64, 0.16, material=4),
            b(0.08, 0.59, 0.08, 0.82, 0.05, 0.16, material=4),
            b(0.13, 0.39, 0.12, 0.03, 0.2, 0.04, material=4),
        ]
    if form == "containers":
        return [
            b(0.04, 0, 0.08, 0.4, 0.2, 0.26, material=4),
            b(0.56, 0, 0.08, 0.4, 0.2, 0.26, material=4),
            b(0.04, 0, 0.42, 0.4, 0.2, 0.26, material=4),
            b(0.56, 0, 0.42, 0.4, 0.2, 0.26, material=4),
            b(0.2, 0.2, 0.08, 0.4, 0.2, 0.26, material=4),
            b(0.34, 0, 0.77, 0.32, 0.18, 0.18),
        ]
    if form == "gallery":
        return [
            b(0.04, 0, 0.1, 0.92, 0.14, 0.66, material=2),
            b(0.04, 0.14, 0.1, 0.92, 0.26, 0.44, material=2),
            b(0.01, 0.4, 0.07, 0.98, 0.045, 0.75, material=4),
            b(0.12, 0, 0.75, 0.1, 0.4, 0.1),
            b(0.45, 0, 0.75, 0.1, 0.4, 0.1),
            b(0.78, 0, 0.75, 0.1, 0.4, 0.1),
        ]
    if form == "arena":
        return [
            b(0.02, 0, 0.05, 0.21, 0.33, 0.9),
            b(0.77, 0, 0.05, 0.21, 0.33, 0.9),
            b(0.23, 0, 0.05, 0.54, 0.22, 0.19),
            b(0.23, 0, 0.76, 0.54, 0.22, 0.19),
        ]
    if form == "row":
        return [
            b(0.03, 0, 0.12, 0.28, 0.43, 0.76, "GABLE", 3),
            b(0.36, 0, 0.12, 0.28, 0.54, 0.76, "GABLE", 3),
            b(0.69, 0, 0.12, 0.28, 0.4, 0.76, "GABLE", 3),
        ]
    if form == "shed":
        return [
            b(0.04, 0, 0.08, 0.92, 0.28, 0.84, "GABLE", 3),
            b(0.29, 0, 0.84, 0.42, 0.11, 0.14, material=4),
        ]
    if form == "verification":
        return [
            b(0.02, 0, 0.04, 0.96, 0.12, 0.92),
            b(0.06, 0.12, 0.08, 0.6, 0.28, 0.84, "SAWTOOTH", 4),
            b(0.7, 0.12, 0.1, 0.24, 0.34, 0.42, "DOME", 2),
            b(0.7, 0.12, 0.58, 0.24, 0.54, 0.35, "CHAMFER"),
        ]
    raise ValueError("unknown architecture grammar: " + form)


# Exact proposal vocabulary. Requirements are conservative semantic gates, not
# guesses from suggestive file names. Unavailable roles stay dormant prototypes.
FAMILIES = {
    "service": (
        "SERVICE",
        [
            ("OFFICE_BAR", "bar"),
            ("OFFICE_STEPPED", "terrace"),
            ("OFFICE_TWIN", "twin"),
            ("OFFICE_COURTYARD", "court"),
            ("ORCHESTRATION_HQ", "tower"),
            ("OFFICE_CAMPUS", "pavilions"),
        ],
    ),
    "api": (
        "ENTRYPOINT API_ENDPOINT",
        [
            ("API_GATEHOUSE", "gate"),
            ("API_EXCHANGE", "atrium"),
            ("GATEWAY_TOWER", "tower"),
            ("EDGE_TERMINAL", "terminal"),
            ("CIVIC_PLAZA_HALL", "hall"),
        ],
    ),
    "security": (
        "AUTH_CONFIGURATION",
        [
            ("AUTH_BUREAU", "atrium"),
            ("SECURITY_CHECKPOINT", "gate"),
            ("POLICY_ARCHIVE", "archive"),
            ("TOKEN_VAULT", "vault"),
            ("WATCHTOWER", "mast"),
        ],
    ),
    "relational": (
        "PERSISTENCE_ADAPTER",
        [
            ("RDB_GRID_WAREHOUSE", "warehouse"),
            ("RDB_INDEX_HALL", "archive"),
            ("RDB_TRANSACTION_BANK", "vault"),
            ("ORM_TRANSFER_DEPOT", "terminal"),
            ("RDB_STORAGE_COURT", "arena"),
            ("SCHEMA_REGISTRY", "archive"),
        ],
    ),
    "data": (
        "DOCUMENT_PERSISTENCE_ADAPTER CACHE_ADAPTER SEARCH_ADAPTER",
        [
            ("DOCUMENT_PODS", "pods"),
            ("KEYVALUE_EXCHANGE", "hub"),
            ("CACHE_TRANSFER_HUB", "terminal"),
            ("SEARCH_INDEX_TOWER", "archive"),
            ("GRAPH_DATA_ATRIUM", "hub"),
            ("TIMESERIES_SILOS", "silos"),
        ],
    ),
    "messaging": (
        "MESSAGE_PRODUCER MESSAGE_CONSUMER",
        [
            ("MESSAGE_SORTING_HALL", "sawtooth"),
            ("EVENT_EXCHANGE", "hub"),
            ("KAFKA_PORT", "gantry"),
            ("RABBITMQ_DEPOT", "warehouse"),
            ("STREAM_RELAY_TOWER", "mast"),
            ("WORKER_FABRIC", "warehouse"),
        ],
    ),
    "frontend": (
        "UI_COMPONENT UI_PAGE STATE_STORE",
        [
            ("UI_STOREFRONT", "bar"),
            ("PAGE_GALLERY", "gallery"),
            ("COMPONENT_ARCADE", "row"),
            ("DESIGN_STUDIO", "terrace"),
            ("CLIENT_PAVILION", "gallery"),
            ("STATE_EXCHANGE", "hub"),
        ],
    ),
    "networking": (
        "HTTP_CLIENT WEBSOCKET_ENDPOINT GRPC_ENDPOINT INTEGRATION_ADAPTER",
        [
            ("HTTP_INTERCHANGE", "terminal"),
            ("WEBSOCKET_TOWER", "mast"),
            ("GRPC_EXCHANGE", "twin"),
            ("PROTOCOL_BRIDGE", "gate"),
            ("INTEGRATION_STATION", "atrium"),
        ],
    ),
    "operations": (
        "CONFIGURATION BUILD_TOOL CI_WORKFLOW DEPLOYMENT_ORCHESTRATOR",
        [
            ("BUILD_WORKSHOP", "shed"),
            ("CI_ASSEMBLY_LINE", "sawtooth"),
            ("DEPLOY_CONTROL_CENTER", "mast"),
            ("CONTAINER_YARD", "containers"),
            ("CLUSTER_CONTROL_TOWER", "tower"),
            ("OBSERVABILITY_DOME", "dome"),
        ],
    ),
    "testing": (
        "TEST",
        [
            ("TEST_LAB", "pavilions"),
            ("QUALITY_INSPECTION_HALL", "sawtooth"),
            ("SIMULATION_CHAMBER", "dome"),
            ("BENCHMARK_ARENA", "arena"),
            ("FUZZING_RANGE", "warehouse"),
        ],
    ),
    "research": (
        "ML_COMPONENT DATA_PROCESSOR RESEARCH_COMPONENT",
        [
            ("RESEARCH_INSTITUTE", "court"),
            ("MODEL_LAB", "dome"),
            ("EXPERIMENT_PAVILION", "pods"),
            ("DATA_SCIENCE_CENTER", "terrace"),
            ("OBSERVATION_SPIRE", "mast"),
        ],
    ),
    "content": (
        "OBJECT_STORAGE_ADAPTER MEDIA_PROCESSOR FILE_ADAPTER ASSET_MANAGER",
        [
            ("MEDIA_STUDIO", "sawtooth"),
            ("ASSET_LIBRARY", "archive"),
            ("FILE_DOCK", "terminal"),
            ("OBJECT_STORAGE_TERMINAL", "silos"),
        ],
    ),
    "workflow": (
        "TASK_WORKER SCHEDULER WORKFLOW_ENGINE BATCH_PROCESSOR",
        [
            ("SCHEDULING_CLOCKTOWER", "mast"),
            ("WORKFLOW_FACTORY", "sawtooth"),
            ("JOB_DISPATCH_CENTER", "hub"),
            ("BATCH_PROCESSING_PLANT", "warehouse"),
        ],
    ),
    "shared": (
        "GENERAL_COMPONENT DATA_MODEL INTERFACE ADAPTER",
        [
            ("COMMON_WORKSHOP", "shed"),
            ("CORE_LIBRARY", "archive"),
            ("INTERFACE_PAVILION", "gallery"),
            ("ADAPTER_ROW", "row"),
        ],
    ),
    "tools": (
        "CLI_ENTRYPOINT DEVELOPER_TOOL DESKTOP_COMPONENT PLUGIN",
        [
            ("COMMAND_TERMINAL", "terminal"),
            ("TOOL_SHED", "shed"),
            ("DESKTOP_STUDIO", "bar"),
            ("PLUGIN_MARKET", "pavilions"),
        ],
    ),
    "generic": (
        "",
        [
            ("GENERIC_ROW", "row"),
            ("GENERIC_MIDRISE", "bar"),
            ("GENERIC_TOWER", "tower"),
            ("MIXED_USE_PODIUM", "twin"),
            ("AGGREGATE_COMPLEX", "atrium"),
            ("AGGREGATE_COURT", "court"),
            ("DISTRICT_LANDMARK", "tower"),
            ("UNCLASSIFIED_DEPOT", "shed"),
        ],
    ),
}
CATALOG = {
    identity: dict(
        id=identity,
        family=family,
        grammar=form,
        label=identity.replace("_", " ").title(),
    )
    for family, (_, recipes) in FAMILIES.items()
    for identity, form in recipes
}

# Auto-select only claims the existing source graph can actually support.
# E.g. TEST alone never proves simulation/benchmarks, nor AUTH a token vault.
ROLE_CHOICES = {
    "SERVICE": ("OFFICE_BAR", "OFFICE_STEPPED", "OFFICE_COURTYARD"),
    "ENTRYPOINT": ("API_GATEHOUSE", "API_EXCHANGE", "EDGE_TERMINAL"),
    "API_ENDPOINT": ("API_EXCHANGE", "EDGE_TERMINAL", "API_GATEHOUSE"),
    "AUTH_CONFIGURATION": ("AUTH_BUREAU", "SECURITY_CHECKPOINT"),
    "PERSISTENCE_ADAPTER": ("RDB_GRID_WAREHOUSE", "ORM_TRANSFER_DEPOT"),
    "DOCUMENT_PERSISTENCE_ADAPTER": ("DOCUMENT_PODS",),
    "CACHE_ADAPTER": ("KEYVALUE_EXCHANGE", "CACHE_TRANSFER_HUB"),
    "SEARCH_ADAPTER": ("SEARCH_INDEX_TOWER",),
    "MESSAGE_PRODUCER": ("MESSAGE_SORTING_HALL", "EVENT_EXCHANGE"),
    "MESSAGE_CONSUMER": ("MESSAGE_SORTING_HALL", "WORKER_FABRIC"),
    "UI_PAGE": ("PAGE_GALLERY", "CLIENT_PAVILION"),
    "UI_COMPONENT": ("UI_STOREFRONT", "DESIGN_STUDIO", "CLIENT_PAVILION"),
    "STATE_STORE": ("STATE_EXCHANGE",),
    "HTTP_CLIENT": ("HTTP_INTERCHANGE",),
    "WEBSOCKET_ENDPOINT": ("WEBSOCKET_TOWER",),
    "GRPC_ENDPOINT": ("GRPC_EXCHANGE",),
    "INTEGRATION_ADAPTER": ("INTEGRATION_STATION",),
    "CONFIGURATION": ("COMMON_WORKSHOP",),
    "BUILD_TOOL": ("BUILD_WORKSHOP",),
    "CI_WORKFLOW": ("CI_ASSEMBLY_LINE",),
    "DEPLOYMENT_ORCHESTRATOR": ("DEPLOY_CONTROL_CENTER",),
    "TEST": ("TEST_LAB", "QUALITY_INSPECTION_HALL"),
    "SIMULATION": ("SIMULATION_CHAMBER",),
    "BENCHMARK": ("BENCHMARK_ARENA",),
    "FUZZ_TEST": ("FUZZING_RANGE",),
    "ML_COMPONENT": ("MODEL_LAB",),
    "DATA_PROCESSOR": ("DATA_SCIENCE_CENTER",),
    "RESEARCH_COMPONENT": ("RESEARCH_INSTITUTE", "EXPERIMENT_PAVILION"),
    "OBJECT_STORAGE_ADAPTER": ("OBJECT_STORAGE_TERMINAL",),
    "MEDIA_PROCESSOR": ("MEDIA_STUDIO",),
    "ASSET_MANAGER": ("ASSET_LIBRARY",),
    "FILE_ADAPTER": ("FILE_DOCK",),
    "TASK_WORKER": ("JOB_DISPATCH_CENTER", "WORKFLOW_FACTORY"),
    "SCHEDULER": ("SCHEDULING_CLOCKTOWER",),
    "WORKFLOW_ENGINE": ("WORKFLOW_FACTORY",),
    "BATCH_PROCESSOR": ("BATCH_PROCESSING_PLANT",),
    "GENERAL_COMPONENT": ("COMMON_WORKSHOP", "INTERFACE_PAVILION"),
    "DATA_MODEL": ("CORE_LIBRARY",),
    "INTERFACE": ("INTERFACE_PAVILION",),
    "ADAPTER": ("ADAPTER_ROW",),
    "CLI_ENTRYPOINT": ("COMMAND_TERMINAL",),
    "DEVELOPER_TOOL": ("TOOL_SHED",),
    "DESKTOP_COMPONENT": ("DESKTOP_STUDIO",),
    "PLUGIN": ("PLUGIN_MARKET",),
}


def face_normal(vertices):
    for b, c in zip(vertices[1:], vertices[2:]):
        a = vertices[0]
        u, v = [b[i] - a[i] for i in range(3)], [c[i] - a[i] for i in range(3)]
        n = [
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        ]
        length = math.hypot(*n)
        if length > 1e-9:
            return [t / length for t in n]
    return [0, 1, 0]


def unit_faces(shape, roof_pitch=0.64):
    """Outward closed meshes in [0,1]^3; face surface is wall/roof only."""
    if shape in ("DRUM", "CHAMFER"):
        count = 12 if shape == "DRUM" else 8
        ring = (
            [
                [
                    0.5 + 0.5 * math.cos(i * math.tau / count),
                    0.5 + 0.5 * math.sin(i * math.tau / count),
                ]
                for i in range(count)
            ]
            if shape == "DRUM"
            else [
                [0.15, 0],
                [0.85, 0],
                [1, 0.15],
                [1, 0.85],
                [0.85, 1],
                [0.15, 1],
                [0, 0.85],
                [0, 0.15],
            ]
        )
        return [
            (list(reversed([[x, 1, z] for x, z in ring])), "roof"),
            ([[x, 0, z] for x, z in ring], "wall"),
        ] + [
            (
                [[a[0], 0, a[1]], [a[0], 1, a[1]], [b[0], 1, b[1]], [b[0], 0, b[1]]],
                "wall",
            )
            for a, b in zip(ring, ring[1:] + ring[:1])
        ]
    if shape == "DOME":

        def at(ring, side):
            theta = ring * math.pi / 8
            phi = side * math.tau / 12
            return [
                0.5 + 0.5 * math.sin(theta) * math.cos(phi),
                math.cos(theta),
                0.5 + 0.5 * math.sin(theta) * math.sin(phi),
            ]

        return [
            ([at(r, s), at(r, s + 1), at(r + 1, s + 1), at(r + 1, s)], "roof")
            for r in range(4)
            for s in range(12)
        ] + [([at(4, s) for s in range(12)], "wall")]
    if shape in ("GABLE", "SAWTOOTH"):
        ridge = 0.5 if shape == "GABLE" else 0.82
        faces = [
            ([[0, 0, 0], [1, 0, 0], [1, 0, 1], [0, 0, 1]], "wall"),
            ([[0, 0, 0], [0, 0.64, 0], [0, 0.64, 1], [0, 0, 1]], "wall"),
            ([[1, 0, 1], [1, 0.64, 1], [1, 0.64, 0], [1, 0, 0]], "wall"),
            ([[0, 0, 0], [1, 0, 0], [1, 0.64, 0], [ridge, 1, 0], [0, 0.64, 0]], "wall"),
            ([[0, 0, 1], [0, 0.64, 1], [ridge, 1, 1], [1, 0.64, 1], [1, 0, 1]], "wall"),
            ([[0, 0.64, 0], [ridge, 1, 0], [ridge, 1, 1], [0, 0.64, 1]], "roof"),
            ([[ridge, 1, 0], [1, 0.64, 0], [1, 0.64, 1], [ridge, 1, 1]], "roof"),
        ]
        return [
            (vertices if i == 0 else list(reversed(vertices)), surface)
            for i, (vertices, surface) in enumerate(faces)
            for vertices in [
                [[x, roof_pitch if y == 0.64 else y, z] for x, y, z in vertices]
            ]
        ]
    if shape != "BOX":
        raise ValueError("unknown architectural primitive")
    return []


def compile_parts(envelope, specs):
    """Retain source yaw/frontage and original conservative collision envelope."""
    if len(specs) > MAX_PARTS:
        raise ValueError("architecture part budget")
    c, s = math.cos(envelope["angle"]), math.sin(envelope["angle"])
    width, depth, height = envelope["width"], envelope["depth"], envelope["height"]

    def locate(x, y, z):
        u, v = (x - 0.5) * width, (z - 0.5) * depth
        return [
            q(envelope["center"][0] + c * u - s * v),
            q(y * height),
            q(envelope["center"][1] + s * u + c * v),
        ]

    result = []
    for spec in specs:
        x, y, z, w, h, d = (
            spec[k] for k in ("x", "y", "z", "width", "height", "depth")
        )
        if min(x, y, z) < 0 or min(w, h, d) <= 0 or max(x + w, y + h, z + d) > 1.000001:
            raise ValueError("architecture escaped source envelope")
        shape = spec["primitive"]
        if shape == "DOME":
            h = min(h, min(w * width, d * depth) * 0.6 / height)
        elif shape == "DRUM":
            h = min(h, min(w * width, d * depth) * 2.2 / height)
        pitch = spec.get("roofPitch", 0.64)
        if shape in ("GABLE", "SAWTOOTH"):
            span = w * width / (3 if shape == "SAWTOOTH" else 1)
            pitch = max(pitch, 1 - min(0.4, span * 0.3 / (h * height)))
        faces = unit_faces(shape, pitch)
        if spec["primitive"] == "SAWTOOTH":
            # Three connected roof teeth, not one fake industrial source per bay.
            faces = [
                ([[(v[0] + i) / 3, v[1], v[2]] for v in vertices], surface)
                for i in range(3)
                for vertices, surface in faces
            ]
        model = dict(
            y=q(y * height),
            height=q(h * height),
            shade=0,
            width=q(w * width),
            depth=q(d * depth),
            materialKind=spec["materialKind"],
            primitive=spec["primitive"],
            footprint=[
                point([v[0], v[2]])
                for v in [
                    locate(a, 0, b)
                    for a, b in ((x, z), (x + w, z), (x + w, z + d), (x, z + d))
                ]
            ],
        )
        if faces:
            model["meshFaces"] = [
                dict(
                    points=[
                        locate(x + a * w, y + b * h, z + t * d) for a, b, t in vertices
                    ],
                    surface=surface,
                )
                for vertices, surface in faces
            ]
        result.append(model)
    if sum(len(p.get("meshFaces", [])) for p in result) > MAX_FACES:
        raise ValueError("architecture face budget")
    return result


def claims(entity, key, evidence, *, usage=False):
    return {
        r["value"]: r
        for r in entity.get(key, [])
        if r["confidence"] in ("DIRECT", "RESOLVED")
        and r["evidenceIds"]
        and all(k in evidence for k in r["evidenceIds"])
        and (
            not usage
            or any(
                evidence[k]["kind"] not in ("MANIFEST", "PATH")
                for k in r["evidenceIds"]
            )
        )
    }


def frontage_details(specs, envelope, family):
    """Architectural dressing on local +Z, never a new door/path in the graph.

    Find an actual ground-floor wall, not the empty middle of a court/gateway.
    Physical dimensions bound door height, canopy thickness and projection;
    narrow reserves omit supports rather than obstructing the central approach.
    """
    width, depth, height = (envelope[k] for k in ("width", "depth", "height"))
    hosts = [
        p
        for p in specs
        if p["y"] == 0
        and p["primitive"] in ("BOX", "GABLE", "SAWTOOTH", "CHAMFER")
        and p["width"] * width >= 0.35
        and p["height"] * height >= 0.25
    ]
    if not hosts:
        return list(specs), None
    # Prefer the wall in front of the existing centre approach. A side pavilion
    # is preferable to fabricating a floating lobby in the gateway opening.
    host = min(
        hosts,
        key=lambda p: (
            max(p["x"] - 0.5, 0.5 - p["x"] - p["width"], 0),
            -p["z"] - p["depth"],
            p["x"],
        ),
    )
    wall_width = host["width"] * (0.55 if host["primitive"] == "CHAMFER" else 1)
    middle = host["x"] + host["width"] / 2
    face = host["z"] + host["depth"]
    room = (1 - face) * depth
    if room < 0.025:
        return list(specs), None
    loading = family in ("relational", "data", "messaging", "media")
    style = "LOADING_BAY" if loading else "SHELTERED_LOBBY"
    ceiling = (
        host["height"]
        * height
        * (0.52 if host["primitive"] in ("GABLE", "SAWTOOTH") else 0.9)
    )
    door_h = min(3.2 if loading else 2.5, ceiling * 0.72)
    door_w = min(4.8 if loading else 3.4, wall_width * width * 0.62)
    panel_d = min(0.055, room * 0.18)
    additions = [
        part(
            middle - door_w / width / 2,
            0.015 * door_h / height,
            face,
            door_w / width,
            door_h / height,
            panel_d / depth,
            material=13 if loading else 12,
        )
    ]
    canopy_w = min(wall_width * width * 0.88, max(door_w * 1.35, door_w + 0.15))
    projection = min(1.6 if loading else 1.25, room * 0.85)
    canopy_y = door_h * 1.08
    thickness = min(0.18, ceiling * 0.07)
    if projection >= 0.1:
        additions.append(
            part(
                middle - canopy_w / width / 2,
                canopy_y / height,
                face,
                canopy_w / width,
                thickness / height,
                projection / depth,
                material=14,
            )
        )
        # Only wide public arcades need posts. Keep the doorway/central lane open.
        if not loading and canopy_w >= 3.5 and projection >= 0.55:
            post_w = min(0.18, canopy_w * 0.035)
            for x in (
                middle - canopy_w / width / 2,
                middle + canopy_w / width / 2 - post_w / width,
            ):
                additions.append(
                    part(
                        x,
                        0,
                        face + (projection - post_w) / depth,
                        post_w / width,
                        canopy_y / height,
                        post_w / depth,
                        material=14,
                    )
                )
    return list(specs) + additions, dict(
        style=style,
        derived=True,
        decorative=True,
        frontageAxis="LOCAL_POSITIVE_Z",
        partCount=len(additions),
        doorHeight=q(door_h),
        doorWidth=q(door_w),
    )


def select(entity, topology, seed, evidence):
    roles = claims(entity, "roles", evidence)
    technologies = claims(entity, "technologies", evidence, usage=True)
    # Specific observed roles take precedence over a broad component stereotype.
    precedence = [
        r for r in ROLE_CHOICES if r not in ("GENERAL_COMPONENT", "DATA_MODEL")
    ] + ["DATA_MODEL", "GENERAL_COMPONENT"]
    role = next((r for r in precedence if r in roles), None)
    choices = ROLE_CHOICES.get(
        role, ("GENERIC_ROW", "GENERIC_MIDRISE", "GENERIC_TOWER", "UNCLASSIFIED_DEPOT")
    )
    if role == "SERVICE" and topology["incoming"] >= 4:
        choices = ("OFFICE_STEPPED", "OFFICE_BAR")
    if role in ("MESSAGE_PRODUCER", "MESSAGE_CONSUMER"):
        if "KAFKA" in technologies:
            choices = ("KAFKA_PORT",)
        elif "RABBITMQ" in technologies:
            choices = ("RABBITMQ_DEPOT",)
    if role == "PERSISTENCE_ADAPTER" and not any(
        "JPA" in t or "ORM" in t or t == "SQLALCHEMY" for t in technologies
    ):
        choices = ("RDB_GRID_WAREHOUSE",)
    identity = choices[int(derive(seed, "footprint"), 16) % len(choices)]
    proof = sorted(roles[role]["evidenceIds"]) if role else []
    return identity, role, proof, technologies


def catalog_world(world, graph):
    evidence = {e["evidenceId"]: e for e in graph["evidence"]}
    entities = {e["id"]: e for e in graph["entities"] if e["kind"] == "FILE"}
    topology = file_topology(graph)
    parcels, profiles = [], {}
    for source in world["parcels"]:
        identity = source["entityId"]
        seed = derive(world["seed"], identity, MASSING_SEED_VERSION)
        selected, role, proof, technologies = select(
            entities[identity], topology[identity], seed, evidence
        )
        recipe = CATALOG[selected]
        specs = grammar(recipe["grammar"])
        # Independent roof/material stream; no geometry changes when UI filters.
        facade_seed = derive(seed, "facade")
        roof_seed = derive(seed, "roof")
        modifiers = []
        if role in ("UI_COMPONENT", "UI_PAGE"):
            for tech in ("REACT", "VUE", "SVELTE"):
                if tech in technologies:
                    modifiers.append(
                        dict(
                            value=tech,
                            style="GLAZED_INTERFACE",
                            evidenceIds=sorted(technologies[tech]["evidenceIds"]),
                        )
                    )
        if selected in ("KAFKA_PORT", "RABBITMQ_DEPOT"):
            tech = "KAFKA" if selected == "KAFKA_PORT" else "RABBITMQ"
            modifiers.append(
                dict(
                    value=tech,
                    style="INLAND_TRANSFER",
                    evidenceIds=sorted(technologies[tech]["evidenceIds"]),
                )
            )
        handedness = int(derive(seed, "footprint"), 16) % 2
        for spec in specs:
            if handedness:
                spec["x"] = q(1 - spec["x"] - spec["width"])
            spec["roofPitch"] = (0.56, 0.64, 0.72)[int(roof_seed, 16) % 3]
            if spec["materialKind"] == 1:
                spec["materialKind"] = (
                    2
                    if any(m["style"] == "GLAZED_INTERFACE" for m in modifiers)
                    else (1, 3)[int(facade_seed, 16) % 2]
                )
        # A bounded roof-plant accent; not a server, container or instance count.
        decks = [
            p
            for p in specs
            if p["primitive"] == "BOX"
            and p["y"] + p["height"] < 0.91
            and p["width"] > 0.3
            and p["depth"] > 0.3
        ]
        if decks and int(derive(seed, "props"), 16) % 2:
            deck = max(decks, key=lambda p: p["width"] * p["depth"])
            specs.append(
                part(
                    deck["x"] + deck["width"] * 0.23,
                    deck["y"] + deck["height"],
                    deck["z"] + deck["depth"] * 0.22,
                    deck["width"] * 0.2,
                    0.04,
                    deck["depth"] * 0.22,
                    material=4,
                )
            )
        profiles[identity] = dict(
            version=VERSION,
            archetypeId=selected,
            family=recipe["family"],
            label={
                "CONFIGURATION": "Configuration workshop",
                "DATA_PROCESSOR": "Data processing center",
            }.get(role, recipe["label"]),
            derived=True,
            verifiedRole=role,
            roleEvidenceIds=proof,
            visualSeed=seed,
            facadeSeed=facade_seed,
            roofSeed=roof_seed,
            incomingFiles=topology[identity]["incoming"],
            outgoingFiles=topology[identity]["outgoing"],
            declarations=topology[identity]["declarations"],
            relationEvidenceIds=topology[identity]["evidenceIds"],
            technologyModifiers=modifiers,
        )
        # A thin legacy parcel must not turn a low shed into a cathedral. Keep
        # original source height as a capacity bound, not a mandatory roof top.
        low_forms = {
            "shed",
            "row",
            "warehouse",
            "sawtooth",
            "pavilions",
            "gallery",
            "terminal",
            "hall",
            "containers",
            "archive",
            "gate",
            "vault",
            "pods",
            "hub",
            "silos",
            "dome",
        }
        budget = (
            min(source["height"], min(source["width"], source["depth"]) * 2)
            if recipe["grammar"] in low_forms
            else source["height"]
        )
        envelope = dict(source, height=budget)
        specs, detail = frontage_details(specs, envelope, recipe["family"])
        profiles[identity]["frontageDetail"] = detail
        parts = compile_parts(envelope, specs)
        profiles[identity]["renderedHeight"] = q(
            max(p["y"] + p["height"] for p in parts)
        )
        parcels.append(dict(source, parts=parts))
    return dict(world, parcels=parcels), profiles


def catalog_compounds(compounds):
    """Restyle already-certified groups; never regroup or invent a landmark."""
    result = []
    for source in compounds:
        model = source["physicalModel"]
        kind = source.get("campusProgram", {}).get("kind")
        chosen = {
            "VALIDATION": "AGGREGATE_COURT",
            "APPLICATION": "MIXED_USE_PODIUM",
            "INTERFACE": "AGGREGATE_COMPLEX",
            "DATA": "AGGREGATE_COURT",
            "COMPUTE": "AGGREGATE_COMPLEX",
            "TOOLING": "AGGREGATE_COURT",
        }.get(kind)
        if chosen is None:
            chosen = (
                "AGGREGATE_COMPLEX"
                if source.get("role", "").startswith("GATE")
                else "AGGREGATE_COURT"
            )
        # Neutral named aggregate when the constituent facts do not prove a
        # research institute, database engine, or business service complex.
        label = "Verification hall" if kind == "VALIDATION" else "Source complex"
        form = (
            "verification"
            if kind == "VALIDATION" or source.get("role") == "TEST"
            else "archive"
            if kind == "DATA"
            else "gallery"
            if kind == "INTERFACE"
            else CATALOG[chosen]["grammar"]
        )
        envelope = dict(model, height=source["height"])
        family = "relational" if kind == "DATA" else "generic"
        specs, detail = frontage_details(grammar(form), envelope, family)
        parts = compile_parts(envelope, specs)
        base = model.get("baseElevation", 0)
        parts = [
            dict(
                p,
                y=q(p["y"] + base),
                **(
                    {
                        "meshFaces": [
                            dict(
                                f,
                                points=[[x, q(y + base), z] for x, y, z in f["points"]],
                            )
                            for f in p["meshFaces"]
                        ]
                    }
                    if "meshFaces" in p
                    else {}
                ),
            )
            for p in parts
        ]
        result.append(
            dict(
                source,
                physicalModel=dict(model, parts=parts),
                architecture=dict(
                    version=VERSION,
                    archetypeId="AGGREGATE_COURT" if kind == "VALIDATION" else chosen,
                    label=label,
                    derived=True,
                    memberCount=len(source["memberEntityIds"]),
                    frontageDetail=detail,
                ),
            )
        )
    return result


def catalog_summary(profiles):
    return dict(
        version=VERSION,
        recipeCount=len(CATALOG),
        primitiveKit=["BOX", "GABLE", "SAWTOOTH", "CHAMFER", "DRUM", "DOME"],
        selectedCounts=dict(
            sorted(Counter(p["archetypeId"] for p in profiles.values()).items())
        ),
        presentationOnly=True,
    )
