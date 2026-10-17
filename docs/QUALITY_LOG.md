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

## Checkpoint 2026-10-17 — npm manifest evidence (`aea2d34`)

- Implemented: strict, bounded `package.json` dependency parsing across
  runtime, development, optional, and peer sections; npm package entities and
  manifest-backed dependency edges; reuse of the same package entity when a
  JS/TS file also imports the declared package.
- Fixture(s) / revision(s): `tests/fixtures/repositories/npm-manifest` at
  synthetic revision `fixture-1`, with one imported `react` dependency, one
  declaration-only `redis` dependency, a scoped development dependency, a
  duplicate declaration, and a deliberately harmful `postinstall` script.
- Commands run: two identical `python -m metropogits build --repo
  tests/fixtures/repositories/npm-manifest --repo-id fixture/npm-manifest
  --revision fixture-1 --source-url
  https://github.com/example/npm-manifest/tree/fixture-1 --out <artifact-dir>`
  builds; explicit marker check; UCG and City validation; Chrome headless
  viewer and SVG captures; lint, compilation, 165-test full suite, dependency
  consistency, readiness validation, and JavaScript syntax checks.
- Artifacts inspected: `graph.ucg.json`, `city.json`, `preview.svg`,
  `index.html`, `npm-viewer.png`, and `npm-preview.png` under
  `C:\WINDOWS\TEMP\metropogits-npm-cd659c4ac49e48c4a286c5e712c03e9e`.
  `react` has separate `DEPENDS_ON` and `IMPORTS` edges to one package entity;
  `redis` has only `DEPENDS_ON`; no technology claim is fabricated.
- Visual findings: the generic JS building renders cleanly and no manifest or
  external-package edge is misrepresented as an internal runtime road. The
  sparse city still allocates excessive district space and places its lone
  building near a corner, confirming the previously logged layout issue.
- Spec alignment: DEVIATION. The scanner now covers the three planned manifest
  families—Maven, Gradle, and npm—without executing scripts, and the graph
  structurally distinguishes declaration from observed import usage. FR-003
  readiness has not yet been changed pending a dedicated traceability audit;
  FR-009 remains incomplete until catalog resolution consumes both evidence
  classes and exposes the distinction to users.
- Tests / determinism / stability: 165 tests passed with one unavailable
  symlink skip. Repeated builds produced SHA-256
  `1605ccf2e159aeade6c6cc9edb66dbcaf6e435bcb14d240e16a503d9f5b39eee`
  for `graph.ucg.json`,
  `7d9f4155c97642bc01533b4d92899238cfcf7a8fba686b7da721e94b78bdc037`
  for `city.json`, and
  `c1107eb5b179a406ba249d03f93cf4fb1cbf3e409f220776273a761a8e6abbcd`
  for `preview.svg`. The fixture's `executed.marker` remained absent.
- Fixes applied and reverified: JS/TS enrichment now reuses manifest-created
  external package entities instead of emitting duplicate IDs. Duplicate JSON
  keys reject the manifest safely; file, link, workspace, and npm-alias
  specifiers remain outside external package facts. Positive and negative
  cases pass in scanner and JS/TS integration tests.
- Open risks / next actions: audit FR-003 readiness evidence, then connect
  manifest facts to catalog code signatures so declared-only packages cannot
  become active facilities. Add viewer inspection for external dependencies
  without turning them into runtime roads, and separately correct sparse
  layout placement. Existing dense SVG label, road endpoint, 2D-versus-3D,
  hosted-runner, and license risks remain open.
- Commits created / pushed (and branch): `aea2d34` on local `main`; push is
  scheduled after this checkpoint log commit and final repository-state check.

## Checkpoint 2026-10-17 — catalog evidence intersection (`b404ff6`)

- Implemented: conversion of manifest dependency edges into catalog facts for
  the closest enclosing module; Java annotation facts supplied to the catalog;
  deterministic merging of identical claims so code and manifest provenance
  remain on one role or technology claim.
- Fixture(s) / revision(s):
  `tests/fixtures/repositories/spring-manifest-usage` at synthetic revision
  `fixture-1`, containing a root Maven declaration and one exact Spring
  `@Service` usage. A temporary sibling-directory fixture verifies that a
  manifest outside the source hierarchy is not borrowed.
- Commands run: two identical `python -m metropogits build --repo
  tests/fixtures/repositories/spring-manifest-usage --repo-id
  fixture/spring-manifest-usage --revision fixture-1 --source-url
  https://github.com/example/spring-manifest-usage/tree/fixture-1 --out
  <artifact-dir>` builds; graph claim/evidence inspection; UCG and City
  validation; Chrome headless viewer and SVG captures; lint, compilation,
  168-test full suite, dependency consistency, readiness validation, and
  JavaScript syntax checks.
- Artifacts inspected: `graph.ucg.json`, `city.json`, `preview.svg`,
  `index.html`, `catalog-viewer.png`, and `catalog-preview.png` under
  `C:\WINDOWS\TEMP\metropogits-catalog-5d38f2531e1349cfa91a8057fa137216`.
  The service has one `SERVICE` role and one `SPRING_FRAMEWORK` technology
  claim; each references exact `ANNOTATION`, `IMPORT`, and `MANIFEST` evidence.
- Visual findings: both render targets show the verified service color and
  height without clipping or invented network roads. As in the other one-file
  fixtures, the district remains much larger than its content; the sparse
  layout correction remains warranted.
