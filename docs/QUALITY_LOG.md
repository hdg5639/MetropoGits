# Quality checkpoints

## Checkpoint 2026-10-17 — layout and viewer work through `ff651d9`

- Implemented: previous-scene layout hints; hierarchical and paged district
  geometry; empty-directory chain compaction; larger, outlined buildings;
  adaptive district-label decluttering; balanced sibling packing; centered SVG
  preview composition.
- Fixture(s) / revision(s): `tests/fixtures/repositories/spring-positive`,
  `tests/fixtures/repositories/jsts-basic`, and the MetropoGits repository at
  `ff651d9`. The first is a small semantic Spring city, the second is a
  low-semantic JS/TS fallback city, and the third is a medium mixed repository.
- Commands run: `python -m metropogits build --repo <fixture> --repo-id
  <fixture-id> --out <artifact-dir>` for all three inputs; a second identical
  Spring build; Chrome headless captures at `1440x900` for viewers and
  `1200x675` for SVG previews; `python -m pip check`; `python -m ruff check .`;
  `python -m compileall -q metropogits scripts tests`; `python -m unittest
  discover -s tests -v`; `python -m metropogits validate --input
  release/readiness.json`; and `node --check` for every JavaScript asset.
- Artifacts inspected: generated `index.html`, `preview.svg`, `graph.ucg.json`,
  `city.json`, and `manifest.json` under
  `C:\WINDOWS\TEMP\metropogits-checkpoint-ox5j05yh.x5y\after`. Browser captures
  inspected were `spring-viewer.png`, `spring-preview.png`,
  `jsts-current.png`, `metropogits-viewer.png`, and
  `metropogits-preview.png`.
- Visual findings: role colors and building heights distinguish the six Spring
  buildings; the JS/TS fixture remains a readable generic fallback; viewer
  labels no longer form a path stack; and both the medium viewer and README SVG
  use the viewport more evenly. Roads remain visually detached from their
  contributing buildings because routes currently terminate at district
  centers. Some long district labels still collide in the dense SVG preview.
- Spec alignment: DEVIATION. Evidence, determinism, local-only execution,
  unknown fallback, scene contracts, and grounded network IDs remain intact.
  The interactive renderer is still a 2D canvas rather than the DEC-009 3D
  target, and P0 manifest/config analysis for FR-003 and FR-009 is not yet
  implemented; both are already tracked as explicit blockers.
- Tests / determinism / stability: 156 tests passed; one symlink test was
  skipped because symbolic links are unavailable in this environment. Two
  Spring builds produced identical SHA-256 values:
  `02f01a2a27cd70b7baa25de1ffddc4ee9a41eb6b51a2d161bbe32a53a3ef5f47`
  for `graph.ucg.json`,
  `d0bb4a2e9009d65991b6c51270c5fb4db99040982117a78bec547f735879f704`
  for `city.json`, and
  `d4fe612651fe1a355ec95b2a29ae92125b4907d556321dd5ebed452ede382576`
  for `preview.svg`. Hint-based file and district churn tests passed.
- Fixes applied and reverified: the medium fixture's root footprint improved
  from `432x752` under layout 1.2 to `480x752` under layout 1.3, avoiding a
  second full-height row; SVG content is centered in unused canvas space. New
  mixed-size packing and centered-preview regression tests pass, and the actual
  outputs were recaptured after the fixes.
- Open risks / next actions: implement bounded Maven, Gradle, and npm manifest
  facts before further optional scope; then connect declared-versus-used
  technology resolution. Improve network endpoints so grounded roads visibly
  meet their contributing buildings, add SVG label decluttering, obtain the
  DEC-009 renderer decision, verify AC-010 on a hosted runner, and select a
  project license.
- Commits created / pushed (and branch): local `main` contains `890d69e`,
  `423543f`, `2dad35a`, and `ff651d9`; push is scheduled immediately after the
  checkpoint log commit and final repository-state verification.
