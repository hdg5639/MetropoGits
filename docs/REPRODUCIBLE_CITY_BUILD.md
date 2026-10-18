# Cold rebuilds and stable geography

Rebuilding does not shuffle a city randomly. A cold build without a previous
scene is deterministic for the same source tree, repository namespace, engine,
catalog, options and supported runtime. A previous scene is an additional input:
it preserves compatible existing positions rather than asking the allocator to
choose its cold-start sites again.

## Reproduce the current experimental road viewer from source

Run from the MetropoGits repository. Use fresh, distinct output directories;
keep generated outputs outside the source repository being analyzed.

```powershell
python -m metropogits build --repo <source-root> --out <new-output>/base
python -m scripts.parcel_viewer <new-output>/base --out <new-output>/parcel
python -m scripts.road_consolidation <new-output>/parcel --out <new-output>/roads --shared-frontage
```

Open `<new-output>/roads/after/index.html`. The normal CLI build is still the
default directory-first layout; the last two commands explicitly opt into the
parcel experiment and complete-trip road consolidation. Omitting these stages
does not reproduce the experimental viewer. None of these commands runs the
target application's code, dependency installation or build scripts.

For the subsequent fixed-door cleanup experiment, replace `--shared-frontage`
with `--simplify` in the last command. Its `before` is the shared-frontage result;
`after` smooths complete trips and removes redundant corridors atomically.
This option rebuilds all prerequisite routing passes from the supplied City/UCG;
it does not execute or trust an old viewer's JavaScript. The same original detour
budget applies across every pass. It does not move buildings or change the
default CLI layout. Use a new output directory and compare route geometry and
travel distance, not merely fewer rendered segments.

For a cold-repeat check, run all three commands again with another new output
root and **no `--previous-scene`**. Compare files and coordinates by stable entity
ID, not by screenshot appearance alone. Retain canonical graph/scene hashes,
exact underlying relationship IDs, routing data, engine commit and source revision.
Compare actual renderings at the same camera and LOD after the data comparison.

## Preserve an existing map instead

Use a compatible previous scene explicitly when geographic continuity is wanted:

```powershell
python -m metropogits build --repo <source-root> --out <new-output>/base --previous-scene <previous-base>/city.json
python -m scripts.parcel_viewer <new-output>/base --out <new-output>/parcel --previous-scene <previous-parcel>/city.json
```

The default generator expects its own layout version. The experimental parcel
hint requires the same experimental version, exact directory geometry and file
membership/ownership/footprint size (ADR-017); it is not a general incremental
growth allocator. Do not feed an experimental scene to the default generator
or relabel a scene to bypass compatibility. Review diagnostics for hint acceptance.

## What counts as the same input?

- Files and relevant manifests/configuration, including exclusion rules.
- Repository ID. If none is supplied, the local root determines its namespace;
  moving a repository can therefore change IDs. Supply the same `--repo-id`
  deliberately when comparing across local paths. Do not silently rewrite IDs.
- Engine commit, catalog, layout and routing options, theme and output dimensions.
- Previous-scene hint, including the distinction between an explicit hint and none.

Same-input repeatability is not a guarantee that changing source relationships,
engine algorithms or hints leaves every coordinate unchanged. Cold rebuilding is
also not a repair for repeated awkward bends: deterministic planning constraints
will reproduce them. Fix and measure the planner rather than rerolling the city.

## Verified cold rebuild — 2026-10-18

Engine `1956e78`, catalog 0.4.0, unchanged GJ-Cloud source `3d9b53f`, minimal theme,
same local repository namespace; no previous-scene input in either full build.

| Comparison | Observed result |
| --- | --- |
| Two independent source-to-default builds | All 13 files identical, including manifest |
| Two independent experimental parcel exports | All 14 files identical |
| Two independent full road consolidations | All 14 final files identical |
| Building/district movement between the two fresh runs | 0 / 0 |
| Fresh vs previously displayed city | 58 of 1,324 buildings moved, all within Portal; all 506 districts unchanged |
| Fresh vs previous UCG | Identical canonical bytes |
| New graph + previous default-scene hint | Exactly reproduces previous default city bytes |
| Final source-linked routes | 4,209 routes / 6,157 edges preserved; intersections and unresolved eligible edges: 0 |

The default-to-parcel experiment moves 35 Ops buildings in both old and fresh
pipelines. This is a separate, explicit layout stage, not repeat-run drift.
Previous historical builds used layout hints; omitting them explains the 58
Portal differences. Route identities remain exact, but 2,681 route polylines
differ after whole-city planning on the changed geometry. This is deterministic
replanning, **not** a claim of local road stability across different layout inputs.

The new full-trip pass still hits its 12M-state limit and accepts 372 entrance
changes. Compared with its own gateway baseline, centerline length falls
26,865.5 → 23,918.5 and nearby parallel length 4,742.5 → 2,495.5. Against the previous
displayed result, however, bends rise 22,642 → 23,341 and junctions 1,402 → 1,420;
do not call the cold rebuild a visual optimization or an improvement in every metric.

Local artifacts (not published or committed):

- `artifacts/visual/clean-rebuild-r1/gj/run1/roads/after/index.html`
- `artifacts/visual/clean-rebuild-r1/gj/verification.json`
- `artifacts/visual/clean-rebuild-focus-r1/index.html` — identical-camera comparison
- `artifacts/visual/clean-rebuild-audit-r2/index.html` — final interactive audit