- Spec alignment: DEVIATION. The implementation now enforces the specified
  manifest-plus-code catalog intersection for the Spring service rule and
  preserves closer-module scope, stable evidence, and declaration-only
  fallback. Most catalog rules still lack package coordinates, configuration
  facts are absent, and declared-only status is not exposed in the viewer, so
  FR-009 remains blocked.
- Tests / determinism / stability: 168 tests passed with one unavailable
  symlink skip. Repeated builds produced SHA-256
  `6021f00cf6d1155924f8908e14c1a1320f4dfd406d674b664905c998e1f27642`
  for `graph.ucg.json`,
  `51c40ce6954ffa9f88b55e85ee17f73c8ed9296f5adcb01e4a1a4346d8b5b2cf`
  for `city.json`, and
  `b3e71c539d108bb91eecaa8a4af23db85cec067cfe60defb47ec08a12795ece8`
  for `preview.svg`. All contract and auxiliary gates passed.
- Fixes applied and reverified: identical hard-coded and catalog Spring claims
  now merge evidence IDs instead of producing duplicate semantic claims. The
  closest-manifest scope and sibling exclusion have dedicated passing tests.
- Open risks / next actions: add exact package coordinates to eligible catalog
  rules with updated positive/negative fixtures, keeping declared-only Redis
  from becoming an active cache facility. Then implement bounded configuration
  facts and expose dependency evidence in the inspector. The sparse layout,
  dense SVG labels, road endpoints, 2D-versus-3D decision, hosted runner, and
  project license remain open.
- Commits created / pushed (and branch): `b404ff6` on local `main`; push is
  scheduled after this checkpoint log commit and final repository-state check.

## Checkpoint 2026-10-17 — catalog 0.3.0 (`2676c84`)

- Implemented: immutable catalog `0.3.0`; exact Maven coordinates and required
  manifest evidence for Spring RestClient, Kafka, MongoDB, RabbitMQ, and Redis
  direct-use rules; preserved validation of catalog `0.1.0` and `0.2.0`.
- Fixture(s) / revision(s): `tests/fixtures/repositories/technology-positive`
  and `technology-declared-only` at synthetic revision `fixture-1`. Both
  declare the same five packages; only the positive fixture imports their
  exact code signatures. Matching and lookalike catalog fixtures include the
  same declaration precondition.
- Commands run: two identical positive `python -m metropogits build` runs and
  one declared-only build; UCG and City validation for both outcomes; graph
  claim counts; Chrome headless captures for the positive viewer/SVG and the
  declared-only viewer; catalog validation; full lint, compile, 169-test,
  dependency, readiness, and JavaScript syntax gates.
- Artifacts inspected: positive and declared-only `graph.ucg.json`,
  `city.json`, `preview.svg`, and `index.html`, plus `positive-viewer.png`,
  `positive-preview.png`, and `declared-viewer.png` under
  `C:\WINDOWS\TEMP\metropogits-catalog-030-dc6db118422f433096116b8f76239177`.
  The positive graph has five technology claims; the declaration-only graph
  has five dependency edges and zero technology claims.
- Visual findings: the positive city displays five distinct specialized
  archetype/color outcomes, while the same declarations without code usage
  produce a single gray generic building. Neither case invents runtime roads.
  The five-building composition is readable, but stable hashed cells leave
  uneven gaps; the one-building negative retains the known sparse-layout issue.
- Spec alignment: DEVIATION. Catalog-only declarations no longer assert active
  Redis, MongoDB, Kafka, RabbitMQ, or RestClient facilities, satisfying the
  central FR-009 negative behavior for the bundled mappings. Configuration and
  lockfile facts remain absent, declared dependencies are not yet visible in
  the inspector, and the 2D viewer still deviates from DEC-009.
- Tests / determinism / stability: 169 tests passed with one unavailable
  symlink skip. Positive builds produced identical SHA-256
  `71ad55a0874c88f51a19bad447096879d8c43cc54cc1ffc8788972132cef2409`
  for `graph.ucg.json`,
  `a2ad3212b55cb7d7f1ec9cab46234fd38b684aa980fba95d47032ebf80b3ca8d`
  for `city.json`, and
  `7dd6164639aefff295a61881b0579643fe8f3999e2acd8c60b74153077955272`
  for `preview.svg`. Both positive and declared-only contracts validated.
- Fixes applied and reverified: an accidental leading patch marker in the new
  repository POM fixtures caused manifest rejection and was caught by the Java
  integration tests; it was removed before commit, the targeted suites passed,
  and the full gates were rerun. Trailing blank lines reported by Git's
  whitespace check were removed before finalizing the feature commit.
- Open risks / next actions: audit whether FR-009 can now leave `BLOCKED`, then
  add bounded lockfile and non-secret configuration facts for FR-003. Expose
  declared dependencies in the inspector without drawing runtime roads, and
  correct sparse placement. Dense SVG labels, road endpoints, the 3D decision,
  hosted runner, and project license remain open.
- Commits created / pushed (and branch): `2676c84` on local `main`; push is
  scheduled after this checkpoint log commit and final repository-state check.

## Checkpoint 2026-10-17 — npm lockfile analysis (`78f7fe6`)

