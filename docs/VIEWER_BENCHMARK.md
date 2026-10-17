# Controlled WebGL comparison

VIS-06 baseline, 2026-10-18. Viewer under test: `dc10c1a`.
This is a local development audit, not a performance SLA or public demo.

## Reproduce

Use Node 22+ (built-in WebSocket) and a locally installed Chromium browser.
The product and normal test suite do not require a browser installation.
Build the inputs with this checkout first; use only trusted artifacts generated
locally by MetropoGits, not arbitrary downloaded HTML/JavaScript.

```powershell
node scripts/viewer_audit.mjs "C:\Program Files\Google\Chrome\Application\chrome.exe" ../artifacts/visual/comparison-new ../artifacts/visual/showcase-20261018/gj ../artifacts/visual/showcase-20261018/oj
node --test tests/viewer_audit.test.mjs
```

The output directory must not exist. Open its `index.html` to compare captures;
`report.json` contains raw samples, source artifact SHA-256 hashes, browser/OS/CPU
versions, actual WebGL renderer, camera state, counts and labels. Repeat with
the input order reversed and a fresh output directory. Do not run heavy builds
or tests concurrently with timing collection.

The harness copies prepared viewer assets into the output directory and inserts
an audit bridge **only into that copy**. The five executable/style asset files
must match the checkout; marker drift fails instead of silently measuring the
wrong code. This is not a security sandbox: HTML/data must also be trusted.
No hook is shipped in the normal viewer, and original assets, canonical City,
UCG, manifest and source repositories are not edited. These instrumented copies
are development captures, not distributable build bundles.

A fresh isolated browser profile and loopback debugging port are used. The
owned browser closes on completion/failure. Its temporary profile path is
reported and retained for diagnosis; no user's browser profile is touched.
Generated reports include local paths and architecture metadata: keep them
local unless separately reviewed for publication.

## Controls and measurement limits

- Browser viewport: 1280×800, device scale factor 1. Actual city canvas:
  940×558 after shared toolbar/inspector layout.
- Camera yaw −0.68, pitch 0.62, common field of view π/4; synthetic activity off.
- Normalized comparison uses each city's original fitted distance, then zoom
  ratios 1 / 1.6 / 2.5. These invoke **natural** Overview / District / Detail
  transitions. Fit-relative zoom is not identical pixel occupancy or world scale.
- Absolute comparison uses distance 774.096921822578 for both cities, each
  centered on its own bounds, and explicitly fixes Overview. City coordinates
  and per-city target height remain unchanged. This isolates the world-scale
  difference; it does not stretch the smaller city to match the larger one.
- Each LOD gets actual CDP mouse orbit/wheel events, 5 warm-up draws followed by
  20 measured draws per interaction. Camera movement and natural LOD are checked.
- `cpuMs` measures the instrumented JavaScript render callback through draw
  submission and label creation. Stages separate geometry preparation (including
  LOD/matrix update), buffer/draw submission, hit regions, and label DOM work.
- `inputToSubmitMs` starts before the CDP mouse command, so includes automation
  transport/scheduling. Neither metric measures completed GPU rendering or
  physical input-to-display latency. Draws are paced one per input; **do not
  convert these values into sustained FPS**. Static idle rendering is on demand.
- `firstDrawSubmittedMs` is navigation performance time at the first completed
  callback, not first presented pixels. Startup/cache order strongly affects it.
- Counts mean objects submitted by LOD, not objects within the visible frustum.
  District/detail screenshots intentionally crop the outskirts when zoomed in.
- PNG bytes and timings are environment-dependent; they are not canonical
  determinism assertions. Canonical City/UCG hashes and submitted geometry are
  the repeatability baseline.

## Corpus and actual results

Existing full-pipeline outputs from `showcase-20261018` were reused unchanged:

| Input | Source revision | Buildings / districts / networks |
| --- | --- | --- |
| GJ-Cloud (GamjaBox) | `3d9b53f9dac9af1187ac9754cb3066b27e43b766` | 1324 / 506 / 135 |
| GamjaOJ | `b163acd2b5fe41edfc1e7fc7d367362851241896` | 681 / 117 / 31 |

Environment: Windows 10.0.26200, i9-11900KF, Node 24.15.0,
Chrome 152.0.7977.84, ANGLE Vulkan SwiftShader. **Software WebGL**, not a
hardware-GPU claim. Reports/captures are local under the workspace, outside Git:

- `artifacts/visual/comparison-20261018-r2/`: GJ then OJ, full stage timings.
- `artifacts/visual/comparison-20261018-reverse/`: OJ then GJ, same final protocol.
- `artifacts/visual/comparison-20261018/`: exploratory run before stage timing;
  not combined with the two baseline runs below.

| City / LOD | Individual buildings | Blocks / represented files | Routes | Triangles submitted |
| --- | ---: | ---: | ---: | ---: |
| GJ Overview | 0 | 37 / 1324 | 24 | 31794 |
| GJ District | 640 | 0 / — | 64 | 41760 |
| GJ Detail | 1324 | 0 / — | 135 | 70816 |
| OJ Overview | 0 | 30 / 681 | 24 | 13638 |
| OJ District | 409 | 0 / — | 31 | 21216 |
| OJ Detail | 681 | 0 / — | 31 | 30628 |

