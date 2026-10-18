# Structural street experiment

Approved direction: ADR-020. Branch: `experiment/street-grid`.

## Work sequence

1. [x] Record user-approved semantic separation before implementation.
2. [x] Build deterministic directory/block street infrastructure without UCG
   relationship input, including per-building access and explicit resource caps.
3. [x] Assign evidence-backed trips and report budget-constrained fallbacks.
4. [x] Add opt-in `--street-grid` developer export, structural legend and shared
   WebGL/Canvas/SVG output; retain detailed relation selection and Synthetic.
5. [x] Test independence from relation edits, determinism, obstacles, provenance,
   sparse/unknown fallback and unchanged default behavior.
6. [x] Inspect matched-camera GJ/GamjaOJ outputs, document measurable results and
   remaining defects; commit each coherent unit and push the experimental branch.

Do not resume low-impact entrance micro-tuning as the main development track.
Do not conflate static dependency demand with measured traffic. Lighting,
landscaping and new silhouette work follow the structural comparison, not precede
it. This checklist is an implementation plan, not a claim of completed output.

## First prototype / 2026-10-18

Implemented as an explicit developer comparison, **not a promoted replacement**:

```powershell
python -m scripts.street_grid <existing-build> --street-grid --out <new-directory>
```

The command compares original access/0.2 routing against structural assignment.
For the private visual review, the same after-data is compared instead against
the latest `frontage-refinement-r2` baseline. Do not confuse these baselines.
Artifacts: `artifacts/visual/street-grid-r3/{gj,cold,oj}/{before,after}`;
matched-camera gallery `street-grid-focus-r3/index.html`, cold Portal gallery
`street-grid-cold-focus-r1/index.html`. Generated/private artifacts are not Git content.

| Measure | Hinted GJ | Cold GJ | GamjaOJ |
| --- | ---: | ---: | ---: |
| Assigned trips / all trips | 2,487 / 4,209 | 2,483 / 4,209 | 547 / 1,381 |
| Explicit original-path fallbacks | 1,722 | 1,726 | 834 |
| Structural entrances / buildings | 1,324 / 1,324 | 1,324 / 1,324 | 681 / 681 |
| Structural centerline length | 34,419.5 | 34,419.5 | 14,393 |
| Legacy latest evidenced pavement length | 23,446 | 23,302.5 | 6,076.5 |
| New all-trip pavement length, including fallback | 54,998.5 | 55,558.5 | 14,522 |

Structural and all-trip lengths overlap; **do not add them**. These are world
units, not runtime throughput. All-trip geometry is available with All routes;
default mode only displays assigned demand over non-semantic streets. Default
line reduction is therefore **not** evidence that all original paths got simpler.

Fixed geography, original route identities/provenance and complete-trip limits
survive; full-width building intersections are zero. Repeated assignments are
identical. Removing all networks while retaining geography leaves infrastructure
identical. Unsupported fixture still has zero logical relations but visible
structural streets. Spring sparse fixture assigns 0/2 trips, retaining both as
fallback: the first skeleton is not universally adequate.

Observed visual result: streets now exist independently of relationships and
some blocks read more continuously, but the regular grid and empty parcels
remain. Infrastructure is longer, not shorter. Keeping the existing building
layout is a controlled experiment, not proof that it suits street-first design.
LOD obstruction inputs are deliberately frozen to the legacy geography so this
comparison does not silently alter aggregate building shapes. Canonical building
clearance is verified; aggregate/infrastructure visual clearance needs its own
future check. Canvas overview still has noisy aggregate outlines.

## Next decision gates

1. [Done] Diagnose fallback trips without altering routes; see the measured
   breakdown below. Do not relax budgets blindly.
2. Prioritize distance-compatible block streets/access over further road deletion.
   Removing edges alone cannot shorten shortest paths in the same graph. Preserve
   all source relationships and compare complete-trip assignment, not hidden lines.
3. Test a bounded street-first block layout separately if fixed parcels prevent
   useful assignment. Any relocation needs explicit stable-geography comparison;
   no global relayout is part of this first prototype.
4. Re-evaluate both source fidelity and appearance before promotion. Do not stack
   lighting/landscaping onto this grid and describe it as a solved city model.

## Fallback review / 2026-10-18