- Implemented: bounded strict-JSON parsing for npm `package-lock.json` v2/v3;
  extraction limited to the root `packages[""]` dependency sections; explicit
  rejection of legacy structures that cannot distinguish direct dependencies
  conservatively.
- Fixture(s) / revision(s): `tests/fixtures/repositories/npm-lockfile` at
  synthetic revision `fixture-1`, with two direct root packages and one nested
  transitive-only package. A temporary v1 lockfile covers the unsupported path.
- Commands run: two identical `python -m metropogits build --repo
  tests/fixtures/repositories/npm-lockfile --repo-id fixture/npm-lockfile
  --revision fixture-1 --source-url
  https://github.com/example/npm-lockfile/tree/fixture-1 --out <artifact-dir>`
  builds; UCG and City validation; graph package/evidence inspection; Chrome
  headless viewer and SVG captures; lint, compilation, 171-test full suite,
  dependency consistency, readiness validation, and JavaScript syntax checks.
- Artifacts inspected: `graph.ucg.json`, `city.json`, `preview.svg`,
  `index.html`, `lockfile-viewer.png`, and `lockfile-preview.png` under
  `C:\WINDOWS\TEMP\metropogits-lockfile-48155fb9301f4a599016e3ed89339ad2`.
  Only `npm/react` and `npm/@types/node` exist as packages; the nested
  `transitive-only` entry is absent. Evidence identifies
  `manifest.npm-lock/0.1` and the lockfile source path.
- Visual findings: both render targets retain one generic JS building and draw
  no lockfile dependency as a runtime road. The stable hash slot again leaves
  a small repository visually sparse, consistent with the tracked layout risk.
- Spec alignment: DEVIATION. The supported lockfile is parsed without running
  npm or lifecycle scripts, observes the same resource bounds as source and
  manifest files, and does not inflate transitive packages into direct facts.
  Other lockfile families and bounded configuration facts remain absent, so
  FR-003 stays blocked.
- Tests / determinism / stability: 171 tests passed with one unavailable
  symlink skip. Repeated builds produced SHA-256
  `e71d0abd92faf7c66d3546c9dffc80ad7ebf006bbdeabe106d7dc24f53bb9b66`
  for `graph.ucg.json`,
  `12851bbe1e779fe1f768b4a44d31c58ec4a62525017a0b9919752d3231604034`
  for `city.json`, and
  `827d41a6e0f7367b239059d754d1c20894d0f91aec865ea14bc3ef78135307ac`
  for `preview.svg`. All auxiliary gates and contracts passed.
- Fixes applied and reverified: the parser shares npm package-name and local
  specifier policy with `package.json`; duplicate keys, malformed sections,
  and missing root package entries fail safely. Positive and legacy-negative
  tests pass.
- Open risks / next actions: add bounded non-secret configuration facts and
  decide whether additional lockfile families are necessary for FR-003. Expose
  declaration facts in the inspector and correct sparse placement. Dense SVG
  labels, road endpoints, the 3D decision, hosted runner, and license remain
  open.
- Commits created / pushed (and branch): `78f7fe6` on local `main`; push is
  scheduled after this checkpoint log commit and final repository-state check.

## Checkpoint 2026-10-17 — safe configuration evidence (`ffd4276`)

- Implemented: bounded UTF-8 parsing of Spring `application*.properties`, an
  allowlist that emits only the non-secret PostgreSQL driver signature, nearest
  module scoping, and catalog `0.4.0` classification that requires the exact
  driver dependency, verified `JpaRepository` inheritance, and configuration
  signature together.
- Fixture(s) / revision(s):
  `tests/fixtures/repositories/postgresql-config` at synthetic revision
  `quality-check`. The fixture includes a password value specifically to prove
  that raw secret keys and values never enter generated graph data.
- Commands run: two identical `python -m metropogits build --repo
  tests/fixtures/repositories/postgresql-config --repo-id fixture/postgresql
  --revision quality-check --out <artifact-dir> --json` builds; UCG claim and
  evidence inspection; Edge headless viewer and SVG captures; Ruff,
  `compileall`, the 174-test full suite, dependency consistency, catalog and
  release-readiness validation, JavaScript syntax checks, and Git whitespace
  checks.
- Artifacts inspected: `graph.ucg.json`, `city.json`, `preview.svg`,
  `index.html`, `viewer.png`, and `preview.png` under
  `C:\WINDOWS\TEMP\metropogits-config-3d41730f67c045b189995344af4e8452`.
  The repository building exposes `POSTGRESQL`, `RELATIONAL_DB`, and
  `PERSISTENCE_ADAPTER` with CONFIG, INHERITANCE, and MANIFEST evidence. The
  password key and value are absent.
- Visual findings: the persistence building uses the expected green archetype
  in both render targets. The one-building fixture also confirms the known
  sparse-layout defect: its district consumes most of the viewport and the
  viewer projection makes the lone building disproportionately tall.
- Spec alignment: PASS for the scanner/config/catalog slice. Configuration is
  bounded and non-executing, evidence summaries contain no raw values, and JPA
  or a PostgreSQL declaration alone cannot establish the engine. FR-003
  readiness still needs a dedicated traceability update after this checkpoint.
