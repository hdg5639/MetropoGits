# Current implementation contract baseline

Verified 2026-10-18 against the checked-in producer, schemas, validators, and
accepted ADRs. This document reconciles implementation with the original
`MPG-TECH`, `MPG-FUNC`, and `MPG-PLAN` revision 1.0 design baseline. It does not
introduce a new schema or weaken a requirement.

| Surface | Current producer | Compatibility / authority |
| --- | --- | --- |
| UCG | `ucg/0.1` | [Schema](../../schemas/ucg-0.1.schema.json); file/edge/evidence identities are unchanged |
| City Scene | `city/0.2` | [Schema](../../schemas/city-0.2.schema.json), [ADR-009](../adr/ADR-009.md); `city/0.1` remains readable and validated under its original contract |
| Single-repository layout | `hierarchical-paged/1.14` | [ADR-009](../adr/ADR-009.md), [ADR-010](../adr/ADR-010.md), [ADR-011](../adr/ADR-011.md), [ADR-014](../adr/ADR-014.md); hints require the current supported layout version |
| Opt-in developer layout | `hierarchical-parcel/0.1-experimental` | [ADR-017](../adr/ADR-017.md); single-district measured candidate, not the CLI/Action default; older enum validators need updating |
| Catalog | release `0.4.0`, schema `catalog/0.1` | [Catalog](../../catalog/0.4.0/catalog.json), [path rules](../PATH_SEMANTICS.md) |
| Viewer | browser-native WebGL with 2D fallback | [ADR-002](../adr/ADR-002.md), [ADR-005](../adr/ADR-005.md) amend the original Three.js candidate |
| Static preview | CPU-only deterministic detailed and isometric SVG | `preview.svg` and `showcase.svg`; [ADR-013](../adr/ADR-013.md) and [output guide](../SHOWCASE.md) |

## City v0.2 interpretation

Each district has a required `footprint`: an ordered union of non-overlapping
axis-aligned rectangles. `x`, `z`, `width`, and `depth` describe its exact
bounding box. Sibling bounding boxes can overlap; sibling footprints cannot.
Direct buildings and child footprints must be covered by the parent footprint.

The original technical specification's City v0.1 JSON is a historical example,
not the current producer contract. New consumers must use the versioned
schemas and the polygon rules from ADR-009. Existing v0.1 artifacts keep their
rectangle-based interpretation; do not add footprints without a version change.

Structural street surfaces are derived visual geometry under ADR-010, not UCG
relationships or mandatory `decorations` entries. Evidence-backed networks
retain their exact `edgeIds`. Overview block aggregates are visual projections
under ADR-012, with complete file membership; they are not new City buildings.

[ADR-015](../adr/ADR-015.md) adds evidence-compatible role landmarks to
all interactive LODs: nearby gate or test-file groups become bounded halls,
centers, terminals or campuses. Hover/inspector disclose constituent files and
evidence; only explicit expansion restores originals, not zoom or file selection.
Focus facility and Expand/Collapse are separate. File selection shows its footprint
within the compound and its evidenced aggregate routes. Detail retains a bounded
route budget; All routes explicitly overrides it. Canonical City/UCG, roads and
static SVG outputs are unchanged. CPU showcase role-compound parity is open.

ADR-014 amends DEC-007/ADR-004's hash-only interpretation: evidenced roles and
DIRECT/RESOLVED file dependencies may influence local sites while retaining
directory ownership. Compatible hints take priority over relationship changes.
Internal circulation is reserved before buildings are placed; visual street
surfaces are not communication claims. Layout 1.13 hints are intentionally
incompatible with 1.14; all source identities and UCG facts remain unchanged.

ADR-014's review amendment replaces vacant-cell paving with a presentation-only
segment graph derived from canonical `network.path`. Overlaps share provenance,
crossings define visual junctions, and lane paint/animation use those same paths.
LOD/filter-hidden routes also hide their corridor surfaces. Unknown/no-relation
inputs produce no paved streets. This does not change canonical layout/paths
or schema versions; aggregate route anchors are not per-file doorways.

## Functional scope and open work

