# Hierarchical semantic zoning implementation plan

Start each continuation with [WORLD_EXECUTION_LEDGER](WORLD_EXECUTION_LEDGER.md):
the consolidated requirements, rejected directions, retained work and active
delivery gates. Latest feedback adds constraints; it does not erase earlier work.

Source proposal: `MetropoGits_Hierarchical_Voronoi_Semantic_Zoning_Design.md`
(workspace `MetropoGits_Docs`, proposal v0.1). Incorporation requested by the
maintainer on 2026-10-19. This extends, rather than replaces, the procedural
world plan and [ADR-024](adr/ADR-024.md).

## Direction

Keep three distinct graphs: immutable UCG truth, derived planning ownership,
and physical infrastructure. A source-owned principal district can contain
several evidence-backed neighborhoods; its entire territory need not repeat
one radial/grid stencil. Voronoi allocates land, not semantic truth or roads.
Directory ownership and exact file/edge coverage remain non-negotiable.

## Active correction — do not promote the soft-placement experiment

Maintainer rejected the direction of the soft output on2026-10-19: internal
evidence-backed neighborhoods became visually ineffective, while restored
district-wide patterns made streets repetitive again. This is a structural
failure, not a missing color palette or insufficient number of patterns.

Code evidence: `generate_soft_world` first generates the complete structural
world, then swaps files on its existing occupied addresses. Influence cells
never affect its streets/blocks. `generator.requested_profile` selects one
grammar for a principal district; each grammar emits roads and frontage sites
together. Therefore fewer dependency meters cannot demonstrate improved
neighborhood structure or a more convincing street network.

Measured counterexample in soft-zoning-r1/gj/after: SERVICE_QUARTER has18
occupants but none of its reference service files; COMMERCIAL_FRONTEND has30
occupants but none of its reference frontend files. Explicit advisory disclosure
avoids false source claims, but does not rescue the intended city semantics.
Keep this opt-in mode only as a reproducible ablation, not the new visual baseline.

The source proposal already specifies the missing order (hierarchical design
sections8/9; procedural world sections9/10):

1. Keep source-owned services and evidence-backed internal neighborhood cores.
   Admit existing supporting files via actual dependency provenance, without
   pure-category sorting or a mixing quota. Every named core must remain in
   its own physical neighborhood, not become a remote reference list.
2. Choose neighborhood access ports and a continuous shared arterial/collector
   backbone from adjacency, real aggregate demand and fixed geography. Streets
   are disclosed infrastructure; demand never invents an edge. Do not pave
   every Voronoi boundary or stamp concentric rings across an entire service.
3. Derive actual enclosed block polygons from that road graph. Primary roads
   must exist before frontage lots/buildings and survive local grammar changes.
4. Use GRID/ORGANIC/RADIAL/INDUSTRIAL/HYBRID as **block-local planning tools**,
   not one whole-district stencil or random pattern patchwork. Existing
   grammars/seeded outline are reusable ingredients, not immutable city plans.
5. Build rotated frontage parcels/buildings within those blocks; optimize local
   affinity without erasing neighborhood cores or upstream road continuity.

Next vertical slice: flat, convex, source-traceable neighborhood cores + actual
access backbone + enclosed blocks, first on the maintained mixed-role fixture
and GJ/OJ. Keep old generation available for honest comparison. Version new
experimental physical metadata explicitly; do not break City/UCG or silently
change existing cold/hinted geography. Terrain/concave coasts are separate work.

Gates must include actual core retention/containment, supporting-member edge
IDs, neighborhood readability in overview/district, arterial continuity across
local-pattern boundaries, block area/coverage, full-width clearance, exact trip
coverage, repeat bytes and hinted edits. Add a controlled local-pattern ablation:
changing a block's local grammar must not regenerate the entire main road graph.
Road angle entropy alone is not a quality target; arbitrary jitter/rotaries are
not evidence that a city is more natural.

Neutral materials/role accents remain wanted but are deferred behind this
structural repair. Do not spend another series of commits on tiny road bends,
cosmetics, or new patterns while the same pipeline order remains wrong.

## Delivery order and scope

First road-first vertical slice is now implemented as `--zoning neighborhoods`
under [ADR-030](adr/ADR-030.md). It preserves physical source cores and explicit
supporting edges, precomputes road-cut blocks/backbone, and applies existing
grammars locally. See current contracts for limits and
`artifacts/visual/neighborhoods-r4/index.html` for actual before/after outputs.
It is not completion of all HZ-03/04 work: boundary blocks are disclosed as
administrative-edge bounded, role mixing is conservative, and land usage grows.
The original delivery packages below remain partially open.

1. HZ-00: [ADR-028](adr/ADR-028.md), opt-in contract and geometry gates.
2. HZ-01: deterministic role-backed zone candidates, explicit member claims,
   minimum-size merging and honest GENERAL_MIXED fallback.
3. HZ-02/03 first vertical slice: bounded clipped power cells inside principal
   districts, capacity checks, existing street/frontage grammars, exact trips,
   and inspectable `planning.json` plus both real renderers.
4. Next: package/dependency affinity within large mixed neighborhoods; localized
   cluster growth and bounded sub-zones; suppress needless zone-border pavement.