- Tests / determinism / stability: 174 tests passed with one unavailable
  symlink skip. Repeated builds produced identical SHA-256
  `7c8ea3610dd3a28c92aabe522db2bb462f966ae8def8b6de8edd260c84a2f007`
  for `graph.ucg.json`,
  `a7dbcd432a18fe80961aa9b7b3bdc885c5ed8c50b2046cd8efa25a7322e39b30`
  for `city.json`, and
  `ee0d542eac58d17298ee1d6c3336562659af0ac5d88a4996a622534881e87772`
  for `preview.svg`.
- Fixes applied and reverified: the initial configuration scope followed the
  physical `src/main/resources` directory and therefore could not reach Java
  sources under `src/main/java`; scoping now maps the conventional resource
  directory back to its module root, and the focused and full suites pass.
- Open risks / next actions: update FR-003 readiness, then fix the confirmed
  sparse-layout defect. Declared-dependency inspector visibility, dense SVG
  labels, road endpoints, DEC-009, hosted runner evidence, and the project
  license remain open.
- Commits created / pushed (and branch): `ffd4276` on local `main`; push is
  scheduled after this checkpoint log commit and final repository-state check.

## Checkpoint 2026-10-17 — sparse city layout (`445a254`)

- Implemented: layout `hierarchical-paged/1.4`, which compacts unused leading
  rows and columns in cold building pages, sizes the final occupied area with a
  24 by 24 minimum district, preserves positions from valid 1.4 hints, and caps
  the viewer's initial fit scale for very small cities.
- Fixture(s) / revision(s):
  `tests/fixtures/repositories/postgresql-config` at synthetic revision
  `sparse-check`, plus generated 1, 65, 100, and 1,000-file layout fixtures and
  the existing collision/hint stability fixtures.
- Commands run: two identical end-to-end CLI builds; layout, viewer, governance,
  preview, and full test suites; UCG/City validation through the build; Edge
  headless viewer and SVG captures; Ruff, `compileall`, dependency consistency,
  release-readiness validation, JavaScript syntax checks, and Git whitespace
  checks.
- Artifacts inspected: `graph.ucg.json`, `city.json`, `preview.svg`,
  `index.html`, `viewer.png`, and `preview.png` under
  `C:\WINDOWS\TEMP\metropogits-sparse-final-7c203071908647db828e97582b3d4da4`.
  The single occupied district is now 24 by 24 with the building at local
  coordinates 6,6; the prior checkpoint used a 64 by 64 lot.
- Visual findings: the viewer now presents a centered, legible small lot and
  building instead of a viewport-filling empty district and oversized tower.
  The SVG preserves a larger README-safe projection, where the building takes
  one quarter of the lot width. The district label remains close to the tower
  in this deliberately minimal case but does not obscure its silhouette.
- Spec alignment: PASS. The change is recorded in ADR-004, increments the
  layout algorithm because persisted geometry changed, rejects earlier layout
  versions as hints, retains directory hierarchy, and passes containment,
  overlap, capacity, determinism, and hinted churn gates.
- Tests / determinism / stability: 175 tests passed with one unavailable
  symlink skip. Repeated builds produced identical SHA-256
  `075236a5fe1c74d53a43eed685445f5a32419150fb5eff5511baaf857b3ee2b6`
  for `graph.ucg.json`,
  `0139123e262c3bc3111fa3a037f4498d8848994bce09e88f0eef611b75501c75`
  for `city.json`, and
  `97ad5966fba936c547086ad6f9e07499b67e59cd479dfe7176e6f7a74fc14910`
  for `preview.svg`.
- Fixes applied and reverified: the first viewer scale cap of 7 made the city
  too small in the captured viewport; it was adjusted to 11 and the viewer
  suite, syntax check, end-to-end build, screenshots, and full gates were rerun.
  The intentional SVG snapshot change was updated only after byte determinism
  and visual inspection.
- Open risks / next actions: expose declared dependency evidence in the
  inspector and improve network endpoint readability. Dense SVG labels,
  DEC-009, hosted runner evidence, and the project license remain open.
- Commits created / pushed (and branch): `445a254` on local `main`; push is
  scheduled after this checkpoint log commit and final repository-state check.

## Checkpoint 2026-10-17 — declared dependency inspector (`5a435f2`)

- Implemented: nearest-module dependency lookup for file buildings and a
  dedicated `DECLARED DEPENDENCIES (NOT USAGE)` inspector section. Maven paths
  are restored to `group:artifact`, npm package names remain intact, duplicate
  package declarations merge evidence, and sibling or outer module declarations
  are not borrowed when a closer module exists.
- Fixture(s) / revision(s):
  `tests/fixtures/repositories/postgresql-config` at synthetic revision
  `inspector-check`, plus a Node fixture with root and nested Maven modules.
- Commands run: two identical end-to-end CLI builds; viewer-focused and full
  176-test suites; a Node nearest-module assertion; release-readiness and
  dependency validation; JavaScript syntax, Ruff, and Git whitespace checks;
  and an Edge headless inspector capture. For that capture only, the generated
  artifact copy called its existing `showBuilding` function after startup so
  the first building was selected without changing repository code.
- Artifacts inspected: the original generated `graph.ucg.json`, `city.json`,
  `preview.svg`, `index.html`, and the selected-state `inspector.png` under
  `C:\WINDOWS\TEMP\metropogits-inspector-42e3b35f09634bdbb80637c51119ebfa`.
