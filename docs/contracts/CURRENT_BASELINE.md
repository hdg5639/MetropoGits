# Current implementation contract baseline

## Physical urban land and modern massing — 2026-10-22

[ADR-066](../adr/ADR-066.md) adds opt-in building style `urban` with
urban-land/0.1 and urban-architecture/0.1. Derived world-view/0.3 explicitly
permits admitted physical envelopes different from original source addresses.
Canonical UCG/City/World/Planning schemas, IDs, dimensions and their existing
strict validators are unchanged. Exact source front doors, yaw, owners, paths,
road mesh and certified campus models remain; admitted body centers/dimensions
are disclosed separately. Full-area requests or equal-area alternatives precede
compilation; unavailable capacity is DEFERRED_REPLAN, not silent downsizing.
Independent admission reconstruction and collision checks precede shared CPU/
WebGL compilation. New urban-land.json and manifest/inspectors retain evidence
and both envelopes. Other modes/old saved artifacts remain compatible. This
first vacant-reserve admission is not completed general land/master planning.

## Continuous district height allocation — 2026-10-22

[ADR-065](../adr/ADR-065.md): catalog0.5 adds district-skyline/0.1 and
height-allocation/0.1. Form/footprint capacity remains physical-height/0.1;
actual compiled height uses a continuous district field within it. No legacy10
recap, universal maximum, per-file fan-in height or new HQ claim. Add
skyline-plan.json and compact inspector data; independently validate allocation
and all parts/mesh vertices. Canonical schemas/geography/relationships and
certified campus models remain unchanged. World-view0.2 already describes
architectural height; other modes and saved old artifacts retain their meaning.
The field composes existing land; distinct master plans/variable land admission
remain explicitly pending, not silently claimed from this migration consumer.

## Source-first urban character — 2026-10-22

[ADR-064](../adr/ADR-064.md) adds `urban-character/0.1` repository/district/zone
profiles and `spatial-demand/0.1` relative unallocated demand. Catalog exports
include checksum-covered `urban-character.json`. Facts retain exact source,
edge and evidence IDs; derived typology preferences are not constructed urban
plans. No canonical schemas, IDs, geography, physical meshes or existing modes
change in this slice. It is a dependency of the mandatory redesign, not its
visual completion.

## Architectural height separation — 2026-10-22

[ADR-063](../adr/ADR-063.md), explicitly requested by the maintainer, removes
legacy source height10 as a catalog architectural ceiling. Catalog0.4 uses
physical-height/0.1 form/footprint capacities and independently checks compiled
parts/mesh vertices and unchanged ground geography. Derived world-view/0.2
models distinguish architectural `height` from legacy `sourceHeight`; canonical
UCG/City/World/Planning bytes and their old size validators remain unchanged.
CPU and WebGL consume the same new geometry. The inspector and manifest disclose
the policy. There is no universal replacement height cap and no import-count
height assignment. Reference-skyline0.1 massing is retired from catalog0.4;
old artifacts/modes retain their meaning. Full urban redesign is tracked in
[the execution ledger](../URBAN_REDESIGN_EXECUTION.md), not claimed complete here.

## Cold-start campus bootstrap — 2026-10-22

[ADR-062](../adr/ADR-062.md) adds explicit `--campus-bootstrap` for precinct
initial generation without a previous World. One private geography/capacity
prepass stops before dependency routing and export; final ordinary generation
uses its transient layout hint and retains all existing validation gates.
The internal PlanningFrame is not a valid/publishable World. Diagnostics disclose
campus-bootstrap/0.1 and internal—not cached—provenance. No public schema/ID
changes. Bootstrap and supplied previous-world hints are mutually exclusive;
all previous defaults/styles remain available unchanged. Extra planning cost
and infeasible-campus fallback remain explicit.

## Program-led precinct reservations — 2026-10-22

[ADR-061](../adr/ADR-061.md) adds opt-in `--campus-style precinct` with
campus-plan/0.9. Source-derived physical demand reserves a sufficiently large
existing sector before arterial subdivision. Internal structural spans divert
onto a shared perimeter while outside endpoints, nature and sector/district
polygons remain. The adaptive pattern records campus-reservation/0.1; independent
reconstruction verifies its exact demand, reservation and street identity.

Typed facility sites keep their0.8 representation. UCG/City and source dimensions
are unchanged. Existing campus styles remain supported; unreserved parents keep
their programmed campus. Compatible explicit previous-world migration reuses
baseline geography while reconstructing circulation and exact dependency trips.
All original evidence/capacity/terrain/overlap/access checks remain mandatory.
This is not universal individual footprint scaling or forced city-wide growth.

## Source-affinity campus estates — 2026-10-21

[ADR-060](../adr/ADR-060.md) adds opt-in campus-plan/0.8 via
`--campus-style estate`, with typed variable multi-address facility sites and
explicit constituent assignments. Requirements precede local subdivision;
certified complexes, not individual8x8 source addresses, provide their visible
architecture. Static shared LOCAL targets are disclosed affinity, never new
peer/runtime relationships. Retain UCG/City IDs, roles, evidence and dimensions.

World/Planning schema extensions accept the new style while retaining all old
versions and existing size, capacity, overlap, ownership and source checks.
Independent planner reconstruction validates reservations and member placement.
Program area pressure is recorded; forced terrain expansion/general variable
individual footprints are not delivered. Failed optional layouts disclose
retained programmed morphology/style. See
[Architectural scale plan](../ARCHITECTURAL_SCALE_PLAN.md) for exact staged scope.

## Open river landscape and conditional mountain passes — 2026-10-19

[ADR-039](../adr/ADR-039.md) adds opt-in `river-landscape`, terrain/0.4 and
terrain-adaptive/0.4. Canonical City/UCG and all existing generator versions are
unchanged. The older bounded river/valley prototypes retain their original meaning.

Before streets/parcels, extend the same main river's end cross sections beyond
the bounded urban repair domain and connect one narrower tributary. No terminal
pools. Fixed topology has11 main stations,3 tributary stations and12 convex water
reaches. The shared height field includes both water paths. Only open water
reserves may extend beyond the urban envelope; independent validation checks
that both main ends and the stream end stay outside, not trapped in a larger city.
Renderers clip one shared natural mesh to the final boundary; this is not water
regeneration after urban placement. Bank streets are clipped to current land.

One elongated protected ridge is selected where the initial envelope allows it.
It is procedural natural terrain, not an inferred code role. Up to one tunnel
candidate joins existing mountain contour roads. After ordinary streets are
routed, retain a mountain crossing only if an actual source-backed shortest
trip uses it. No traffic is created to justify a tunnel; unsupported/no-edge
input does not construct one. Complete spans, widths, cover, water exclusion,
height profiles and exact logical endpoints/edge IDs are independently checked.

The slope-aware road/picking/animation profile follows the base terrain under
the ridge. A genuine passage prism is subtracted from the ridge surface; open
portal lintels and interior lining share CPU/WebGL/Canvas geometry. Selected
paths remain complete x-ray traces; ordinary cars are occluded by the mountain.
The inspector discloses the structural tunnel separately from evidence records.

