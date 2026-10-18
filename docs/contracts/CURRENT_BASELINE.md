# Current implementation contract baseline

## Procedural-world experimental addition — 2026-10-19

[ADR-024](../adr/ADR-024.md) introduces a separate
[`world/0.1-experimental`](../../schemas/world-0.1.schema.json) physical document
through `python -m scripts.procedural_world BUILD --out NEW_WORLD`. Its CPU SVG
and existing WebGL/Canvas adapter consume the same polygons, oriented buildings
and exact source-backed trips. Original UCG and City artifacts are retained;
the derived browser `world-view/0.1` projection is not a City schema migration.

This first flat engine uses capacity bisection, rotated frontage grids and
structural collectors, with explicit source-directory mapping and complete edge
accounting. It does not implement Voronoi, relief, water, bridges or every planning
profile. Legacy default output remains authoritative for its existing contract.
See [commands and limits](../URBAN_BLOCK_PLAN.md#2026-10-19--첫-procedural-world-평지-도시-생성).

The browser audit now returns one requested road's complete choices rather than
serializing full trajectories for every visible road. This prevents oversized
inspection payloads on highly shared street graphs; assertions are unchanged.

## Existing City/UCG baseline

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
old lines. Inputs with partial routing are rejected. WebGL joins existing
same-kind junction surfaces inside the original pavement envelope and clips
ordinary markings at approach mouths; exact selection and animation paths
remain complete. Canvas/SVG surfaces and all routing data are unchanged.
An additional opt-in `--junctions` comparison removes short links between nearby
branch nodes when every dependency can reuse surviving crossings. Fixed entrance
ports are excluded; distance/+2 bend bounds stay frozen against original 0.2
routes across BOTH passes. Additional budget: 600 attempts and 2M search states.
The before package is parallel-only 0.3; after is 0.3 with derived
`junctionConsolidation` metadata. No default adoption, node relocation, new
pavement or roundabout implementation is implied.

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

ADR-019 adds derived `road-hierarchy/0.1` presentation alongside access routing in
viewer data, not in UCG or City. Unique edges, endpoint files and cross-major
edges determine fixed access/alley/street/avenue/interdistrict-trunk-demand grades.
Full-road grades survive filtering and single-path selection. Width is capped by
the unchanged certified segment envelope; Inspector exposes counts and clearance
limits. WebGL, Canvas and SVG use the same profiles; older viewer payloads without
profiles retain legacy styling. History frames carry their own routing/profiles.
This is static demand, never measured traffic or a change in relationship kind.
Stored paths, Synthetic trajectories and buildings are unchanged. Continuous
trunk planning, reserved road space, curves and selective roundabouts remain future
stages; grade labels alone do not establish highway geometry.

The developer comparison command now accepts `--avenues`: compare existing
parallel+junction consolidation with bounded reuse of continuous high-demand
straight spines. It implies the earlier passes but keeps every bound frozen from
fresh complete0.2 routing. Optional `avenueConsolidation` metadata (version
`avenue-consolidation/0.1`) records fixed spine paths, attempts, rejected reasons,
reuse and limits in derived0.3. No UCG/City schema, default routing, building or
source-ID changes. All renderers and Synthetic follow the same rebuilt paths.
The pass removes existing roads only; reserved road space/curves remain pending.

`scripts.avenue_reservation <parcel-build> --out <new-directory>` now provides a
separate `avenue-reservation/0.1` opt-in clearance experiment. The existing
`hierarchical-parcel/0.1-experimental` engine can reserve a demand-backed avenue
inside one leaf, move at most eight blocking parcels locally, and certify a
continuous 2.5-unit road. Through-centerlines/ports and provenance are preserved;
only access endpoints and safe widths change. City fields/enums, dimensions,
districts and IDs are unchanged; aggregate network paths follow new coordinates.
Decision and manifest identify the option. Earlier experimental commands and
default build output are unchanged. Optional `--previous-scene` uses the existing
same-structure-only policy; no implicit growth allocator or cold reset is added.
This implements local width reservation, not reserved city-wide trunks or curves.

The separate developer comparison `scripts.road_consolidation --urban` now adds
whole-network corridor consolidation, explicitly approved on 2026-10-18. A
unique-evidence-demand-ranked forest guides reuse; all dependencies on a removed
corridor must receive complete replacements on existing same-kind pavement.
Fixed ports, access, buildings, UCG/City and source IDs remain unchanged. Default
build and previous conservative options remain unchanged; `--backbone` exposes
the same fourth pass with the previous conservative bounds.

Only urban pass four permits max(floor(1.5*N), N+4) through-road steps and four
extra complete-path bends, frozen from original0.2. N excludes access spurs;
four steps equal a 14-unit short-route block allowance. Do not describe this as
an unconditional 50% cap: the short-path exception can exceed that percentage.
`backboneConsolidation.policy` in derived0.3/decision identifies `urban-road/0.1`;
earlier-stage `originalBoundsPreserved` flags describe those stages only. Search
caps and safe atomic rejection remain. No new public schema or invented road.
WebGL, SVG, inspection and Synthetic share the resulting paths. This is removal
and rerouting on an existing orthogonal network, not curved highway/roundabout
geometry or a default replacement for stable directory-first layout.

`scripts.road_consolidation --continuity` compares urban routing with a further
continuous-road cleanup. It first aligns routes on existing roads without adding
length or bends, then reconsiders remaining cycle corridors (including former
forest roads) with atomic rerouting. Each path may use the original urban distance
allowance during deletion, but may not gain bends relative to its current path.
Heading-change cost includes fixed entrance/exit directions. Iterative bridge
detection is refreshed after deletions; indispensable connectors stay intact.
Derived `roadContinuity` metadata uses `road-continuity/0.1` and discloses per-phase
caps, alignment/removal counts and bend totals. Earlier modes/IDs/UCG/City remain
unchanged. This does not create new alignments outside existing pavement or move
access ports; a road-first placement experiment is still a separate decision.

`scripts.road_consolidation --collectors` compares continuity output against
bounded block collector planning. Derived `blockCollectors` (`block-collectors/0.1`)
records accepted ownership blocks, actual terminal counts, retained cross-link
routes and search limits in the existing visual-access/0.3 payload. It can add
obstacle-certified local pavement and reroute complete paths, unlike deletion-only
passes. UCG/City, source IDs, buildings, doors, access spurs and boundary terminals
stay fixed. Original0.2 urban distance and +4-bend bounds apply, not continuity's
stricter per-route bend nonincrease; individual paths can become longer/more bent.
Necessary old cross-links remain, so this is not a mandatory tree topology.
All accepted local proposals strictly reduce total pavement without increasing
junctions or nearby parallel length. Unused candidate roads are never emitted.
Limits: 160 block/kind proposals, three demand-ranked roots each, 4096 lattice
nodes per block, 96 terminals, 2M search expansions, 1M input through steps.
Only directories containing 4–64 files are eligible, smallest first. These are
planning limits, not semantic truncation; rejected blocks keep their old routes.
Defaults/earlier options are unchanged. Curves, moved doors and road-first parcel
placement remain separate work. Prior-stage metrics describe those stages only.

`scripts.road_consolidation --frontage` adds an opt-in comparison against block
collectors. It chooses an existing evidenced local collector before reconnecting
the building's visual entrance; the whole incident-route set changes atomically.
Buildings, districts, canonical UCG/City and source IDs stay fixed. Derived doors
and ports may move to another clear face; this explicitly differs from fixed-port
experiments. New spur length counts inside the original0.2 urban world-distance
budget, with original complete-path bends+4. No compounded allowance or fabricated
edges. `roadFrontage` / `road-frontage/0.1` in visual-access/0.3 records changed
doors, chosen collector, planning-time unique-edge demand, attempts and limits.
Private dead-end length precedes unique demand in candidate ranking. Limits:
600 proposals, 1M popped states, 21-unit local radius, 7-unit ownership margin,
12 approach steps. Mixed-kind or zero-through-route endpoints retain old doors.
Only actual route-used pavement is exported. Preview, viewer, Inspector and
Synthetic consume the same paths; earlier diagnostic blocks describe earlier
passes. This first road-first frontage slice is not a parcel reallocator,
city-wide arterial planner or curved/roundabout implementation. Defaults stay intact.

`scripts.road_consolidation --gateways` compares the frontage result with joint
block-boundary routing. Derived `blockGateways` / `block-gateways/0.1` in
visual-access/0.3 records selected/removed crossings, changed/unchanged routes,
rejections and caps. All doors/buildings/UCG/City/semantic IDs remain fixed.
Existing pavement is preferred; new local connectors require full-width obstacle
clearance and actual complete-route membership. Original0.2 world-distance and
+4-bend bounds include frontage changes; no compounded allowance. Accept only
fewer used crossings and less pavement, with non-increasing total bends,
junctions and nearby parallel length. Necessary old routes remain.
Limits:4–96 files per directory,256 districts,480 patches,240 connected proposals,
1M search states,21-unit grouping distance and28-unit patch radius. This heuristic
does not promise city-wide optimization. `retainedRoutes` means unchanged,
not necessarily rejected or essential. Old options/defaults are unchanged;
preview, Inspector and Synthetic use the same final exact route geometry.

The subsequent joint entrance/gateway study was not promoted: two bounded
candidate rankings each accepted zero proposals in both real cities. There is
no `--joint` product option or additional default pass. Keep `--gateways` as
the current experimental baseline; see ADR-019 and URBAN_BLOCK_PLAN for the
rejected trial, limitations and next parcel-constraint diagnostics.

`scripts.road_consolidation --shared-frontage` now compares gateway routing with
complete-trip entrance planning (`sharedFrontage`, `shared-frontage/0.1`, existing
visual-access/0.3 payload). It moves only derived door/port choices and reroutes
every incident relationship atomically; canonical City/UCG and source IDs stay
fixed. Original0.2 world-distance/+4-bend bounds include new door spurs. Strict
pavement reduction, non-increasing junctions/parallel length and a final total-bend
rollback guard apply. Inherited earlier-stage metadata describes earlier stages.
No `--joint` option, parcel reallocation, semantic inference or default change.
Limits:1600 entrances,4800 proposals,12M states overall,12000 states/60000 labels
per trip,100000 candidate edges,20000 input routes,existing1M expanded-step limit.
Candidate connectors extend at most three obstacle-clear lattice steps from
alternative faces. Only accepted route-used geometry is exported. Search caps
retain the last safe result and are reported, not treated as infeasibility proofs.

Road hierarchy grades and widths are unchanged. Derived `road-hierarchy/0.1`
profiles now also carry optional `shoulder`, `marking`, and `lanePattern`
presentation fields; older profiles retain compatible styling fallbacks.
Dependency AVENUE/TRUNK paint uses world-aligned 1.6-unit dashes every4 units,
trimmed at visible same-kind junction mouths. Narrow roads retain pavement without
center paint. Each segment's paint expansion is capped at513 candidate intervals;
the cap never removes roads, source relations, selection traces or Synthetic paths.
Python SVG and browser renderers share geometry fixtures. Canvas caches paint
with its access frame; WebGL retains static geometry caching. HTTP/messaging
semantic colors and continuous selected-route overlays remain separate.

`scripts.road_consolidation --simplify` explicitly runs the preceding experimental
passes, then compares shared-frontage routing with existing-pavement trip
simplification. Derived `routeSimplification` (`route-simplification/0.1`) records
individual bend/length reductions and atomic corridor removals separately.
Door positions, canonical City/UCG and all source/target/kind/edge identities stay
fixed. First smooth trips without increasing individual length or bends; then
remove redundant corridors only when every affected trip can use remaining
same-kind pavement within original0.2 world-distance/+4-bend bounds and summed
bends do not increase. Removed roads cannot be resurrected. Inspector, Synthetic,
SVG and WebGL use the resulting exact complete paths, not a cosmetic overlay.

Limits: 20,000 routes, 100,000 graph edges, existing 1M expanded-step guard,
3M total states, 6,000 states/30,000 predecessor labels per trip, 1,200 corridor
proposals over at most two rounds. Cost is lattice length +15 per bend; ties and
candidate order are deterministic. Caps preserve safe complete routes and report
truncation; they do not prove no better route exists. No new public schema,
default, curve, roundabout, relation inference or layout-locality guarantee.
Inherited diagnostic blocks describe earlier passes; only `routeSimplification`
describes this additional pass. `searchExpansions` remains initial route-search
work, not total planning cost; use each pass's own search counters.

The simplification report additionally includes `constraints`
(`corridor-constraints/0.1`), without changing any routing geometry or decision.
Counts classify attempted corridor proposals as accepted, `search_cap`,
`no_admissible_trip`, or `total_bend_regression`; skipped connectivity bridges
and already-removed corridors are separate. Counts are proposal events across
rounds, not distinct roads/files. `unsampledRejections` explicitly discloses
omitted diagnostic examples, not omitted relationships.

Keep at most24 samples, the first8 per reason in deterministic search order.
Each sample stores at most64 blocked lattice keys, with full count and explicit
truncation flag. For sampled no-admissible-trip failures, a separate distance-only
probe returns `WITHIN_DISTANCE_BUDGET`, `EXCEEDS_DISTANCE_BUDGET`, `DISCONNECTED`,
or `CAPPED`. A within-distance result does not certify the bend-constrained trip;
an exceeded-distance result supplies a lower bound, not an exact shortest length.
Probe limits are5,000 states per sample/100,000 total, separate from routing
search; unknown/capped never means impossible. Distances are remaining lattice
steps after fixed access spurs, not world units or runtime latency. Samples refer
to the candidate graph at rejection time and are not statistical estimates of
all remaining roads. This is developer metadata, not a semantic UCG fact.

`scripts.road_consolidation --refine-frontage` runs the preceding experimental
pipeline and compares the simplified baseline with a single entrance refinement.
The derived `frontageRefinement` (`frontage-refinement/0.1`) report records seed
route IDs, nearby/eligible/truncated building counts, accepted door changes,
removed pavement lengths, complete incident-trip counts, rejections and budgets.
Prior reports remain historical, including simplification's fixed-door/no-new-
pavement assertions; those assertions describe that earlier pass, not refinement.

Seeds are the bounded no-admissible-trip samples. Up to96 buildings within21
Manhattan world units of their current endpoint doors are considered. Try other
clear faces and at-most-three-step connectors, jointly rerouting every incident
relationship while retaining its identity and original0.2 full-trip bounds.
Mixed-kind and access-only endpoints retain their doors. Only actual used
connectors become pavement. Every accepted proposal strictly reduces union
pavement and does not increase junctions, nearby parallel length or total bends.
Individual trip distances may grow within the original allowance; report their
sum separately. No claim of global optimum or unchanged roads outside the patch:
changed complete trips can reuse existing distant roads.

Search compares turn costs25/150, existing/new steps10/80. Limits:768 proposals,
1M popped states,12000 states/60000 labels per trip,100000 graph edges,20000
routes and1M expanded steps. Caps retain complete valid routes. Repeated input
is deterministic; a refinement result cannot be refined again. Default CLI,
UCG/City schemas, positions and evidence stay unchanged. This remains an explicit
developer comparison rather than a default production pipeline.

### ADR-020 opt-in structural infrastructure (not the default)

`python -m scripts.street_grid BUILD --street-grid --out NEW_DIRECTORY` creates
an original-access/0.2 versus structural-assignment comparison. Public City/UCG,
canonical positions, IDs and normal CLI behavior do not change.

Derived access/0.3 may carry `streetGrid` with version `structural-streets/0.1`,
`semantic:false`, directory/geography basis, safe-width segments, entrances,
block ownership, diagnostics/status and assignment data. Geometry generation
does not read networks or UCG edges. A bounded directory frontier (up to64 files
where hierarchy permits) gets28-unit seed streets, obstacle-clear connectors
and one geometric entrance per building. A directory with more than64 direct
files remains one group;64 is a frontier target, not a hard building cap.

Assignment retains original doors, all relationships and original0.2 trip
length/bend limits. At most4-step connections attach original ports to the
skeleton; these are evidenced access connectors, not extra structural claims.
`assignedRouteIds` and `fallbackRouteIds` partition all routes. Fallback routes
keep their original geometry. Consumers show assigned demand by default, disclose
counts and allow selection/All routes to expose exact fallback paths. Synthetic
follows the same stored paths; it never randomly branches. This is static demand,
not runtime traffic. SVG metadata retains all routes; visible captions disclose
structural meaning and partial assignment.

Caps:10000 buildings,250000 bounding lattice cells,500000 seed steps,2M BFS
states for infrastructure, another2M for original-port connections,20000 routes,
3M route search states (per-trip12000 states/60000 labels), existing1M route
expansion limit. Hard input caps fail; exhausted searches report partial streets
or retain fallback relationships. No default schema/config migration or claim of
incremental street stability. LOD obstacle rectangles stay at the legacy value
for controlled comparisons; new surfaces do not retile aggregate facilities.

Assignment diagnostics are additive under
`diagnosticsVersion: street-assignment-diagnostics/0.1`: `fallbackReasons`
contains one `{routeId, reason}` per fallback, `fallbackReasonCounts` aggregates
them, and `diagnosticSearchStates` reports a separate global1M-state budget.
Optional `latticeStepLimit` and `shortestLatticeSteps` are lattice distances,
not world lengths or traffic. This diagnostic budget cannot change routed trips.

Reasons distinguish `distance_limit`, `joint_constraints`, `missing_access`,
`disconnected_streets`, `access_only`, `no_structural_streets`, and connector,
route or diagnostic search limits. Capped searches mean unknown feasibility;
joint constraints mean a distance-feasible path exists but the combined
bend/simple-path search did not return one, not proven bend-only infeasibility.
Older artifacts lacking reasons display `unrecorded` rather than an invented
diagnosis. The opt-in viewer's Review fallbacks panel respects current endpoint
and network filters, renders at most25 paths per page, and opens exact original
path evidence. Default viewers do not gain this experimental control.

`--aligned-blocks` optionally selects `structural-streets/0.2`, with basis
`aligned-block-boundaries-and-building-geography`. It uses zero half-cell padding
on block seed bounds, preserving the28-world-unit interior line period. A
simultaneous, deterministic nearest-component wavefront retains one link per
geometric wave-neighbor pair. Local alternate circuits are structural, not
source relationships. Infrastructure search remains bounded by2M popped states,
with the existing area/building/seed limits; incomplete exploration is PARTIAL.
Original0.1 mode, City/UCG, canonical positions and original trip doors/budgets
are unchanged. No full incremental stability guarantee for derived streets is
introduced; geometry changes can change wave ownership and connector choices.

### Perspective framing (viewer only)

Initial WebGL fitting solves the perspective-frustum inequalities over the same
district/building/aggregate extent points instead of moving backward around a
fixed world-AABB center. Yaw, pitch, margins, point membership and rendered LOD
are unchanged. The target may translate in X/Z; its ground-relative Y is retained
so zoom never starts with an underground orbit pivot. A1% distance guard remains.
Reset restores this fitted target. This changes neither scene/routing data nor
CPU preview/Canvas projection, and does not crop outlier buildings to enlarge
the city. Subsequent manual camera movement remains user-controlled.

### Structural pavement presentation

For `structural-streets/0.2`, renderer-derived `streets.surfaces` may contain
four X/Z `points` and `segmentId` plus the existing bounding rectangle. All three
renderers consume the points; bounds are not a substitute for the polygon.
This is packaged viewer geometry, not a City/UCG schema field or new relation.
Routing segments retain original clear widths and existing IDs/paths.

On the structural3.5-unit lattice, remove short straight-run width expansions
with two-step erosion/dilation, then constrain full-width growth to0.25 per
world unit. End neighborhoods truncate; door stubs do not constrain trunk
width. Polygons remain subsets of previous clearance rectangles. Sampling is
capped at500000 with an explicit error, not silent street truncation.
Equal-slope pieces coalesce; order is deterministic. Legacy structural0.1 and
normal nonexperimental output retain their prior form.

`streetDemand` (`street-demand-surfaces/0.1`) is optional renderer data for the
aligned experiment. Its segment-ID-keyed polygons intersect each dependency
segment's demand/clearance cap with collinear structural pavement. Perpendicular
crossings do not count as coverage. Uncovered intervals remain intact at their
original certified width; HTTP/messaging retain their category geometry.
No path, identity, source/destination, grade or assignment changes. Inspector
separates physical width range from demand cap/target. Paint clips to sufficiently
wide pieces and junction fills cannot enlarge the resulting envelope. All
renderers use the same polygons; the500000-piece cap fails explicitly.

### Experimental city context

Aligned structural0.2 output optionally packages `cityContext` version
`city-context/0.1`: neutral `ground` and ordered `majorColors` presentation
values, not UCG/City facts. WebGL/Canvas initially suppress minor directory
outlines, civic curbs and minor labels. Major identities and selected district
context remain; district picking, buildings, aggregates and route membership
are unchanged. Structure overlay restores full context and participates in
static geometry cache invalidation, not per-frame Synthetic work.

CPU showcase uses the same palette and removes decorative plot outlines.
Accessible preview deliberately retains its detailed structural-diagram style.
Neither changes canonical position/shape, road paths or evidence. Default and
structural0.1 viewers do not gain this experimental toggle or styling.

### Opt-in curved streets

`scripts.street_grid --curved-streets` requires aligned structural0.2. Optional
derived `routing.curvePlan` version `street-curves/0.1` contains geography-only
degree-two bend supports (`point`, `radius`, `direction`). It does not rewrite
canonical City/UCG or original route records. Viewer-only `streetCurves` has
sampled paths keyed by unchanged segment ID and original paint-width pieces.
Routes follow these paths in their original direction, including reverse trips.
All scene/relationship IDs and endpoint provenance remain intact.

Support squares are building-free, disjoint and bounded by half the approach to
the next structural branch/turn. The common quadratic map is identity outside
them. Surfaces are subdivided before mapping; round corner joins remain inside
the certified empty support. Source selection, picking, highlight and Synthetic
consume the same mapped centerlines. CPU SVG maps pavement and paint as well.
Planning caps500000 nodes/5M clearance checks; presentation caps500000 pieces.
Limits raise an error rather than silently omitting paths. Legacy/default modes
are unchanged. This version does not reroute a staircase chain or create rotaries.