- Visual findings: the selected repository building clearly separates verified
  PostgreSQL/JPA facts from `org.postgresql:postgresql · MAVEN · DECLARED`.
  The evidence list includes the manifest source, safe config line, and Java
  inheritance line, and the section fits the inspector without obscuring the
  city canvas.
- Spec alignment: PASS. A manifest dependency remains declaration evidence and
  does not create a runtime road or claim on its own; displayed repository text
  still uses DOM `textContent`, and exact evidence IDs remain available.
- Tests / determinism / stability: 176 tests passed with one unavailable
  symlink skip. Repeated builds produced identical SHA-256
  `6588f87cd6dd0efe6a9b5bc07c5d35a6e6c744eabdb44a69cd2dad4c2bd94f8f`
  for `graph.ucg.json`,
  `4ba251cddf615ac267ac91bad20f855086dd30340663f4627c7a1f02691405c2`
  for `city.json`, and
  `97ad5966fba936c547086ad6f9e07499b67e59cd479dfe7176e6f7a74fc14910`
  for `preview.svg`.
- Fixes applied and reverified: no post-commit implementation correction was
  required; the nearest-scope negative case, syntax gates, selected-state
  screenshot, and complete suite all passed.
- Open risks / next actions: improve network endpoints so roads visibly attach
  to their source and target buildings, then re-audit release blockers. Dense
  SVG labels, DEC-009, hosted runner evidence, and the project license remain
  open.
- Commits created / pushed (and branch): `5a435f2` on local `main`; push is
  scheduled after this checkpoint log commit and final repository-state check.

## Checkpoint 2026-10-17 — building-attached networks (`6e86b45`)

- Implemented: layout `hierarchical-paged/1.5`, which starts and ends each
  network at its contributing file building center. Aggregated logical edges
  use the deterministic centroid of unique source and target buildings. Version
  1.4 geometry remains accepted as a hint because district/building placement
  did not change.
- Fixture(s) / revision(s): `tests/fixtures/repositories/spring-positive` at
  synthetic revision `road-check`, plus the three-source aggregation fixture
  and a 1.4 hint compatibility fixture.
- Commands run: two identical end-to-end CLI builds; layout, preview,
  governance, and full 177-test suites; Edge headless viewer and SVG captures;
  Ruff, `compileall`, dependency consistency, release-readiness validation,
  JavaScript syntax checks, and Git whitespace checks.
- Artifacts inspected: `graph.ucg.json`, `city.json`, `preview.svg`,
  `index.html`, `viewer.png`, and `preview.png` under
  `C:\WINDOWS\TEMP\metropogits-roads-1cc9c64fc19a4e9d903de7f46e995869`.
- Visual findings: both dependency roads visibly terminate beneath the source
  and target buildings in the canvas and SVG. The service-to-repository route
  now reaches the blue service and green persistence structures instead of
  stopping at the centers of their district rectangles. Roads remain behind
  buildings, so endpoints read as attached rather than overpainting roofs.
- Spec alignment: PASS. Every visible network still preserves its exact UCG
  `edgeIds`; aggregation changes only deterministic path geometry. ADR-004 and
  the City schema record 1.5, while 1.4 hints retain zero-churn placement.
- Tests / determinism / stability: 177 tests passed with one unavailable
  symlink skip. Repeated builds produced identical SHA-256
  `407be1003cfa2989b43d7408dd3d0c7caf7be4e99cc37c11d91f05795ac3b69e`
  for `graph.ucg.json`,
  `eaae320c80cd36f431d5e1cfebbe4d1efad33d2986a0e2e814c72326681b4be3`
  for `city.json`, and
  `f6199218167e0464617e81dd7b7fc97f362b2b87393ab6a87e0b2a348ed9c4fc`
  for `preview.svg`.
- Fixes applied and reverified: the deterministic preview snapshot changed as
  expected with the road geometry and was updated only after endpoint tests,
  byte-for-byte repeat builds, and both visual captures passed.
- Open risks / next actions: re-audit release blockers and hosted workflow
  evidence. Dense SVG labels, DEC-009, hosted runner evidence, and the project
  license remain open.
- Commits created / pushed (and branch): `6e86b45` on local `main`; push is
  scheduled after this checkpoint log commit and final repository-state check.

## Checkpoint 2026-10-17 — hosted composite Action (`427ca3b`)

- Implemented: a least-privilege `action-smoke` CI job that invokes the checked
  out composite Action through `uses: ./`, analyzes the bundled Spring fixture,
  requires `COMPLETE`, and asserts the six required static artifact files on an
  actual GitHub-hosted `ubuntu-24.04` runner.
- Fixture(s) / revision(s): `tests/fixtures/repositories/spring-positive` with
  repository ID `fixture/hosted-action` and synthetic revision `hosted-runner`.
- Commands run: local CI contract tests and the complete 178-test suite, Ruff
  and Git whitespace checks, an authenticated read-only GitHub Actions status
  audit, and the pushed `Quality gates` workflow at commit
  `427ca3b233df89038375989f977243e6698f8ad7`.
- Hosted evidence: workflow run
  `https://github.com/hdg5639/MetropoGits/actions/runs/39018586521` completed
  successfully. Both `quality` job `117355647077` and `action-smoke` job
  `117355647299` completed with `success`.
- Artifacts inspected: the hosted smoke job verified non-empty
  `graph.ucg.json`, `city.json`, `preview.svg`, `index.html`, `manifest.json`,
  and `README_SNIPPET.md` at the composite Action's exported artifact path.