New-mode clipping seams within0.0005 units are joined deterministically while
source entrance/frontage and certified crossing anchors remain pinned. This
repairs quantization cracks, not merging unrelated streets. One actual vacant
address per new district is required for practical hinted growth. Version
changes may still reallocate the city; land cost must be reported, not hidden.

Bounds:24 features,4 crossings,1 tunnel candidate,2M shore/junction work and
50k raw junction roads, plus prior terrain/mesh/route/parcel/repair limits.
Mountain height is capped at35 procedural units. Sparse land may have no ridge
or tunnel. General watershed hydrology, curved civil-engineering tunnels,
steep switchbacks and arbitrary mountain chains are not implemented.

## Graded valley, shared street profiles and foundations — 2026-10-19

[ADR-038](../adr/ADR-038.md) adds opt-in `river-valley`, terrain/0.3 and
terrain-adaptive/0.3. Existing flat/lake/river versions and source City/UCG
contracts/IDs remain unchanged. World/planning enums expand compatibly.

Before urban supply, persist one global surface-field/0.1 (seed,16-unit lattice,
bounded amplitude/rise length and flat valley radius). Lattice vertex samples
are deterministic world-space values; a fixed triangular interpolation defines
all intervening heights. This is coherent gentle upland relief, not simulated
watershed drainage. Initial water/crossings remain fixed during urban repairs.
If the original river template is geometrically infeasible, at most3 additional
seeded templates are tried BEFORE allocation; `elevation.waterAttempt` discloses
this. Work-budget exhaustion is not retried. Old river0.2 behavior stays intact.

Complete candidate lots with relief>1 or excessive predicted driveway grades
are rejected before source assignment. Every source still gets a real lot,
level `baseElevation` and `foundationLow`; original dimensions/roles/evidence
remain intact. Exact lattice-clipped footprint extrema determine the pad, and
foundation walls split at lattice breakpoints to contact actual ground.

Each physical street carries `heights` and an exact `heightProfile` of X/Z/Y
breakpoints. Ground roads follow the same field; certified bridges retain their
own fixed profiles. Doorways meet pad height and street connections meet ground
height. Grades are limited to0.16 on roads and0.20 on short accesses. Physical
3D lengths inform routing without changing exact logical endpoints/edge IDs.
Validators independently recompute full profiles, foundations, joint heights
and the derived surface mesh; labels alone never authorize a different height.

World `surface/0.1` records the final envelope's shared explicit ground mesh and
height grid. This mesh is derived after land repair from the original field,
not terrain rerolling. CPU/WebGL/Canvas share tessellated pavement, foundations,
raised full source meshes, planting and natural-feature geometry. Picking,
camera framing/focus, labels, LOD masses and Synthetic use the same heights.
The source inspector separates procedural ground/pad height from source height.
Aggregate plinths extend down into terrain instead of floating above it.

Caps:16,384 surface cells,65,536 faces,256 points per road profile,150,000 total
profile points and100,000 candidate lots; prior planning/routing/terrain limits
remain. Hinted edits reuse immutable field/terrain and compatible complete frames.
Switching preset intentionally changes geography and is not a small-edit claim.
Steep engineering, tunnels, drainage and remaining density/material work stay open.

## Connected water and physical crossings — 2026-10-19

[ADR-037](../adr/ADR-037.md) adds opt-in `--terrain river-corridor`, generator
`terrain-adaptive/0.2`, with terrain/0.2. Flat and lake-district/terrain0.1 are
unchanged; compatible enum/optional-field additions only in experimental World
and planning0.5. Source City/UCG versions and bytes stay intact.

Before source assignment, generate one seeded continuous nine-station channel,
eight convex reaches sharing cross-sections, two terminal pools and feasible
protected hills. Persist the original envelope, channel and fixed crossing
profiles. Adjacent masks form one protected union; exposed bank edges are
shared physical streets, never separate road rings around water tiles. Maximum
three transverse bridges, with one/two for smaller demand envelopes. Capacity
repairs may change urban land but cannot reroll that initial water geography.

The first river is an analytical connected corridor with a level water surface,
not a height-field drainage solver. Buildable plains remain flat. Graded terrain,
watershed hydrology, coastlines and tunnels remain future W-19 work.

Crossings contain path/height profiles,4.5-unit physical widths, ground-level
abutments and approach grades at most0.16. Ordinary roads and whole source lots
cannot enter protected water/slopes. Certified bridge pieces carry `bridgeId`
and per-endpoint `heights` after atomization; validators independently regenerate
terrain and check full spans, grades, endpoint-height continuity and route/physical
profile identity. Labels alone are not water-crossing permits. Shared bridges
remain structural infrastructure even with zero evidenced traffic.

The derived viewer adapter carries matching per-vertex pavement heights and
structural fascia/parapet faces. CPU/WebGL/Canvas use these geometry profiles.
Picking, route overlays, markings and forward/reverse Synthetic interpolate the
same physical heights without changing XZ source paths or inventing destinations.
The inspector exposes a selected bridge's structural identity and endpoint heights.
Geometry is static-batched; Synthetic retains its separate dynamic buffer.

Caps:24 terrain features (currently8 reaches+2 pools+up to3 hills),9 channel
stations,3 crossings,2M bank-union clipping work; existing24k adapted-road,
2M per-plan clipping/projection,50k atomic-piece and bounded repair/routing caps
apply. Different presets reject geography hints; compatible river hints preserve
terrain and complete frames in the maintained one-file-addition fixture.

## Terrain before urban placement — 2026-10-19

[ADR-036](../adr/ADR-036.md) adds explicit `--terrain lake-district` to adaptive
neighborhood generation. It records `terrain-adaptive/0.1` and a `terrain/0.1`
payload in experimental World, not a replacement UCG/City contract. World and
planning0.5 enums expand compatibly; flat defaults and old artifacts remain valid.

Order is demand-sized envelope → shared natural reserves → district allocation
→ terrain-adapted street/slot supply → source assignment → exact trip routing
→ planting. Terrain generation receives only initial land and stable world seed,
never buildings, streets, roles or leftover space. Up to2 closed lakes and3 hills
are selected in28 bounded candidates; all footprints/height faces are shared
across districts. Very sparse worlds reserve at least4000 area units for an
actual feature/access before planning. This is not a minimum for old flat worlds.

Natural protected polygons plus road setbacks exclude complete parcels. Affected
roads are clipped and reconnected to common shoreline/contour infrastructure,
not drawn across water. Adapted supply is cleared before population; insufficient
capacity uses existing bounded repair/repartition/envelope growth. Terrain stays
fixed throughout repair. Original semantic neighborhoods, core/support members,
roles, edge IDs and endpoints remain unchanged, although positions can change.

Flat→natural is an explicit geography migration, not a small edit: pinned OJ679/
681 and GJ1324/1324 buildings move. Area increases about4.4%/13.4%; PocketBase
retains its outer area, SQLite grows31.1%. Do not call all of that expansion
efficient density improvement. Natural→natural compatible hints preserve the
terrain and existing complete frames on the maintained one-file-addition test.
Flat hints are explicitly rejected rather than forcing nature into leftover gaps.