Ranges below are the two run results, **not confidence intervals**. P95 is the
nearest-rank 19th of 20 measured samples. Median uses the upper middle sample
for even sample counts; do not infer statistical guarantees.

| City / LOD | Orbit CPU median ms | Orbit CPU p95 ms | Wheel CPU p95 ms | Orbit input→submission p95 ms |
| --- | ---: | ---: | ---: | ---: |
| GJ Overview | 26.1–28.6 | 31.6–35.8 | 28.1–28.5 | 33.3–41.9 |
| GJ District | 25.4–29.0 | 27.7–80.3 | 31.3–33.0 | 31.7–82.2 |
| GJ Detail | 54.9–55.3 | 87.3–98.5 | 85.4–93.8 | 95.0–100.9 |
| OJ Overview | 10.1–12.6 | 14.2–18.7 | 9.8–11.2 | 18.7–24.0 |
| OJ District | 14.3–15.6 | 18.6–19.4 | 12.5–16.2 | 24.5–25.1 |
| OJ Detail | 18.8–22.4 | 22.3–26.9 | 21.9 | 24.9–31.0 |

First draw submission: GJ 842.7 ms first / 213.4 ms second, OJ 635.2 ms first /
163.3 ms second. This order sensitivity prevents attributing initialization
differences solely to repository size. No controlled cold-start conclusion.

GJ Detail geometry-preparation p95 was 78.2 / 90.8 ms; median total callback
was about 55 ms in both orders. This identifies repeated geometry preparation
as the main measured CPU cost, rather than proving the GPU is slow. Individual
stage percentiles are not additive. District p95 variance also warrants more
samples before any hard threshold or regression gate is introduced.

## Visual observations and next work

All eight main captures (two cities × three natural LODs + common scale) were
opened and inspected. The common-scale view still distinguishes the sprawling
GJ service groups from compact OJ blocks; the difference is not just an arbitrary
camera zoom. Overview represents every file through traceable block membership;
it does not show individual files. District selects 640/409 buildings and Detail
submits all 1324/681, as expected.

Confirmed issues:

1. The lower legend overlaps real city content in **both fitted Overview views**.
   This is an avoidable UI framing issue, unlike the intentional crop after zoom.
2. OJ still has two indistinguishable `tests` labels in Overview/District.
   Showcase has context labels, but WebGL has not adopted them yet.
3. Structural street surfaces are visible, while relation routes still look like
   fine circuit traces. The structural/evidence distinction needs stronger
   visual hierarchy, not a new inferred relationship system.
4. Generic silhouettes remain dominant; semantic groups are easier to identify
   through color than shape. This confirms VIS-04 remains necessary.
5. GJ Detail has a repeatable CPU bottleneck. Current rendering rebuilds world
   geometry on every orbit even when only the camera changed.

Next slices: cache unchanged geometry/buffers with explicit invalidation for
LOD, filters, selection and synthetic activity; reserve space for the legend;
then VIS-03 road hierarchy and VIS-04 silhouette legibility, followed by context
labels. Preserve all memberships and canonical positions. Measure before/after
with this harness; do not disguise performance problems by removing facts.

This task establishes the comparison tool and baseline only. It does not claim
to have fixed these defects, measured native GPU FPS, or enabled Pages.

## Follow-up checkpoint: 1.14 frontage and internal streets

Geometry reuse (`86b50a9`) and a separate legend row (`9779393`) address items
5 and 1 above. ADR-014 adds internal circulation and evidence-aware local sites.
The duplicate WebGL `tests` labels and aggregate silhouette proportions remain
open; do not interpret this as completion of all visual work.

Fresh full builds: workspace `artifacts/visual/frontage-streets-r4/{gj,oj}`.
Controlled captures: `frontage-streets-r4-audit`; isolated timing rerun (no
concurrent build/test): `frontage-streets-r4-timing`. Same harness and viewport,
three natural LODs and common scale. GJ/OJ Overview and Detail screenshots plus
both CPU showcases were inspected. Streets now pass between building groups,
not just around major service outlines. Zoomed Detail deliberately crops the
city; fitted Overview no longer has legend overlap. Fine relation traces and
thin aggregate towers still need work, with no new semantic claims introduced.

| Orbit callback CPU p95 (ms) | Overview | District | Detail |
| --- | ---: | ---: | ---: |
| GJ | 3.1 | 2.3 | 5.4 |
| OJ | 1.2 | 1.7 | 2.1 |

First draw submission: GJ 730.9 ms, OJ 135.6 ms. These are single-order software
renderer observations, not GPU FPS or a cold-start SLA. Reproduce and reverse
order for broader performance conclusions. Canonical layout changed in 1.14,
so this final run is not a cache-only controlled A/B; the earlier cache-specific
checkpoint used unchanged scenes.