- Visual findings: not applicable to the CI-only change; the same Spring
  fixture's viewer and SVG were inspected in the immediately preceding network
  checkpoint.
- Spec alignment: PARTIAL. The composite Action and static artifact contract
  are now proven on the standard hosted runner with only `contents: read`.
  GitHub Pages is not configured for this repository, and its API returned 404,
  so AC-010 must remain blocked until an owner explicitly opts into publishing
  and a deployment URL is verified.
- Tests / determinism / stability: 178 tests passed locally with one unavailable
  symlink skip, and both hosted jobs passed. Existing deterministic artifact
  hashes from the preceding checkpoint remain applicable because this work
  changed only CI orchestration.
- Fixes applied and reverified: no correction was required after push; the
  first hosted run containing the smoke job passed both jobs.
- Open risks / next actions: update readiness evidence to distinguish the now
  verified hosted Action from the still-unconfigured Pages deployment. DEC-009
  and the project license also remain owner decisions.
- Commits created / pushed (and branch): `427ca3b` on `main`, pushed before the
  hosted check by design; this checkpoint log follows as a separate commit.

## Checkpoint 2026-10-17 — resolved Java type references (`a21e895`)

- Implemented: conservative Java local-type `REFERENCES` extraction for actual
  body uses bound by an exact import, same package, wildcard import with one
  possible local target, or a fully qualified name. Package/import statements,
  type declaration headers, comments, strings, self-file targets, duplicates,
  and ambiguous wildcard targets do not emit reference edges.
- Fixture(s) / revision(s): `tests/fixtures/repositories/spring-positive` at
  synthetic revision `reference-check`, plus temporary same-package positive,
  comment/string/unused-import negative, and ambiguous wildcard fixtures.
- Commands run: two identical end-to-end CLI builds; Java-focused and full
  181-test suites; UCG relationship and City network inspection; Edge headless
  viewer and SVG captures; Ruff, `compileall`, dependency consistency,
  release-readiness validation, JavaScript syntax, and Git whitespace checks.
- Artifacts inspected: `graph.ucg.json`, `city.json`, `preview.svg`,
  `index.html`, `viewer.png`, and `preview.png` under
  `C:\WINDOWS\TEMP\metropogits-java-refs-94bc1cc6a770422081fc32fe658c7b6e`.
  The graph contains two local IMPORTS and two local REFERENCES edges; each of
  the two displayed roads preserves the matching import and type-reference IDs.
- Visual findings: the canvas and SVG keep two clear building-attached roads.
  Adding type-reference provenance does not duplicate visible routes or detach
  their endpoints; it enriches the drill-down records behind each route.
- Spec alignment: PASS. FR-004's proven reference path now covers bound Java
  type uses without suffix guessing or unresolved name assumptions, and every
  edge has source-line AST evidence with RESOLVED confidence.
- Tests / determinism / stability: 181 tests passed with one unavailable
  symlink skip. Repeated builds produced identical SHA-256
  `ab85bf5d5f6ec7d451d218682f1a2bcbb63aea85df2f3560058d5f3dc2cd2b2a`
  for `graph.ucg.json`,
  `5446e4979e21ccd263ca16a7118c269f76c0c819d23bf36de8f2866d4df479d4`
  for `city.json`, and
  `8f14a0e66802a1ef916b24165dd0f142d8f0652785d580498bf9ee9a72185ee2`
  for `preview.svg`.
- Fixes applied and reverified: the first temporary positive fixture placed its
  package and class declaration on one physical line, outside the analyzer's
  supported top-level declaration form; the fixture was corrected to normal
  Java formatting. Existing network assertions were also expanded to require
  both import and reference edge IDs. Focused and full gates then passed.
- Open risks / next actions: update FR-004 readiness evidence and finish the v1
  candidate audit. Pages publication, DEC-009, and the project license remain
  owner-controlled blockers.
- Commits created / pushed (and branch): `a21e895` on local `main`; push is
  scheduled after this checkpoint log commit and final repository-state check.

## Checkpoint 2026-10-17 — v1 candidate repository audit (`96340b2`)

- Implemented: collision-aware SVG district labels that prioritize populated
  deeper districts, fit labels inside their visible bounds, and omit lower
  priority overlaps without changing canonical graph or scene geometry.
- Fixture(s) / revision(s): the complete MetropoGits repository at revision
  `96340b2`, analyzed as `hdg5639/MetropoGits`; a second independent build used
  the same revision and inputs for byte-for-byte comparison.
- Commands run: two real end-to-end CLI builds; Edge headless captures of the
  interactive viewer and generated SVG; `python -m pip check`; Ruff;
  `compileall`; JavaScript syntax checks; release-readiness validation; the
  complete unit, integration, contract, security, and regression suite; and
  Git whitespace checks.
- Artifacts inspected: `graph.ucg.json`, `city.json`, `preview.svg`,
  `index.html`, `manifest.json`, `README_SNIPPET.md`, `viewer.png`, and
  `preview.png` under
  `C:\WINDOWS\TEMP\metropogits-v1-final-9b500165ac8c4a3caf68815b5b3f0bda`.
  The build completed with 75 buildings, 52 districts, 3 aggregated networks,
  5 informational diagnostics, no warnings, and no errors.