World/CPU/WebGL/Canvas use the same real terrain faces; nature has no source
entity or inferred dependency. Administrative lines are hidden by default in
natural mode so a cut through a lake is not mistaken for pavement; selection and
Structure restore the original boundaries. Picking/member/source data stay intact.
Planting is last and excludes protected water/slopes and actual roads/entrances.

Caps:5 features,16 footprint vertices,64 faces/feature,24k adapted roads and2M
clipping/portal work; inherited candidate/index/repair/routing limits still apply.
Exhaustion is explicit, never an omitted building or invented relationship.
The first mode uses **flat buildable plains** and protected low-poly relief/closed
lakes. It does not implement continuous city-wide grading, drainage-derived
rivers, bridges, tunnels or coastlines; those parts of W-19 remain open.

## Opt-in sparse frontage alleys — 2026-10-19

[ADR-035](../adr/ADR-035.md) adds `--street-policy permeable` for adaptive
neighborhoods, generator `flat-adaptive-neighborhoods/0.5`. It first applies
shared0.4, then adds rare narrow physical cross-links through existing lot gaps.
Original0.3/shared0.4 bytes and defaults remain unchanged; all three share
compatible geography hints. City/UCG/planning and all source IDs remain intact.

A candidate needs at least6 locally aligned buildings spanning54 units, with
at least2 on either side. Alignment tolerance10 degrees/1.2 lateral units;
gap spacing9–30. Corridors are1.6 wide,10–44 long, stay in their principal
district, clear whole parcels/driveways with0.2 side allowance, and join
existing non-driveway roads at both ends. Avoid existing nearby junctions and
short cross-street alternatives (at most max(1.65*length,length+16)).
At least58 units separate accepted centers; at most1 per neighborhood below
160 files,2 for larger ones,24 globally. These are visual planning rules, not
evidence or runtime volume. Stable source IDs order candidate gaps.

Caps:6000 candidates,200k spatial entries,500k geometry checks,100k shortest-path
states. Exhaustion retains certified cuts only. Atomize the actual junctions
and rebuild original source trips; identity loss, routing errors or a trip
increase above0.003 units rolls back additions. Structural alleys without source
trips carry no invented animation. Landscaping is regenerated around real cuts.
Validation independently checks full-width pavement, source row membership,
principal containment, whole-parcel clearance and existing entrance access.

Pinned GJ/PocketBase each gain2 alleys (53.63/50.84 total units). OJ/SQLite
gain none: no eligible safe candidate, not a forced quota. All3175 whole frames,
parent patterns and mixed neighborhoods are unchanged. GJ31 original trips
shorten; an actually inspected path goes192.12→70.48. Extra atomic road pieces
also split existing segments at junctions; they are not extra independent roads.
Same-camera real close-ups: `artifacts/visual/sparse-alleys-focus-r1/index.html`.
This is restrained local permeability, not a global density or terrain redesign.

## Opt-in shared junctions — 2026-10-19

[ADR-034](../adr/ADR-034.md) adds `scripts.procedural_world --street-policy shared`
only with `--zoning neighborhoods --pattern-scale adaptive`. The default remains
`original`/adaptive0.3. The shared variant records
`flat-adaptive-neighborhoods/0.4`; it retains adaptive-patterns/0.3,
functional-neighborhoods/0.1 and planning0.5. Only the experimental World's
generator enum expands; City/UCG/source IDs are unchanged.

After unchanged lot planning and original seam cleanup, preserve every parent
main/orbital piece, principal boundary, driveway and actual tangent frontage.
Consider complete nonprotected chains between existing junctions, up to120 units.
Delete only when a bounded existing alternate traverses reserved or busy shared
infrastructure. Require real reuse after loop erasure, not a ceremonial loop to
an artery. No pavement/node/building is added or moved. Rebuild exact routes on
the retained graph; source/target/kind/edge/network identities remain exact.

Each affected full trip is charged against its ORIGINAL length: at most
max(1.5*original, original+12 units), not repeated increases from its last detour.
Local replacement is capped by min(1.5*chain+8, chain+32), inside a16-unit search
padding. If any trip fails, reject the chain. If final source identity/budget
checks or routing fail, retain the certified original streets/routes and record
fallback. No route-free traffic/semantics are invented for unsupported input.

Caps:500k index entries/reservation checks,768 candidate attempts,500k search
states and2M cumulative trip-index/update work. Budget exhaustion retains already
certified changes only and is explicit. Old original/adaptive0.3 and shared0.4
may exchange geographic hints; older0.1/0.2 geography remains incompatible.
All12 legacy default/block/district snapshots stay unchanged.

Controlled `shared-junctions-r1` comparisons retain all3175 complete building
frames, parent/district land and planning bytes. Removed physical pieces:
OJ32/GJ62/PocketBase21/SQLite3. Actual rerouted trips:OJ89/GJ211/PB0/SQLite0;
maximum changed-trip increases8.76%/10.15% for OJ/GJ. Overall pavement reduction
is only1.61%/1.25%: this is functional consolidation and local cleanup, not a
claim of a transformed city. Real same-camera changed-region and exact-trip
pointer captures: `shared-junctions-focus-r1/index.html`.

## Continuous district fabric and flat landscaping — 2026-10-19

[ADR-033](../adr/ADR-033.md) adds a presentation-only `landscape/0.1` artifact
to adaptive World packages. Existing World/City/UCG/planning bytes, parcel
frames, physical streets, source roles/membership and exact trips are unchanged.
Other World modes retain their former presentation. The local Python packaging
API accepts `landscaping=False` for a same-world ablation; Structure overlay hides
the decorative layer in the viewer. This is not elevation/hydrology or a new
City archetype. No additional runtime package or network service is required.

`landscape.json` and the derived adapter's `landscape` hold `decorative:true`,
`terrainPreset:"flat"`, green `patches`, explicit low-poly tree `faces`, and
bounded-work diagnostics. CPU SVG/WebGL/Canvas consume this same geometry.
No source entity/edge is created for scenery. Parent districts provide continuous
ground materials; administrative neighborhoods remain exact selectable polygons
and inspectable memberships, not individually colored solid floor plates.

Planting follows one seeded smooth world-space field, clipped by parent land
and subtracted against buffered whole parcels, full-width streets/driveways
including their end caps, and junction clearance. Rounded polygons retain a
conservative margin. Trees fit fully in retained patches and avoid each other.
Caps:16k candidates,250k index entries,2M broad/500k narrow checks,64 temporary
pieces per candidate,12k output patches and900 trees. On incomplete indexing,
emit no planting; on later budget exhaustion, retain only already-certified
pieces and report the reason. These limits never truncate source facts.

Real four-repository before/after outputs are `district-fabric-reviewed-r1`,
with actual WebGL comparisons in `district-fabric-focus-r1`. Patches/trees:
OJ2320/538, GJ2815/645, PocketBase1468/319, SQLite1191/210; no budget exhausted.
Repeated packages match and unchanged physical worlds need no hint migration.
More geometry and larger packages are a real presentation cost; cached Synthetic
builds stay0. Crowded pattern intersections remain open, not solved by planting.