ADR-016 supersedes mean-anchor rendering with `visual-access/0.2` derived data
(arrival-direction-aware continuity; see the urban block plan).
Canonical City/UCG and building coordinates remain unchanged; network groups
remain compatibility/inspection records, not the displayed file endpoints.
Viewer, detailed SVG and showcase derive geometry from the same access graph.
Shared segment route IDs resolve to exact UCG edges, never implied cross-product
relationships. Straight runs merge only with identical provenance and width.
District/Detail retain every routed endpoint; Overview suppresses local spurs.
Selection reveals complete incident routes, with a disclosed x-ray trace through
visual occluders. All routes can restore context without highlighting unrelated
branches. Synthetic is a bounded sample (at most 96) of stored complete routes,
not a random walk or measured traffic. Partial routing is disclosed in viewer,
SVG metadata and CLI manifest diagnostics. Java nested imports remain unresolved
work; communication-renderer changes were deferred at maintainer direction.

[ADR-018](../adr/ADR-018.md) adds opt-in `visual-access/0.3` consolidation through
`python -m scripts.road_consolidation <build> --out <new-directory>`. Default
derivation remains 0.2. The command emits before/after packages with identical
canonical UCG/City and fixed building entrances. It reroutes dependencies over
remaining same-kind roads and removes redundant parallel pavement atomically.
The original 100/90 lattice-distance bound is preserved; at most two additional
bends per original route are permitted. Total individual travel can increase
slightly while global paved centerline/parallel overlap cannot increase. All
consumers, selection and synthetic use the consolidated stored paths, not hidden
old lines. Junction surface unification and selective roundabouts are subsequent
work, not delivered by this pass. Inputs with partial routing are rejected.

ADR-017 exposes the measured parcel candidate through `scripts.parcel_viewer`.
Only one selected leaf changes file coordinates; all directory geometry, file
ownership and semantic facts remain intact. Canonical network paths and the
whole-city access graph are recomputed. All three renderers consume the same
scene/routes; incomplete coverage or pavement/building overlap blocks export.
The experimental label and manifest `options.experimental` are explicit, while
manifest status retains its existing COMPLETE/PARTIAL diagnostic meaning.
Existing UCG/City fields, IDs, normal builds and renderer logic are unchanged.

Experimental hints lock X/Z only when directory geometry and file membership,
ownership and footprint dimensions match exactly. Current graph facts win over
old hint evidence. Structural changes require an explicit cold experiment;
incompatible hints fail rather than silently relocate files. This is NOT a claim
that the experiment meets AC-003's file-addition workflow or is ready to replace
the default layout. See [usage and open risks](../URBAN_BLOCK_PLAN.md#opt-in-3d-실험).

JS/TS configured-path resolution reads bounded `tsconfig.json`/`jsconfig.json`
without executing plugins. Exact and single-wildcard `compilerOptions.paths`
use the declared baseUrl (or config directory), longest-prefix matching and
ordered fallbacks, following the [TypeScript reference](https://www.typescriptlang.org/docs/handbook/modules/reference.html#paths).
Only unique already-scanned local sources resolve; IMPORT and CONFIG provenance
are both retained. Nearest-directory config scopes are a conservative subset,
not a full compiler project graph. Strict JSON is supported; JSONC, extends,
package exports and implicit baseUrl-only imports remain unsupported. Invalid
configs block outer aliases and report diagnostics. Aliases with missing,
ambiguous or excluded targets never become invented external dependencies.

P0 FR-001 through FR-016 are mapped to automated evidence in
[`release/readiness.json`](../../release/readiness.json). AC-010 still needs
authorized Pages deployment and an actual repository-subpath check. The public
repository conversion is complete, as recorded in ADR-007's amendment.

P2 FR-021 through FR-023 remain optional and outside initial acceptance even
though implementations exist. Their historical sequencing deviation remains
visible in the [decision audit](../DECISION_AUDIT.md).

The product plan's L1 size/line metrics are not yet implemented in UCG FILE.
Adding them needs an explicit versioned contract decision. Next.js page/route
and test-source PATH rules already exist; future work should assess their
coverage and false positives before adding further rules.

Visual polish remains an open product goal independently of automated
requirement coverage. See the [visual roadmap](../V1_VISUAL_COMPLETION_PLAN.md).
