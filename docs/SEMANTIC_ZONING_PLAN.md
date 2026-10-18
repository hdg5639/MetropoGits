# Hierarchical semantic zoning implementation plan

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

## Delivery order and scope

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