5. HZ-04: real road-enclosed block polygons, corner parcels and aggregate sites.
6. HZ-05: globally continuous terrain/developability, then clipped zoning,
   bridges/tunnels with validated approaches. Flat land is explicit until then.
7. HZ-06: rotated source-traceable H-SLOD/chunks, including reveal reservations.
8. HZ-07: four-repository visual/stability/performance ablations and release gates.

Initial clustering uses supported role claims, not unsupervised communities,
directory-name semantics or inferred runtime flow. Go/C++ sources without role
evidence stay neutral. INDUSTRIAL is a planning grammar; it does not establish
a particular database or production infrastructure. Tests are a test campus,
not evidence of AI/research. CAMPUS grammar is not implemented yet; use ORGANIC
and record the actual grammar instead of relabeling it.

## Compatibility and observability

- Legacy generation and existing world options remain unchanged by default.
- UCG and City bytes/IDs stay intact; opt-in World gains additive planning data.
- Planning IDs derive from parent ID + category key + zoning version, not array
  position or graph revision. Classification is a disclosed derived grouping;
  every specialized member retains the exact source role/evidence claim.
- All files belong to exactly one planning zone; tiny incompatible groups enter
  GENERAL_MIXED rather than a falsely homogeneous specialized zone.
- Inspect members and evidence in the browser and canonical `planning.json`.
- Record actual partition algorithm, convergence, capacity fallback, hint reuse
  and replanning. Never claim all HZ packages done from this first slice.

## Verification

Compare structural-only and zoning-enabled views on GJ-Cloud, GamjaOJ,
PocketBase and SQLiteBrowser, plus fresh Spring/unknown fixtures. Check exact
members, source claims, area/overlap/clearance, reachable entrances, route edges,
repeat bytes and hinted small edits. Inspect actual overview/district/detail
and CPU SVG. Record timing outside canonical outputs; no universal FPS promise.
Concave/holed geometry is rejected or remains outside this convex-only stage.

Avoid serial micro-tuning: prioritize a visible complete slice, measure it,
and use real outputs to choose the next architectural improvement.

## Soft influence correction (2026-10-19)

Maintainer feedback: pure role quarters looked like category-sorted production
lines. [ADR-029](adr/ADR-029.md) supersedes exclusive occupancy **only for the
new opt-in soft policy**. Keep hard quarters available for comparison.

Run `python -m scripts.procedural_world BUILD --namespace owner/project
--planning varied --outline varied --zoning soft --out NEW_OUTPUT`.
All five existing grammars and seeded convex outline families remain the
physical base. Soft zoning does not rebuild streets or add land to enforce a
category. Functional centers attract weakly; actual DIRECT/RESOLVED file/symbol
dependencies attract across roles within the original principal district.
Only equal-footprint occupants swap existing frontage sites, with meshes,
rotation and entrances regenerated together. All source dimensions, roles,
evidence, IDs and exact trip endpoints remain unchanged.

`planning/0.2-experimental` distinguishes center `referenceEntityIds` /
`referenceClaims` from actual mixed `memberEntityIds` / `memberClaims`.
Region membership uses address centers, not exclusive parcel containment.
A center's classification does not classify every occupant. Per-file roles
and evidence remain inspectable, with paged source navigation in both renderers.
Principal service names remain visible independently of derived regions.

The bounded sparse optimizer uses at most24 neighbors, three passes,
32 candidate addresses and per-district400k evaluations /10M scored pairs.
It records work limits, objective changes and actual mean dependency distance;
optimization limits never remove source relations from routing. Compatible
previous worlds pin existing physical frames, even when influence membership
changes after an edit. This is not unrestricted global force-directed layout.

This experiment's geometry/source gates passed, but the subsequent maintainer
review above rejects it as the main visual direction. Neutral exterior materials
are deferred until evidence-backed neighborhoods and road-enclosed blocks work
together. Do not disguise this structural defect with decorative irregularity.

## First delivered slice (2026-10-19)

HZ-00 and the first role-quarter HZ-01 policy are implemented. The convex-only
HZ-02/03 slice is available with `scripts.procedural_world --zoning semantic`;
see [current contracts](contracts/CURRENT_BASELINE.md) and QUALITY_LOG for exact
verification. This is not completion of all clustering/terrain/LOD packages.
Structural-only defaults and original City/UCG remain available unchanged.

Controlled four-repository comparison: `artifacts/visual/semantic-zoning-r4`.
Browser/CPU captures: `semantic-zoning-reviewed-r1`; Canvas inspection:
`semantic-zoning-canvas-r1`. GJ has13 zones, OJ11; PocketBase8 and SQLite3 all
neutral because there are no supported role claims. Real files/relations remain
individually inspectable. The GJ ellipse comparison currently uses GRID in all
zones after capacity fallback; OJ retains ORGANIC and INDUSTRIAL, while varied
GJ retains one ORGANIC zone. Do not claim every semantic category has a unique
planning morphology. The next high-impact zoning task is bounded package/graph
affinity inside large mixed quarters, with persistent keys and real block/LOD
geometry, not tuning another individual bend.