## Mixed functional neighborhoods and adaptive patterns — 2026-10-19

[ADR-032](../adr/ADR-032.md) adds `--pattern-scale adaptive` with neighborhoods,
`flat-adaptive-neighborhoods/0.3`, `functional-neighborhoods/0.1`,
`adaptive-patterns/0.3` and [planning0.5](../../schemas/planning-0.5.schema.json).
The earlier block/district modes remain reproducible ablations, not accepted
visual baselines. Original City/UCG and source IDs/roles/evidence stay intact.

Within immutable source-owned principal districts, deterministic strongest-link
region growth uses actual DIRECT/RESOLVED file/symbol dependency pairs, excludes
CONTAINS/DECLARES, and caps the same import/reference weights at4. Target112
files, at most7regions per principal, 500k queue pops; pack a final under24-file
fragment structurally rather than create a tiny wedge. Disconnected files may
share a structural administrative neighborhood: this does not claim a new edge,
runtime service or fully connected community. `growthRestarts` records that
planning work, not a measured count of runtime components.

Original verified roles define the region's actual mixed `coreClaims` and
`roleCounts`, never exclusive category bins. Unknown direct neighbors retain
supporting edge IDs; other structural members are listed separately. All actual
internal edge IDs remain inspectable. Source reconstruction rejects fabricated
members/role counts/edges; relation locality is measured on real cross-role
pairs rather than an invented target color mix.

Reserve connecting collectors/spokes/spines AND selected shape-bearing orbital
families from the parent grammar first. Uniform0.2 removal of all orbital families
was rejected for OJ: fewer road meters did not justify a monotonous city and288
relocated buildings. Avoid a second parent linear frontage lattice across an
adapted neighborhood, but never mistake a characteristic ring for such waste. The bounded
no-artery fallback retains the former sparse selection. Keep the largest
source-anchored neighborhood on its full original local field; select other
local grammars from actual roles and neutral base-pattern
context. Select local tangent axes from the original sparse reference field,
separately from physical thinning, so removing a corridor cannot rotate an
entire neighborhood. Unused original
full-stencil roads are not overlaid under replacements. Adapted local grids do
not add redundant automatic cross-collectors beside the reserved shared network.
Actual shared cuts/access ports favor cross-neighborhood source affinity; only
the selected boundary subtree is paved, not every administrative boundary.

Before placing files, filter vacant frontage against the complete reserved
road plan, including neighboring approaches and port connectors. Validation
independently checks source groups, profile/frame inheritance, full-width road
coverage, source dimensions, parcel ownership, collisions and exact trips.
Plans cap100k candidates/20k raw roads, 1M index entries/5M clearance checks per
filter; existing5parent/4local capacity attempts remain explicit. Fail on limits
or infeasible capacity rather than drop files or silently substitute a grammar.

Compatible hints pin existing addresses while groups/capacity still fit. This
is bounded graph-aware experimental planning, not unrestricted force layout or
universal cold-edit stability: changes near batch boundaries/major graph edits
may change derived groups and require replanning. Administrative development
sectors are not yet extracted enclosed road faces. Terrain, materials, source
metrics and detailed semantic landmarks remain separate work. Growing land and
road count must be reported, not hidden by cross-role co-location improvements.

The seam correction is an explicit generator revision, not old geography
stability: address seed namespaces/source IDs remain unchanged but smaller land
and changed reservations can relocate buildings and physical trips. Old
adaptive0.1/0.2 exports still validate against their original reservation policy;
their hints are explicitly rejected for a cold0.3 rebuild. Experimental schema
version enums expand compatibly; original fields and City/UCG remain unchanged.
Invalid quantized child supporting edges trigger a tiny shared-cut demand repair
within the existing four local attempts, then bounded parent repair as needed.
Keep the same strict containment/clearance checks and retain repair diagnostics.
If capacity AND quantization fail during one local attempt sequence, retain the
normal capacity repair; only exclusively quantization failures use tiny parent
adjustments. The former last-error classification could unnecessarily reshape
all land even when the final valid baseline already fit.

After placement and exact routing, stitch only UNUSED, nonreserved nearby
parallel street pieces. Protect main patterns, principal boundaries, entrances,
driveways and every physical segment used by a source trip. Require an existing
alternate path through a corridor within8 units/15 degrees; cap its length at
min(1.5 times the removed piece plus8, original length plus24). This changes no
source trip/path, building or road coordinate and adds no pavement. Optional
cleanup caps500k index entries,200k comparisons,256 attempts and100k search states;
budget exhaustion retains remaining certified geometry and is disclosed. A small
removal count is acceptable; do not increase it by flattening patterns again.

## Inherited district street patterns — 2026-10-19

[ADR-031](../adr/ADR-031.md) adds `--pattern-scale district` when using
`--zoning neighborhoods`. Existing default `block` output is unchanged. The
new `flat-neighborhood-patterns/0.1` World explicitly records `patternScale`
and `zoning.districtPatterns` (`district-patterns/0.1`); derived planning data
uses [`planning/0.4-experimental`](../../schemas/planning-0.4.schema.json).
Canonical City/UCG, role/evidence claims and source IDs are unchanged.

Reserve a complete parent street field from the requested existing grammar
before source-file assignment. Curves, orbital hub, axes, sampling phase and
HYBRID regions are shared across physical semantic subdivisions. Entire lots
inherit those addresses/tangents; neither the street planner nor GRID fallback
restarts inside each neighborhood. Measured frontage supply guides up to six
neighborhood allocation attempts and the existing five bounded parent repairs.
Insufficient capacity fails explicitly. Subdivision work is capped at5M checks.

Every core and actual dependency-linked helper remains in its real neighborhood,
not merely a reference list. One inherited development sector per neighborhood
is an administrative subdivision, **not** a claimed closed road block. Do not
pave those borders automatically. Exact source-target pairs route on the same
reserved field in CPU/Canvas/WebGL; selection and Synthetic retain original IDs.
Validators reconstruct fields and exact parcel frames, independent of labels.
Hint reuse requires the same pattern scale/version; a scale change cold-replans
and reports the incompatibility. Matching hints pin old addresses when they fit.

This is pattern preservation, not completion of local road-face extraction,
mixed verified-role communities, material separation, density, LOD or terrain.
The five-profile fixture atlas explicitly requests each grammar; a real seeded
city is not forced to contain all five. The current four-repository comparison
is `artifacts/visual/inherited-patterns-r3/index.html`. Whole-city fitted image
scale differs as land requirements change; see the browser common-scale views.

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

## Radial world planning addition — 2026-10-19

ADR-025 adds opt-in `--planning mixed|radial|grid` to the World command.
`flat-planning/0.2` records non-default `planningPolicy` and per-zone GRID/RADIAL
profiles; old `flat-capacity/0.1` worlds remain valid. Default GRID world bytes
are unchanged. The extension is additive to the experimental World schema,
not a City/UCG migration. Radial geometry, doors and source-backed trips share
the same physical street graph in browser and CPU output. Mixed policy emits
explicit local GRID fallback diagnostics when orbital frontage lacks capacity.
Compatible hints preserve profile/slot choices; a policy change cold-replans.
Independent validation now also rejects overlapping parcels and building
envelopes outside their own parcels. See [ADR-025](../adr/ADR-025.md).

