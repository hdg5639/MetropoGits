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

## Checkpoint 2026-10-17 — Maven manifest evidence (`4401455`)

- Implemented: bounded parsing of direct Maven `pom.xml` dependencies; stable
  `MODULE` and `EXTERNAL_PACKAGE` entities; evidence-backed `DEPENDS_ON` edges;
  conservative rejection of malformed XML, DOCTYPE declarations, interpolated
  coordinates, dependency-management entries, and plugin dependencies.
- Fixture(s) / revision(s):
  `tests/fixtures/repositories/maven-manifest` at synthetic revision
  `fixture-1`, containing one Java source file and one duplicated direct Maven
  dependency. Duplicate declarations collapse to one dependency fact.
- Commands run: two identical `python -m metropogits build --repo
  tests/fixtures/repositories/maven-manifest --repo-id
  fixture/maven-manifest --revision fixture-1 --source-url
  https://github.com/example/maven-manifest/tree/fixture-1 --out <artifact-dir>`
  builds; UCG and City validators; Chrome headless captures at `1440x900` and
  `1200x675`; `ruff check metropogits scripts tests`; `python -m compileall -q
  metropogits scripts tests`; `python -m unittest discover -s tests -v`;
  `python -m pip check`; readiness validation; and `node --check` for each
  viewer JavaScript asset.
- Artifacts inspected: `graph.ucg.json`, `city.json`, `preview.svg`,
  `index.html`, `maven-viewer.png`, and `maven-preview.png` under
  `C:\WINDOWS\TEMP\metropogits-maven-42812c4213694fadbed291a96c4b86da`.
  The graph contains one `MANIFEST` evidence record from `pom.xml`, one
  `MODULE -> EXTERNAL_PACKAGE` dependency, and no manifest-derived technology
  claim or visual network.
- Visual findings: the one generic Java building renders without clipping in
  both targets, and the intentionally non-runtime manifest dependency creates
  no misleading road. The sparse fixture exposes excessive empty district
  area around a single deeply nested building; this is a pre-existing layout
  quality issue and should be corrected separately.
- Spec alignment: DEVIATION. This slice satisfies the Maven portion of FR-003,
  preserves DEC-003/DEC-005 and the explicit-manifest `DEPENDS_ON` rule, and
  keeps declarations distinct from actual usage under FR-009. Gradle and npm
  manifests plus declared-versus-used resolution remain incomplete, so FR-003
  and FR-009 stay blocked.
- Tests / determinism / stability: 160 tests passed and one symlink test was
  skipped because symbolic links are unavailable. Both builds produced the
  same SHA-256 values: `5d631ba5a844e62cf9d4cfe8ba8ef0b9868da5b44dad29e531ae3a12016b797d`
  for `graph.ucg.json`,
  `508fb699de5f09dac3cc8ca85821e6a0b9489afa933619eeb65bad95fd75f808`
  for `city.json`, and
  `41f436635742c65d940378ea86179053461bba23fff820b68013002fb72c3f9c`
  for `preview.svg`. Lint, bytecode compilation, dependency consistency,
  readiness validation, JavaScript parsing, and both contract validators pass.
- Fixes applied and reverified: shared dependencies across multiple Maven
  manifests now reuse one external-package entity; a dedicated regression test
  proves the resulting UCG remains valid. The Chrome command was corrected
  after an initial PowerShell argument-splatting error, and both images were
  then generated and inspected.
- Open risks / next actions: implement bounded Gradle and npm manifest facts,
  then add evidence intersection for declared-versus-used technology. Track a
  separate sparse-layout correction so tiny repositories do not render inside
  disproportionately large districts. Existing road endpoint, dense SVG label,
  2D-versus-3D renderer, hosted-runner, and license risks remain open.
- Commits created / pushed (and branch): `4401455` on local `main`; push is
  scheduled after this checkpoint log commit and final repository-state check.

## Checkpoint 2026-10-17 — Gradle manifest evidence (`be96b73`)

- Implemented: non-executing extraction of literal Maven-style coordinates
  from `dependencies {}` blocks in `build.gradle` and `build.gradle.kts`;
  comment, string, and brace-aware lexical scoping; Gradle-specific manifest
  evidence attached to stable package dependencies.
- Fixture(s) / revision(s):
  `tests/fixtures/repositories/gradle-manifest` at synthetic revision
  `fixture-1`, with one Kotlin source file, one direct external dependency, one
  project dependency, and one commented near-match.
- Commands run: three equivalent `python -m metropogits build --repo
  tests/fixtures/repositories/gradle-manifest --repo-id
  fixture/gradle-manifest --revision fixture-1 --source-url
  https://github.com/example/gradle-manifest/tree/fixture-1 --out
  <artifact-dir>` builds; UCG and City validators; Chrome headless viewer and
  SVG captures; full lint, compile, unit-test, dependency, readiness, and
  JavaScript-parse gates. After tightening multiline-string handling, the
  scanner suite and end-to-end fixture build were rerun.
- Artifacts inspected: `graph.ucg.json`, `city.json`, `preview.svg`,
  `index.html`, `gradle-viewer.png`, and `gradle-preview.png` under
  `C:\WINDOWS\TEMP\metropogits-gradle-20e4f3856db441e0afdc9d7c96909924`.
  The graph contains one direct `MODULE -> EXTERNAL_PACKAGE` edge backed by
  `manifest.gradle/0.1`; the project dependency and commented coordinate do not
  appear.
- Visual findings: both render targets show the single generic Kotlin building
  without clipping and correctly omit a road for the declaration-only package.
  The stable hash slot places this lone building near the district corner, and
  the deep source path again produces excessive empty space in a sparse city.
- Spec alignment: DEVIATION. Maven and Gradle now cover two principal JVM
  manifest forms while preserving no-execution, exact evidence, stable IDs,
  and declaration-versus-runtime separation. npm parsing and the cross-layer
  declared-versus-used resolver are still missing, so FR-003 and FR-009 remain
  blocked.
- Tests / determinism / stability: the full suite passed 162 tests with one
  unavailable-symlink skip. The final scanner suite passed 14 tests with the
  same skip after multiline-string hardening. Repeated artifacts retained
  SHA-256 `2e0773286dd8b7f2b9ffe2fef5907d8152b23133770c616c792e75115c608338`
  for `graph.ucg.json`,
  `7fc00e11f03012efe04117728ccb326b6fdeb6363c56bf792d795ab298d53f75`
  for `city.json`, and
  `ab2b8e1361fc3733d9210d32f595cf7de7b8778d33be017258eee6ca09359cf9`
  for `preview.svg`.
- Fixes applied and reverified: dependency-block membership is evaluated at
  each call position, so a call after a same-line closing brace is ignored;
  Groovy triple-quoted strings cannot inject fake dependency blocks. Both
  cases have regression coverage and the maintained fixture hash is unchanged.
- Open risks / next actions: add bounded npm `package.json` parsing, then join
  manifest coordinates with code-use evidence without promoting declarations
  alone. Correct sparse single-building placement as a separate layout unit.
  Existing road endpoint, dense SVG label, 2D-versus-3D renderer,
  hosted-runner, and license risks remain open.
- Commits created / pushed (and branch): `be96b73` on local `main`; push is
  scheduled after this checkpoint log commit and final repository-state check.