- Visual findings: PASS. The canvas opens with the repository hierarchy framed
  and separated, role-colored Spring buildings and their attached roads remain
  legible, and controls plus inspector have adequate contrast. The 1200x630 SVG
  keeps the city centered and removes the previous district-label pileup;
  long labels are deliberately truncated within their districts. Thumbnail
  scale still favors structural composition over reading every directory name.
- Spec alignment: PASS. The change affects only accessible static-preview label
  selection, preserves evidence-linked structures and roads, adds no runtime
  service or repository execution, and leaves the UCG and City contracts intact.
- Tests / determinism / stability: 182 tests passed; one symlink-boundary test
  was explicitly skipped because this Windows environment cannot create the
  required symbolic link. Repeated builds produced identical SHA-256
  `15b7c110725c2f9e20627e47045f2a57eff048e8d7054ecc7e89b23f01cfbfc8`
  for `graph.ucg.json`,
  `be6b5d60fcbb5539399ed3bad1e0c01da86c2172dce79c93e9fd65976f70cc98`
  for `city.json`, and
  `4979c6d9cb481b0f516572809b8584c71b67f7f9ed7a8d8337dbfd85d7adbc4a`
  for `preview.svg`. Dependency, lint, compile, JavaScript, readiness, and
  whitespace gates also passed.
- Fixes applied and reverified: SVG label collisions found during the first
  full-repository visual audit were corrected in `96340b2`; the regenerated
  SVG and viewer were then captured and inspected again before the full gates.
- Open risks / next actions: the implementation is a local v1 candidate, not a
  public v1 release. Owner action remains necessary to resolve DEC-009, choose
  a project license, and opt into plus verify GitHub Pages publication.
- Commits created / pushed (and branch): `96340b2` on local `main`; push is
  scheduled after this checkpoint log commit and final repository-state check.

## Checkpoint 2026-10-17 — owner decisions and publication deferral (`2a9063c`)

- Implemented: ADR-005 requires genuine interactive 3D for stable v1 while
  preserving the deterministic 2D preview/fallback; ADR-006 adopts Apache-2.0
  with package and contribution metadata; ADR-007 selects Pages for the future
  public demo but prohibits repository visibility or deployment changes until
  explicit maintainer approval.
- Fixture(s) / revision(s): the complete MetropoGits repository at revision
  `2a9063c5b5b7a6f05845958fe2e451f3bffbb11f`, analyzed twice as
  `hdg5639/MetropoGits`.
- Commands run: two real end-to-end CLI builds; Edge headless viewer and SVG
  captures; official Apache License 2.0 text comparison; `pip check`; Ruff;
  `compileall`; JavaScript syntax checks; release-readiness validation; the
  complete unit, integration, contract, security, governance, and regression
  suite; and Git whitespace checks.
- Artifacts inspected: `graph.ucg.json`, `city.json`, `preview.svg`,
  `index.html`, `manifest.json`, `README_SNIPPET.md`, `viewer.png`, and
  `preview.png` under
  `C:\WINDOWS\TEMP\metropogits-decisions-92741a946c5f4af393bafce9aa09ad79`.
  The build completed with 75 buildings, 52 districts, 3 networks, 5
  informational diagnostics, no warnings, and no errors.
- Visual findings: PASS with no renderer change. The full-repository isometric
  viewer remains framed, separated, and inspectable; the SVG remains centered
  with bounded, non-overlapping district labels. The image also confirms why
  ADR-005 treats this renderer as a preview/fallback rather than genuine 3D.
- Spec alignment: PASS. DEC-009 now follows its original true-3D wording,
  Apache-2.0 resolves the license choice without changing visibility, and the
  explicit publication gate reinforces private-data opt-in requirements. No
  public repository setting, Pages setting, or active deployment workflow was
  changed.
- Tests / determinism / stability: 184 tests passed; one symlink-boundary test
  was explicitly skipped because this Windows environment cannot create the
  required symbolic link. Repeated builds produced identical SHA-256
  `acece0e32d01b5119ebbc4486ae7d70e6b066abf8fd6d509b969f41941070155`
  for `graph.ucg.json`,
  `c5d8b7d684a4882e61a58cae48136daa37fc0fb60e33438e3be9998aa41ece5a`
  for `city.json`, and
  `4979c6d9cb481b0f516572809b8584c71b67f7f9ed7a8d8337dbfd85d7adbc4a`
  for `preview.svg`. The local `LICENSE` matched the trimmed official Apache
  Foundation text fetched over HTTPS.
- Fixes applied and reverified: the release map now distinguishes the resolved
  license decision, accepted-but-unimplemented 3D decision, and intentionally
  deferred deployment. Governance tests require the three boundaries and
  confirm that `ci.yml` is the only active workflow.
- Open risks / next actions: implement and visually validate the genuine 3D
  renderer plus non-WebGL fallback. AC-010 and public release remain blocked by
  the explicit ADR-007 deferral until the maintainer approves publication.
- Commits created / pushed (and branch): `42ebb20`, `6ec36e5`, and `2a9063c`
  on local `main`; push is scheduled after this checkpoint log commit.

## Checkpoint 2026-10-17 — genuine WebGL 3D viewer (`bc8d613`)