## Remaining planning grammars and outlines — 2026-10-19

[ADR-026](../adr/ADR-026.md) implements ORGANIC, INDUSTRIAL and within-district
HYBRID in `flat-planning/0.3`. `--planning varied` selects all five grammars,
with explicit local capacity fallback; existing `mixed` remains a two-grammar
policy. Hybrid region polygons and parcel region IDs are independently validated.
Industrial lots reserve additional land without changing source building sizes.

[ADR-027](../adr/ADR-027.md) adds `--outline varied`, independently derived
`seeded-convex/1` silhouettes and additive `flat-world/0.4` metadata. Existing
ellipse/default GRID worlds reproduce their original bytes. This is convex
connected land only, not a terrain/coastline or concave polygon implementation.
Original UCG/City contracts and browser source inspection remain unchanged.

## Source-core neighborhoods and road-cut blocks — 2026-10-19

[ADR-030](../adr/ADR-030.md) adds `--zoning neighborhoods`,
`flat-neighborhoods/0.1`, `neighborhoods/0.1` and the separately versioned
[`planning/0.3-experimental`](../../schemas/planning-0.3.schema.json) projection.
This is an additive developer experiment, not a City/UCG migration, default
change or claim that the full hierarchical proposal is complete.

Core source files stay inside their real neighborhood polygons. Existing
unclassified files may join only with DIRECT/RESOLVED source-core links:
pair weight at least2, strictly more than1.5 times the next neighborhood's
score, and at most half as many supporting files as core files. These are
documented planning heuristics, not probabilities or a required mixing quota.
Each attachment preserves exact `coreEdgeIds`; original per-file roles never
change. Ambiguous/verified tiny roles and unconnected files remain mixed.

Dependency-local batches target64 files, balanced to avoid a tiny last batch.
Stable source anchors determine block IDs. Convex capacity cuts and a shared
access backbone are computed before local frontage/meshes. Zone adjacency uses
distance divided by `1 + log1p(sourceAffinity)` to prefer real cross-neighborhood
connections, without creating dependencies. Selected boundary subtrees/ports,
not every semantic border, connect neighborhoods. A fixed GRID capacity
certificate governs upstream repair; local grammar failure falls back on that
same block. The entire GJ all-GRID ablation changes452 local building frames
without changing its envelope, block polygons or reserved main-road digest.

`zoning.blocks` stores actual polygons, exact members, capacity, requested/actual
grammar, hybrid subregions and affinity measurements; `zoning.mainRoads` stores
reserved structural segments. `ROAD_CUT` versus `NEIGHBORHOOD_BOUNDARY` explicitly
distinguishes physical cuts from outer/administrative land boundaries. These
are road-cut development blocks, not arbitrary fully road-enclosed planar faces.
Both renderers expose core/supporting counts, local block IDs/plans and exact
supporting edges. Main/context ground and CPU geometry use the same World.

Bounds: existing10000 files/64 principal districts/448 neighborhoods; per-parent
256 blocks,1024 persisted blocks overall,5M boundary/coverage checks,2M spatial
entries,10k-unit extent guard. Existing bounded power/three local repairs/five
parent attempts remain; a quantized convexity failure gets a disclosed0.2%
local demand retry, not a relaxed validator. Compatible hints preserve old
neighborhood/block anchors and full file frames when capacity fits; any local
capacity/membership replan is diagnosed. Existing default World bytes match all
four fixed corpus baselines. Cold opt-in geography intentionally changes.

Current limits: core grouping is still role-led; recruitment currently admits
only unclassified helpers, not arbitrary mixed verified-role communities.
Regular frontage rows, GRID fallbacks, colored facades and extra land reserve
remain visible. Area grew versus soft by25.5% GJ/17.7% OJ/9.1% PB/36.1% SQLite;
this is not a density success. Continue with measured block/frontage efficiency
and relationship-aware mixed neighborhoods, then the deferred materials/LOD
work in the ledger. Terrain, concave coastlines and arbitrary planar road-face
extraction are not implemented.

## Soft functional influence — 2026-10-19

This opt-in ablation was **not accepted as the visual baseline**. See the
[execution ledger](../WORLD_EXECUTION_LEDGER.md) and the road-first policy below.

[ADR-029](../adr/ADR-029.md) adds `--zoning soft`, compatible with all existing
planning/outline policies, without changing their physical sites, streets or
principal territory. `flat-soft-zoning/0.1` adds optional `softZoning` metadata;
[`planning/0.2-experimental`](../../schemas/planning-0.2.schema.json) separates
center evidence from mixed geographical occupants. The hard0.1 policy below
is unchanged, and legacy City/UCG bytes/IDs remain the source of truth.

Swaps are deterministic, bounded, within the same principal directory/service,
and restricted to matching source footprint sizes. Graph affinity uses only
DIRECT/RESOLVED non-containment relationships, resolves symbols to actual files,
caps pair weights at4 and optimization degree at24. Role-center preference is
6% of local affinity weight. These are planning heuristics, not new graph facts.
Routing still includes all supported source trips, not just optimizer pairs.

`referenceEntityIds/referenceClaims` describe the functional center;
`memberEntityIds/memberClaims` describe actual occupants with unchanged claims.
Only the center of an address determines its influence-region membership; a
parcel may straddle an advisory influence boundary but never its true parent.
The occupied-address digest, optimizer counters/energy and exact center/occupant
evidence are validated. Unsupported/no-edge inputs remain useful neutral worlds.
Hints pin existing physical frames; an updated influence boundary may change a
file's derived `zoneId` without moving that file or rewriting its source role.

## Internal semantic neighborhoods — 2026-10-19

[ADR-028](../adr/ADR-028.md) adds opt-in `--zoning semantic` to the World
command, with `flat-zoning/0.1` and an optional `zoning` object. Existing
experimental World documents remain valid; `--zoning none` is unchanged.
[`planning/0.1-experimental`](../../schemas/planning-0.1.schema.json) is a
canonical projection of those same zones, not a second source of truth.

Each neighborhood stores stable parent/category/version ID, exact member files,
original role claims/evidence, requested/actual grammar, land demand/target/area,
capacity and allocator diagnostics. Source City/UCG and source-directory
ownership are retained. Derived browser zones are not new source modules.
The inspector and counts distinguish principal districts from planning zones.

Role-quarter policy only accepts DIRECT/RESOLVED evidence-backed claims. Groups
below12 files or districts below24 are neutral; ambiguous/unknown files remain
GENERAL_MIXED. SERVICE_QUARTER does not claim CBD/orchestration; CAMPUS_RESEARCH
is labeled Test campus and does not establish research/AI technology. Missing
Go/C++ role support never manufactures a specialized zone. Only one internal
level and six current categories are generated, within a seven-cell solver cap.