Artifacts: `artifacts/visual/street-diagnostics-r1/{gj,cold,oj}/index.html`.
`Review fallbacks` opens a filtered, paged list in both WebGL and Canvas. A row
opens the exact original path and source evidence, not an invented connection.
The default view and every road/building coordinate remain unchanged.

| Fallback reason | Hinted GJ | Cold GJ | GamjaOJ |
| --- | ---: | ---: | ---: |
| No street path within original distance allowance | 1,392 | 1,390 | 706 |
| Distance fits; joint bend/simple-path search did not find a route | 324 | 331 | 124 |
| Original path has no lattice road segment (access-only) | 6 | 5 | 4 |
| All fallbacks | 1,722 | 1,726 | 834 |

Distance alone explains approximately81% of hinted GJ and85% of OJ fallbacks.
No missing access, disconnected topology or capped diagnostic searches were
observed in these three cases. The joint category is **not proof of a bend-only
failure**. A bounded independent shortest-distance check separates it from the
distance category; exhausted checks explicitly report an unknown cause.

A conservative branch-removal trial protected every geometry-eligible building
access and selected structural entrance, then removed only terminal-free bridge
subtrees. GJ9645 and OJ4015 lattice edges stayed unchanged: zero improvement.
That ineffective deletion pass was **not shipped**. This does not establish that
all possible topology simplifications are ineffective.

Next experiment: compare a bounded street-first block/access arrangement against
this unchanged baseline, measuring assignment, total infrastructure, detour and
relocations together. Do not add per-fallback shortcut streets based on dependency
edges: that would turn independent infrastructure back into relationship wiring.
This diagnostic work is useful evidence, **not a visual road improvement**.

## Aligned block streets / 2026-10-18

```powershell
python -m scripts.street_grid BUILD --street-grid --aligned-blocks --out NEW_DIRECTORY
```

The original half-cell padding put many periodical seed lines through parcel
centers, causing gaps and extra detours. Align seeds to occupied block bounds,
then connect geometric wave-neighbor components with bounded alternate loops.
No building or original door moves. Do not reorient entrances independently per
trip: that discarded trial violates the single-door consistency invariant.
Per-building perimeter roads were also rejected: with neighbor loops GJ reached
3328 assigned trips but infrastructure grew to54282, versus34419.5 previously.

| Measure | Hinted GJ before → after | Cold GJ before → after | OJ before → after |
| --- | ---: | ---: | ---: |
| Assigned / all trips | 2487 → 3642 / 4209 | 2483 → 3642 / 4209 | 547 → 1113 / 1381 |
| Structural centerline | 34419.5 → 32095.5 | 34419.5 → 32095.5 | 14393 → 13245 |
| All-trip pavement centerline | 54998.5 → 43739 | 55558.5 → 43672.5 | 14522 → 12607.5 |
| All-trip junctions | 4152 → 3029 | 4159 → 3020 | 1171 → 952 |
| Nearby parallel pair length | 28175 → 19008.5 | 29148 → 19204.5 | 8242.5 → 6601 |
| Sum of complete trip lengths | 752257 → 762890 | 746174 → 755981 | 167295 → 174351 |

Infrastructure and all-trip pavement overlap: do not sum those measures.
Original per-trip allowances and bend limits hold, although travel sums increase
about1.4%/1.3%/4.2%. Coverage gains are real assignment, not relation omission.
All input routes4209/4209/1381 survive. Canonical City/UCG and positions remain
unchanged. Repeated outputs are identical and street geometry is independent
of dependency input. Neither v0.1 nor v0.2 becomes the default CLI layout.

Artifacts: `artifacts/visual/aligned-streets-r1/{gj,cold,oj}/{before,after}`;
same-camera Detail gallery `aligned-streets-focus-r1/index.html`. Actual Ops
capture has fewer broad parallel surfaces, while retaining more assigned trips.
Remaining failures567/567/268, sparse-unknown width transitions, regular grid
appearance and excess overview whitespace still need work. This improves the
experimental street skeleton; it does not solve city composition or prove the
new infrastructure is universally better than the older dependency-only renderer.

## Viewer composition follow-up

`artifacts/visual/aligned-framing-r2/{gj,oj,cold}` combines the above unchanged
street assignment with perspective-aware initial framing. Comparison gallery:
`framing-comparison-r1/index.html`. Same1500x1000 viewport, same Overview LOD,
same entity counts; only camera target/distance change. In the drawable canvas,
projected canonical building bounds span GJ53.4%→74.4% of width and67.4%→87.5%
of height; OJ65.2%→85.9% and69.7%→83.7%. These are bounding spans, not occupied
pixel area. No projected canonical building corner is outside the view frustum
in these captures. Orbit target height is preserved. Smaller fixtures also pass.

