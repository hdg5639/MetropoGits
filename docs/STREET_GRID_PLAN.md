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

1. Diagnose fallback trips by missing access, disconnected topology, length and
   bend constraints; current report counts fallback but does not prove which
   constraint dominates. Do not relax budgets blindly.
2. Reduce redundant structural loops using building-frontage coverage and block
   connectivity, **without consulting dependency edges** or paving empty space
   simply to fill it. Compare infrastructure length and access coverage together.
3. Test a bounded street-first block layout separately if fixed parcels prevent
   useful assignment. Any relocation needs explicit stable-geography comparison;
   no global relayout is part of this first prototype.
4. Re-evaluate both source fidelity and appearance before promotion. Do not stack
   lighting/landscaping onto this grid and describe it as a solved city model.