Clipped power cells use fixed sites, Newton weight balancing with32 iterations
and16 backtracking steps,1.5% relative target-area tolerance and deterministic
capacity-bisection fallback. Frontage capacity is checked separately. A bounded
capacity-feedback repartition inside the same parent precedes wider envelope
repair. `areaTarget` discloses the final target rather than pretending the
initial analytic demand predicted exact frontage efficiency. Four bounded local
GRID axis/phase fits avoid avoidable expansion. New parcels have0.01-unit inset
clearance; default legacy lots/bytes are not changed.

Only required local frontage and selected adjacency access ports are linked;
the largest port-free boundary arc is omitted. Raw power-cell borders are not
automatically full roads or semantic dependencies. Source-backed trips still
use the shared physical graph and retain exact edges/endpoints.

Compatible hints preserve parent/zone polygons, actual profiles and available
file slots. Changed zone sets, exhausted capacity or changed policy explicitly
replan. This is not arbitrary-rename or cold-build stability. The optional
`--outline varied` remains compatible; `--planning` must remain its default
`grid` because semantic policy chooses local grammars itself. No silent ignored
grammar override. Full block polygons, graph-affinity sub-clustering, terrain,
water, bridges/tunnels and rotated semantic aggregate LOD remain pending.

## Existing City/UCG baseline (unchanged)

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

### Opt-in World physical street hierarchy (ADR-041)

`python -m scripts.procedural_world INPUT --zoning neighborhoods
--pattern-scale adaptive --street-hierarchy ...` adds experimental World
`streetPlan`, version `street-plan/0.1`. Existing terrain/planning/street-policy
options remain explicit; the flag neither replaces them nor changes geography.
UCG, City, physical streets, parcels and exact source trips remain identical.
Without the flag, prior canonical World output is unchanged.

The plan classifies existing physical IDs as ARTERIAL, COLLECTOR, LOCAL or
SERVICE/building access. PEDESTRIAN is reserved, not assigned to ordinary roads.
This initial SERVICE interpretation records actual approach spurs; it does not
assert a loading/maintenance role for every source file. Shared interdistrict
corridors, reserved spines and real crossings establish the coarse hierarchy;
existing shortest street paths connect it. Component/frontage/zone-port audits
retain unattached cases explicitly. Geometry is never invented to pass an audit.

`planning.json` carries the same plan. Derived browser `physicalStreetPlan`
contains class palettes, summary and bounded offline marking surfaces; physical
surfaces and routed segments retain class/physical identity. CPU/WebGL/Canvas
use this classification. Normal view paints each physical street once and gives
local/access pavement lower priority. Selection, All routes and Structure overlay
restore the full source-demand layer, including exact complete paths and edge
evidence. Synthetic retains bounded own-path animation and static cache reuse.
HTTP/messaging semantics are independent of physical class and demand grade.

Limits: 50000 streets, 500000 spatial entries, 2000000 geometry checks,
500000 shortest-path states, 100000 marking surfaces; explicit failure rather
than truncated infrastructure. Validation reconstructs metadata from actual
world geometry. This RC-00/01 slice does not add CAMPUS, pedestrian networks,
new highway semantics, or a claim of finished metropolitan road planning.

### Local bridge-approach feasibility repair

Terrain-first `river-landscape` keeps its initial candidate whenever its full
bridge/approach pavement is disjoint from previously reserved crossings. Only a
conflicting otherwise feasible crossing tries four fixed nearby fractions of
the SAME river reach. Water, terrain seed, earlier crossings and bridge identity
stay fixed. If those five total candidates cannot separate the approaches,
generation fails explicitly; no mandatory crossing is silently discarded and
no certificate height/grade tolerance is relaxed. An originally infeasible
candidate remains absent, preserving prior no-crossing outcomes.

Porous local connections also check intersections against the at-most-four
certified three-span bridge profiles. A ground-height alley can join a ground
bank endpoint, but cannot attach to or cross an elevated approach/deck at a
different height. No flat ramp join is fabricated after source routing. The
existing independent bridge/profile validators remain unchanged. This repairs
formerly rejected geography; valid frozen corpus fields/geography stay exact.

### Opt-in source-mixed courtyard pockets (ADR-042)

`scripts.procedural_world INPUT --zoning neighborhoods --pattern-scale adaptive
--campus ...` enables the bounded CP-00/01 pilot and derives street hierarchy.
World/planning optionally carry `campusPlan` version `campus-plan/0.1` with
reproducible eligibility, evidence IDs, actual member/anchor IDs, court polygons
and physical walking segments. City/UCG/IDs and original source sizes/roles stay
unchanged. Without the flag, old canonical World output stays unchanged.

Eligibility uses verified TEST claims or actual internal source-pair cohesion,
including cross-parent pairs in the external-coupling count. Seeded weighted
choice is not a role mapping: a tests directory alone does not qualify. At most
one feasible MIXED_CAMPUS pocket per parent uses8..32 actual related files;
remaining source files retain the base local planning grammar. Blocks retain
planningProfile/patternMode and add urbanGrammar/campusSite; selected parcels
use blockProfile CAMPUS. No research/framework capability is inferred.

First finish the original neighborhood capacity repairs. Then reserve1..3 courts
and full rotated parcels, remove conflicting unoccupied local address candidates
and connect a width1.2 walking loop/spur to existing actual streets before file
assignment. Terrain, parent/zone boundaries and protected macro roads stay fixed.
Insufficient supply, disconnected/unsafe access or campus resource exhaustion
retains the original grammar with an explicit reason, not enlarged city land.
Require at least three non-corner frontage sides and bounded lawn per potential
member; a large lawn with every building on one side is not a successful campus.

Walkways belong to the authoritative physical graph and are PEDESTRIAN with
CAMPUS_WALKWAY provenance, not promoted vehicular collectors. Original source
pair/edge identities are retained while routes follow the changed local graph.
CPU/WebGL/Canvas share reserved lawns and paths; procedural trees avoid courts.
Both interactive inspectors enumerate exact pocket members and disclose that
physical planning is not research or runtime-communication evidence. Synthetic
uses stored complete original-pair paths and reuses static meshes.

Limits per candidate:384 centers,200000 clearance/access checks,256 walking
pieces; independent final court validation checks whole parcels and pavement.
Cross-policy hints are incompatible; same-policy growth preserves actual slots
when feasible. Riverside/other campus variants, vehicle service/emergency access,
materials, and campus-derived landmark redesign remain outside this pilot.

### Opt-in garden-cluster campus forms (ADR-043)

`scripts.procedural_world INPUT --campus --campus-style varied` (with the
adaptive/neighborhood options above) selects source-neutral ACADEMIC_QUAD or
TECH_PARK forms. `campusPlan` uses version `campus-plan/0.2` and explicit style
`varied`. Omitting the style or using `quad` preserves campus-plan/0.1 exactly;
existing Worlds stay valid. No UCG/City/semantic ID or original dimension changes.

Evidence eligibility and its seed remain0.1. A separate zone-local form seed
prefers TECH_PARK with probability0.75, then tries the alternate form if needed.
The number is a physical design preference, not analytical confidence. This is
not a promise that every repository or zone gains a garden-cluster campus.