Remaining work is still physical street/parcel readability: narrow/wide surface
transitions and overly regular grids are visible. Better framing exposes those
issues rather than fixing them, and is not grounds to promote the experiment.

## Continuous structural pavement / 2026-10-18

Aligned-block presentation removes short width bulges before tapering from
narrow to wide clearance. The first taper-only trial produced diamond-shaped
bulges in the three-building unsupported fixture and was rejected. A two-step
straight-run opening (14-unit neighborhood) suppresses short expansions; a
bounded shortest-envelope pass limits full-width growth to0.25 per world unit.
Door stubs do not dictate trunk width. This is geography-only presentation,
not demand or inferred traffic. Equal-slope spans share one quad.

WebGL, Canvas and CPU SVG use the same tapered polygons inside the former safe
rectangles. Scene, UCG, entrances, all4209/1381 GJ/OJ trips, assignments and
fallback reasons remain byte-identical. Original structural0.1 rendering stays
rectangular. Compare `artifacts/visual/street-width-focus-r3/index.html`; usable
viewers are `street-width-r2/{gj,oj}/after/index.html`. Fresh small pipeline
fixtures/captures: `street-width-fixtures-r2`. Small streets lose isolated slabs;
GJ Detail has less broad unpainted pavement. Dense thumbnails are not radically
changed. Quads increase GJ3679->4781 and OJ1536->1903; browser Synthetic still
rebuilds static geometry0 times. This is not a GPU/FPS or speedup claim.

Next: evaluate a shared presentation envelope for structural pavement and its
assigned-demand overlay. The latter retains its current quantitative grade and
safe rectangular width, so it can still expand over a narrower structural
surface. Keep paths, fallbacks and demand values intact; do not describe the
entire layered road model as continuous. Regular grids, empty parcels and
aggregate silhouettes remain broader tasks, not reasons for endless per-trip
micro-optimization. No default promotion of the street experiment.

## Shared physical envelope / 2026-10-18

Dependency pavement now fits inside the structural taper, not a wider rectangular
second road. Remove repeated shoulder strips and additional rectangular junction
fills; retain every connector, fallback and exact route. Inspector distinguishes
physical width from the unchanged quantitative demand grade. HTTP/messaging are
not reclassified. All three renderers share these derived polygon fragments.

`artifacts/visual/shared-street-r2/{gj,oj}/after/index.html` and same-camera
`shared-street-focus-r2/index.html` show the change. GJ's interrupted edge strips
are visibly reduced; preview-scale change remains modest. Polygon count9209/2632
for8011/2372 dependency segments is presentation cost, not added streets or edges.
Keep this verified unit separate from the following structure-overlay declutter.

## City context and explicit structure overlay / 2026-10-18

Aligned experimental viewers now default to major-service context, selected
district boundaries and quieter neutral ground. Minor directory outlines,
civic plot curbs and unselected minor labels no longer resemble extra roads.
The Structure overlay button restores those details without moving anything;
all districts remain pickable and exact route inspection is unchanged.
This is a reversible presentation choice, not omitted source data or a new
layout. Legacy viewers retain their existing appearance and controls.

Showcase SVG uses the same context palette and omits decorative plot outlines;
the accessible preview remains a detailed structural diagram. Both retain the
same canonical buildings, roads and projection geometry. No invented facilities.

Artifacts: `artifacts/visual/urban-street-r1/{gj,oj}/after/index.html`, comparison
`urban-street-focus-r1/index.html`, and city/structure toggle captures at
`urban-context-focus-r1/index.html`. Same-camera Portal Detail labels22->1 and
line vertices3300->568; OJ29->2 and874->196. These are viewport-specific
presentation counts, not deleted entities or a frame-rate claim. Toggle-back
restores exact geometry counts. All4209/1381 routes and1324/681 buildings remain.

WebGL and forced Canvas were exercised; three-LOD browser audits retain zero
static rebuilds during Synthetic. Repeated generic towers, empty parcels and
regular street geometry are still visible and should guide the next broader
improvement. This milestone improves readability, not architectural coverage,
and does not promote the experiment to the default pipeline.
