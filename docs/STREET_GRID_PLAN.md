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