TECH_PARK reserves two7.5-unit square gardens and nine candidate frontage plots
in the same bounded53x45 support used by the smallest courtyard option. Real
source members occupy the chosen plots around garden-facing loops, a short
offset promenade and an actual exterior walking link. Shared planting avoids
whole parcels, entrances, gardens and paths. Source dimensions are never shrunk
to force fit. The existing whole-parcel/access, slope, connectivity, graph and
resource gates apply; infeasible candidates keep the original safe grammar.

The form is prepared before actual file placement, not generated per browser
frame. CPU/WebGL/Canvas share the same gardens, rotated file parts and physical
pedestrian graph. Both inspectors show actual selected variant/member IDs and
retain the physical-planning disclaimer. Source-pair paths/Synthetic may change
their physical route, never their original source, destination or contributing
edge identities. Same-style geography hints preserve feasible original slots;
cross-style hints trigger an explicit deterministic cold rebuild.

This is CP-02's first garden-cluster option. Riverside-specific geometry,
cross-boundary campus transitions, emergency/service access and architectural
materials/lighting are not implicitly completed by this flag.

### Opt-in architectural building colours (ADR-044)

`python -m scripts.procedural_world INPUT --building-style architectural ...`
changes packaging/rendering only. `semantic` is the unchanged default. There is
no World generation option or geography version change: World, City, UCG,
planning, validation, terrain, physical parts and all exact source trips remain
byte-identical between the two presentation styles.

Private viewer data optionally carries `buildingMaterials` with pinned version
`building-materials/0.1`, six wall/neutral-roof palettes and the existing archetype
colour table. FNV-1a over Unicode code points selects the neutral palette using
only stable entity ID, independently of role, graph degree or source size.
Materials are procedural colours, not factual construction/technology claims.
Known archetype accents are blended onto existing highest roof faces; generic
or unrecognized archetypes receive no invented semantic accent. Existing part
shading is retained. CPU SVG and both interactive renderers share the rule.

Role colours (accessible pressed-state button), active filters and source
selection restore strong category tint. Inspectors still report exact roles,
confidence, paths, evidence, original aggregate members and contributing edges.
The policy also handles existing aggregate/role-compound masses without adding
geometry or changing their membership/expansion behavior. Ordinary World parcels
remain explicit at the existing LODs; this does not redesign Semantic LOD.

The manifest's optional `buildingStyle`/`buildingMaterialsVersion` options record
the presentation. Only page, viewer-data, SVGs and manifest differ; shared viewer
assets are the same in paired packages. Cache keys include colour mode, so a
toggle rebuilds once, while Synthetic uses the existing static cache. No new
textures, WebGL programs/draw passes, surfaces, runtime dependencies or target
repository execution. Reduced role salience at thumbnail size is intentional;
use the explicit semantic view for high-contrast analysis. This is not new
archetype geometry, physical material inference, lighting/AO or a complete city
aesthetic milestone.

### Whole-neighborhood campus precincts (ADR-045)

`scripts.procedural_world INPUT --campus --campus-style neighborhood` with the
adaptive/neighborhood options selects the whole-neighborhood `campus-plan/0.3`
experiment. Quad0.1 and varied0.2 remain reproducible pocket prototypes, not the
completed interpretation of the original campus design. City/UCG/IDs/source
dimensions and evidence remain unchanged. Style switches reject old geography
hints explicitly; same-style growth retains compatible source addresses.

The selected source neighborhood keeps its membership, parent, polygon, terrain
and protected major/inter-zone corridors, but its ordinary local road/address
plan is REPLACED before source assignment. Two or three actual activity centers
reserve shared courts, connected promenades, short frontage wings and a real
external street join. Known source-pair degree/affinity chooses actual anchor
files and guides local address optimization; no research role or new logical
dependency is inferred. This is not new authoritative community detection.

All neighborhood files participate:12..256 members, no eight-file quota or
retained ordinary remainder. A bounded12x12 center search measures surrounding
developable room; at most three layout trials. Secondary walking wings are
accepted only if they increase safe frontage. At least half the required file
capacity comes from internal pedestrian frontage; where needed, additional
frontage uses EXISTING protected vehicle corridors. Those corridors remain
vehicular, not falsely reclassified as pedestrian-only. No old local road grid
is retained simply to satisfy campus capacity. If full capacity/connectivity/
grade/clearance fails, the original neighborhood is retained with a reason, never
a successful-looking small garden pocket. No unrelated land enlargement.

Additive0.3 site metadata includes scope NEIGHBORHOOD, variant PEDESTRIAN_PRECINCT,
activityCenters with real anchors and candidate slot IDs, anchorSlots, and
vehicleFrontageSlotIds. It is a physical precinct form, not completion of all
Academic/Tech/Riverside variants. The existing inspectors enumerate ALL original
members and provide source-counted activity-group focus in WebGL and Canvas.
Independent reconstruction checks selection, complete membership, slots, anchor
placement, group occupancy, court clearance and block grammar. All-source route
and physical access validators remain strict. New late-stage alleys may not cut
through the reserved whole precinct after assignment.

Work is bounded by300000 clearance tests per layout invocation; existing output,
terrain/routing/spatial limits still apply. The new mode preserves exact local
axes instead of re-deriving yaw from a slightly moved quantized wing endpoint:
48->49 file hinted growth preserves all48 complete frames. No per-frame campus
planning or geometry generation is added.

Remaining limitations: rectilinear courts/wing grammar, some long/unused walking
branches, retained major through roads, no differentiated emergency/service
vehicle model, riverside-specific precinct or finished architectural landscape.
The0.3 correction makes campus the planning unit; it is not the full road/campus
milestone or a claim that every eligible neighborhood must fit this form.

### Purposeful built campus circulation — ADR-046

Neighborhood mode now applies offline `campus-circulation/0.1`: peel only unused
walking graph leaves beyond real frontage, not every street without dependency
demand. Retain court loops, promenades, exterior gates, occupied access (including
generic files), vehicle corridors, crossings and exact trip pavement. Keep every
parcel frame, all planning reservations and all source routing records identical.
No per-frame repair or source rerouting is added; resource exhaustion retains the
original complete graph.

`campus-plan/0.3` remains the pre-assignment plan; authoritative built pavement is
`streets`. An optional diagnostic records exact omitted atomic geometry/IDs and
length. Validation restores those atomic pieces, independently retests their
purpose against reconstructed reservations, and only then allows them to satisfy
unbuilt reservation coverage. A diagnostic is not blanket permission to omit a
main road. Old artifacts without the policy record still validate under complete
coverage; old quad/varied outputs are unchanged. The older untrimmed neighborhood
output is reproducible at its pinned revision `d7393de`.

This addresses excess tails, not rectilinear court morphology, riverside campus
forms, service/emergency travel semantics or finished architectural archetypes.

### Diverse nature and continuous pavement — ADR-047/048/049

