# Structural street experiment

Approved direction: ADR-020. Branch: `experiment/street-grid`.

## Work sequence

1. [x] Record user-approved semantic separation before implementation.
2. [ ] Build deterministic directory/block street infrastructure without UCG
   relationship input, including per-building access and explicit resource caps.
3. [ ] Assign evidence-backed trips and report budget-constrained fallbacks.
4. [ ] Add opt-in `--street-grid` developer export, structural legend and shared
   WebGL/Canvas/SVG output; retain detailed relation selection and Synthetic.
5. [ ] Test independence from relation edits, determinism, obstacles, provenance,
   sparse/unknown fallback and unchanged default behavior.
6. [ ] Inspect matched-camera GJ/GamjaOJ outputs, document measurable results and
   remaining defects; commit each coherent unit and push the experimental branch.

Do not resume low-impact entrance micro-tuning as the main development track.
Do not conflate static dependency demand with measured traffic. Lighting,
landscaping and new silhouette work follow the structural comparison, not precede
it. This checklist is an implementation plan, not a claim of completed output.