- Implemented: a project-authored WebGL renderer with perspective projection,
  depth-tested extruded buildings, district and grid geometry, evidence-backed
  road ribbons, deterministic camera fitting, orbit/pan/zoom controls,
  selection and evidence inspection, category filters, synthetic activity, and
  collision-aware projected labels. The existing isometric canvas starts
  automatically when WebGL context or shader initialization fails.
- Fixture(s) / revision(s): the complete MetropoGits repository at revision
  `bc8d613`, analyzed twice as `hdg5639/MetropoGits`; the maintained
  `spring-positive` fixture was also rendered through both browser paths.
- Commands run: two real end-to-end CLI builds; Edge headless WebGL capture
  using software SwiftShader; forced `--disable-webgl` fallback capture; SVG
  capture; `pip check`; Ruff; `compileall`; JavaScript syntax checks;
  release-readiness validation; the complete unit, integration, contract,
  security, governance, and regression suite; and Git whitespace checks.
- Artifacts inspected: the complete 11-file static artifact set plus
  `viewer-webgl.png`, `viewer-fallback.png`, and `preview.png` under
  `C:\WINDOWS\TEMP\metropogits-3d-checkpoint-fa88b61ceadd4dfaab310d927a0cc50d`.
  The self-analysis completed with 76 buildings, 52 districts, 3 networks, 5
  informational diagnostics, no warnings, and no errors.
- Visual findings: PASS. The `WEBGL 3D` path visibly provides real perspective,
  height, face shading, and depth occlusion; the initial camera contains the
  complete city while filling the available height, roads remain attached to
  their source-backed buildings, and projected labels avoid collisions. A
  separate forced capture showed the `2D FALLBACK` badge and the unchanged
  readable isometric city. The deterministic SVG remains centered and legible.
- Spec alignment: PASS. Both renderers consume the same `city/0.1` and UCG
  artifacts, keep exact edge/evidence identity, require no network request or
  backend, and preserve the GPU-free SVG path. ADR-002 and ADR-005 are now
  implemented locally; publication remains untouched under ADR-007.
- Tests / determinism / stability: 187 tests passed; one symlink-boundary test
  was explicitly skipped because this Windows environment cannot create the
  required symbolic link. Repeated builds produced identical SHA-256
  `8feb34a76903cad0112d5904a676dfb9dc99093100eb2d2db5b1e4fd5cc365bd`
  for `graph.ucg.json`,
  `384bcbea81670ebb6eb48581f5652b96d0aacc7aa8a3c876cd89dfd4960d82bb`
  for `city.json`, and
  `cdd61683c786b14b7b5009928c6a5c6990d8d428e0ca8af4e3549ca01ce2aaf9`
  for `preview.svg`. Node validates every shipped JavaScript asset; focused
  matrix projection and fallback-boundary tests also pass.
- Fixes applied and reverified: a fixed initial camera distance first framed
  the small fixture well but made the full repository too small. It was
  replaced with a deterministic viewport-aware fit over actual district ground
  and building-roof corners, then both fixture shapes were recaptured.
- Open risks / next actions: add an actual WebGL smoke assertion to the hosted
  workflow, then update DEC-009 readiness evidence. AC-010 and public release
  remain blocked solely by the explicit ADR-007 publication deferral.
- Commits created / pushed (and branch): `02556fe` and `bc8d613` on local
  `main`; push is scheduled after this checkpoint log commit.

## Checkpoint 2026-10-17 — hosted WebGL browser smoke (`a9d9a88`)

- Implemented: the read-only hosted `action-smoke` job now opens the composite
  Action's generated `index.html` in the Ubuntu runner's Google Chrome through
  SwiftShader and requires both the rendered `WebGL 3D` mode and the interactive
  3D canvas accessibility label.
- Fixture(s) / revision(s): `tests/fixtures/repositories/spring-positive` at
  synthetic revision `hosted-runner`, built by the composite Action at commit
  `a9d9a88e06e2b9fd03c74eb4d0a5677a80995894`.
- Commands run: focused local CI and Action contract suites, Ruff, compile and
  whitespace checks, followed by the pushed `Quality gates` workflow run
  `39029488279` on GitHub's `ubuntu-24.04` runner.
- Artifacts inspected: the hosted job first required the complete graph, scene,
  SVG, viewer, manifest, and README snippet contract, then inspected Chrome's
  post-JavaScript DOM for the genuine 3D renderer state.
- Visual findings: the immediately preceding checkpoint contains local actual
  WebGL, forced fallback, and SVG captures. This CI-only change did not alter
  rendered pixels; it proves that the 3D path also initializes outside the
  development machine.
- Spec alignment: PASS. The browser smoke uses only generated static files and
  software WebGL. The job retains `contents: read`, has no deployment or secret
  permissions, and does not weaken ADR-007's publication deferral.
- Tests / determinism / stability: hosted `quality` job `117386896985` and
  `action-smoke` job `117386896818` both completed with `success` at
  `https://github.com/hdg5639/MetropoGits/actions/runs/39029488279`.
- Fixes applied and reverified: a local contract assertion initially expected
  escaped quote characters that are not present in the YAML source; the test
  expectation was corrected to the literal shell pattern before commit and all
  focused checks passed.
- Open risks / next actions: mark DEC-009 implementation compliance automated.
  AC-010 and public release remain deliberately blocked by ADR-007 until the
  maintainer approves repository visibility and Pages publication.
- Commits created / pushed (and branch): `a9d9a88` on `main`, pushed and
  verified by the hosted workflow above.