Explicit `--terrain varied-landscape` uses terrain/0.5 / terrain-adaptive/0.5.
Counts, locations, outlines, bearings and heights vary by independent local
seeds and domain area: up to4 lakes,6 hill/ridge groups,0..3 branch paths and
sometimes a second through-flowing river. Feasibility can reduce these budgets;
small domains do not receive stacked bridge ramps. Limits are48 convex feature
pieces,8 crossings,3 conditional tunnels; old versions retain their old limits.
Independent lakes use level basins in the shared height field with gentle
transitions, not tilted water faces. This profile reserves additional land
BEFORE terrain/urban assignment. Source/edge identities stay intact but changing
the terrain profile deliberately changes geography; compatible hints retain it.

`world-street-mesh/0.1` is an offline presentation mesh shared by CPU/Canvas/
WebGL: bounded actual-node bevel joins, parcel/nature/court clearance, no fake
ground connection at a bridge, and walking/entry colour clipped at vehicle
curbs. Four-corner triangle faces retain all vertices in the existing quad
consumers. World/source paths are unchanged by this presentation-only repair.

Optional `--campus-style landscape`, campus-plan/0.4, retains whole neighborhoods
and offers softer commons with actual walking arcs at unused square corners.
It keeps occupied straight frontage and reconnects gates/promenades. Coordinated
group bearings are attempted only under full capacity, clearance and grade
checks. The roomy positive fixture really rotates; dense GJ/OJ groups retain
zero rotations and some GJ courts retain their original form after safe fallback.
Do not claim the original row-monotony problem is completely solved. Existing
quad/varied/neighborhood modes and canonical UCG/City contracts remain intact.

### Pre-assignment organic campus frontage — ADR-050

Optional `--campus-style organic` adds `campus-plan/0.5`. Reserve elliptical
commons and real connected fanning walking paths before laying out parcels.
Generate full-size tangent-facing frontage along the actual polyline, with
distinct local group bearings; do not rotate already interlocked source rows.
Preserve whole original neighborhoods, evidenced eligibility/anchors and mixed
source membership, protected vehicle corridors and terrain. Source assignment
still uses real graph affinity. No role, file or dependency is invented.

Six bounded fan proposals per center, at most three centers and three fits;
the existing300000 clearance-work bound applies. A fixed64-unit maximum branch
reserve avoids changing every tangent under one-file growth. The planner can
retain the complete0.4/0.3 precinct with explicit `organicFallback` when the new
grammar cannot fit; it never claims a small pocket as whole-neighborhood success.
Old styles keep their original IDs and output semantics. New experimental
style/version enums are additive; UCG/City and runtime dependencies are unchanged.

Terrain and macro geography remain unchanged when switching campus style;
affected campus interior frames and source-trip geometry deliberately change.
Exact original source/target/edge identities must be conserved. No per-frame
planning is added. This does not complete riverside-specific design, emergency
vehicle semantics, or all natural campus variants.

### Non-radial campus compositions and rotated role compounds — ADR-051/052

User visual review rejected the0.5 fan as repeated sunburst emblems despite
passing geometry checks. Keep0.5 reproducible, not the recommended baseline.
Optional `--campus-style fabric`, campus-plan/0.6, combines meandering malls,
open arcades and staggered garden lanes with different convex commons outlines.
Use real neighboring street bearings, zone/terrain clearance and connected
feasible frontage runs. Full membership and graph-aware source assignment remain;
fallback is the complete0.4/0.3 precinct, never the rejected0.5 spokes.

World export previously marked every building oriented, so the legacy LOD guard
removed every aggregate. Do not remove that safety guard. Offline
`world-role-compounds/0.1` supplies separately checked rotated envelopes for at
least4 adjacent same-evidence page/API/gate/test files, bounded by module/zone,
source occupancy, public streets, commons and nature. Absorb all eligible
occupants; never cover an omitted unrelated source. Only members' own final door
stubs can meet their building envelope. At most16 members and56-unit spans,
300000 clearance checks/500000 index entries; exhaustion retains individuals.

CPU/WebGL/Canvas share actual oriented compound models. Existing LOD/inspector
keeps compounds at all zooms, lists exact source members/evidence and explicitly
expands originals; filtering and selected-source routes remain exact. World,
City, UCG, planning, source entrances and paths are unchanged by aggregation.
The export-only `role_compounds=False` option is available for controlled
same-World comparisons. Generic overview plates remain excluded on rotated
World geometry. This restores eligible role landmarks, not arbitrary mass merging.

### Main-river/tributary topology diversity — ADR-053

Explicit `--terrain watershed-landscape` adds terrain/0.6 and terrain-adaptive/0.6.
Older terrain presets retain their bytes and stricter payload bounds. UCG/City,
source IDs and evidence contracts are unchanged. Before urban assignment, use
local seeds and available scale for one/two through rivers and zero/three curved
tributaries, including nested confluences. Counts are actual channel records,
not the number of convex RIVER mesh pieces. Broad meanders cover the developable
domain, rather than a tiny central bend with long straight urban extensions.

The additive experimental channel `waterways` array carries environmental IDs,
MAIN/TRIBUTARY kind, parentId, centerline and width. Existing centerline and
tributaries project all these paths into the same shared height field; that
projection's tributaries array can include an additional main path. Consumers
must use waterways kinds when counting rivers. Waterway parents and shapes are
reconstructed independently during terrain validation. These are procedural
environmental relationships, not source dependency claims or simulated drainage.

Bounds: five waterways,17 vertices/line,64 natural convex pieces,eight certified
crossings,three conditional tunnels. Branch fitting is bounded and may reject
infeasible proposals. Overlapping water is removed from shared shore faces;
disjoint cutters are skipped to prevent artificial fragmentation. Lakes retain
level basins; mountains and terrain-first access/grade/collision gates remain.
New-mode clipping seams alone use a0.002-unit snap bound (old0.0005 preserved),
within the existing reserved-street validation tolerance; source entrances and
bridge endpoints are fixed. Budget exhaustion never silently drops waterways.
Changing profiles deliberately changes geography; compatible same-mode hints
retain terrain and existing frames in the named growth fixture.

### Coplanar road corruption and intersection paint — ADR-054

`world-street-mesh/0.2` partitions overlapping same-level span/joint polygons
into single-owner asphalt, using stable class/width/ID precedence. It also
deduplicates ordinary shared walking surfaces; individual door ramps retain
their own slope groups. Grade-separated bridge/tunnel surfaces are not merged
with ground beneath. Joint patches keep the existing bounded bevel/parcel/
nature/campus-clearance rules and use the dominant incident street class.

Structural center paint is clipped at actual overlapping crossing/merge mouths,
not merely a half-width distance from a graph node. Collinear atomic spans keep
their dash phase, and different crossing levels do not erase each other's paint.
Spatial indexes and work/output bounds fail explicitly; no per-frame clipping,
additional browser draw pass, physical road deletion or source rerouting is added.
The source World/City/UCG/planning and natural geography remain unchanged.

The reported GJ close-up's same-level face overlap pairs fall691->0 (80x80
region, positive intersection area>.001). This is overdraw removal, not691
removed roads or a global speedup. Polygon subdivision increases static face
counts/payload somewhat; actual viewer/Synthetic regressions remain checked.
Old saved packages keep their old meshes; regenerate/export to see the repair.
