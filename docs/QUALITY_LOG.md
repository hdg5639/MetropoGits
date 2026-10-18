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

## Checkpoint 2026-10-17 — private technical v1 candidate (`87f4d2e`)

- Implemented: DEC-009 and the release map now record the genuine WebGL 3D
  renderer, deterministic 2D fallback, and GPU-free SVG preview as verified.
  Apache-2.0 licensing and the explicit publication gate remain in force.
- Fixture(s) / revision(s): the complete MetropoGits repository at revision
  `87f4d2e`, analyzed twice as `hdg5639/MetropoGits`.
- Commands run: two real end-to-end CLI builds; Edge headless WebGL capture
  using software SwiftShader; forced `--disable-webgl` fallback capture; SVG
  capture; `pip check`; Ruff; `compileall`; JavaScript syntax checks;
  release-readiness validation; the complete unit, integration, contract,
  security, governance, and regression suite; and Git whitespace checks.
- Artifacts inspected: the complete 11-file static artifact set plus
  `viewer-webgl.png`, `viewer-fallback.png`, and `preview.png` under
  `D:\Code\MetroPoGits\.verification-private-v1-d2ae4ee25145415183057d56fa149361`.
  The self-analysis completed with 76 buildings, 52 districts, 3 networks, 5
  informational diagnostics, no warnings, and no errors.
- Visual findings: PASS. The `WEBGL 3D` capture visibly preserves perspective,
  height, shading, depth, evidence-backed roads, and a complete-city initial
  frame. The forced `2D FALLBACK` capture remains readable and complete. The
  SVG preview remains deterministic, centered, and independent of WebGL.
- Spec alignment: PASS for the private technical v1 candidate. DEC-001 through
  DEC-013, including the stable-v1 3D requirement, are implemented and mapped.
  Repository visibility and Pages were not changed, as required by ADR-007.
- Tests / determinism / stability: 188 tests passed; one symlink-boundary test
  was explicitly skipped because this Windows environment cannot create the
  required symbolic link. Repeated builds produced identical SHA-256
  `097a3fce2845ddf0b3f13badb4d38eab9daba83401429fe4c620b76f3f50362f`
  for `graph.ucg.json`,
  `9b73b62b1df409f2c8bea143991c59bde8c86903b1d452c4c01e3232419df098`
  for `city.json`, and
  `cdd61683c786b14b7b5009928c6a5c6990d8d428e0ca8af4e3549ca01ce2aaf9`
  for `preview.svg`.
- Hosted evidence: GitHub Actions run `39029488279` passed both the quality job
  (`117386896985`) and the Ubuntu Chrome WebGL smoke job (`117386896818`) on
  private `main`.
- Fixes applied and reverified: the release evidence now distinguishes the
  completed technical v1 scope from publication readiness, so genuine 3D is no
  longer reported as an implementation blocker.
- Open risks / next actions: AC-010, `ACCEPTANCE_EVIDENCE`, and
  `FRESH_REPOSITORY_PUBLISHING` remain intentionally blocked by ADR-007. They
  require explicit maintainer approval before repository visibility or Pages
  can change. No `v1.0.0` tag or version promotion is authorized yet.
- Commits created / pushed (and branch): `1ba3f7f` and `87f4d2e` on local
  `main`; push is scheduled after this checkpoint log commit.

## Checkpoint 2026-10-17 — dense city blocks (`8e26d08`)

- Implemented: layout `hierarchical-paged/1.6` reduces sparse and empty
  directory lots, building setbacks, and sibling padding while preserving the
  complete directory hierarchy and one source file per semantic building.
- Fixture(s) / revision(s): the complete MetropoGits repository at revision
  `8e26d08`, analyzed twice as `hdg5639/MetropoGits`; sparse, nested, hinted,
  and 1,000-file layout fixtures were also exercised.
- Commands run: two real CLI builds; Edge SwiftShader WebGL and CPU SVG
  captures; `pip check`; Ruff; `compileall`; JavaScript syntax checks;
  release-readiness validation; all unit, integration, contract, security,
  governance, and regression tests; and Git whitespace checks.
- Artifacts inspected: baseline captures under
  `D:\Code\MetroPoGits\.visual-recovery-baseline` and improved artifacts under
  `D:\Code\MetroPoGits\.visual-recovery-density-checkpoint`.
- Visual findings: PASS for the density slice. With the same 76 buildings and
  52 districts, the city changes from a long 318 by 649 footprint to a balanced
  338 by 321 footprint. Root area falls from 206,382 to 108,498 world units
  (47.4% smaller), and building footprint density rises from 1.33% to 2.52%.
  Buildings are visibly larger in the initial frame and clustered into clearer
  neighborhoods. Archetype silhouettes and road treatment still need the next
  recovery slices.
- Spec alignment: PASS. Directory IDs, parent hierarchy, file-to-building
  mappings, evidence-backed networks, and `city/0.1` remain intact. No
  decorative building or unsupported semantic fact was introduced.
- Tests / determinism / stability: 189 tests passed; one Windows symlink test
  was skipped because symbolic links are unavailable. Repeated builds produced
  identical SHA-256 `bbd49df21bccc1ffa51b9dd16590c0f76b8c9f4a44b03bea1335b263c8d10f9a`
  for `graph.ucg.json`,
  `bdda98df59c6df8eb18f134446ea0eb3886b4acbfa44b3cc656eb344d582af93`
  for `city.json`, and
  `f61e4e12b6d8b25e8914108a08c719e9f1b0123fa2f3e2050625cfc0dfca91b1`
  for `preview.svg`. Current-version hints preserve anchors; older geometry is
  rejected as a hint; containment and non-overlap validations pass.
- Fixes applied and reverified: the first full run exposed the intentionally
  changed preview golden hash. The checked-in deterministic SVG expectation was
  updated to the inspected layout-1.6 output and the full gate was rerun.
- Open risks / next actions: replace uniform cuboids with evidence-backed
  archetype silhouettes, then upgrade road hierarchy and camera emphasis.
  Public repository and Pages activation remain deferred by ADR-007.
- Commits created / pushed (and branch): `8e26d08` on local `main`; push is
  scheduled after this checkpoint log commit.

## Checkpoint 2026-10-17 — semantic building forms (`cc07c73`)

- Implemented: the WebGL renderer now composes distinct bounded meshes for
  gate, service office, structured warehouse, document depot, cache tower,
  exchange, port, and control-center archetypes. Generic buildings use four
  stable entity-ID variants. The CPU SVG adds matching roof signatures.
- Fixture(s) / revision(s): the complete MetropoGits repository at revision
  `cc07c73`, analyzed twice as `hdg5639/MetropoGits`; the Spring role fixture
  exercises service and persistence forms in both renderers.
- Commands run: two real CLI builds; Edge SwiftShader WebGL and CPU SVG
  captures; `pip check`; Ruff; `compileall`; JavaScript syntax checks;
  release-readiness validation; the full automated suite; and whitespace
  checks.
- Artifacts inspected: `viewer-webgl.png`, `preview.png`, and the complete
  static artifact set under
  `D:\Code\MetroPoGits\.visual-recovery-archetype-checkpoint`.
- Visual findings: PASS. The actual repository capture shows stepped offices,
  low ribbed warehouses, stacked depots and caches, bridged exchanges, gates,
  ports, command spires, and varied generic masses instead of one repeated
  cuboid. All forms remain legible inside their original six-unit parcels; the
  README preview exposes high-contrast roof marks at thumbnail scale.
- Spec alignment: PASS. Forms are selected only from the existing
  evidence-backed `archetype` field. Generic variation is explicitly visual,
  deterministic, and tied to an existing entity ID; it adds neither entities
  nor semantic claims.
- Tests / determinism / stability: 191 tests passed; one Windows symlink test
  was skipped because symbolic links are unavailable. A Node geometry test
  proves all eight semantic forms are distinct, positive, and bounded by their
  scene building. Repeated builds produced identical SHA-256
  `e064fb0044999eec8a446c5754de16f45688ffd89c5e97d875d8b3017e27d8b8`
  for `graph.ucg.json`,
  `ab2b46a0a3ff77c6e88a1d1c60e2c1a8820572b926b94da736b10fc2c461acf4`
  for `city.json`, and
  `d6880852962a690ab71b0bf68fbd760174d7a081d5bbee1dac175967abc60f81`
  for `preview.svg`.
- Fixes applied and reverified: the preview golden digest was updated to the
  inspected deterministic roof-signature output before the complete gate.
- Open risks / next actions: the three evidence networks still read as thin
  graph strokes. Add layered roads, junctions, and category identity without
  changing their exact edge membership, then refine camera and selection focus.
  Publication remains deferred by ADR-007.
- Commits created / pushed (and branch): `cc07c73` on local `main`; push is
  scheduled after this checkpoint log commit.

## Checkpoint 2026-10-17 — evidence-road infrastructure (`b8b3f78`)

- Implemented: every evidence network now renders as a layered route with
  shoulder, surface, category marking, and junction pads. Dependency, HTTP, and
  messaging categories have distinct profiles. Existing building clusters gain
  muted civic blocks that are explicitly labeled as visual, non-evidence
  infrastructure.
- Fixture(s) / revision(s): the complete MetropoGits repository at revision
  `b8b3f78`, analyzed twice as `hdg5639/MetropoGits`; renderer contracts also
  exercise all three allowed network kinds.
- Commands run: two real CLI builds; Edge SwiftShader WebGL, forced 2D fallback,
  and CPU SVG captures; `pip check`; Ruff; `compileall`; JavaScript syntax;
  release-readiness validation; the full automated suite; and whitespace checks.
- Artifacts inspected: `viewer-webgl.png`, `viewer-fallback.png`, `preview.png`,
  and the complete static artifact set under
  `D:\Code\MetroPoGits\.visual-recovery-road-checkpoint`.
- Visual findings: PASS. The three actual dependency aggregates now read as
  bright-centered roads with dark asphalt and visible junctions rather than
  single black graph lines. Civic blocks establish local parcels in occupied
  districts without competing with evidence routes. The legend states the
  distinction, and the WebGL, 2D fallback, and SVG outputs all preserve it.
- Spec alignment: PASS. The scene still contains exactly 3 networks, and every
  selectable semantic route retains only its original validated `edgeIds`.
  Civic blocks are renderer-derived visual treatment, have no hit target, and
  make no architecture or dependency claim.
- Tests / determinism / stability: 193 tests passed; one Windows symlink test
  was skipped because symbolic links are unavailable. Network profiles are
  tested as three distinct ordered layers; preview tests require one evidence
  route per scene network and explicit non-evidence labeling. Repeated builds
  produced identical SHA-256
  `664f577d84814947b8567ac9a62d7e43fca2310b9abb0ffe010809409a45b751`
  for `graph.ucg.json`,
  `3fc65f497ce36078d8031f49ef647b718e7112ec4b57f4bb387d1daeefa47dc4`
  for `city.json`, and
  `3d1bde5d78fe13f371fc8c003cb3afc0756a5b9d98df85b52c445c191fb62b60`
  for `preview.svg`.
- Fixes applied and reverified: dependency markings were brightened after the
  first capture still read too much like black graph strokes; all three outputs
  were regenerated and inspected afterward.
- Open risks / next actions: improve the default camera composition and make
  selected buildings, districts, and routes more obvious at city scale.
  Publication remains deferred by ADR-007.
- Commits created / pushed (and branch): `b8b3f78` on local `main`; push is
  scheduled after this checkpoint log commit.

## Checkpoint 2026-10-17 - city-scale camera and selection (`5526854`)

- Implemented: the WebGL view now fits the complete city with explicit
  horizontal and vertical margins, aims above ground level according to the
  tallest building, and uses a lower city-scale pitch. Building focus uses a
  bright full-volume wireframe, district focus uses a thick perimeter ribbon,
  and focus distance is derived from the selected element's extent.
- Fixture(s) / revision(s): the complete MetropoGits repository at exact
  revision `5526854`, built twice as `hdg5639/MetropoGits`; the small semantic
  `spring-positive` fixture; and the low-semantic `jsts-basic` fixture.
- Commands run: four real CLI builds; Edge SwiftShader WebGL captures for all
  three repository shapes; forced 2D fallback and CPU SVG captures for the
  complete repository; `pip check`; Ruff; `compileall`; JavaScript syntax;
  release-readiness validation; the full automated suite; and whitespace
  checks.
- Artifacts inspected: `actual-webgl.png`, `actual-fallback.png`,
  `actual-preview.png`, `spring-webgl.png`, `jsts-webgl.png`, and all generated
  static artifacts under
  `D:\Code\MetroPoGits\.visual-recovery-final-5526854`.
- Visual findings: PASS. The complete repository is centered as one balanced
  city block with readable height, parcel, road, and district separation. The
  Spring slice makes role-specific silhouettes and routes immediately visible.
  The low-semantic JavaScript/TypeScript slice stays neutral and uses only
  deterministic generic massing instead of inventing roles.
- Spec alignment: PASS. The complete scene retains exactly 76 file buildings,
  52 directory districts, and 3 evidence networks. Renderer-only civic blocks
  add no scene entities or edge references. The three slices retain their
  evidence-backed archetypes and exact network edge membership.
- Tests / determinism / stability: 194 tests passed; one Windows symlink test
  was skipped because symbolic links are unavailable. Repeated complete builds
  produced identical SHA-256
  `183ceea1019b9cef809350c6e0dc4efe3917dff13439e12baaea44636acabb0a`
  for `graph.ucg.json`,
  `6281f8e87d01fae116ad927f1b74a7e13730e21674cce4e06b04511808a1e001`
  for `city.json`, and
  `0c66f15464be9197effc95d864023d1bf9c8fb4dc07a27ab2eb82d0c78e057fc`
  for `preview.svg`.
- Fixes applied and reverified: the camera target and fit margins were tuned
  against the complete repository after the previous high, distant view made
  building heights and roads harder to read. All renderer paths were captured
  again after the adjustment.
- Open risks / next actions: visual recovery is complete for the current
  private v1 candidate. Public repository conversion and Pages activation
  remain explicitly deferred by ADR-007 until maintainer approval.
- Commits created / pushed (and branch): `5526854` on local `main`; push is
  scheduled after this checkpoint log commit.

## Checkpoint 2026-10-17 - GJ-Cloud baseline and JSX recovery (`000769c`)

- Implemented: the JavaScript/TypeScript tokenizer now distinguishes JSX
  closing tags and JSX path text from regular-expression literals. A focused
  fixture keeps a real comparison regex beside nested JSX so the two cases
  cannot regress into one heuristic.
- Fixture(s) / revision(s): the external `visual_test_proj/GJ-Cloud` repository
  at exact revision `3d9b53f9dac9af1187ac9754cb3066b27e43b766`, plus the
  maintained JS/TS analyzer fixtures.
- Commands run: two complete pre-fix CLI builds; an analyzer-only post-fix run;
  direct post-fix tokenization of all 468 eligible JavaScript/TypeScript files;
  Edge SwiftShader WebGL, forced 2D fallback, and CPU SVG captures; `pip check`;
  Ruff; `compileall`; JavaScript syntax; release-readiness validation; the full
  automated suite; and whitespace checks.
- Artifacts inspected: `viewer-webgl.png`, `viewer-fallback.png`, `preview.png`,
  both deterministic baseline builds, and `tsx-fixed.ucg.json` under
  `D:\Code\MetroPoGits\.visual-gj-cloud-3d9b53f`.
- Visual findings: DEVIATION. The baseline scene contains 1,324 buildings, 506
  districts, and 1,053 evidence networks. At overview scale WebGL shows labels
  but almost no city mass, the 2D fallback appears empty, and the SVG is
  overwhelmed by overlapping roads. This large-repository result is not an
  acceptable visual baseline and remains the next correction target.
- Spec alignment: PASS for the analyzer correction. The initial build reported
  143 `JSTS_ANALYSIS_SKIPPED` warnings caused by valid TSX. The post-fix analyzer
  run reduced that to one exposed JSX path-text case, and the final direct audit
  tokenized all 468 JS/TS files without a failure. No repository code or build
  script was executed.
- Tests / determinism / stability: 195 tests passed; one Windows symlink test
  was skipped because symbolic links are unavailable. The two pre-fix complete
  builds produced identical SHA-256
  `77411db297c6095b627100ea242c872ac5a4a6fcb7d53fa4250de0906ce0af2f`
  for `graph.ucg.json`,
  `38f88298259915fea5698f33fda1ed6943add0c1e0bdc2db1a12a8c4201e4b14`
  for `city.json`, and
  `f1f963cd7266c737d1bdc857093f15d92f56c555285f12673aeac910c3c0165a`
  for `preview.svg`.
- Fixes applied and reverified: valid JSX closing tags no longer start a regex,
  and a slash followed by a JSX expression remains ordinary path text. The
  malformed-source fixture continues to be rejected instead of silently
  manufacturing imports.
- Open risks / next actions: reduce analysis time from the observed 188-second
  analyzer-only run, then add large-city overview treatment and road
  decluttering while preserving all exact scene edge IDs. Public repository and
  Pages activation remain deferred by ADR-007.
- Commits created / pushed (and branch): `000769c` on local `main`; push is
  scheduled after this checkpoint log commit.

## Checkpoint 2026-10-17 - GJ-Cloud large-city recovery (`8c96e22`)

- Implemented: Java local-type reference extraction now indexes declared types
  and searches only source-body identifiers; hierarchical layout padding is
  bounded for large repository trees; and cities with at least 256 buildings
  aggregate logical roads through stable directory routing zones. Small-city
  routing and 1.7 geometry hints remain compatible.
- Fixture(s) / revision(s): the external `visual_test_proj/GJ-Cloud` repository
  at exact revision `3d9b53f9dac9af1187ac9754cb3066b27e43b766`, plus the
  maintained Java and layout fixtures.
- Commands run: timed analyzer-only runs before and after indexing; multiple
  complete CLI builds with explicit matching repository identity and revision;
  Edge SwiftShader WebGL and forced 2D fallback captures; CPU SVG rendering;
  exact Java edge-set and scene edge-membership audits; `pip check`; Ruff;
  `compileall`; JavaScript syntax; release-readiness validation; the full
  automated suite; and whitespace checks.
- Artifacts inspected: `viewer-webgl.png`, `viewer-fallback.png`, and
  `preview.png` under
  `D:\Code\MetroPoGits\.visual-gj-cloud-network-zones`, plus both exact
  repeated builds under the adjacent `repeat-exact` directories.
- Visual findings: PASS. The 1.7 packing reduces the root footprint from
  1924x2943 to 1680x1913, a 43 percent area reduction. WebGL now exposes the
  major backend and frontend clusters in one centered overview; the fallback
  and SVG retain readable module blocks without the previous thousand-road
  washout.
- Spec alignment: PASS. The scene retains 1,324 file buildings and 506 nested
  districts. Network grouping falls from 1,064 leaf-level routes to 135
  evidence routes while preserving all 5,670 logical edge IDs exactly once:
  no missing or duplicated edge membership was found. No repository code,
  package script, or build script was executed.
- Tests / determinism / stability: 198 tests passed; one Windows symlink test
  was skipped because symbolic links are unavailable. Two complete builds with
  identical provenance produced identical SHA-256
  `265744be3ab128404eee37cbb9a8b8f048ce0babc44fb239a36792189df50859`
  for `graph.ucg.json`,
  `d8ea9667648f818abe84ac4c31d14486bc6903a56db2a344fc6717ea3a0dcb5c`
  for `city.json`, and
  `672a8a15fde28a2194054cb3b13d7043a629dd480a2d0aea849c7f38846377ec`
  for the default-size `preview.svg`.
- Fixes applied and reverified: analyzer-only time fell from 188.099 seconds to
  13.419 seconds, about 14 times faster, with the same 9,721 Java-origin edge
  IDs. The first SVG comparison used mismatched render dimensions; rerunning
  two complete builds with the same inputs confirmed byte-identical output.
- Open risks / next actions: very large scenes still prioritize a complete-city
  overview over individual building detail, so deeper inspection requires zoom
  and filters. Public repository conversion and Pages activation remain
  explicitly deferred by ADR-007 until maintainer approval.
- Commits created / pushed (and branch): `b800094`, `eac434f`, and `8c96e22`
  on local `main`; push is scheduled after this checkpoint log commit.

## Checkpoint 2026-10-17 - major structural districts (`9feedc5`)

- Implemented: the viewer and README SVG now identify major structural
  districts from the real directory hierarchy and subtree building counts.
  Deterministic colored ground plates, stronger borders, and priority labels
  expose large module boundaries without adding scene entities or claiming
  that directory names prove runtime services.
- Fixture(s) / revision(s): the external `visual_test_proj/GJ-Cloud` repository
  at exact revision `3d9b53f9dac9af1187ac9754cb3066b27e43b766`, plus synthetic
  large-branch and small two-district renderer fixtures.
- Commands run: two complete matching CLI builds; UCG-to-archetype count audit;
  Chrome SwiftShader WebGL, forced 2D fallback, and CPU SVG captures; `pip
  check`; Ruff; `compileall`; JavaScript syntax; release-readiness validation;
  the full automated suite; whitespace checks; and SHA-256 comparisons across
  graph, scene, preview, HTML, and viewer assets.
- Artifacts inspected: `viewer-webgl.png`, `viewer-fallback.png`, `preview.png`,
  and the generated static artifacts under
  `D:\Code\MetroPoGits\.visual-gj-cloud-major-districts-2`.
- Visual findings: PASS. The overview now names and separates `Auth`, `Ops`,
  `User`, `Vm`, and `portal`. WebGL presents five distinct ground zones, the
  2D fallback makes their boundaries immediately legible, and the SVG keeps
  all five labels above buildings and roads. The one-building `api-docs-ui`
  and `gamjabox-landing` branches remain in the city but are not promoted as
  major overview districts.
- Spec alignment: PASS. Selection uses only observed directory containment and
  building membership. It is labeled `Major district (structural)` and does
  not infer service semantics, modify the UCG, add semantic decorations, or
  execute repository code. Graph and City Scene hashes remain unchanged.
- Tests / determinism / stability: 201 tests passed; one Windows symlink test
  was skipped because symbolic links are unavailable. Matching builds produced
  identical SHA-256
  `265744be3ab128404eee37cbb9a8b8f048ce0babc44fb239a36792189df50859`
  for `graph.ucg.json`,
  `d8ea9667648f818abe84ac4c31d14486bc6903a56db2a344fc6717ea3a0dcb5c`
  for `city.json`, and
  `ce7b780f2ff2aadb9ba1cfe92c9fc94189a458b5ca8e808eb5a122575b010f84`
  for `preview.svg`; HTML and all changed viewer assets also matched exactly.
- Fixes applied and reverified: initial WebGL labels clipped short names and
  initial SVG labels were overdrawn by buildings. Major-label widths were
  expanded and SVG labels were moved to the final paint layer, then all three
  renderers were captured again. A blank fallback capture was traced to a
  browser-process race and repeated with an isolated, waited Chrome process.
- Open risks / next actions: the mapping audit found no role-to-archetype loss:
  all 254 file role claims are represented. The 140 specialized buildings map
  from 49 entrypoints, 43 services, 26 persistence adapters, and 22
  configurations; 114 general components intentionally remain generic. The
  remaining generic majority therefore requires new evidence-backed semantic
  coverage, especially for JS/TS, rather than cosmetic reclassification. LOD
  and a distinct README showcase composition remain the next visual priorities.
- Commits created / pushed (and branch): `9feedc5` on local `main`; push is
  scheduled after this checkpoint log commit.

## Checkpoint 2026-10-17 - progressive large-city detail (`70ea174`)

- Implemented: large cities now use one deterministic LOD policy in both the
  WebGL and 2D renderers. The initial overview retains all evidence-backed
  semantic archetypes, a stable sample of generic buildings, the 24
  highest-volume routes, root boundaries, and major structural districts.
  Zooming reveals a district stage and then the complete city. Active filters
  force full detail, selected elements remain rendered, and the toolbar states
  the current level and rendered/eligible counts.
- Fixture(s) / revision(s): the external `visual_test_proj/GJ-Cloud` repository
  at exact revision `3d9b53f9dac9af1187ac9754cb3066b27e43b766`, plus a
  synthetic 300-building, 100-network policy fixture.
- Commands run: two complete matching CLI builds; Chrome SwiftShader WebGL,
  forced 2D fallback, and CPU SVG captures; `pip check`; Ruff; `compileall`;
  JavaScript syntax checks; release-readiness validation; the full automated
  suite; whitespace checks; and SHA-256 comparisons across graph, scene,
  preview, manifest, HTML, and changed viewer assets.
- Artifacts inspected: `viewer-webgl.png`, `viewer-fallback.png`, `preview.png`,
  and the generated static artifacts under
  `D:\Code\MetroPoGits\.visual-gj-cloud-lod-2`.
- Visual findings: PASS for the interactive overview. Both renderers state
  `Overview · 265/1324 buildings · 24/135 routes`; `Auth`, `Ops`, `User`, `Vm`,
  and `portal` remain immediately distinguishable while the initial road and
  boundary load is materially lower. The static SVG remains complete and
  intentionally unchanged; a separate README showcase composition is still
  required.
- Spec alignment: PASS. LOD changes only rendering visibility and never alters
  UCG or City Scene facts. Specialized buildings are never sampled out,
  generic sampling uses stable IDs, route priority uses observed edge counts,
  and the interface discloses every reduction instead of presenting it as the
  complete visible set.
- Tests / determinism / stability: 202 tests passed; one Windows symlink test
  was skipped because symbolic links are unavailable. Matching builds produced
  identical SHA-256
  `265744be3ab128404eee37cbb9a8b8f048ce0babc44fb239a36792189df50859`
  for `graph.ucg.json`,
  `d8ea9667648f818abe84ac4c31d14486bc6903a56db2a344fc6717ea3a0dcb5c`
  for `city.json`,
  `ce7b780f2ff2aadb9ba1cfe92c9fc94189a458b5ca8e808eb5a122575b010f84`
  for `preview.svg`, and matching HTML, manifest, and viewer assets.
- Fixes applied and reverified: LOD computation was cached by level, filter
  revision, and selection so synthetic activity does not repeatedly sort the
  complete scene or retrigger the live status region on every animation frame.
- Open risks / next actions: the README SVG still renders the complete
  architecture graph and remains visually dense. A truthful showcase
  composition and tighter initial camera framing are the next visual
  priorities. Public repository conversion and Pages activation remain
  explicitly deferred by ADR-007 until maintainer approval.
- Commits created / pushed (and branch): `70ea174` on local `main`; push is
  scheduled after this checkpoint log commit.

## Checkpoint 2026-10-17 - traceable semantic LOD (`1434e9b`)

- Implemented: the large-city overview now replaces sampled file buildings
  with deterministic aggregate facilities grouped by the existing major
  structural districts. Each facility preserves its complete sorted member
  list and observed archetype composition. Both WebGL and 2D render the same
  composition, label it as a visual aggregate, and let the inspector disclose
  that it is not a code entity or inferred service before listing every source
  file and allowing a drill-down to the real buildings.
- Fixture(s) / revision(s): the external `visual_test_proj/GJ-Cloud` repository
  at exact revision `3d9b53f9dac9af1187ac9754cb3066b27e43b766`, plus the
  synthetic 300-building, 100-network LOD policy fixture.
- Commands run: two complete matching CLI builds; Chrome SwiftShader WebGL,
  forced 2D fallback, and CPU SVG captures; an aggregate coverage audit; `pip
  check`; Ruff; `compileall`; JavaScript syntax checks; release-readiness
  validation; the full automated suite; whitespace checks; and recursive
  SHA-256 comparisons across every generated non-image artifact.
- Artifacts inspected: `viewer-webgl.png`, `viewer-fallback.png`, `preview.png`,
  and the generated static artifacts under
  `D:\Code\MetroPoGits\artifacts\visual\.visual-gj-cloud-semantic-lod-final`.
- Visual findings: PASS for the Semantic LOD objective. The overview states
  `7 aggregate facilities / 1324 files` and exposes Auth (86), Ops (493), User
  (115), Vm (162), portal (466), and two single-file structural branches as
  distinct facilities. The larger facilities visibly encode their observed
  archetype mix, while amber boundaries and labels distinguish aggregates from
  canonical file buildings. The underlying 24 evidence routes remain intact.
- Spec alignment: PASS. Aggregates exist only as viewer projections over the
  unchanged City Scene, use structural ancestry and observed archetypes only,
  and never invent service semantics. The coverage audit found 1,324 members,
  1,324 unique entity IDs, and 1,324 canonical buildings, so no file is omitted
  or duplicated by the overview abstraction.
- Tests / determinism / stability: 202 tests passed; one Windows symlink test
  was skipped because symbolic links are unavailable. Matching builds produced
  identical bytes for all 12 non-image artifacts, including SHA-256
  `8382dbb2beb4fa888ba0a5d5caffa113c9671e2b2e94a446f457e10e8a8c65cf`
  for `graph.ucg.json`,
  `1137232b7d87b5b9a9cf70fadcc47e41c62f990581a8919439c609fb2759c464`
  for `city.json`, and
  `5a5d65b0f494d14cc8107a2aa583e6e74e6fa96eea8c877ec7e5b5469e6806e8`
  for `preview.svg`.
- Fixes applied and reverified: an intermediate WebGL build referenced hit-test
  regions while constructing geometry and rendered black. The aggregate hit
  box construction was moved to the hit-region phase, after which both WebGL
  and fallback captures rendered correctly. Hidden aggregate dimensions were
  also excluded from initial camera fitting for small repositories.
- Open risks / next actions: canonical district geometry still leaves large
  unused areas, evidence routes still read like circuit traces, and the static
  README SVG intentionally remains unchanged. The portal aggregate also
  exposes that all 466 files currently remain generic. Urban density, road
  hierarchy, JS/TS archetype coverage, and a shared-model showcase renderer
  should remain separate evidence-backed work units.
- Commits created / pushed (and branch): `1434e9b` on local `main`; push is
  scheduled after this checkpoint log commit.

## Checkpoint 2026-10-17 - cold-page urban density (`45593a3`)

- Implemented: layout `hierarchical-paged/1.9` removes unused internal rows
  and columns from each occupied cold-layout building page while preserving
  hashed row/column order, building size, occupied-cell spacing, directory
  hierarchy, and page capacity. Current 1.9 scenes remain eligible as layout
  hints; 1.8 and earlier geometry is deliberately repacked once.
- Fixture(s) / revision(s): the external `visual_test_proj/GJ-Cloud` repository
  at exact revision `3d9b53f9dac9af1187ac9754cb3066b27e43b766`, the maintained
  Spring preview fixture, and the synthetic layout density, containment,
  capacity, and small-change fixtures.
- Commands run: two complete matching cold CLI builds; one complete build using
  the new City Scene as a previous-scene hint; Chrome SwiftShader WebGL, forced
  2D fallback, large CPU SVG, and small golden SVG captures; graph/scene metric
  audits; `pip check`; Ruff; `compileall`; JavaScript syntax checks;
  release-readiness validation; the full automated suite; whitespace checks;
  and recursive SHA-256 comparisons across generated artifacts.
- Artifacts inspected: `viewer-webgl.png`, `viewer-fallback.png`, `preview.png`,
  and the complete static output under
  `D:\Code\MetroPoGits\artifacts\visual\.visual-gj-cloud-density-final`, plus
  the small Spring preview under
  `D:\Code\MetroPoGits\artifacts\verification\layout-1.9-spring`.
- Visual findings: PASS for the density objective. The GJ-Cloud root changes
  from 1,474 by 2,512 to 1,583 by 1,359 world units, reducing canonical area
  by 41.90 percent and producing a balanced overview. File-building footprint
  density rises from 1.287 to 2.216 percent. WebGL and 2D retain the seven
  traceable aggregate facilities, and the complete SVG fits the service blocks
  into a materially smaller canvas region without clipping or overlap.
- Spec alignment: PASS. The graph is byte-identical, and the scene still has
  exactly 1,324 file buildings, 506 directory districts, and 135 evidenced
  networks. Compaction changes geometry only; it does not remove hierarchy,
  invent semantics, or alter network edge membership. The City 0.1 schema now
  explicitly permits the audited 1.9 layout identifier.
- Tests / determinism / stability: 203 tests passed; one Windows symlink test
  was skipped because symbolic links are unavailable. All 12 generated
  non-image artifacts matched across cold builds, including SHA-256
  `8382dbb2beb4fa888ba0a5d5caffa113c9671e2b2e94a446f457e10e8a8c65cf`
  for `graph.ucg.json`,
  `a868a17370d1fe26dbea2d486fd5d8a95d862ed2cc141d57a42611b96228854b`
  for `city.json`, and
  `93f578fb5486ff3575afc3f37d8c94442fa145611e22c4f26613c0a89fb2f845`
  for `preview.svg`. Rebuilding with the 1.9 scene hint produced the same City
  hash and a `LAYOUT_HINT_APPLIED` diagnostic.
- Fixes applied and reverified: the first full suite correctly rejected the old
  Spring preview golden hash after the intentional geometry migration. The new
  SVG was rendered and visually inspected before updating its hash; the full
  suite then passed. A dedicated regression now requires internal occupied rows
  and columns to be contiguous and raises the modular-fixture density floor.
- Open risks / next actions: migration from 1.8 changes 1,307 building anchors
  and geometry for 496 districts once; this is why older hints are rejected
  explicitly. Subsequent 1.9 hinted builds are stable. Nested directory parcels
  still reserve visible open areas, dependency routes remain circuit-like, and
  all 466 portal files remain generic. Evidence-backed JS/TS archetypes and
  road hierarchy remain the next highest-impact visual work.
- Commits created / pushed (and branch): `45593a3` on local `main`; push is
  scheduled after this checkpoint log commit.

## Checkpoint 2026-10-17 - balanced campuses and corner-fit districts (`c90c496`, `a1a9d6a`)

- Implemented: overview aggregates now render as deterministic campuses of up
  to 12 representative buildings instead of one undersized block, preserving
  the full member count and observed archetype mix. Layout
  `hierarchical-paged/1.10` replaces shelf rows with deterministic corner-fit
  packing so smaller sibling districts fill usable gaps beside larger ones.
- Fixture(s) / revision(s): the external `visual_test_proj/GJ-Cloud` repository
  at exact revision `3d9b53f9dac9af1187ac9754cb3066b27e43b766`, the maintained
  Spring preview fixture, and synthetic aggregate-coverage and corner-fit
  regression fixtures.
- Commands run: two complete matching cold CLI builds; one complete build using
  the new City Scene as a previous-scene hint; Chrome SwiftShader WebGL, forced
  2D fallback, and CPU SVG captures; `pip check`; Ruff; `compileall`;
  JavaScript syntax checks; release-readiness validation; the full automated
  suite; whitespace checks; and recursive SHA-256 comparisons across generated
  non-image artifacts.
- Artifacts inspected: `viewer-webgl.png`, `viewer-fallback.png`, `preview.png`,
  and the complete static output under
  `D:\Code\MetroPoGits\artifacts\visual\.visual-gj-cloud-balanced-final`.
- Visual findings: PASS for the balanced-overview objective. The Auth, User, VM,
  Ops, and portal aggregates now read as campuses with 5, 6, 7, 12, and 11
  representative buildings respectively, rather than isolated blocks on large
  parcels. The service districts form a compact block arrangement instead of
  the previous long shelf/L-shaped composition, while both WebGL and 2D expose
  the same aggregate membership and counts.
- Density findings: the GJ-Cloud root changes from 1,583 by 1,359 world units in
  layout 1.9 to 967 by 1,367 in layout 1.10. Root footprint density rises from
  2.216 to 3.606 percent. Backend area falls by 37.8 percent, Ops by 43.0
  percent, Auth by 24.3 percent, User by 10.5 percent, VM by 16.0 percent, and
  portal by 40.0 percent without removing canonical buildings or districts.
- Spec alignment: PASS. Campuses remain viewer-only projections over canonical
  file buildings and expose the files each part represents; they do not create
  graph entities or inferred dependencies. Corner-fit packing preserves the
  directory hierarchy, containment, deterministic ordering, and exact City
  counts. ADR-004 records the 1.10 geometry migration boundary.
- Tests / determinism / stability: 204 tests passed; one Windows symlink test
  was skipped because symbolic links are unavailable. All 12 generated
  non-image artifacts matched across cold builds, including SHA-256
  `8382dbb2beb4fa888ba0a5d5caffa113c9671e2b2e94a446f457e10e8a8c65cf`
  for `graph.ucg.json`,
  `8f9161dd3ffd6c99f99d40572aa62d3678ef9f185b3203c92c01201bb3fe2893`
  for `city.json`, and
  `6dcf92d43b065e661b013c429dbf4a20b0c6a6c4205e681df96ca5058429a68e`
  for `preview.svg`. A 1.10 hinted rebuild produced the same City hash.
- Fixes applied and reverified: aggregate sizing was expanded from a narrow
  center marker to a centered district-scale campus after inspection showed
  that the first multi-building version remained visually undersized. The
  shared part generator is now used by both renderers, and regressions require
  exact member allocation, containment, archetype retention, and compact
  sibling placement.
- Open risks / next actions: evidence routes still resemble circuit traces in
  the complete view, portal's 466 files remain semantically generic, and strict
  hierarchy still reserves some open space around nested parcels. Road
  hierarchy and evidence-backed JavaScript/TypeScript archetypes are the next
  highest-impact visual work; the README showcase should remain a separate
  renderer over the same City Scene rather than fabricated geometry.
- Commits created / pushed (and branch): `c90c496` and `a1a9d6a` on local
  `main`; push is scheduled after this checkpoint log commit.

## Checkpoint 2026-10-17 - occupancy-derived district territory (`56d11c1`, `221f729`)

- Implemented: static packaging now derives deterministic orthogonal territory
  masks from real descendant building footprints. Disconnected occupied blocks
  receive shortest deterministic connectors and one-cell dilation, adjacent
  cells are merged into rendering rectangles, and the largest fully occupied
  rectangle becomes the aggregate-campus plot. WebGL, the 2D fallback, history
  frames, and CPU SVG all consume the same derived territory data.
- Fixture(s) / revision(s): the external `visual_test_proj/GJ-Cloud` repository
  with the audited source state and explicit revision metadata
  `3d9b53f9dac9af1187ac9754cb3066b27e43b766`; the maintained Spring-positive
  repository fixture; and synthetic sparse, nested, and empty territory cases.
- Commands run: three iterative complete GJ-Cloud builds followed by two
  byte-matching final builds; a baseline-options build for semantic artifact
  comparison; Chrome SwiftShader WebGL, forced 2D fallback, and CPU SVG
  captures; territory coverage and size audits; `pip check`; Ruff;
  `compileall`; JavaScript syntax checks; release-readiness validation; the
  full automated suite; and whitespace checks.
- Artifacts inspected: `viewer-webgl.png`, `viewer-fallback.png`, `preview.png`,
  and the complete output under
  `D:\Code\MetroPoGits\artifacts\visual\.visual-gj-cloud-occupied-territory`,
  plus the small-fixture output under
  `D:\Code\MetroPoGits\artifacts\verification\occupied-territory-spring`.
- Visual findings: PASS for false-land removal and PARTIAL for physical
  compaction. WebGL no longer draws one full rectangular ground slab, and Auth,
  Ops, User, VM, and portal render as separate concave occupied territories.
  VM's internal void and the gaps between services remain visibly empty instead
  of being colored as district land. Aggregate campuses sit on the largest
  occupied plot. Canonical service positions are intentionally unchanged, so
  the remaining distance between territories has not yet been repacked away.
- Coverage findings: occupied territory covers 61.5 percent of Auth's canonical
  envelope, 59.6 percent of Ops, 60.6 percent of User, 60.8 percent of VM, and
  63.3 percent of portal. The other 36.7 to 40.4 percent is no longer rendered
  as owned land. All 506 districts produce 1,443 merged rectangles and 4,136
  exterior segments in about 0.65 seconds on the reference machine.
- Spec alignment: PASS. Territory is a renderer projection over unchanged
  `city/0.1` allocation bounds, not a new entity, relationship, or semantic
  claim. Every building intersects its direct and ancestor territory, all
  rectangles remain inside canonical bounds, empty districts retain a safe
  rectangular fallback, and selection still resolves to canonical district
  IDs. ADR-008 records the separation between stable allocation envelopes and
  rendered territory.
- Tests / determinism / stability: 208 tests passed; one Windows symlink test
  was skipped because symbolic links are unavailable. All 12 non-image
  artifacts matched across final repeated builds. With prior build options,
  `graph.ucg.json` remains byte-identical at SHA-256
  `8382dbb2beb4fa888ba0a5d5caffa113c9671e2b2e94a446f457e10e8a8c65cf`
  and `city.json` remains byte-identical at
  `8f9161dd3ffd6c99f99d40572aa62d3678ef9f185b3203c92c01201bb3fe2893`.
  The new deterministic `preview.svg` hash is
  `4024fbd59c411ce25849038ac875be424ad4b435371ba2d60c564b7f3f52e63d`.
- Size findings: the GJ-Cloud viewer data grows from 11,884,025 to 12,165,718
  bytes (2.37 percent), and the SVG grows from 2,048,971 to 2,273,976 bytes
  (10.98 percent). This remains a bounded derived-geometry cost, but SVG size
  should be watched on larger fixtures.
- Fixes applied and reverified: the first undilated mask looked like thin
  circuit traces and left aggregate campuses undersized. One-cell dilation and
  a deterministic maximal occupied plot changed the result into substantial
  city blocks. A second inspection found the old full WebGL base slab still
  presented unused bounds as land; it was replaced with occupied territory
  slabs. An initially blank fallback capture was rerun with a complete browser
  frame and rendered correctly.
- Open risks / next actions: this work does not yet let sibling allocation
  envelopes interlock, so it removes false visible land without moving Auth,
  Ops, User, VM, or portal closer together. A true polygon-aware allocator
  would change overlap validation and previous-scene hint semantics and needs a
  separate layout version plus churn tests. Complete-view dependency roads also
  remain visually circuit-like, and portal's 466 files remain generic.
- Commits created / pushed (and branch): `56d11c1` and `221f729` on local
  `main`; push is scheduled after this checkpoint log commit.

## Checkpoint 2026-10-17 - polygon-aware district allocation (`53f88d1`, `6b862ac`)

- Implemented: City Scene `city/0.2` adds canonical orthogonal district
  footprints while retaining exact AABBs for camera and indexing work. Layout
  `hierarchical-paged/1.11` packs complete child-subtree shapes instead of
  reserving their rectangular envelopes, fills enclosed internal voids while
  preserving exterior concavity, and lets sibling bounds interlock only when
  their owned footprint rectangles remain disjoint. The v0.1 validator remains
  available, and the CLI, static renderers, history, and metropolis path accept
  the versioned contract.
- Fixture(s) / revision(s): the external `visual_test_proj/GJ-Cloud` repository
  at revision `3d9b53f9dac9af1187ac9754cb3066b27e43b766`; the maintained Spring
  UCG fixture; and synthetic interlocking, dense modular, hierarchy, hint, and
  metropolis cases.
- Commands run: one complete iterative GJ-Cloud build, one corrected complete
  build after visual inspection, parallel cold and previous-scene rebuilds,
  City and release-readiness validation, Chrome SwiftShader WebGL and CPU SVG
  captures, `pip check`, Ruff, `compileall`, JavaScript syntax checks, the full
  automated suite, and whitespace checks.
- Artifacts inspected: `viewer-webgl.png`, `preview.png`, and the complete
  output under
  `D:\Code\MetroPoGits\artifacts\visual\.visual-gj-cloud-polygon-allocation`;
  deterministic comparison builds under
  `D:\Code\MetroPoGits\artifacts\verification\polygon-allocation-repeat` and
  `polygon-allocation-hinted`.
- Visual findings: PASS for physical compaction and PARTIAL for the broader
  living-city target. Auth, Ops, User, VM, and Portal now occupy adjoining
  concave land instead of isolated rectangular reservations, and the 3/4 view
  fills the frame without the former central rectangular fields. The first
  render exposed excessive maze-like internal holes; filling only enclosed
  voids produced broader readable land masses without making the exterior
  rectangular. Overview still reduces 1,324 files to seven aggregate
  facilities, and detailed dependency roads remain visually dense; those are
  explicit follow-up visual tasks rather than hidden by this allocator change.
- Geometry findings: the GJ-Cloud root AABB changes from `967 x 1367`
  (`1,321,889` square units) in layout 1.10 to `707 x 714` (`504,798` square
  units), a 61.8 percent reduction. The scene contains 175 sibling AABB
  intersection pairs backed by zero sibling footprint intersections, proving
  that formerly reserved corners are physically reused. Major footprint
  coverage is 71.6 percent for Auth, 45.3 percent for Ops, 76.5 percent for
  User, 68.4 percent for VM, and 60.7 percent for Portal.
- Spec alignment: PASS under ADR-009. The migration is explicit and versioned;
  UCG entity, evidence, edge, building, district, and network counts remain
  `2,919`, `11,531`, `13,332`, `1,324`, `506`, and `135`, with role data
  unchanged. No repository code, dependency, AI service, or external analyzer
  was executed.
- Tests / determinism / stability: 210 tests passed with one expected Windows
  symlink skip. Ruff, compilation, JavaScript syntax, dependency health,
  release-readiness, City validation, and whitespace checks passed. All 12
  non-image artifacts matched byte-for-byte across cold builds. A v1.11 hinted
  rebuild reproduced byte-identical graph, City, viewer, and preview artifacts;
  only `manifest.json` changed to record the applied hint diagnostic. The City
  SHA-256 is `f70f675672cdaa5b2c1f09c9d5650e9f35c49e58562a3806a2e9297bb3d5ba72`
  and the SVG preview SHA-256 is
  `ca66e252083da122c3c34bd64304aa8ee8cb640ffeae409f32ba9b05dcbc5542`.
- Fixes applied and reverified: balanced longest-side scoring replaced
  area-first placement after synthetic siblings formed a strip; previous-scene
  children are placed at eligible hinted anchors before new siblings; and
  enclosed footprint holes are filled after the first real render exposed an
  unreadable jigsaw surface. All affected tests and the complete GJ-Cloud
  pipeline were rerun after the corrections.
- Open risks / next actions: increase overview aggregate richness without
  fabricating buildings, then separate arterial roads from fine dependency
  traces. Ops remains the most concave major service because its real child
  structure is substantially larger than its peers; future shaping should use
  explicit visual LOD over the same canonical footprint rather than restoring
  empty rectangular allocation.
- Commits created / pushed (and branch): `53f88d1` and `6b862ac` on local
  `main`; push is scheduled after this checkpoint log commit.

## Checkpoint 2026-10-17 - hierarchy-aware street routing (`ed1012d`, `771f80a`)

- Implemented: layout `hierarchical-paged/1.12` reserves a two-cell boulevard
  between top-level siblings and a one-cell street between shallow package
  groups. Dependency networks now follow deterministic orthogonal shortest
  paths through building-free cells instead of three-point L-shaped lines
  through buildings. Static and WebGL renderers derive explicitly non-semantic
  boulevard, street, alley, and route-access surfaces from the same City Scene.
  Evidence-backed networks remain separate and retain every exact `edgeId`.
- Fixture(s) / revision(s): the external `visual_test_proj/GJ-Cloud` repository
  at revision `3d9b53f9dac9af1187ac9754cb3066b27e43b766`; the maintained Spring UCG
  fixture; and synthetic top-level sibling, aggregate-edge, large-zone, hint,
  history, and metropolis cases.
- Commands run: one complete GJ-Cloud build, independent cold and v1.12 hinted
  City generations, City and UCG validation through the end-to-end pipeline,
  Edge SwiftShader WebGL and CPU SVG captures, Ruff, `compileall`, JavaScript
  syntax checks, whitespace checks, and the complete automated suite.
- Artifacts inspected: `viewer-webgl.png`, `preview.png`, and the complete
  output under
  `D:\Code\MetroPoGits\artifacts\visual\.visual-gj-cloud-street-grid-2`;
  deterministic City comparisons under
  `D:\Code\MetroPoGits\artifacts\quality\street-grid-1.12`.
- Visual findings: PASS for explicit inter-block streets and PARTIAL for the
  broader living-city target. Major services are separated by dark boulevard
  corridors, detailed dependency routes no longer cross buildings, route
  junction dots were removed, and evidence roads use thinner bounded widths.
  The overview still replaces 1,324 files with seven aggregate facilities, so
  the large-plot sparse view remains a separate semantic-LOD follow-up rather
  than being disguised by this routing change.
- Geometry findings: the GJ-Cloud root AABB is `833 x 532` (`443,156` square
  units), 12.2 percent smaller than layout 1.11's `504,798` square units while
  adding hierarchy-aware gaps. The derived street projection contains 717
  merged rectangles: 388 boulevard, 13 street, 280 alley, and 36 route-access
  rectangles. Its total projected area is `151,508` square units. All 135
  evidence networks route through 1,023 orthogonal segments over `48,328`
  world units, with zero building intersections. Simplified paths range from
  2 to 25 vertices with a median of 7.
- Spec alignment: PASS under ADR-010. Street surfaces are a renderer
  projection and explicitly make no dependency claim. Canonical network
  records still provide the only evidence-backed road semantics and preserve
  all UCG edge identities. No repository code, dependency, AI service, or
  external analyzer was executed. The UCG schema is unchanged; file-size and
  line-count work remains held for its separately approved schema decision.
- Tests / determinism / stability: 213 tests passed with one expected Windows
  symlink skip. Ruff, compilation, JavaScript syntax, and whitespace checks
  passed. The end-to-end, independent cold, and same-version hinted City files
  are byte-identical at SHA-256
  `12bb2c0e1842edf39d3e2bc40ac148dda4583aa063813493fda85e19609d8eca`.
  The unchanged UCG SHA-256 is
  `8382dbb2beb4fa888ba0a5d5caffa113c9671e2b2e94a446f457e10e8a8c65cf`,
  and the new deterministic SVG SHA-256 is
  `848d6d11d3972f8e6b62bf77c99fc919691f521a54b42d6066faf6109ba985e6`.
- Fixes applied and reverified: the first rendering made weighted network roads
  too tube-like and marked every route turn as a node. Widths were reduced,
  logarithmically bounded by represented edge count, and junction markers
  removed. Structural street halos were then widened around top-level service
  footprints so the reserved allocation gaps read as continuous boulevards.
- Open risks / next actions: group one-to-three-file leaf directories into
  shared rectangular blocks without losing canonical district identity, then
  replace seven-facility overview LOD with traceable block-level massing. File
  size and line-count skyline metrics require an explicit UCG schema approval
  before implementation. Portal's 466 TypeScript files also remain generic.
- Commits created / pushed (and branch): `ed1012d` and `771f80a` on local
  `main`; push is scheduled after this checkpoint log commit.

## Checkpoint 2026-10-18 - compact small-leaf blocks (`87c2d20`, `d0d0077`)

- Implemented: layout `hierarchical-paged/1.13` identifies groups of at least
  two deep sibling leaf districts containing one to three files, aligns their
  six-unit buildings inside seven-unit parcels, and packs them as one balanced
  rectangular block. Every source directory remains an individual canonical
  district. Shallow module and service boundaries retain the 1.12 street
  reserves. Root packing permits a bounded 12 percent long-side tradeoff before
  minimizing AABB area so local compaction does not create a larger city void.
- Fixture(s) / revision(s): the external `visual_test_proj/GJ-Cloud` repository
  at revision `3d9b53f9dac9af1187ac9754cb3066b27e43b766`; the maintained Spring
  UCG fixture; synthetic three- and four-member small-leaf blocks; and existing
  large, mixed-size, polygon-interlock, hint, history, and metropolis cases.
- Commands run: one initial and one corrected complete GJ-Cloud build; cold,
  repeated, and v1.13 hinted City generations; UCG and City CLI validation;
  Edge SwiftShader WebGL and CPU SVG captures; Ruff, `compileall`, JavaScript
  syntax checks, whitespace checks, and the complete automated suite.
- Artifacts inspected: `viewer-webgl.png`, `preview.png`, and the complete
  output under
  `D:\Code\MetroPoGits\artifacts\visual\.visual-gj-cloud-leaf-block-2`;
  deterministic comparison files under
  `D:\Code\MetroPoGits\artifacts\quality\leaf-block-1.13`.
- Visual findings: PASS for compact detailed blocks and PARTIAL for overview
  presentation. Deep one-to-three-file districts now form dense parcels with
  narrow internal alleys instead of repeated padded islands. The first render
  exposed a larger central service void despite smaller leaves; bounded
  density-aware root packing removed that regression. Overview still replaces
  all files with seven aggregate facilities, so the new block structure is
  mainly visible in the detailed SVG and close viewer levels. The resulting
  city is denser but portrait-oriented in the fixed wide README frame; the
  planned block-level semantic LOD and showcase camera remain necessary.
- Geometry findings: 45 eligible sibling blocks contain 137 canonical leaf
  districts. Their combined AABB area falls from `92,561` to `16,464` square
  units, an 82.2 percent reduction. Mean member-footprint coverage rises from
  65.8 to 85.7 percent, median coverage from 72.0 to 88.9 percent, and minimum
  coverage from 6.4 to 52.0 percent. The root AABB falls from `833 x 532`
  (`443,156`) to `525 x 777` (`407,925`), an 8.0 percent area reduction; root
  occupied footprint falls from `231,329` to `210,651`. Building density rises
  from 10.8 to 11.7 percent of the AABB and from 20.6 to 22.6 percent of the
  occupied root footprint.
- Integrity findings: all 506 district IDs and 1,324 building identities remain
  present. Sibling footprint intersections and evidence-route/building
  intersections are both zero. The 135 networks use 1,120 orthogonal segments
  over `48,265` world units; simplified paths contain 2 to 34 vertices with a
  median of 8. Network edge IDs and UCG semantic counts are unchanged.
- Spec alignment: PASS under ADR-011, DEC-007, DEC-008, AC-003, and AC-006.
  Compact blocks and alleys are layout infrastructure rather than semantic
  entities. Directory hierarchy, source membership, UCG evidence, relationship
  aggregation, inspector traceability, and City `city/0.2` remain intact. No
  repository code, dependency, external analyzer, or AI service was executed.
- Tests / determinism / stability: 215 tests passed with one expected Windows
  symlink skip. Ruff, compilation, JavaScript syntax, contract validation, and
  whitespace checks passed. The end-to-end, independent cold, and same-version
  hinted City files are byte-identical at SHA-256
  `33d3d4ff869979f95297d3f3d20c6ee9679d2ea3048072b46582339af43f70c1`.
  The unchanged UCG SHA-256 is
  `8382dbb2beb4fa888ba0a5d5caffa113c9671e2b2e94a446f457e10e8a8c65cf`,
  and the deterministic SVG SHA-256 is
  `67eeaeff469b9cdf3a16aa05e535f7c6fa2c8944badc65674b9522684786334f`.
  Adding a fourth leaf sibling with a canonical JSON round-tripped previous
  scene moved zero existing block members.
- Fixes applied and reverified: strict longest-side root scoring initially
  changed a smaller local footprint into a larger `721 x 714` city AABB.
  Bounded density selection reduced it to `525 x 777` without breaking the
  existing corner-fit and aspect-ratio fixtures. Canonical JSON loads fractional
  coordinates as `Decimal`; the hint validator initially rejected those values.
  Decimal-safe validation and offset conversion restored a real CLI
  `LAYOUT_HINT_APPLIED` result with zero moved districts and buildings.
- Open risks / next actions: overview semantic LOD must expose these compact
  blocks instead of seven isolated aggregate towers. README framing should then
  choose a showcase composition suited to the city aspect ratio. File line and
  byte metrics remain held for explicit UCG schema approval, and Portal's 466
  TypeScript files remain generic.
- Commits created / pushed (and branch): `87c2d20` and `d0d0077` on local
  `main`; push is scheduled after this checkpoint log commit.

## Checkpoint 2026-10-18 - traceable block overview LOD (`4f9fffb`, `6eb5bb6`)

- Implemented: large-city overview no longer replaces each major service with
  one tower. It assigns every file through canonical district ancestry, makes
  a deterministic spatial partition inside each major district, and renders
  each partition as a visual city block. Block floors are clipped to the real
  polygon territory rather than refilling an overlapping rectangular AABB.
  District/detail levels still reveal canonical file buildings.
- Fixture(s) / revision(s): the external `visual_test_proj/GJ-Cloud` repository
  at revision `3d9b53f9dac9af1187ac9754cb3066b27e43b766`; a synthetic 300-file
  large-city fixture with nested districts, filters, and 100 ranked networks;
  and all existing viewer, history, metropolis, layout, and contract fixtures.
- Commands run: three complete GJ-Cloud builds while correcting rectangular
  overlap and label priority; Node-derived block integrity measurements; Edge
  SwiftShader WebGL captures; repeated in-memory viewer packaging; Ruff,
  `compileall`, JavaScript syntax checks, whitespace checks, and the complete
  automated suite.
- Artifacts inspected: `viewer-webgl.png` and the complete static output under
  `D:\Code\MetroPoGits\artifacts\visual\.visual-gj-cloud-block-lod-3`.
- Visual findings: PASS for the block-level overview objective and PARTIAL for
  the broader living-city target. The metropolitan view now shows a populated
  campus of blocks inside Ops, VM, Auth, User, and Portal instead of seven
  structures surrounded by unchanged territory. Default block labels were
  removed after they obscured the more important service labels; block names
  remain available through hover and selection. The grey massing is still an
  intentionally schematic blueprint rather than a finished city art style.
- Overview findings: 1,324 files map exactly once to 37 visual blocks and 128
  representative masses. Median block population is 37 files, with a range of
  1-61. Polygon clipping produces 511 non-overlapping plot rectangles and zero
  inter-block plot intersections. Overview keeps the existing cap of 24 from
  135 evidence networks.
- Traceability and evidence findings: every block retains sorted canonical
  file IDs and constituent district IDs. The inspector explicitly labels it a
  visual aggregate, lists both compositions, and can enter the real buildings.
  Filters hide blocks without matching files but never invent filtered
  membership. UCG entities, City buildings, evidence, layout coordinates, and
  network edge IDs are unchanged.
- Spec alignment: PASS under ADR-012, DEC-008, AC-006, and the renderer-only
  aggregation boundary. Block IDs use `visual:block:` and are not encoded as
  semantic UCG or City entities. No schema change, repository-code execution,
  dependency installation, external analyzer, or AI service was introduced.
- Tests / determinism: 215 tests passed with one expected Windows symlink skip.
  Ruff, compilation, JavaScript parsing, and whitespace checks passed. Repeated
  viewer packaging was byte-identical with aggregate artifact SHA-256
  `83ad9b49194937fab6c924c022e36ab362f50001ffdd8c8462dd3c152224118f`.
  The end-to-end City SHA-256 remains
  `33d3d4ff869979f95297d3f3d20c6ee9679d2ea3048072b46582339af43f70c1`;
  the UCG SHA-256 remains
  `8382dbb2beb4fa888ba0a5d5caffa113c9671e2b2e94a446f457e10e8a8c65cf`.
- Fixes applied and reverified: the first block implementation used occupied
  AABBs and created three overlaps where concave service territories interlock.
  Intersecting each block with the major district's polygon territory reduced
  physical overlap to zero. The first readable capture then showed too many
  block labels; limiting persistent labels to major districts restored the
  service-first hierarchy without removing block hover or inspection.
- Open risks / next actions: README SVG remains the detailed renderer rather
  than a dedicated showcase composition. Building silhouettes still lack
  source-size variation because line/byte metrics require explicit UCG schema
  approval. Portal's 466 TypeScript files also remain generic, so semantic
  landmark classification is the next approved visual improvement.
- Commits created / pushed (and branch): `4f9fffb` and `6eb5bb6` on local
  `main`; push is scheduled after this checkpoint log commit.

## Checkpoint 2026-10-18 - distributed block massing and path landmarks (`86bafe7`, `5476e42`)

- Implemented: overview representative masses now select usable plots by
  center proximity and deterministic farthest-point separation instead of
  taking the largest territory rectangles. A new path-semantics analyzer adds
  direct `PATH` evidence for exact Next.js App Router pages and handlers plus
  conventional Java and JavaScript/TypeScript test sources. UI pages render as
  gates, API handlers as ports, and tests as yellow library facilities with a
  dedicated form and legend entry.
- Fixture(s) / revision(s): the external `visual_test_proj/GJ-Cloud` repository
  at revision `3d9b53f9dac9af1187ac9754cb3066b27e43b766`; new positive and
  negative path-convention repositories; the 300-file LOD fixture with a
  four-corner spread assertion; and all maintained contract fixtures.
- Commands run: two complete post-change GJ-Cloud builds, canonical hash
  comparison, Node block-spread and semantic-count measurements, Edge
  SwiftShader WebGL capture, Ruff, `compileall`, JavaScript syntax checks,
  whitespace checks, and the complete automated suite.
- Artifacts inspected: `viewer-webgl.png`, `preview.svg`, and the complete
  static output under
  `D:\Code\MetroPoGits\artifacts\visual\.visual-gj-cloud-spread-landmarks-2`.
- Visual findings: PASS for the reported upper-left concentration defect and
  PASS for the first path-derived landmarks. Representative structures occupy
  the center and separated extents of their polygon blocks rather than the
  first large rectangles. Pink UI gates and yellow test libraries add a
  visible Portal and test signature; the legend explicitly distinguishes test
  facilities from the yellow-orange visual block outline. Overview remains a
  blueprint massing view rather than a finished showcase renderer.
- Distribution findings: among the 35 blocks with multiple representative
  masses, mean normalized X span rises from 15.6 to 54.3 percent and mean Z
  span from 48.0 to 85.4 percent. Block count, file membership, polygon plots,
  road selection, and canonical layout positions are unchanged.
- Semantic findings: GJ-Cloud contains 42 exact `app/**/page.tsx` matches and
  122 conventional test-source matches, producing 164 `PATH` evidence records.
  No exact `app/**/route.ts` file exists in this fixture, so API endpoint
  behavior is verified by the positive fixture instead of claimed for the
  real repository. Generic buildings fall from 1,184 to 1,020; the scene now
  contains 91 gates and 122 libraries. Near-match fixtures for `application`,
  `route.tsx`, `testing`, and Java tests under `src/main` remain unclassified.
- Spec alignment: PASS for evidence provenance, deterministic enrichment,
  non-execution, and graceful fallback. Path rules make narrow convention
  claims only; they do not assert runtime success or traffic. UCG and City
  schemas, stable IDs, relationships, and layout algorithm remain unchanged.
- Tests / determinism: 218 tests passed with one expected Windows symlink skip.
  Ruff, compilation, JavaScript parsing, and whitespace checks passed. Two
  complete builds produced identical UCG, City, and SVG bytes. Their SHA-256
  values are UCG
  `6206f0a3bcee714b19805407b1c35821b6ca485b8a65a408ecbc65b012c101f6`,
  City
  `d57f4ba36f0044b3a3012acf66cb78049c045f00bfdc83c18ac0bee0edcc31b8`,
  and SVG
  `b2695896fd6abb6ee2b371b9c14072c314e9a39ed1ecb8378766ff757bc309d6`.
- Fixes applied and reverified: initial overview plot choice ranked by area and
  repeatedly favored rectangles at one corner. Deterministic spatial
  separation replaced that ranking. The first semantic capture also exposed
  a missing test-facility legend; the final artifact includes the disclosure.
- Open risks / next actions: the 42 Next.js UI files share one gate archetype,
  so route/page hierarchy and frontend component families still need richer
  silhouettes. File size and line metrics remain blocked on explicit UCG
  schema approval. A dedicated README showcase composition is still pending.
- Commits created / pushed (and branch): `86bafe7` and `5476e42` on local
  `main`; push is scheduled after this checkpoint log commit.

## Checkpoint 2026-10-18 - centered overview massing and GamjaOJ cross-check (`08948d9`, `329b40b`)

- Implemented: overview blocks now render a bounded square-root population of
  representative masses, balance plot selection around both block axes, and
  center incomplete rows. Nested major-district territory is subtracted from
  residual parent blocks so two aggregate layers cannot paint the same land.
- Fixture(s) / revision(s): external `visual_test_proj/GJ-Cloud` at revision
  `3d9b53f9dac9af1187ac9754cb3066b27e43b766` and the newly added external
  `visual_test_proj/GamjaOJ` at revision
  `b163acd2b5fe41edfc1e7fc7d367362851241896`; a synthetic nested-major-district
  regression scene; and all maintained contract and viewer fixtures.
- Commands run: complete builds for GJ-Cloud and two complete post-fix GamjaOJ
  builds; Node geometry, membership, and distribution audits; Edge SwiftShader
  WebGL and CPU SVG captures; `python -m pip check`; Ruff; `compileall`;
  JavaScript syntax checks; release-readiness validation; whitespace checks;
  and the complete automated suite.
- Artifacts inspected: GJ-Cloud WebGL and SVG output under
  `D:\Code\MetroPoGits\artifacts\visual\.visual-gj-cloud-centered-overview-1`;
  GamjaOJ `viewer-webgl.png`, `preview-browser.png`, and complete static output
  under
  `D:\Code\MetroPoGits\artifacts\visual\.visual-gamja-oj-overlap-fixed-1`.
- Visual findings: PASS for the reported upper-left overview concentration.
  GJ-Cloud increases from 128 to 235 representative masses across the same 37
  traceable blocks; their mean normalized center changes from X 32.4%, Z 47.9%
  to X 49.7%, Z 50.2%. The inspected overview fills formerly empty block land
  while preserving readable service campuses and distinct semantic colors.
- Cross-repository findings: GamjaOJ produces 681 buildings, 117 districts,
  and 31 evidence networks from 322 Java, 160 JavaScript, 106 Python, 79 SQL,
  13 shell, and one C++ file. Its overview contains 30 blocks, 148
  representative masses, and 198 polygon plots. All 681 canonical files occur
  exactly once; mean normalized mass center is X 49.8%, Z 50.3%. Backend source,
  frontend app, frontend tests, repository tests, and scripts remain visually
  distinct instead of inheriting the GJ-Cloud service arrangement.
- Traceability and evidence findings: GamjaOJ analysis completes with 1,251
  entities, 5,130 relations, and 4,605 evidence records. Diagnostics disclose
  seven unresolved Java relations, ten unavailable Java types, and thirteen
  unresolved JavaScript imports without fabricating targets. No target code,
  package manager, or build script was executed.
- Spec alignment: PASS under DEC-008, ADR-012, FR-002, and the renderer-only
  LOD boundary. The change modifies only visual aggregate projection; UCG,
  City Scene, canonical file positions, stable IDs, evidence, and network edge
  membership remain unchanged. Aggregate structures remain explicitly visual
  and traceable to their complete member lists.
- Tests / determinism / stability: 218 tests passed with one expected Windows
  symlink skip. Ruff, compilation, JavaScript parsing, dependency consistency,
  release readiness, and whitespace checks passed. The two GamjaOJ builds are
  byte-identical across every generated artifact. Canonical SHA-256 values are
  UCG `596ea09876c85509966337e74fabe8b01205146a8abb8028d94d14bac2dc7518`,
  City `623591c0bf8c5f35ada1aeae9b21bed0fa510aa01f68a620cde9e9a206d6559c`,
  and SVG `e269643073771c9630862580909cccb1ab822cfe271f18d249436b8b0a96fee3`.
- Fixes applied and reverified: the first GamjaOJ audit found three physical
  overlaps between residual `frontend` block floors and nested `frontend/app`
  floors. Subtracting nested major territory reduces GamjaOJ overlap from three
  to zero; GJ-Cloud remains at zero. A synthetic hierarchy now locks this case
  independently of either external fixture.
- Open risks / next actions: two unrelated major districts whose final path
  segment is `tests` currently receive the same short visible label; selection
  and inspector identity are correct, but path-aware duplicate-label
  disambiguation would improve overview legibility. README SVG still uses the
  detailed renderer rather than a dedicated showcase composition, and file
  size/line metrics still require explicit schema approval.
- Commits created / pushed (and branch): `08948d9` and `329b40b` on local
  `main`; push is scheduled after this checkpoint log commit.

## Checkpoint 2026-10-18 - contract documentation and public repository state

- Implemented: reconciled README, candidate status, versioned contract notes,
  roadmap, ADR-007, and release-readiness descriptions. Repository visibility
  is public; Pages remains deferred. Corrected the roadmap's already-shipped
  Next.js/test PATH rules. No renderer or scene-generation code changed.
- Fixture(s) / revision(s): maintained `spring-positive` fixture at source
  revision `22aafa8`; generated revision label `docs-sync`.
- Commands run: `python -m unittest discover -s tests -q` (218 run, 217 pass,
  one Windows symlink skip); after the publication assertion update,
  governance (9) and readiness (11) tests passed; CLI readiness validation,
  Ruff, compileall, Node parsing, pip check, and git whitespace checks passed.
  Built twice with `python -m metropogits build --repo
  tests/fixtures/repositories/spring-positive --repo-id fixture/docs-sync
  --revision docs-sync --out ../artifacts/visual/docs-sync-20261018/first`
  and the same command with output `second`; all 12 files including the
  manifest matched by SHA-256. GitHub repository API returned `private:false`,
  `visibility:public`, `has_pages:false`.
- Artifacts inspected: `artifacts/visual/docs-sync-20261018/first` UCG/City,
  and sibling `viewer.png` / `preview.png` captures from headless Chrome.
  WebGL rendered six role-colored buildings and two evidenced networks.
  Representative building evidence and network edge references were inspected.
- Visual findings: WebGL initialization and the small fixture's distinct
  silhouettes are usable. Existing detailed SVG has a framing/layering defect:
  a large district surface covers part of the title region. Recorded as an
  explicit VIS-02 correction and regression case; visual completion is NOT
  claimed. No new large-repository or interaction-performance measurement ran.
- Spec alignment: PASS for documentation reconciliation; UCG remains 0.1,
  City producer remains 0.2 and layout 1.13. Original sibling specifications
  received dated reconciliation notes; the committed contract baseline records
  the same facts because those sibling files are outside this Git repository.
- Fixes applied and reverified: governance assertion now distinguishes
  completed public conversion from deferred Pages. Release state remains
  BLOCKED with unchanged check statuses. The SVG defect is queued for the
  renderer work unit and blocks claiming visual polish complete.
- Open risks / next actions: write Showcase ADR, then implement its CPU
  renderer with protected header bounds and cross-repository visual checks.
- Commits created / pushed (and branch): this documentation work unit is on
  `main`; push follows the final documentation validation.

### Documentation follow-up — ADR-013

- Accepted the implementation contract for an additional CPU-only
  `showcase.svg`, with preserved detailed-preview defaults, traceable block
  membership, versioned SVG metadata, deterministic camera selection,
  protected header/legend bounds, and staged CLI/Action integration.
- Reviewed consumers: CLI build/render, artifact manifest, generated README
  snippet, Action artifact directory, hosted smoke checks and viewer fallback.
  No runtime implementation or generated artifact changed after the checkpoint
  above; the new renderer is explicitly still pending.
- Documentation/link and whitespace validation precede the independent ADR
  commit. VIS-00 is commit `fa4c1ae`; VIS-01 is the subsequent ADR commit.

## Checkpoint 2026-10-18 - detailed SVG framing correction

- Implemented: include street rectangles and civic-plot margins in preview
  bounds and clip city geometry below the header. Updated the SVG golden hash
  for the intentional framing change; no UCG, layout, or viewer code changed.
- Fixture / command: `python -m metropogits build --repo
  tests/fixtures/repositories/spring-positive --repo-id fixture/showcase
  --revision showcase --out ../artifacts/visual/showcase-20261018/spring`,
  repeated at `spring-repeat`; maintained fixture from `3829d6e`.
- Artifacts inspected: generated SVG via headless Chrome screenshot
  `artifacts/visual/showcase-20261018/detail.png`. Header is fully visible,
  six file buildings and both evidence routes fit below it. Static viewer
  assets are unchanged; fresh interaction testing is deferred to the showcase
  checkpoint. The earlier WebGL checkpoint remains the viewer baseline.
- Tests / determinism: 219 tests run, 218 passed, one Windows symlink skip;
  Ruff passed; all generated files matched across the two builds. Regression
  checks all drawn rectangle extents remain below the protected header.
- Spec alignment: PASS under FR-011 and AC-002; scene identities and canonical
  coordinates are unchanged. The formerly omitted street bounds explain the
  revised static preview scale.
- Open risks / next actions: implement ADR-013 isometric showcase; detailed
  top-down output remains a structural inspection target.
- Commit / push: independent preview fix on main; delivery follows the
  completed showcase checkpoint.

## Checkpoint 2026-10-18 - CPU showcase and build integration (ADR-013)

- Implemented: CPU block/representative projection and existing WebGL cuboid
  forms, deterministic four-orientation isometric framing, bounded evidence
  routes, path-aware major labels, protected header/footer and trace metadata.
  `render --mode showcase` is opt-in; `build` emits both SVGs, checksums them,
  and points the generated README snippet at showcase. Composite Action output
  remains compatible; hosted smoke now requires both images.
- Fixture(s) / revision(s): GJ-Cloud at
  `3d9b53f9dac9af1187ac9754cb3066b27e43b766`, GamjaOJ at
  `b163acd2b5fe41edfc1e7fc7d367362851241896`; maintained Spring positive,
  new Go/Rust/Elixir structural-only fixture, and a synthetic 315-file nested
  major-district scene including mixed-case IDs. Target code was not executed.
- Pipeline commands: `python -m metropogits build --repo
  ../visual_test_proj/GJ-Cloud --out ../artifacts/visual/showcase-20261018/gj`
  and the equivalent `GamjaOJ` / `oj` command; small fixture builds use
  `--repo tests/fixtures/repositories/spring-positive --repo-id fixture/showcase
  --revision showcase --out ../artifacts/visual/showcase-20261018/spring` and
  `--repo tests/fixtures/repositories/structural-showcase --repo-id fixture/unknown
  --revision showcase --out ../artifacts/visual/showcase-20261018/unknown`.
  All four builds returned COMPLETE with 12 manifest-listed artifacts.
- Render commands: `python -m metropogits render --scene <build>/city.json
  --graph <build>/graph.ucg.json --mode showcase --width 640 --height 360
  --out ../artifacts/visual/showcase-20261018/<case>-thumb.svg` for GJ/OJ.
  Default 1200x675 images are in each complete build directory.
- Artifacts inspected: `gj.png`, `oj.png`, `spring.png`, `unknown.png`,
  `gj-thumb.png`, `oj-thumb.png`, `gj-viewer.png`, and `oj-viewer.png` under
  `artifacts/visual/showcase-20261018`. Chrome headless captured SVG at
  1200x675 / 640x360 and WebGL with SwiftShader at 1280x800. WebGL initializes
  with the existing overview blocks and the detailed-preview fallback link.
- Visual findings: major services are legible in the GJ isometric composition;
  OJ's distinct facility clusters persist and its duplicate tests labels are
  disambiguated in showcase. Building silhouettes now show genuine vertical
  faces in the README image. Header/footer and building tops are not clipped.
  Small output initially reserved too much margin; reduced thumbnail margins
  were re-rendered and inspected. Sparse input remains three generic files,
  with no invented landmarks to fill its structural street area.
- Projection measurements (relative to the protected content area):

  | Fixture | Files / blocks | Yaw | Bounding-box occupancy | Sampled polygon coverage | Shown routes |
  | --- | --- | --- | --- | --- | --- |
  | GJ-Cloud | 1324 / 37 | 90 degrees | 87.9% | 40.2% | 24 / 135 |
  | GamjaOJ | 681 / 30 | 270 degrees | 76.1% | 35.8% | 24 / 31 |
  | Spring | 6 / detail | 180 degrees | 76.4% | 37.4% | 2 / 2 |
  | Unknown languages | 3 / detail | 180 degrees | 92.5% | 50.4% | 0 / 0 |

  Coverage is deterministic 160x90 center sampling of terrain/building polygons,
  not pixel opacity, building density, or measured runtime usage.
- Tests / determinism / stability: 229 tests run, 228 passed and one expected
  Windows symlink skip. Ruff, compileall, Node syntax, pip consistency,
  readiness validation and whitespace checks passed. Re-rendering each of the
  four saved scenes twice reproduced its build SVG bytes; every manifest
  artifact size and SHA-256 was checked. Fresh GJ/OJ graph and City bytes are
  identical to their previous centered-overview/overlap-fixed baselines, so
  this work introduces no semantic or canonical layout churn.
- CPU/WebGL parity: synthetic regression compares complete block geometry and
  membership, balanced representative positions and all archetype cuboids.
  A separate Node/Python comparison of the actual GJ/OJ City documents found
  zero membership or geometry differences across 37/30 blocks and 235/148
  representative masses. Browser locale list order is ignored by matching
  stable block IDs and canonical member lists; numeric tolerance is 1e-7 for
  that audit. Complete membership, plot containment, explicit hidden route
  IDs and exact evidence edge lists remain tested independently.
- Fixes applied and reverified: standalone CLI strict JSON decoding exposed
  Decimal/float mixing in projection; a private numeric render copy fixes it
  without mutating canonical input. Detailed preview's unpublished framing
  commit was also corrected and given a strict-loader regression; its final
  commit is `0c64bb1`.
- Spec alignment: PASS under ADR-013, DEC-005/006/008/009/011 and FR-011.
  UCG/City contracts, file IDs and network membership are unchanged. The
  original sibling specification files were updated locally to describe the
  additive output; those files are outside this Git repository.
- Open risks / next actions: VIS-06 controlled same-view WebGL comparisons and
  input/FPS measurements remain pending. WebGL still has duplicate short tests
  labels and dense content near its legend; this renderer does not change that
  UI. Thin evidence routes and dense generic silhouettes still need VIS-03/04
  polish. Neither the new artifact nor public repository visibility activates
  Pages; external repository output stays local.
- Commits / push: `0c64bb1` is the independent preview fix; showcase plus its
  build/Action integration is the following feature commit. Both use the
  configured human identity, with delivery to the maintainer-authorized main.

## Checkpoint 2026-10-18 — VIS-06 controlled WebGL audit

- Implemented: local Node/CDP comparison harness with isolated instrumented
  viewer copies, fixed camera/viewport, natural three-level LOD, common-distance
  overview, trusted mouse inputs, render-stage timings, raw JSON and HTML gallery.
  Normal viewer assets and product dependencies are unchanged. Five browser-free
  Node regression cases run through one Python suite test.
- Fixtures / revisions: unchanged full GJ-Cloud and GamjaOJ builds from
  `showcase-20261018`, source revisions and environment in `VIEWER_BENCHMARK.md`.
  Fresh small Spring and unsupported Go/Rust/Elixir pipeline builds use this
  checkout's fixtures with explicit `checkpoint` revision labels.
- Commands: `node scripts/viewer_audit.mjs <chrome> <new-output> <gj> <oj>`
  and a second run reversing input order (full paths in benchmark guide);
  `python -m unittest discover -s tests -q`; `node --test
  tests/viewer_audit.test.mjs`; `node --check scripts/viewer_audit.mjs`;
  `python -m ruff check metropogits scripts tests`; `python -m compileall -q
  metropogits scripts tests`; `python -m pip check`; `python
  scripts/validate_release_readiness.py release/readiness.json`; `git diff --check`.
  Fresh builds: `python -m metropogits build --repo
  tests/fixtures/repositories/spring-positive --repo-id fixture/visual-audit
  --revision checkpoint --out ../artifacts/visual/comparison-20261018-fixture`
  and the same command with `structural-showcase`, `fixture/visual-audit-unknown`,
  and `comparison-20261018-unknown` respectively.
- Artifacts inspected: eight WebGL PNGs and the gallery screenshot in workspace
  `artifacts/visual/comparison-20261018-r2`; raw reports there and in
  `comparison-20261018-reverse`; fresh Spring/unknown showcase SVG captures.
  Generated samples, browser profiles and reports remain outside the Git repo.
- Visual findings: same camera/scale preserves different city morphology;
  both fitted overviews lose foreground content under the legend. OJ has
  duplicate tests labels. Circuit-like relation lines and generic silhouettes
  remain, while block membership and major service groupings remain legible.
  Small fixture forms retain their role differences; unsupported sources remain
  generic without invented roads. No claim that visual defects were fixed here.
- Performance findings: software SwiftShader, 20 measured inputs after five
  warm-ups per interaction/LOD. GJ Detail orbit CPU median 54.9–55.3 ms,
  p95 87.3–98.5 ms; geometry-preparation p95 78.2–90.8 ms. First-draw latency
  is highly order-sensitive. These are draw-submission CPU timings, not native
  GPU FPS or physical input-to-display measurements; no universal SLA asserted.
- Tests / determinism / stability: 230 tests run, 229 pass, one expected Windows
  symlink skip; all five Node audit cases pass. Lint, syntax, compile, dependency,
  readiness and whitespace checks pass. Rechecked all original input hashes in
  both audit reports and checksums/sizes of both fresh build manifests. No
  canonical geometry/graph changes or layout churn. Existing deterministic
  pipeline and source-evidence tests remain green.
- Fixes applied and reverified: Node test output needs explicit UTF-8 decoding
  under Windows Python; the initial cp949 subprocess reader failure was fixed
  and the complete suite rerun successfully. CDP failures/disconnects fail closed.
- Spec alignment: PASS — TECH sections 7/8/10/11, FR-012, NF-008/009 and
  product DEC-005/006/008/009/011. Audit code executes only locally prepared viewer
  assets; neither input application nor its dependency/build scripts is executed.
  No schema change, publishing, LLM, or product backend introduced.
- Open risks / next actions: cache static render geometry with tested state
  invalidation; reserve legend space; then road hierarchy, existing silhouette
  readability and contextual labels. Hardware GPU/display timing, larger sample
  statistics and broader corpus remain unverified. Pages stays deferred/BLOCKED.
- Commit / push: this harness, regression cases and measured baseline form one
  `test(viewer)` work unit, delivered to the explicitly authorized owner main
  using the existing human identity. Previous showcase CI `dc10c1a` succeeded;
  new commit CI is checked separately after push.

## Checkpoint 2026-10-18 — camera-only geometry reuse

- Implemented: one-entry geometry cache keyed by LOD/filter generation/selection;
  unchanged arrays retain their GPU buffers. Synthetic activity bypasses the
  cache so animated markers remain current. No graph or layout change.
- Commands: full unittest suite (230 run, 229 pass, one Windows symlink skip);
  real `build --repo ../visual_test_proj/{GJ-Cloud,GamjaOJ}` into workspace
  `artifacts/visual/frontage-cache/{gj,oj}` and spring-positive into `spring`;
  `node scripts/viewer_audit.mjs <chrome> ../artifacts/visual/frontage-cache-audit
  ../artifacts/visual/frontage-cache/gj ../artifacts/visual/frontage-cache/oj`.
- Observed: actual GJ Detail capture retains the same content/roads and counts.
  Same audit protocol: GJ orbit CPU p95 Overview/District/Detail 2.4/3.1/6.6 ms;
  OJ 1.0/1.6/2.5 ms. Prior GJ Detail 87.3–98.5 ms. Software SwiftShader,
  draw-submission CPU only; not a hardware FPS claim. Legend overlap remains.
- Tests: cache reuses identity on camera frames, invalidates all visual state
  keys, and produces fresh animated geometry before restoring static geometry.
  Full pipeline/golden/determinism tests pass. Spec alignment PASS (TECH 8,
  FR-012/NF-008); schema and evidence unchanged.
- Next: legend isolation and ADR-014 frontage/circulation implementation.
- Commit / push: independent perf(viewer) unit on owner-authorized main.

## Checkpoint 2026-10-18 — separate legend row

- Implemented: canvas/labels/hover share a bounded stage; legend occupies an
  independent auto-sized grid row, including wrapping on narrow screens.
- Commands: 231 unittest cases (230 pass, one Windows symlink skip), real
  spring-positive build into `artifacts/visual/frontage-legend/spring`;
  local review repack of unchanged GJ/OJ canonical scenes into `frontage-legend`;
  same Node audit into `frontage-legend-audit`.
- Artifacts inspected: GJ Overview PNG now fits foreground geometry above the
  legend rather than behind it. Both three-LOD browser audits complete without
  exceptions. Static SVG output/graph/City are unchanged; this is a UI-only fix.
- Spec alignment: PASS (FR-012/NF-009). Tests assert stage/legend separation;
  shared CSS applies to WebGL and fallback. Context labels remain separate work.
- Commit / push: independent fix(viewer) unit on owner-authorized main.

## Checkpoint 2026-10-18 — evidence-aware frontage and reserved internal streets

- Implemented: ADR-014, layout `hierarchical-paged/1.14`. Evidenced file roles
  and DIRECT/RESOLVED references influence boundary/interior sites within each
  directory page. Duplicate pairs cannot amplify weights; popular targets are
  normalized. Identical-shape sibling swaps strictly reduce weighted sibling
  distance without changing occupied land; hints and compact leaf groups lock.
  Internal cross streets are reserved before placement. WebGL/fallback/SVG use
  shared curb/asphalt/paint geometry. Overview plots exclude streets.
- Fixtures: GJ-Cloud `3d9b53f9dac9af1187ac9754cb3066b27e43b766` (1324 buildings),
  GamjaOJ `b163acd2b5fe41edfc1e7fc7d367362851241896` (681), maintained
  spring-positive and structural-showcase (unknown-language) fixtures.
- Commands: `python -m unittest discover -s tests` (240 run, 239 pass, one
  expected Windows symlink skip); Ruff, compileall, Node syntax, pip check,
  release-readiness validation, whitespace check. Real `python -m metropogits
  build --repo <fixture> --out ../artifacts/visual/frontage-streets-r4/<case>`
  for all four fixtures. `node scripts/viewer_audit.mjs <chrome>
  ../artifacts/visual/frontage-streets-r4-audit <gj-build> <oj-build>`;
  isolated timing repeat into `frontage-streets-r4-timing`.
- Inspected: GJ/OJ Overview/Detail browser PNGs and both rendered showcase SVGs;
  small Spring preview and unknown-framework showcase. The latter two were
  inspected in the earlier frontage-streets run and rebuilt with final layout.
  Internal road space is now visible inside dense districts. Overview still
  has slender representative towers; OJ duplicate WebGL labels remain open.
- Quantitative comparison: local developer audit `artifacts/visual/audit_frontage.py
  frontage-streets-r4` generates fresh neutral/repeat/hinted scenes and reports
  per-case `layout-review.json`. No sample graph/source data is committed.

| Metric | GJ neutral / current | OJ neutral / current |
| --- | ---: | ---: |
| Root AABB area (same new circulation spacing) | 437325 / 437325 | 150920 / 150920 |
| Mean unique linked-file Manhattan distance | 156.49 / 151.57 | 135.72 / 121.82 |
| Mean normalized boundary inset, outward-biased files | .0880 / .0818 | .0753 / .0628 |
| Mean normalized inset, inward-biased files | .0821 / .1303 | .0814 / .0814 |

- Scope of metrics: distance is unweighted unique-pair file distance, not runtime
  latency or shortest routed distance. Inset is relative to the owning directory
  AABB, not proof of major-service outer-boundary placement. The neutral control
  disables only role/relation preference with identical circulation geometry.
  New root area vs old 1.13: GJ 407925 → 437325 (+7.2%); OJ 121520 → 150920
  (+24.2%). This is the explicit cost of reserving internal street space; do
  not claim the old and new algorithms have equal density.
- Determinism / integrity: both real graphs byte-identical to prior baseline;
  all network IDs and exact edge memberships preserved. Final cold repeat
  canonical City bytes match. Reusing the final scene as hint preserves all
  buildings/districts. Street/building intersections and route centerline
  crossings are zero in both inputs; City validators report zero errors.
  Algorithm migration moves 1324/1324 and 678/681 file positions respectively;
  this is a deliberate version migration, not small-change hint churn.
  Regression fixtures separately cover new-reference hint stability and nearby
  file changes, evidence negatives, exact shape swaps, and JS/Python parity.
- Corrections made: rejected role-first group packing (GJ area 616077), then
  rejected merely equal-score placement ties (global footprint still grew).
  Identical-footprint swaps keep the control's exact root area. Fractional
  building offsets exposed a Decimal/float federation-reader crash; normalized
  coordinate arithmetic and reran the existing CLI test without expanding P2.
  Updated SVG golden hash only for reviewed spacing/street-layer migration.
- Performance: isolated GJ/OJ Detail orbit CPU p95 5.4/2.1 ms, versus the old
  GJ 87–99 ms baseline; software renderer, not GPU FPS. Full measurements and
  limitations are in VIEWER_BENCHMARK.md.
- Spec alignment: PASS with approved ADR-014 amendment to DEC-007/ADR-004.
  UCG/City fields and stable IDs unchanged; City layout enum extended. 1.13
  hints rejected with diagnostics; old scenes remain readable. Three sibling
  source specifications updated locally; tracked current-contract/ADR/roadmap
  documents record the same amendment. No repository code executed, backend,
  LLM, new dependency, deployment, or sample publication introduced.
- Open risks / next actions: macro service-boundary gates are not guaranteed;
  aggregate silhouettes do not preserve individual role frontage. Refine
  semantic Overview anchors/proportions and contextual labels next. Do not
  infer HTTP/message traffic from visual streets or imports. Pages stays blocked.
- Commit / push: one coherent layout/circulation unit on owner-authorized main,
  after the independent ADR, cache and legend commits; no agent attribution.

## Checkpoint 2026-10-18 — synthetic animation regression

- Fixed: synthetic activity no longer bypasses static geometry caching. Moving
  markers have a separate DYNAMIC_DRAW buffer. Unchanged camera/LOD/filter/
  selection reuses hit regions and labels as well. No graph/City changes.
- Baseline correction: prior timing checks covered synthetic-off only. The old
  synthetic path rebuilt/re-uploaded the entire city on every frame. Actual GJ
  Detail CPU p95 was 105.5 ms and upload 14043456 bytes/frame (20 sampled frames,
  20 static builds). This regression was missed in the previous checkpoint.
- Verification: extended `scripts/viewer_audit.mjs` enables/disables synthetic at
  all three LODs, checks marker vertex motion, static build count, and upload
  bytes. Fixes a CDP measurement race by capturing sequence and configuring the
  camera atomically. Cache invalidation and isolated dynamic-buffer tests added.
- Artifacts: unchanged canonical GJ/OJ scenes repackaged with current assets in
  workspace `artifacts/visual/synthetic-fixed-r2/{gj,oj}`; real spring-positive
  pipeline in `synthetic-fixed/spring`. Baseline `synthetic-before/report.json`;
  after `synthetic-after-r2/report.json`. GJ Detail capture inspected: city and
  routes retained; road geometry itself is still the separate next correction.
- Measured: GJ synthetic CPU p95 Overview/District/Detail 0.6/0.8/1.7 ms; every
  sampled frame has zero static builds. Detail uploads 174960 bytes/frame,
  representing 135 animated markers only. Headless SwiftShader, JS CPU draw
  submission, not GPU/display FPS or a universal performance promise.
- Checks: full 240-test suite, 239 pass/one Windows symlink skip; seven Node
  audit tests, Ruff and whitespace checks. No new dependencies or P2 feature
  expansion; this repairs an existing regression under TECH 8 / FR-023.
- Delivery: independent fix(viewer) commit to owner-authorized main. Next is
  route-derived road geometry, not further decoration of empty land.

## Checkpoint 2026-10-18 — route-derived pavement, not empty-space infill

- Implemented: ADR-014 review amendment, authorized by maintainer. Pavement is
  derived from canonical network.path, split at orthogonal crossings and
  collinear overlap boundaries; each segment exposes exact contributing network
  IDs and their edge IDs. Lane paint follows those centerlines. Shared sections
  are drawn once, and pavement visibility follows route LOD/filter visibility.
  Surfaces use flat WebGL quads instead of full 3D boxes. No new graph facts.
- Correction to the preceding frontage assessment: zero building intersections
  did not prove that streets were meaningful. The rejected rule paved vacant
  land; 70.14%/81.12% of GJ/OJ road cells carried no canonical route. This design
  is removed, not hidden by extra decoration. Reserved layout space remains.
- Fixtures: GJ-Cloud 3d9b53f (1324 buildings), GamjaOJ b163acd (681), maintained
  spring-positive and structural-showcase. No input application executed.
- Commands/artifacts: full `build` for all four into workspace
  `artifacts/visual/route-corridors/<case>`; final asset/metadata repack of the
  unchanged GJ/OJ scenes into `route-corridors-r2`, fresh small-fixture builds
  there. `node scripts/viewer_audit.mjs <chrome>
  ../artifacts/visual/route-corridors-audit <gj-r2> <oj-r2>` includes synthetic-on
  checks at three LODs. GJ Detail/Overview and OJ Detail PNGs inspected, GJ
  showcase, Spring detailed SVG and unknown-framework showcase rendered/opened.
- Measurements: GJ 857 derived segments / 286 junctions / 2631 surface pieces;
  OJ 187 / 46 / 594. Previous surface boxes: 5838/2072. New WebGL surface pieces
  are two-triangle quads, not twelve-triangle boxes. Every network's path length
  is exactly covered by its attributed derived segments on both repositories;
  no ungrounded road segments and zero pavement/building intersections. Both
  canonical City and UCG files are byte-identical to frontage-streets-r4, hence
  zero layout churn, unchanged evidence/memberships and hint compatibility.
- Tests: 243 run, 242 pass, one expected Windows symlink skip; eight Node audit
  tests. Added crossing/overlap provenance, input permutation, non-grid path
  coordinates, actual paint direction, no-relation/no-paving and conservative
  diagonal legacy fallback tests. Projection fixture now has an evidenced edge
  so street clipping and Python/JS parity checks cannot pass vacuously. SVG
  golden updated for reviewed route surfaces, not for canonical scene changes.
  Ruff, compile, pip dependency, readiness, and whitespace checks pass.
- Performance: GJ/OJ synthetic Detail CPU p95 1.5/0.5 ms; zero static city builds
  in every sampled animation frame. Marker movement and upload sizes verified.
  No FPS/GPU-completion claim. Actual screenshots have fewer disconnected road
  patches; unsupported/no-edge fixture retains buildings without invented roads.
- Spec alignment: TECH 7/8, AC-006 and DEC-005/011; no schema, stable ID, layout,
  source-execution, backend, dependency or publishing changes. Static showcases
  record selected road provenance in metadata. Old diagonal paths retain their
  original relation overlay without fabricated orthogonal pavement.
- Open limits: existing routes still use aggregate geometric anchors, not
  individual building entrance spurs. Visual intersections do not assert new
  logical relations or runtime transfer. Generalized access-point routing,
  contextual labels and semantic aggregate placement remain follow-up work.
- Delivery: independent fix(renderer) unit after 1d5d63d, committed/pushed to
  owner-authorized main with human attribution only. Pages remains deferred.

## Checkpoint 2026-10-18 — evidence-compatible role landmarks (ADR-015)
- Implemented: shared interactive LOD policy promotes nearby compatible gate
  and test-file clusters to bounded halls/centers (4–11) or terminals/campuses
  (12+). Page/API/controller signatures stay separate; tests need test-source
  evidence. Known module boundaries, parent block land, roads and unrelated
  buildings constrain membership. Generic/unknown facilities are not promoted.
- UI: hover shows three sample paths and an explicit visual-aggregate label;
  inspector exposes complete membership and grouping evidence. File buttons
  select the original entity; Explore clears aggregate selection and zooms in.
  Both interactive renderers share compound volumes. Partial filters do not
  reveal hidden members. Status distinguishes aggregates from individual files.
- Fixtures: GJ-Cloud 3d9b53f, GamjaOJ b163acd, maintained spring-positive and
  structural-showcase. Large cases reuse validated canonical graphs/scenes via
  `artifacts/visual/refresh_for_review.py`; small fixtures use full CLI `build`.
  No target repository code/dependency/build script was executed.
- Artifacts: `artifacts/visual/role-landmarks-r2/{gj,oj}`; small full builds in
  `role-landmarks-r1` and `role-landmarks-r2`. Browser comparisons and screenshots
  in `role-landmarks-audit-r1/r2/r3`. Commands: `python -m unittest discover -s
  tests -q`, `node --test tests/viewer_audit.test.mjs tests/role_landmarks.test.mjs`,
  `python -m ruff check metropogits tests scripts`, `git diff --check`, and
  `node scripts/viewer_audit.mjs <chrome> <new-audit-dir> <gj> <oj>`.
- Measurements: GJ 22 page files -> 3 halls/terminals; 47 tests -> 9 centers.
  OJ 86 tests -> 13 centers/campuses. Exact one-time membership of all 1324/681
  files across Overview aggregates; zero role-footprint/corridor intersections
  and zero unrelated-building intersections on both real scenes. Stage, input
  permutation, sparse/unknown negatives, module separation, geometry bounds,
  filter and selected-file expansion are regression tested.
- Visual findings: inspected GJ Overview and page-hall hover/inspector capture,
  OJ District and test-campus hover/inspector capture, and both static preview
  captures. Real pointer hover/click and constituent navigation pass in Chrome.
  Gate concourses and test wings are distinct; some long narrow test parcels
  remain elongated. Whole-city Overview remains small at this camera fit; this
  unit does not claim to resolve composition or missing relationship coverage.
- Tests: 244 Python tests run, 243 passed, one expected Windows symlink skip;
  13 Node tests passed; Ruff and whitespace checks passed. GJ/OJ UCG, City,
  preview.svg and showcase.svg are byte-identical to route-corridors-r2;
  all generated manifest checksums verified. No canonical layout churn.
- Performance: final r3 synthetic Detail CPU p95 GJ 1.2 ms / OJ 0.5 ms;
  zero static geometry builds in every sampled animation frame at all LODs.
  These are headless SwiftShader CPU submission timings, not GPU FPS.
- Spec alignment: PASS DEC-005/008, AC-002/011, NF-005/008. No schema, source ID,
  graph, runtime service, dependency, security or deployment changes. Canvas
  compound geometry is unit-tested/shared; real pointer audit covers WebGL.
- Open work: CPU showcase role-compound parity, additional role families,
  relationship-assisted grouping, TS aliases/Java nested types, per-file access
  branches/shared routes and evidence-backed HTTP/messaging layers. None is
  implied complete by role landmarks. No new relationship is inferred here.
- Delivery: one feat(viewer) work unit; verified files staged explicitly for
  owner-authorized main. Commit/push outcome is recorded in Git history and the
  handoff, without agent contributor attribution. Pages remains deferred.

## Checkpoint 2026-10-18 — persistent compounds and explicit local expansion
- Corrected e513619's interaction model after maintainer review: Detail zoom
  and constituent inspection no longer dissolve role compounds. Explicit
  Expand constituent files / Collapse facility applies to one facility and
  survives camera zoom. Focus facility only moves the camera; its fit now
  includes compound height to avoid the prior overly close framing.
- Constituent selection keeps the compound and shows a cyan original-footprint
  overlay, disclosed as selection geometry, not another file building. Exact
  entity/evidence inspection remains available. Matching route aggregates are
  selected through their actual UCG edges, without claiming per-file spurs.
- Route visibility: District and Detail keep a 64-route default budget;
  Overview retains 24. Explicit All routes overrides at any zoom. File selection
  shows related routes only unless overridden; no-edge files correctly show
  zero, not fabricated connectivity. Canonical route geometry is unchanged.
- Fixtures/artifacts: unchanged validated GJ-Cloud 3d9b53f and GamjaOJ b163acd
  repackaged to `artifacts/visual/persistent-facilities-r2/{gj,oj}`; fresh full
  CLI builds of spring-positive and structural-showcase in sibling directories.
  Browser reports/captures: `persistent-facilities-audit-r1/r2`. No application
  source, dependencies or build scripts executed.
- Commands: `python -m unittest discover -s tests -q`; `node --test
  tests/viewer_audit.test.mjs tests/role_landmarks.test.mjs`; `python -m ruff
  check metropogits tests scripts`; `git diff --check`; opt-in `node
  scripts/viewer_audit.mjs <chrome> <new-output> <gj> <oj>`; checksum comparison
  against role-landmarks-r2. All canonical UCG/City and static SVG bytes match;
  generated manifest checksums pass, with zero layout/membership churn.
- Browser verification: real hover/click, file navigation without unfolding,
  Focus to natural Detail with all 12 GJ / 13 OJ role facilities retained,
  local expand, zoom-out without collapsing, explicit collapse and All routes
  restore (135 GJ / 31 OJ) pass. Viewed final GJ page-hall and OJ test-campus
  focused images, selected-file image, and the first-pass expanded image. The
  original close-fit clipping was corrected and regenerated. Some neighboring
  ungrouped gates remain separate; no claim that every role file is aggregated.
- Tests: 244 Python tests run (243 pass, one expected Windows symlink skip);
  14 Node tests pass; Ruff/whitespace pass. Updated legacy detail-route count
  expectation to the explicit budget and added all-routes restoration tests.
  Canvas shares the tested policy and controls; browser interaction audit is
  WebGL, not a claim of visually verified Canvas fallback.
- Performance: final synthetic Detail CPU p95 GJ 0.7 ms / OJ 0.8 ms; zero
  static geometry rebuilds in sampled animated frames at all three LODs.
  Headless SwiftShader CPU submission only, not GPU FPS or universal timings.
- Spec alignment: PASS DEC-005/008/011, AC-002/006/011. ADR-015 now explicitly
  separates semantic representation from camera LOD. No schema, graph evidence,
  canonical coordinates, security defaults, dependencies or deployment changes.
- Remaining limits: filters selecting only part of a compound intentionally
  show matching original files; spatial role membership and compound meshes
  are unchanged. True shared access routing, analyzer misses, HTTP/messaging
  extraction and CPU showcase compound parity remain separate work.
- Delivery: one fix(viewer) work unit, explicit staging and human attribution;
  commit/push to owner-authorized main recorded in Git history and handoff.

## Checkpoint 2026-10-18 — District coverage without file sampling
- Implemented: District keeps every filtered file, including persistent role
  compounds; only generic facade geometry is simplified in WebGL. Detail adds
  geometry, not previously hidden files. Original footprints/heights remain.
- Fixtures: unchanged GJ-Cloud 3d9b53f and GamjaOJ b163acd scenes repackaged at
  `artifacts/visual/district-coverage-r2/{gj,oj}`; full CLI builds of
  spring-positive and structural-showcase in `district-coverage-r1`.
- Commands: Python unittest discovery (244 run, 243 pass, one Windows symlink
  skip); Node role_landmarks/viewer_audit tests (15 pass); Ruff; git diff --check;
  refresh_for_review.py; viewer_audit.mjs with local Chrome and both projects.
- Actual captures inspected: district-coverage-audit-r1 case-1/case-2 district.png.
  District now represents GJ 1255 individual + 69 compound members and OJ 595 +
  86, instead of sparse generic samples. Shapes are fuller; long-city framing
  and missing per-file road access are not solved by this change.
- Reverification: corrected optional geometry argument to accept literal true
  only, retaining map-callback compatibility; full suite passes. Repackaged and
  repeated browser audit at district-coverage-audit-r2. District synthetic CPU
  submission p95 GJ 0.8 ms / OJ 0.5 ms, zero animated static rebuilds; headless
  SwiftShader measurements, not GPU FPS. Facility focus/expand/collapse and
  route controls pass at all LODs.
- Determinism/stability: graph.ucg.json, city.json and preview.svg SHA256 match
  previous persistent-facilities-r2 for both repositories (zero canonical churn).
- Spec alignment: PASS; ADR-015 clarified. No new facts, schema or layout change.
- Next: restore missed configured local imports, distinguish communication
  presentation from road pavement, then improve shared access routing.
- Delivery: one fix(viewer) commit, verified milestone pushed to authorized main.

## Checkpoint 2026-10-18 — Recover configured local module relationships
- Implemented: bounded non-executing tsconfig/jsconfig paths resolution. Exact,
  single-wildcard, base-relative mappings and ordered fallback targets bind only
  unique scanned sources. Import and config evidence accompany each resolved
  edge. Missing/ambiguous aliases no longer masquerade as npm dependencies.
  Invalid/nested/oversized configs block ancestor mappings; absolute/URL imports
  cannot be reinterpreted by catch-all patterns. Unsupported JSONC/inheritance
  remains diagnostic, not guessed resolution.
- Commands: Python unittest discovery; Ruff; diff --check; full CLI builds of
  maintained jsts-aliases, structural-showcase, GJ-Cloud and GamjaOJ; browser
  viewer_audit.mjs with Chrome; compare_relations.mjs (local audit helper).
  Artifacts: `artifacts/visual/relations-alias-r2/{gj,oj,aliases,unknown}`;
  browser report/captures `relations-alias-audit-r2`.
- Measurements: GJ local file relationships 5670 -> 6157, with 487 recovered
  imports from 131 files. Connected files 1207 -> 1273; isolated 117 -> 51.
  Four bogus npm/@ packages removed; network aggregates 135 -> 152; all 6157
  eligible edges represented. OJ remains 2243 edges / 400 connected / 281
  isolated / 31 networks. No HTTP or messaging edges manufactured.
- Stability/determinism: previous-scene hints preserve all building coordinates
  in both large projects (0 moved). Repeat analysis is byte-identical in each
  alias regression fixture; unchanged inputs retain source identities. Graph
  and road differences are the expected recovery, not layout resampling.
- Visual check: inspected GJ overview and preview PNGs from the real browser
  audit. Portal has additional dependency corridors; individual access branches
  are still absent in some parcels. District retains full file coverage.
  Browser facility/selection/expansion controls pass for both repositories.
  Synthetic District CPU submission p95 0.9 ms GJ / 0.5 ms OJ, with zero static
  rebuilds (headless SwiftShader, not GPU FPS).
- Tests: 251 Python tests run, 250 pass and one expected Windows symlink skip;
  seven alias tests include maintained positive/negative fixtures, deterministic
  output, scope isolation, ambiguity, exclusions, path escape and resource limits.
- Spec alignment: PASS; no UCG/City contract change, untrusted execution or
  dependency installation. Supported subset and TypeScript reference documented
  in CURRENT_BASELINE. Full TS compiler resolution and Java nested imports remain
  open. Connectivity counts are not an estimate of overall analyzer accuracy.
- Delivery: one fix(analyzer) work unit, human attribution, authorized main push.

## Checkpoint 2026-10-18 — Evidenced endpoints and shared access roads
- Implemented: ADR-016 derived access graph, building-boundary entrances,
  clearance-limited shared pavement and junctions. File-pair routes retain exact
  edge IDs; segments reference their actual routes. Sharing geometry never
  creates a new semantic relation. Communication styling work is deferred;
  shared access is the priority immediately after the alias recovery above.
- Fixtures: GJ-Cloud 3d9b53f, GamjaOJ b163acd, maintained spring-positive and
  structural-showcase (unsupported/low-semantic structural fallback).
- Commands: `python -m unittest discover -s tests -q`; Ruff; Node access_routes,
  role_landmarks and viewer_audit tests; `git diff --check`; full CLI builds via
  `python -m metropogits build --repo <fixture> --out <artifact>`. Large builds
  use `--previous-scene ../artifacts/visual/relations-alias-r2/{gj,oj}/city.json`.
  `node scripts/viewer_audit.mjs <local Chrome> ../artifacts/visual/shared-access-audit-r3
  ../artifacts/visual/shared-access-r3/gj ../artifacts/visual/shared-access-r3/oj`;
  local verify_access.mjs and compare_relations.mjs audit helpers.
- Artifacts: `artifacts/visual/shared-access-r3/{gj,oj,spring,unknown}`;
  controlled browser report/captures in `shared-access-audit-r3`.
  Inspected actual GJ access-selected.png and preview.png, OJ district.png;
  previous r2 GJ selection inspection exposed faint/occluded highlighting.
- Coverage: GJ 6157 evidenced edges / 1273 connected files -> 4209 pair routes,
  9466 segments (7303 shared), 4256 junctions. OJ 2243 edges / 400 files ->
  1381 routes, 2462 segments (1853 shared), 1091 junctions. Both COMPLETE:
  zero unresolved eligible edges and zero pavement/building intersections.
  GJ 51 and OJ 281 files without eligible local edges are not artificially wired.
- Stability: graph.ucg.json and city.json SHA256 unchanged against alias-r2 for
  both projects; zero moved buildings. Public canonical network groups remain
  compatible, while all renderers consume the derived endpoint routes. No new
  HTTP/messaging facts, public schema change, or repository-code execution.
- Visual findings: README now shows internal corridors as well as inter-block
  connections. Dense ground-level access is still narrow/subpixel at city scale;
  selected routes use an explicitly labeled ground-coordinate x-ray overlay.
  It reveals complete paths through visual occlusion without inventing elevated
  roads. District retains individual files and persistent role compounds.
  Large-city framing, narrow-street legibility and muted road contrast remain
  iterative quality work; this is not a claim of final urban appearance.
- Browser checks: real constituent/file clicks, exact selected-route/segment
  coverage, All routes context, facility focus/expand/collapse and synthetic
  path membership pass. Synthetic samples at most 96 stored routes, never random
  junction turns. Static geometry rebuilds during animation: zero at all LODs.
  GJ first draw submission 718.7 ms; orbit CPU p95 Overview/District/Detail
  12.8/20.7/21.0 ms, synthetic 1.5/1.1/1.3 ms. OJ first draw 180.2 ms; orbit
  2.6/5.6/5.6 ms, synthetic 1.1/1.6/1.2 ms. Headless SwiftShader CPU submission
  measurements, not GPU FPS; GJ camera interaction remains above 16.7 ms p95.
- Tests: 257 Python tests run, 256 pass, one expected Windows symlink skip;
  19 Node tests pass; Ruff and whitespace checks pass. Access tests cover
  permutation determinism, exact provenance, bounded detours, collision-free
  pavement, self-reference, filters, synthetic paths and resource-limit fallback.
- Fixes reverified: coalesce only straight segments with identical provenance
  and width (GJ 16047 -> 9466; OJ 4039 -> 2462); restore All routes context;
  label/draw selected-path x-ray; wrap long toolbar counters. Fresh r3 pipeline
  and asset-integrity-checked browser audit pass after these corrections.
- Spec alignment: PASS, derived visual routing with bounded failure diagnostics.
  Open risks: larger viewer payload (~37 MB GJ), camera CPU, narrow access lanes,
  Java/other unresolved analysis coverage. Canvas implementation has regression
  checks but was not visually inspected in a browser this checkpoint. Keep
  communication-layer redesign deferred until this road behavior is reviewed.
- Delivery: one feat(renderer) work unit on authorized main; commit/push and CI
  status are verified separately at handoff, not inferred from local tests.

## Checkpoint 2026-10-18 — Ground camera movement and remote district navigation
- Implemented: visible Move mode, four directional buttons, WASD/arrow movement,
  Shift/Alt/right/middle drag, and a major-district jump selector in both viewer
  paths. WebGL vertical drag now translates X/Z instead of changing target Y.
  Movement follows camera orientation and zoom; rotation retains the translated
  pivot. Reset restores the fitted city view. Form/editable controls and browser
  modifier shortcuts are not intercepted. No change to semantic/layout data.
- Fixtures: maintained structural-showcase through the complete pipeline;
  GJ-Cloud 3d9b53f and GamjaOJ b163acd via trusted shared-access-r3 graph/scene
  snapshots for controlled camera comparison. Input repositories were not run.
- Commands: `python -m unittest discover -s tests -q`; `python -m ruff check
  metropogits tests scripts`; `node --test tests/camera_navigation.test.mjs
  tests/access_routes.test.mjs tests/role_landmarks.test.mjs tests/viewer_audit.test.mjs`;
  JavaScript syntax and `git diff --check`; full `metropogits build` of
  structural-showcase and local GJ; local refresh_for_review.py/repackage_camera.py;
  `node scripts/viewer_audit.mjs <Chrome> ../artifacts/visual/camera-navigation-audit-r3
  ../artifacts/visual/camera-navigation-r3/gj ../artifacts/visual/camera-navigation-r3/oj`.
- Input-change finding: fresh GJ analysis in camera-navigation-r1/gj is PARTIAL,
  with LAYOUT_HINT_PARTIAL, not a successful unchanged-input baseline. Four
  bin/main/schema.sql output copies under Backend/{Auth,Ops,User,Vm} are now
  eligible inputs (1328 rather than 1324 files); 250 existing buildings moved.
  This is not caused by the camera-only patch. No input/cache files were deleted
  to hide it. Generated-output exclusion and hint churn are explicit next fixes;
  arbitrary source directories named bin must not be blindly excluded.
- Artifacts inspected: camera-navigation-audit-r2 case-1/case-2
  camera-district-jump.png and case-1 preview.png; r3 case-1 camera-district-jump.png
  after the Inspector correction. User district is centered and navigable; OJ
  scripts district fills the focused view. Background districts may be cropped
  intentionally while focused. Toolbar wraps without covering the canvas.
- Fix applied after visual inspection: a major district incorrectly displayed
  0/0 because only direct files were counted. Inspector now includes descendants
  and labels counts as filter matches, not rendered/on-screen buildings. GJ
  Backend/User reports 115/115, with regression coverage for sibling exclusion.
- Browser checks: real pointer drag in Move mode, directional control, keyboard
  movement, form-key isolation, orbit-pivot persistence, Reset, and farthest
  major-district jump pass in both projects. Existing role-compound, access-path,
  synthetic provenance and all-LOD controls also pass. Synthetic static builds
  remain zero. GJ orbit CPU p95 Overview/District/Detail 12.2/16.8/20.0 ms;
  OJ 2.8/4.5/4.4 ms. Synthetic p95 GJ 1.5/1.0/1.1 ms, OJ 1.1/1.2/1.5 ms.
  These are headless SwiftShader CPU submission measurements, not GPU FPS.
- Tests/stability: 259 Python tests run, 258 pass, one Windows symlink skip;
  23 Node tests pass; lint/syntax/whitespace checks pass. Repackaged GJ/OJ
  graph.ucg.json, city.json, preview.svg and showcase.svg exactly match prior
  SHA256 values: zero canonical churn for the camera work. The first attempted
  dotted unittest invocation failed because tests is not a Python package;
  corrected discovery invocation passed, without changing or skipping tests.
- Spec alignment: PASS for FR-012, NF-009 and unchanged evidence/scene contracts.
  Canvas controls are implemented and covered by packaging/policy tests but are
  not visually verified in this checkpoint. Large-scene camera CPU and narrow
  road contrast remain open; communication changes remain deferred.
- Delivery: one feat(viewer) local commit. Push intentionally not attempted:
  the latest supplied AGENTS prohibits direct protected-main pushes, superseding
  the earlier owner exception. A permitted delivery branch/workflow needs user
  direction. Existing untracked .gradle/target directories and deferred stash
  are preserved and excluded from the commit.

## Checkpoint 2026-10-18 — Exclude explicitly declared module-local JVM output
- Implemented: a bounded local bin-output declaration beside a regular JVM
  manifest, not global bin exclusion or a general Git ignore/index emulator.
  Exact bin/ or /bin/ declarations authorize pruning; root-matching later
  negations cancel it. Source-level nested bin and ordinary script bins survive.
  Escaped/character-class negations conservatively preserve the output. Unreadable,
  linked, oversized or invalid declarations cannot authorize exclusions.
- Limits/security: no Git subprocess, build, dependency installation or target
  code execution. At most 64 KiB per candidate declaration, charged to the scan
  byte budget. Existing safe reader and reparse/link guard are reused. Explicit
  exclusions of the manifest/declaration also prevent it authorizing pruning.
  Diagnostics disclose the skipped path without embedding ignore-file contents.
- Fixtures/revisions: GJ-Cloud 3d9b53f, GamjaOJ b163acd, maintained
  structural-showcase; six scanner regression cases with temporary positive,
  negative, linked-metadata, size-limit and generated-copy-addition fixtures.
- Commands: `python -m unittest discover -s tests -q` (265 run, 264 pass, one
  Windows symlink skip); focused test_generated_outputs discovery; Ruff;
  `git diff --check`; full CLI builds from both local repository inputs with
  camera-navigation-r3 scenes as previous-scene hints, and structural-showcase.
  `node scripts/viewer_audit.mjs <Chrome> ../artifacts/visual/generated-output-filter-audit-r1
  ../artifacts/visual/generated-output-filter-r1/gj ../artifacts/visual/generated-output-filter-r1/oj`.
  Local compare_relations.mjs and verify_access.mjs audit helpers also run.
- Artifacts: `artifacts/visual/generated-output-filter-r1/{gj,oj,unknown}`;
  all three builds COMPLETE. Actual captures inspected: audit case-1 overview.png,
  case-2 district.png and case-1 preview.png. District structure, existing camera
  movement and traceable roads remain intact; narrow-road contrast and compact
  Overview framing remain open visual issues, not masked with decoration.
- Fidelity/stability: GJ returns from contaminated 1328 files to 1324. Four
  excluded module bin roots explicitly diagnosed. Against the previous clean
  baseline, entity/edge/evidence arrays and district/building/network geometry
  are unchanged; moved buildings 0. GJ retains 6157 local edges, 1273 connected
  files; OJ retains 681 files, 2243 edges, 400 connected files and 0 moved buildings.
  Both route graphs remain COMPLETE with zero unresolved eligible edges and zero
  pavement/building intersections. Repeat regression scans are canonical-equal.
- Artifact diff: preview.svg is byte-identical for GJ and OJ. Showcase geometry
  is identical; only its embedded UCG digest changes with scan diagnostics.
  Do not claim whole graph/scene byte identity: exclusions change diagnostics
  and the derived UCG digest even while all facts and coordinates remain equal.
- Browser audit: all LOD, facility, endpoint-selection, camera move/keyboard/
  district-jump and synthetic checks pass. Synthetic static rebuilds remain 0.
  GJ orbit CPU p95 Overview/District/Detail 13.2/18.0/18.9 ms; OJ 2.9/4.9/5.4 ms.
  This is software-renderer draw submission CPU, not GPU FPS or a new speed claim.
- Fix/reverify: Windows DirEntry stat can lack the Path.stat inode value; the
  mocked reparse test initially failed to mark its intended file. Identified
  metadata by a unique fixture size instead, then verified both declaration and
  manifest guard cases and reran the full suite. No safety assertion weakened.
- Spec alignment: PASS for default build-output exclusion, AC-008/009, stable
  geography and evidence preservation; no schema, layout algorithm or ID change.
  Ordinary source-addition churn is not solved by this input-filter correction.
  Broader build-output detection and full ignore semantics remain unsupported.
- Delivery: one fix(scanner) local commit; no push to protected main under the
  latest instructions. Earlier camera commit, unrelated local caches and the
  deferred communication stash remain preserved; delivery branch needs direction.

## Checkpoint 2026-10-18 — Cache shared picking geometry during camera motion
- Implemented: cache world-space pick descriptors by existing LOD/filter/selection
  key; deduplicate shared vertices and reuse fixed-shape screen regions. Camera
  motion projects each vertex once without recreating geometry/point arrays.
  Off-screen regions are culled; hit priority, depth order and exact path identity
  remain unchanged. Render geometry, canonical data and synthetic routes untouched.
- Evidence: prior generated-output-filter audit attributes GJ District 17.8 ms
  p95 to hit-region projection out of 18.0 ms orbit CPU. Initial cache reduced
  Overview more than District; fixed-shape region reuse then improved both.
- Fixtures: unchanged GJ-Cloud 3d9b53f / GamjaOJ b163acd generated-output-filter-r1
  snapshots; full CLI structural-showcase build for unsupported fallback.
- Commands: Python unittest discovery (265 run, 264 pass, one symlink skip);
  Node viewer_audit.test.mjs (9 pass); Ruff; diff --check; trusted local viewer
  repackaging; viewer_audit.mjs with Chrome on picking-cache-r2/{gj,oj}.
  Artifacts: artifacts/visual/picking-cache-r2 and picking-cache-audit-r2.
- Actual GJ access-selected.png inspected: selection, complete highlighted path
  and source Inspector remain readable. Browser file/facility selection, all
  LODs, camera drag/keyboard/jump and synthetic path checks pass in both projects.
  Graph, City, viewer-data, preview and showcase bytes are unchanged in both.
- Timing: orbit CPU p95 GJ Overview/District/Detail 13.2/18.0/18.9 ->
  5.1/10.4/9.2 ms; OJ 2.9/4.9/5.4 -> 2.1/2.6/2.9 ms. Software SwiftShader
  submission CPU, not FPS. Synthetic has zero static rebuilds; OJ's final
  synthetic p95 was noisy (7.0 ms Detail), so no animation speedup is claimed.
- Regression: independent reference projection checks 120 regions over twelve
  transforms/viewports, shared vertices, ordering, behind-camera rejection and
  input immutability. Cache invalidation retains existing filter/LOD contracts.
- Spec alignment: PASS; no schema, layout, evidence, safety or framework changes.
  Next separate work unit: road hierarchy/contrast without widening through files.
- Delivery: one perf(viewer) local commit; protected-main push remains deferred.

## Checkpoint 2026-10-18 — shared-road contrast after b91446e
- Implemented: brighter trunks for four or more evidenced file-pair paths,
  quieter access spurs, clearance-bounded pavement, junction patches bounded by
  displayed incident widths, depth-tested centerlines for subpixel trunks.
  Legend explicitly distinguishes path sharing from measured traffic.
- Fixtures / revisions: trusted generated-output-filter-r1 snapshots of
  GJ-Cloud 3d9b53f and GamjaOJ b163acd; full CLI structural-showcase fallback.
- Commands run: `python -m unittest discover -s tests -q` (266 run, 265 pass,
  one Windows symlink skip); Node camera_navigation/access_routes/role_landmarks/
  viewer_audit suites (25 pass); `python -m ruff check .`; `git diff --check`.
  `python -m metropogits build --repo tests/fixtures/repositories/structural-showcase
  --out ../artifacts/visual/road-hierarchy-r1/unknown` completed all 12 artifacts.
  Local `repackage_camera.py <baseline> <output> --roads` reused validated routing
  while rerendering viewer/preview/showcase for GJ and OJ (not fresh analysis).
  `node scripts/viewer_audit.mjs <Chrome> ../artifacts/visual/road-hierarchy-audit-r1
  ../artifacts/visual/road-hierarchy-r1/gj ../artifacts/visual/road-hierarchy-r1/oj`.
- Artifacts inspected: actual GJ District before/after and new preview.png,
  OJ Detail WebGL capture in road-hierarchy-audit-r1. Shared interior corridors
  are more visible; building/role silhouettes remain distinct. This is a
  readability increment, not a claim that the circuit-like appearance is solved.
  Dense narrow parcels and some empty areas remain; close views can crop the city.
- Tests / determinism / stability: graph, scene and viewer-data bytes identical
  to baseline for both repositories; SVG preview/showcase differ only in road
  palette. No layout movement, edge additions or altered synthetic trajectories.
  `verify_access.mjs` confirms 6157/2243 edges, 4209/1381 routes, zero unresolved
  edges and zero pavement/building intersections. Projection and filter tests pass.
  Expected preview golden updated only after verifying the palette-only delta.
- Performance: software-rendered orbit CPU p95 GJ Overview/District/Detail
  3.7/9.9/9.3 ms; OJ 1.1/1.7/2.5 ms. Synthetic p95 GJ 1.3/1.4/1.7 ms;
  OJ 1.9/3.3/2.9 ms. Zero static rebuilds during synthetic checks in every LOD.
  These are CPU submission observations, not GPU FPS guarantees.
- Spec alignment: PASS; source evidence, stable IDs and public contracts intact.
  Drawing contrast does not imply traffic volume or create semantic junctions.
- Fixes applied and reverified: test lint violation corrected; full tests pass.
- Open risks / next actions: improve spatial density and road hierarchy beyond
  contrast without widening through buildings; unsupported fixture has no roads.
- Commits created / pushed: separate renderer work-unit commit after b91446e;
  local main only. No push: latest instructions prohibit direct protected-main
  delivery; branch/workflow decision is still required.

## Checkpoint 2026-10-18 — shared-road file-pair inspection
- Implemented: road Inspector path selector in WebGL and Canvas; one source to
  destination path highlights completely without acquiring other branches at a
  shared crossing. Source/destination buttons lead to file inspection. Exact
  original edge IDs are now printed alongside type, endpoints and confidence.
  All-path selection restores the shared segment's contributors. Active filters
  constrain choices and clear a selected path when either endpoint is hidden.
- Fixtures / revisions: GJ-Cloud 3d9b53f and GamjaOJ b163acd validated snapshots
  from road-hierarchy-r1; maintained spring-positive and structural-showcase.
- Commands run: Python unittest discovery (266 run, 265 pass, one Windows symlink
  skip); Node camera_navigation/access_routes/role_landmarks/viewer_audit suites
  (27 pass); Ruff; JS syntax checks; git diff --check. Real CLI `build --repo
  tests/fixtures/repositories/{spring-positive,structural-showcase} --out
  ../artifacts/visual/route-inspection-r1/{spring,unknown}` generated 12 artifacts
  each with COMPLETE status. Large snapshots repackaged with local trusted
  repackage_camera.py, without rescanning or executing source repositories.
- Browser command: `node scripts/viewer_audit.mjs <Chrome> ../artifacts/visual/
  route-inspection-audit-r2 ../artifacts/visual/route-inspection-r2/gj
  ../artifacts/visual/route-inspection-r2/oj`. Actual pointer clicks selected
  shared roads, dropdown changes isolated full paths and exact edge IDs, and
  JavaScript/C++ language filters cleared the respective incompatible selections.
  Clearing filters and choosing all paths restored each shared road's contributors.
- Artifacts inspected: both r1 route-inspector WebGL captures, r2 GJ route-inspector
  and OJ preview PNG. Route isolation reduces visual clutter and preserves the
  existing skyline. Long filenames wrap in the Inspector; narrow dropdowns and
  remaining scene label collisions are not claimed solved. Canvas uses the same
  tested policy and parses successfully; this interaction was not visually tested
  in Canvas fallback during this checkpoint.
- Tests / determinism / stability: UCG, City, routing payload, preview and showcase
  are byte-identical to road-hierarchy-r1 for both large fixtures. Exact route
  coverage remains 6157/2243 edges; no unresolved edges or pavement intersections.
  Tests forbid unrelated route IDs, filtered endpoints, hidden networks and
  accidental A-to-D links; All routes context does not broaden highlighted paths.
- Performance: software WebGL orbit CPU p95 GJ Overview/District/Detail
  3.5/7.8/8.4 ms; OJ 1.2/1.6/1.8 ms. Synthetic static rebuilds remain zero.
  These are submission CPU observations, not GPU FPS or a new speedup claim.
- Spec alignment: PASS, FR-007/012 and AC-006/011; no graph/scene/identity changes,
  no inferred runtime traffic, new road geometry, external services or execution.
- Fixes applied and reverified: stale network Inspector after filters now refreshes
  or clears; dropdown styling matches the existing theme in the r2 capture.
- Open risks / next actions: spatial density, thin route selection and contextual
  labels remain independent visual tasks; long contributor lists may need search.
- Commits created / pushed: one feat(viewer) work unit on main. The maintainer
  explicitly renewed authorization for normal main pushes after ee9deab; use the
  existing origin upstream without force or remote-policy changes. Delivery is
  verified from the Git command outcome, not assumed from ownership.

## Checkpoint 2026-10-18 — road-led block plan and continuity foundation
- Implemented: documented the maintainer's service/block/parcel merge-and-split
  direction in URBAN_BLOCK_PLAN.md (7009244). First implementation refines derived
  routing with arrival-direction state, including access-spur headings, bounded
  bend costs and deterministic fewer-turn tie-breaking. Added road_metrics CLI.
  This is not the planned block allocator, near-parallel snapping, or new scenery.
- Fixtures / revisions: GJ-Cloud 3d9b53f and GamjaOJ b163acd trusted snapshots from
  route-inspection-r2. Fresh CLI builds of spring-positive and structural-showcase.
- Commands run: `python -m unittest discover -s tests -q` (269 run, 268 pass,
  one Windows symlink skip); `python -m ruff check .`; Node access_routes,
  viewer_audit, camera_navigation and role_landmarks suites (27 pass); diff --check.
  `python -m metropogits build --repo tests/fixtures/repositories/spring-positive
  --out ../artifacts/visual/road-continuity-r2/spring` and equivalent
  structural-showcase -> road-continuity-r2/unknown: COMPLETE, 12 artifacts each.
  Trusted local refresh_for_review.py rerouted the large snapshots once and passed
  that same payload to WebGL, preview and showcase; no source repo execution.
  `python -m scripts.road_metrics <route-inspection-r2/case> <road-continuity-r2/case>`
  records geometry-only measures for gj and oj; `verify_access.mjs` checks provenance
  and pavement intersections. No private artifacts were staged for publication.
- Artifacts inspected: actual road-continuity-audit-r1 GJ District and OJ preview,
  r2 GJ District and OJ Detail. Browser audit command:
  `node scripts/viewer_audit.mjs <Chrome> ../artifacts/visual/road-continuity-audit-r2
  ../artifacts/visual/road-continuity-r2/gj ../artifacts/visual/road-continuity-r2/oj`.
  Both pass navigation, actual road click/path selection, filtering and synthetic
  trajectory checks. Silhouettes and district placement remain recognizable;
  straighter paths are incremental, and the dense circuit-like grid still remains.
- Regression found and fixed: lattice-only bend scoring initially added turns at
  small Spring fixture doors. Include both access headings; original minimal path
  is restored. Its SVG golden change is now only visual-access/0.2 metadata, verified
  by reproducing the previous hash with supplied 0.1 metadata. Showcase basis uses
  the supplied routing version rather than a hardcoded old version.
- Tests / determinism / stability: independent no-heuristic directional Dijkstra
  checks 36 source/target/heading cases against the A* lexicographic optimum.
  Straight-run, spur alignment, transition range, bounded detour, resource refusal,
  no-input-mutation and metrics tests pass. Full GJ/OJ routing re-derived identically
  (22.54/4.17 seconds in that run). UCG and City bytes unchanged, hence zero building
  movement. Original route IDs/endpoints/edge and network membership unchanged.
  All 6157/2243 edges covered; zero unresolved or pavement/building intersections.
- Measurements: GJ route-turn sum 31198 -> 24516; OJ 8901 -> 7915. Centerline length
  GJ 52345.5 -> 51796; OJ 12936.5 -> 12376.5. Nearby-parallel pair overlap length
  GJ 31850 -> 31206; OJ 7826 -> 6916 (proxy, not proof those roads can merge).
  Directional expansions increase GJ 1325361 -> 2384938, OJ 242764 -> 449967;
  the 5M ceiling is unchanged, so other large inputs can exhaust it sooner.
  Software WebGL orbit CPU p95 Overview/District/Detail: GJ 4.2/6.3/7.2 ms,
  OJ 1.2/1.4/1.9 ms; synthetic static rebuilds zero. Not GPU FPS guarantees.
- Spec alignment: PASS, ADR-014/016, FR-007 and AC-002/003/006. Public UCG/City
  schemas and IDs untouched; derived routing version records geometry changes.
  Costs including final-spur turns remain 90..100, retaining the 100/90 path bound.
- Open risks / next actions: one-district road-led block/parcel pilot with explicit
  layout-version/hint decision; continuing spatial density and labeling work.
  Synthetic's fixed <=96 path sample remains unchanged and documented for later.
- Commits created / pushed (main): 7009244 documents the plan; separate renderer
  implementation commit follows this verified checkpoint. Normal origin/main push
  authorized explicitly by the maintainer; no force or remote-setting changes.

## Checkpoint 2026-10-18 — bounded street-front parcel pilot
- Implemented: opt-in `scripts.parcel_pilot` comparing one leaf district without
  rewriting UCG, canonical City, default layout or viewer. Same selection rule
  across repositories: connected 8..64-file leaf, sufficient polygon capacity,
  highest incident file-pair count, ID tie-break. Reserve paired frontage rows
  and crossing space for <=2x5-parcel blocks; apportion occupants by capacity,
  then place using real neighbor positions. Only actual paths become pavement.
- Fixtures / revisions: GJ-Cloud 3d9b53f, GamjaOJ b163acd; trusted canonical inputs
  from road-continuity-r2. Fresh spring-positive and structural-showcase builds
  at implementation base ea46409. Target source code was never executed.
- Commands run: `python -m scripts.parcel_pilot
  ../artifacts/visual/road-continuity-r2/<gj|oj> --out
  ../artifacts/visual/parcel-pilot-r4/<gj|oj>`; both exit 0. Fresh pipeline:
  `python -m metropogits build --repo tests/fixtures/repositories/<spring-positive|structural-showcase>
  --out ../artifacts/visual/parcel-pilot-fixtures/<spring|unknown>`: COMPLETE,
  12 artifacts each. Pilot on those fresh builds reports NOT_APPLICABLE rather
  than inventing missing relations or forcing too-small districts to move.
  `python -m unittest discover -s tests -q`: 278 run, 277 pass, one Windows
  symlink skip. `python -m ruff check .`: pass. Node access_routes, viewer_audit,
  camera_navigation, role_landmarks suites: 27 pass. `git diff --check`: pass.
- Artifacts inspected: real Chrome headless screenshots (1500x1400) of
  parcel-pilot-r4/gj.png and oj.png, same-scale baseline/candidate embedded SVGs.
  Actual fresh spring-viewer.png (WebGL) and unknown-preview.png (SVG) inspected
  under parcel-pilot-fixtures. Screenshot command: Chrome --headless --no-sandbox
  --disable-gpu --hide-scrollbars --screenshot=<png> --window-size=1500,1400
  file:///D:/Code/MetroPoGits/artifacts/visual/parcel-pilot-r4/<case>/index.html.
  Fresh fixture screenshots use 1280x900, Spring adds --virtual-time-budget=5000.
- Visual findings / corrections: the first distance-only candidate pulled GJ
  buildings to one side. Capacity quotas and cross-street reservations reduce
  that concentration and produce legible frontage blocks. Some GJ upper empty
  space remains; OJ has more parallel-path pair length. Do not promote to default
  based solely on shorter routes. Private file paths and evidence IDs are escaped
  in hover titles; all source IDs remain in report JSON. Reports have restrictive
  CSP and no executable scripts or network dependency.
- Tests / determinism / stability: 9 new tests cover mutation, ownership, exact
  edge coverage, obstacle intersection, permutation invariance, strict Decimal
  input, concave footprints, bounded capacity, child-district refusal, isolated
  addition stability and HTML escaping. Full real-data experiment re-run and
  report bytes compared equal for both repositories; each route's original edge
  endpoints checked against its UCG. Canonical input files are read-only.
  GJ 36 selected files / 35 moved; OJ 49 / 48 moved. Zero outside movement,
  ownership escapes, overlaps, road/building intersections or unresolved edges.
  Cold local reallocation has no within-district edit/hint stability guarantee.
- Measurements (incident routes only): GJ 357 routes / 556 edges, length
  65667 -> 56945, turns 2113 -> 1893, centerline 5938.5 -> 4885, expansions
  249026 -> 187325. OJ 528 routes / 893 edges, length 79117 -> 70101,
  turns 2937 -> 2717, centerline 5382 -> 5193, expansions 203843 -> 151856.
  Parallel pair length GJ 3013.5 -> 1806; OJ 2975 -> 3174.5 (regression).
  Each selected footprint remains 4900 square units; coverage GJ 26.4%, OJ 36%.
- Spec alignment: PASS for isolated experimental tooling, not an approved
  replacement for DEC-007/ADR-014. Report version parcel-pilot/0.1 is explicitly
  not a City scene or layout hint. No public schemas, IDs, runtime dependencies,
  facts, default geometry or synthetic code changed. AC-002/006 preserved.
- Open risks / next actions: candidate WebGL/showcase/Synthetic performance
  NOT visually/performance verified because candidate is a dedicated 2D report,
  not a City exporter. No new performance claims for default viewer. Before
  promotion, resolve variable block sizes/footprint use, OJ parallel regression,
  layout-version/hint ADR and same-camera 3D comparison. Sparse baseline still
  has oversized land margins, unchanged here. Initial dotted unittest/import
  alias/Decimal and shell-quoting errors were corrected and checks rerun.
- Commits created / pushed (main): one coherent layout-pilot work unit with
  tests, plan boundary and this checkpoint; commit and normal upstream push
  follow verification. No private artifacts or unrelated IDE caches staged.

## Checkpoint 2026-10-18 — measured adaptive parcel selection
- Implemented: parcel-pilot/0.2 experiments with 3/4/5/7-column frontage blocks
  and alternate crossing positions. Preserve original district selection and
  ownership. Enumerate <=72 configurations; route <=6 distinct shortlisted
  candidates plus baseline using the unchanged bounded access router. Select
  only measured candidates with exact evidence, safe geometry, no regression
  versus input in length/turns/centerline/parallel proxy/largest empty rectangle,
  and at least one improvement. Record rejection reasons; keep baseline if none
  pass. This is isolated developer tooling, not a canonical allocator change.
- Fixtures / revisions: GJ-Cloud 3d9b53f / GamjaOJ b163acd trusted
  road-continuity-r2 inputs. Selected districts unchanged from previous experiment.
  Fresh spring-positive and structural-showcase at source base 37aff66.
- Commands run: `python -m scripts.parcel_pilot
  ../artifacts/visual/road-continuity-r2/<gj|oj> --out
  ../artifacts/visual/parcel-adaptive-r1/<gj|oj>`. Fresh pipeline:
  `python -m metropogits build --repo tests/fixtures/repositories/<spring-positive|structural-showcase>
  --out ../artifacts/visual/parcel-adaptive-fixtures/<spring|unknown>`: COMPLETE,
  12 artifacts each; unknown pilot safely NOT_APPLICABLE. Python unittest
  discovery: 282 run, 281 pass, one Windows symlink skip. Ruff all pass;
  Node access_routes/viewer_audit/camera_navigation/role_landmarks: 27 pass;
  git diff --check passes.
- Artifacts inspected: actual Chrome headless embedded SVG comparisons,
  parcel-adaptive-r1/gj.png and oj.png, 1500x1500 identical projection/crop;
  fresh parcel-adaptive-fixtures/spring.png (WebGL) and unknown.png (SVG),
  1280x900. Chrome --headless --no-sandbox --disable-gpu --hide-scrollbars
  --screenshot=<png> --window-size=<size> file:///<artifact>/index.html
  (unknown uses preview.svg; Spring adds --virtual-time-budget=5000).
- Visual findings: GJ no longer concentrates most files on the right as r4 did;
  smaller blocks separate the frontage. OJ forms horizontal blocks with shared
  connecting space. Roads remain rectilinear and some thin parallel spurs remain;
  this is not yet a complete city-like surface treatment. Upper reserved margins
  remain and total land/building areas are unchanged. Candidate is SVG-only:
  candidate WebGL/showcase/Synthetic performance NOT verified or claimed.
- Tests / determinism / stability: 13 pilot tests now cover actual accepted
  selection on a distributed fixture, rejection/fallback on the original compact
  fixture, each individual metric/evidence/safety guard, <=7 router calls, unique
  bounded shortlist, 512 independent exhaustive 3x3 empty-rectangle checks,
  concave footprints, Decimal, escaping, permutation and isolated-addition
  stability. The previous mandatory-movement assertion was replaced by explicit
  accepted/fallback scenarios, not by permitting an unsafe candidate.
  Re-ran full GJ/OJ experiments; report canonical bytes identical, original input
  bytes unchanged, every route endpoint/edge ID checked against original UCG.
  Repeat whole-pilot time 15.30s GJ / 13.16s OJ on this machine, not rendering FPS.
- Measurements: GJ 357 routes / 556 edges, OJ 528 / 893 preserved. Largest
  building-free grid rectangle (includes roads): GJ original686/r4 980/new490,
  OJ490/490/490. Parallel proxy GJ3013.5/1806/1816.5; OJ2975/3174.5/2621.5.
  New length GJ57407/OJ70332 and turns1917/2746 improve the original but slightly
  regress r4 (56945/70101, 1893/2717). Explicit tradeoff: do not claim Pareto
  improvement over r4. Geometry/evidence violations and outside movement zero.
  Experimental movement GJ35/OJ49; no local-edit hint guarantee inside the district.
- Spec alignment: PASS within isolated pilot; FR-006/007, AC-002/003/006 and
  ADR-014/016 boundaries retained. No runtime AI/services/target execution,
  canonical schema/ID/layout/default viewer changes. Report version records
  derived changes. No architecture decision is implied by passing metrics.
- Open risks / next actions: opt-in layout/hint version ADR, actual same-camera
  candidate WebGL inspection, then wider service-level validation before default
  adoption. The bounded shortlist is not globally optimal; cost of up to seven
  routesets makes it unsuitable for blindly enabling per district. Source-free
  sparse preview still has oversized margins, unchanged here.
- Commits created / pushed (main): one measured-selection work unit including
  tests and documentation; commit and normal authorized upstream push follow
  this checkpoint. Private outputs and unrelated IDE caches remain unstaged.

## Checkpoint 2026-10-18 — opt-in parcel City/3D export (ADR-017)

- Implemented: explicit `scripts.parcel_viewer` export from validated layout 1.14
  to `hierarchical-parcel/0.1-experimental`; normal CLI/Action unchanged. Single
  selected leaf coordinates, fresh canonical network paths and full-city access
  graph; one scene/routeset shared by WebGL, detailed SVG and showcase. Export
  refuses partial coverage, pavement/building intersections and existing output
  directories. Fresh bundled assets, visible experimental label, decision report,
  compatible manifest diagnostic summary/media types/checksums; no source HTML
  or JavaScript is loaded. Added layout enum; older validators require updating.
- Hint policy: same experimental version and exact directory geometry/file
  membership/ownership/footprint size. X/Z remain fixed while current graph facts,
  heights and relationships are retained. Structural changes explicitly reject
  hints; no silent cold reset. Default 1.14 continues to reject experimental hints.
  This does not certify experimental file-addition stability (AC-003).
- Fixtures / revisions: GJ-Cloud 3d9b53f, GamjaOJ b163acd, readonly baseline
  `artifacts/visual/road-continuity-r2/{gj,oj}`; fresh maintained spring-positive
  and structural-showcase repositories at implementation parent b85a829.
  No target build/test/dependency installation was executed.
- Commands run (repo root): `python -m scripts.parcel_viewer
  ../artifacts/visual/road-continuity-r2/{gj,oj} --out
  ../artifacts/visual/parcel-3d-r2/{gj,oj}` (two separate invocations).
  `python -m metropogits build --repo tests/fixtures/repositories/spring-positive
  --out ../artifacts/visual/parcel-3d-fixtures/spring --repo-id fixtures/spring`;
  equivalent structural-showcase command with unknown output/repo ID. Both normal
  builds COMPLETE; exported both as `*-experimental`, baseline retained (6/3
  buildings, 2/0 routes). The developer script is not a new public CLI default.
- Real-data checks: `node ../artifacts/visual/verify_access.mjs
  ../artifacts/visual/parcel-3d-r2/{gj,oj}` verifies each route source/target,
  edge membership, segment provenance and pavement AABB. GJ 4,209 routes,
  6,157 edges, 1,273 connected files; OJ 1,381 routes, 2,243 edges, 400 connected
  files. Both COMPLETE; missing represented edges and pavement intersections 0.
  Disconnected files are not falsely connected to fill land.
- Determinism / stability: `python ../artifacts/visual/verify_parcel_export.py`
  independently reruns both cold exports and same-structure hints. All 14 packaged
  artifacts per city repeat byte-for-byte; hinted scene and routes equal cold
  result. GJ 35/OJ 49 file positions change only inside the selected leaf; all
  district records and all other file fields/positions are unchanged. Graph and
  original input bytes retained. Repeat/package/hint check took 116.49s / 37.26s
  locally; this includes multiple generations and is not a single-build benchmark.
- Actual browser commands: `node scripts/viewer_audit.mjs
  'C:\Program Files\Google\Chrome\Application\chrome.exe'
  ../artifacts/visual/parcel-3d-audit-r3
  ../artifacts/visual/parcel-3d-r2/gj ../artifacts/visual/parcel-3d-r2/oj`.
  Chrome 152 SwiftShader, 1280x800, 20 samples per mode. All overview/district/detail
  camera, selection/provenance, filtering and synthetic checks pass. Synthetic
  draw-submission CPU p95 GJ 1.3/1.4/1.1ms, OJ 1.5/1.1/1.1ms; static mesh rebuilds
  0. Software renderer CPU measurements, not GPU frame completion or FPS.
- Artifacts inspected: actual WebGL detail captures, preview and showcase SVG
  captures; `parcel-3d-focus-r3/{gj,oj}-{before,after}/focused.png`, generated with
  `node ../artifacts/visual/parcel_focus_review.mjs` from trusted bundled assets.
  Exact before/after target, distance113.844, yaw-.68, pitch.62 and Detail are
  asserted; 1500x1000 viewport. GJ selected 36-file analysis leaf and OJ 49-file
  service leaf show clearer separated rows/frontage, but thin parallel rectilinear
  roads remain. Fixed land area/outer city geometry are not denser. Overview/README
  differences are subtle; scope is deliberately one leaf, not citywide adoption.
  Spring WebGL and unknown preview screenshots in parcel-3d-fixtures were also
  inspected: usable fallback, sparse unknown still has oversized reserved margins.
- Global routing findings: GJ length698560→690307, turns24516→24261,
  parallel31206→30366, centerline51796→51481. OJ length163515→154618,
  turns7915→7476, centerline12376.5→12282, **parallel6916→7280 (+5.3%)**.
  Incident-only pilot scoring does not predict all-city shared-route effects.
  OJ is retained solely as an opt-in comparison, not approved visual replacement.
  Explicit next correction: include global routing non-regression in selection
  before default adoption or broader allocation; then incremental file-addition hints.
- Fixes applied/reverified: manifest status/diagnostics restored to existing
  contract shape; hint validation separated old semantic evidence from transferred
  geometry so current-graph changes are supported. Malformed/overlapping hints fail.
  Initial test invocations used an unsupported module path/CLI flag and were rerun
  correctly. Initial focus capture ran before OJ finished; completed in focus-r3.
  Audit-r2 included small fixtures and stopped on its large-scene natural-LOD
  expectation (small Spring correctly starts in Detail). No test was weakened:
  large-city audit reran as r3; small fallback rendering checked separately, not
  claimed as a passing full interaction/performance audit.
- Tests: 13 exporter tests cover selected overrides/path refresh, fallback,
  current-relation hint updates, incompatible and colliding hints, deterministic
  packaging, default preservation, fail-closed routing, untrusted input asset
  exclusion, strict JSON and no-overwrite/no-output-on-invalid-input. `python -m
  unittest discover -s tests -q`: 295 run, 294 passed, one Windows symlink skip.
  `python -m ruff check .`: pass. `node --test tests/access_routes.test.mjs
  tests/viewer_audit.test.mjs tests/camera_navigation.test.mjs
  tests/role_landmarks.test.mjs`: 27 passed. `git diff --check`: pass.
- Spec alignment: PASS for bounded experimental scope under ADR-014/016/017,
  technical §7–8, FR-006/007, AC-002/006/014 and DEC-001–009. Geometry version is
  explicit, not silently relabeled. Default AC-003 tests remain intact; experimental
  incremental growth not implemented. No AI/service dependency, invented edges,
  unsafe repository execution, source-ID changes or automatic publication.
- Commits created / pushed (main): ADR work unit b85a829; implementation/checkpoint
  is a separate commit. Verified ordinary owner-authorized upstream push follows
  this checkpoint. Private artifacts, review harnesses and unrelated IDE caches
  are excluded from source control; no agent attribution added.

## Checkpoint 2026-10-18 — dependency road consolidation (ADR-018)

- Implemented: opt-in fixed-city pass removes parallel interior road corridors,
  atomically reroutes all affected file pairs on remaining same-kind roads, and
  rebuilds exact segment provenance/junctions. Door ports/spurs never move or act
  as another file's through road. No new centerline or larger clearance envelope.
  UCG/City bytes and default CLI/Action/parcel scoring remain unchanged; supplied
  derived payload version is visual-access/0.3. Synthetic and selection use these
  actual rerouted paths, not hidden baseline paths. ADR and staged plan recorded
  before implementation in documentation commit 154e422.
- Safety/bounds: max(N_original, floor(100*Manhattan/90)) lattice steps and at
  most two additional bends per ORIGINAL route, frozen across accepted changes.
  This preserves ADR-016's 100/90 shortest-lattice-path guarantee. Two extra bends
  allow merge/exit; replacing the initial proposed zero bend-regression rule is
  explicit in ADR-018, not a relaxation of evidence or distance safety. At most
  1,200 candidates, 2M popped states, 100k predecessor labels/search, 100k atomic
  road edges and 1M route steps. Failed/incomplete candidates roll back together.
- Fixtures / revisions: readonly parcel-3d-r2 GJ (source3d9b53f) and OJ
  (sourceb163acd), plus fresh spring-positive and structural-showcase at parent
  154e422. No target code/build/dependencies executed. Spring 6 files/2 routes and
  unknown 3 files/0 routes retain unchanged safe geometry with zero candidates.
- Commands: `python -m scripts.road_consolidation
  ../artifacts/visual/parcel-3d-r2/{gj,oj} --out
  ../artifacts/visual/road-consolidation-r2/{gj,oj}` separately; fresh
  `python -m metropogits build --repo tests/fixtures/repositories/spring-positive
  --out ../artifacts/visual/road-consolidation-fixtures/spring --repo-id fixtures/spring`
  and analogous structural-showcase/unknown, followed by the consolidation command
  into spring-study/unknown-study. Both baseline fixture builds COMPLETE.
- Measurements (entire city, before→after): GJ parallel30366→15631 (-48.5%),
  centerline51481→40932 (-20.5%), travel690307→692680 (+0.34%),
  turns24261→24055, junctions4063→2959. OJ parallel7280→3794 (-47.9%),
  centerline12282→9569.5 (-22.1%), travel154618→155857 (+0.80%),
  turns7476→6642, junctions1012→652. GJ615/OJ245 candidates accepted;
  both hit 1,200 attempts (of 5,494/1,420), so not a global optimum.
- Provenance/geometry: `node ../artifacts/visual/verify_access.mjs <after>` checks
  each source/target, edge ID, segment incidence and pavement/building AABB.
  GJ4,209 routes/6,157 edges and OJ1,381 routes/2,243 edges preserved; zero
  unresolved represented edges or pavement intersections. Independent atomic-edge
  subset checks verify no new centerline. Source facts and canonical scene bytes
  equal inputs. Unrelated building movement is zero.
- Determinism: `python ../artifacts/visual/verify_consolidation.py` reruns the pass
  and renderer packaging against each baseline. All14 after artifacts repeat
  byte-for-byte. Frozen distance/bend limits checked for EVERY route. Repeat plus
  packaging took28.58s GJ/11.54s OJ, not a pure optimizer or frame-time benchmark.
  Paths/segment decomposition changed for3,273/1,084 routes; no membership changes.
- Artifacts inspected: real Chrome same-camera Detail captures in
  road-consolidation-focus-r2/{gj,oj}-{before,after}/focused.png, produced by
  `node ../artifacts/visual/parcel_focus_review.mjs`; GJ deployment/service leaf
  matches the user's reported area, OJ generation/service. Identical target,
  yaw-.68/pitch.62/distance per pair asserted. GJ distance108.302, OJ113.844,
  viewport1500x1000. Also inspected actual GJ showcase, OJ detailed preview,
  spring.png WebGL and unknown.png preview under road-consolidation-fixtures.
- Visual findings: repeated parallel lanes and closely spaced crossings visibly
  decrease without moving buildings. Main shared runs read more clearly; residual
  orthogonal lines, square junction markings and short local approaches remain.
  Full-city thumbnail difference is subtler than closeup. Unknown sparse margins
  remain an existing issue. Roundabouts and unified junction meshes NOT implemented
  or claimed; next work is approach consolidation and continuous junction surfaces.
- Browser checks: `node scripts/viewer_audit.mjs <Chrome> <audit-output>
  <gj/before> <gj/after> <oj/before> <oj/after>` checks three LODs, source-path
  inspection, selection/filter behavior, pan/orbit/jump and synthetic. Audit-r1
  completed all four cases; final audit-r2 also passed all four cases using
  road-consolidation-r2 packages. Static mesh rebuilds during synthetic0;
  r2 after p95 draw-submission CPU GJ1.3/1.1/1.2ms, OJ2.0/1.0/1.0ms.
  Headless Chrome152 SwiftShader,20 samples;
  these noisy CPU timings are not measured GPU completion/FPS or a speedup claim.
- Tests: full unittest306 run,305 pass,1 Windows symlink skip; Ruff pass;
  Node routing/viewer-audit/camera/role suites27 pass. Eleven new tests include
  actual beneficial detour, independent BFS bound, cross-kind/spur rejection,
  frozen limits, deterministic permutation, multi-route rollback, budgets,
  strict provenance and unchanged canonical packaging. No existing tests weakened.
- Spec alignment: PASS, technical§7–8/FR-007/AC-002/003/006/014 and
  DEC-005/006/007/011. ADR-018 authorizes bounded derived rerouting, not new
  dependencies, runtime traffic claims, building relocation or default adoption.
- Commits created / pushed (main): documentation154e422; implementation/tests/
  checkpoint separately committed after verification, followed by ordinary
  authorized upstream push. Private generated cities/harnesses and unrelated IDE
  caches remain excluded; no agent contributor attribution.

## Checkpoint 2026-10-18 — continuous WebGL junction surfaces

- Implemented: same-kind visible approach rectangle unions produce inset asphalt
  tiles within existing pavement. Internal shoulder seams are covered; ordinary
  centerlines stop at junction mouths, including short segments between joints.
  Selected x-ray paths remain complete. No topology, route membership, animation
  trajectory, UCG/City schema, stable ID, building placement or clearance change.
  Canvas/SVG use unoutlined surfaces already and are unchanged. ADR-018 and the
  urban block plan distinguish this rendering slice from future approach merging.
- Fixtures / revisions: readonly GJ source3d9b53f and OJ sourceb163acd using the
  road-consolidation-r2 after packages at parent264bffd; fresh spring-positive and
  structural-showcase builds. No target source/build/dependency execution.
- Commands: `python ../artifacts/visual/repackage_camera.py
  ../artifacts/visual/road-consolidation-r2/<gj|oj>/after
  ../artifacts/visual/junction-surface-r1/<gj|oj> --roads`;
  `node ../artifacts/visual/verify_junctions.mjs`;
  `node ../artifacts/visual/verify_access.mjs <new-build>` for both cities.
  Fresh `python -m metropogits build --repo tests/fixtures/repositories/spring-positive
  --out ../artifacts/visual/junction-surface-fixtures/spring --repo-id fixtures/spring`
  and analogous structural-showcase/unknown completed with 12 artifacts each.
- Canonical fidelity and determinism: full embedded viewer data, UCG/City bytes,
  preview.svg and showcase.svg equal baseline in both cities. All manifest hashes
  checked. Repeated derived geometry is equal. For every patch at all three LODs,
  independent rectangle subdivision verified containment in contributing pavement.
  Detail GJ2,959 joints/10,160 merged tiles; OJ652 joints/2,083 tiles. GJ4,209 routes,
  6,157 represented edges and OJ1,381 routes,2,243 edges unchanged. Unresolved edges
  and pavement/building intersections0. Unrelated building movement0.
- Browser commands: `node ../artifacts/visual/parcel_focus_review.mjs` captures
  junction-surface-focus-r1. Baseline screenshots are preserved actual previous
  captures; stale JS is not executed. Target/yaw/pitch/distance and1500x1000 viewport
  match exactly. `node scripts/viewer_audit.mjs <Chrome>
  ../artifacts/visual/junction-surface-audit-r1 <gj-build> <oj-build>` passes
  three LODs, selection/drill-down, filters, camera pan/orbit/jump and synthetic.
  `node ../artifacts/visual/junction_smoke.mjs` captures fresh sparse WebGL/SVG.
- Artifacts inspected: focus-r1 GJ before/after and OJ after focused.png; both
  after showcase.png; fixtures spring.png WebGL and unknown-preview.png SVG.
  GJ crossings no longer carry continuous transverse curb/paint grids; some
  short access paint and rectangular/parallel roads remain. OJ change is subtler
  because buildings occlude many joints. Full-city SVG composition is unchanged;
  unknown sparse margins remain an existing visual task, not fixed here.
- Performance: geometry generated only at static-cache invalidation. Local Node
  whole-city Detail geometry samples were GJ113ms/OJ15ms (not frame time).
  Headless Chrome152 SwiftShader audit,20 samples/mode: synthetic CPU p95
  GJ1.4/1.0/1.0ms, OJ4.0/1.2/1.0ms across Overview/District/Detail; static rebuilds0
  in every synthetic mode. These are draw-submission CPU timings, not GPU FPS or
  a speedup claim. More surface triangles are a tradeoff; same camera needs no
  geometry rebuild while synthetic runs.
- Test commands: `python -m unittest discover -s tests`;
  `python -m ruff check metropogits scripts tests`; `node --check` on both changed
  viewer assets; `node --test tests/junction_geometry.test.mjs
  tests/access_routes.test.mjs tests/viewer_audit.test.mjs
  tests/camera_navigation.test.mjs tests/role_landmarks.test.mjs`.
- Tests: full unittest306 run,305 pass,1 Windows symlink skip; Ruff and changed
  JS syntax checks pass. Five Node suites32 pass, including five new junction
  cases covering T/X, empty corners, mixed widths, short approaches, filtering,
  different kinds, ordering, endpoint reversal and paint exhaustion. No tests
  weakened. Existing static-cache and complete route selection tests pass.
- Spec alignment: PASS, technical sections7–8, product5.1 and functional
  AC-002/003/006/014. Visualization remains a traceable depiction of static facts.
  No runtime AI/cloud dependencies, inferred traffic claims or new source edges.
- Open risks / next actions: close distinct approach junctions and rectilinear
  routing still create clutter. Evaluate bounded approach merging before selective
  roundabouts; do not add decorative circles or arbitrary branches for vehicles.
- Commits created / pushed (main): feature, regression tests and documentation
  are one work unit committed after this checkpoint. Maintainer explicitly
  reconfirmed the owner exception to protected-main direct pushes this turn;
  ordinary upstream push follows verification, without force or rule changes.
  Private artifacts/review scripts and unrelated IDE caches are excluded.

## Checkpoint 2026-10-18 — bounded short junction consolidation

- Implemented: opt-in `--junctions` pass transfers dependencies from redundant
  short branch links to surviving crossings. Links span at most two lattice steps,
  exclude fixed ports and must eliminate at least one T. All affected routes move
  atomically within the ORIGINAL 0.2 distance/+2 bend limits across both passes.
  No added pavement, moved buildings, schema/source-ID changes or default adoption.
  ADR-018, current baseline and urban block plan record the policy and limits.
- Fixtures / revisions: GJ3d9b53f and OJb163acd readonly parcel-3d-r2 inputs;
  fresh spring-positive and structural-showcase builds at parentc1dfe3e. No target
  code/build scripts/dependencies executed. Sparse outputs retain2/0 routes.
- Commands: `python -m scripts.road_consolidation
  ../artifacts/visual/parcel-3d-r2/<gj|oj> --out
  ../artifacts/visual/junction-merge-r1/<gj|oj> --junctions`;
  `python -m metropogits build --repo tests/fixtures/repositories/<spring-positive|structural-showcase>
  --out ../artifacts/visual/junction-merge-fixtures/<spring|unknown>
  --repo-id fixtures/<spring|unknown>`, then the same consolidation command into
  `<spring|unknown>-study`. Both maintained fixture builds COMPLETE.
- Metrics relative to parallel-only: GJ junctions2959→2596, pavement40932→39210,
  nearby parallel15631→14066.5, travel692680→694542, turns24055→23129. OJ
  junctions652→631, pavement9569.5→9447, parallel3794→3696, travel155857→155878,
  turns6642→6260. GJ219 accepted/600 attempts (cap reached,1645 candidates);
  OJ13/171 (262 candidates, remaining candidates no longer eligible). Not optimal.
- Fidelity: `node ../artifacts/visual/verify_access.mjs <after-build>` confirms
  GJ4209 complete paths/6157 represented edges, OJ1381/2243; missing edges and
  pavement/building intersections0. City/UCG bytes match input; no building churn.
  `python ../artifacts/visual/verify_consolidation.py` confirms unchanged old
  parallel-only routing, strict atomic-pavement subset, all original endpoint/edge
  identities and frozen per-route distance/bend bounds. All14 after artifacts per
  city reproduce byte-for-byte; repeat+package41.77s GJ/12.55s OJ, not a pure
  optimizer or frame benchmark. New pass is capped at600 attempts/2M popped states;
  comparison recomputes the parallel baseline, increasing developer-command cost.
- Artifacts inspected: `node ../artifacts/visual/parcel_focus_review.mjs` generated
  junction-merge-focus-r1 GJ/OJ before/after focused.png at identical1500x1000
  viewport, target/yaw/pitch/distance; both after showcase.png inspected. GJ short
  transverse branches decrease visibly; OJ selected-area difference is small.
  City silhouette, density and remaining orthogonal roads largely persist.
  `node ../artifacts/visual/junction_smoke.mjs` captured new fixture outputs;
  spring.png WebGL and unknown-preview.png inspected. Sparse margins unchanged.
- Browser: `node scripts/viewer_audit.mjs <Chrome>
  ../artifacts/visual/junction-merge-audit-r1 <gj-after> <oj-after>` passes all three
  LODs, selection/drill-down/filters, camera movement and synthetic route checks.
  Chrome152 SwiftShader20 samples: synthetic CPU p95 GJ1.2/1.0/1.4ms and
  OJ1.2/1.3/1.1ms; static geometry rebuilds0 throughout. Not GPU FPS/speedup claims.
- Tests: `python -m unittest discover -s tests`313 run,312 pass,1 Windows symlink
  skip; `python -m ruff check metropogits scripts tests` passes; Node access_routes,
  junction_geometry, viewer_audit, camera_navigation, role_landmarks suites32 pass.
  Seven new Python cases cover actual branch transfer, excessive detours,
  cross-kind rejection, fixed ports/link length, rollback, budgets, deterministic
  permutation, frozen bounds and package compatibility. No failing tests weakened.
- Spec alignment: PASS, technical7–8, FR-007, AC-002/003/006/014, DEC-005/006/011.
  Existing evidence, static/local-first boundaries and unsupported fallback intact.
- Open risks / next actions: many protected short dependencies and sole bridges
  cannot merge safely. Evaluate remaining complex junctions for selective curved
  connections/roundabouts with complete path/clearance checks, not decoration or
  relaxed detour guarantees. Dense orthogonal appearance is not fully resolved.
- Commits created / pushed (main): implementation, regression cases and docs are
  one work unit committed after verification; ordinary upstream push follows under
  the maintainer's reconfirmed owner exception. No force/rule changes or attribution;
  private generated artifacts and unrelated IDE caches are excluded.

## Checkpoint 2026-10-18 — quantitative road demand grades

- Implemented: ADR-019 stages continuous trunks, reserved parcels, curves and
  selective roundabouts. First slice derives unique-edge/file/major-district
  metrics and fixed access/alley/street/avenue/trunk-demand grades. WebGL, Canvas
  and SVG share profiles; full-road grades/widths survive filters and path focus.
  Inspector separates these counts from selected edges and explains clearance
  limits. History handoff carries its frame's routing/profile. No topology change.
- Fixtures / revisions: GJ3d9b53f and OJb163acd junction-merge-r1 after inputs;
  maintained spring-positive and structural-showcase at parent f4304ae. Target
  source, scripts and dependencies never executed. Both fresh fixture builds COMPLETE.
- Commands: `python -m metropogits build --repo tests/fixtures/repositories/<spring-positive|structural-showcase>
  --out ../artifacts/visual/road-demand-fixtures-r2/<spring|unknown>-study/after
  --repo-id fixtures/<spring|unknown>`; `python ../artifacts/visual/road_demand_review.py`
  packages GJ/OJ fixed routes into road-demand-r3. It repeats all14 after artifacts
  byte-for-byte and checks City/UCG bytes and entire routing objects unchanged.
  Before uses trusted current assets without profiles (legacy style), original SVGs.
- Metrics: segment grades GJ access1273/alley1032/street2666/avenue1636;
  OJ400/284/587/430. Clearance-limited segments3205/925. Trunk-demand segments0:
  cross-major edges per represented segment max0/2, below16. This does NOT prove
  no inter-service communication exists. No fabricated highways were introduced.
- Fidelity: `node ../artifacts/visual/verify_access.mjs ../artifacts/visual/road-demand-r3/<gj|oj>/after`
  confirms GJ4209 paths/6157 edges and OJ1381/2243; missing edges0, pavement/building
  intersections0. Entire City/routing objects unchanged, hence no placement churn,
  extra detours or Synthetic trajectory changes. Profiles derive once at packaging.
- Artifacts inspected: `node ../artifacts/visual/parcel_focus_review.mjs` captured
  road-demand-focus-r3 identical Detail cameras. GJ/OJ fixed-camera and showcase
  captures inspected across r2/r3; GJ minor bright markings recede, avenues stand
  out more. Dense orthogonal topology, district borders and silhouette remain.
  `node ../artifacts/visual/junction_smoke.mjs`: fresh Spring WebGL and unknown SVG
  inspected, sparse/unsupported output retained. OJ preview and GJ route Inspector
  from road-demand-audit-r4 inspected; provenance remains readable via scrolling.
- Browser: `node scripts/viewer_audit.mjs <Chrome> ../artifacts/visual/road-demand-audit-r4
  ../artifacts/visual/road-demand-r3/gj/after ../artifacts/visual/road-demand-r3/oj/after`
  passes all three LODs, real pointer selection, full-demand Inspector counts,
  drill-down/filter reset, camera and Synthetic. CPU p95 synthetic GJ1.8/1.3/1.1ms,
  OJ1.0/1.0/1.0ms; static rebuilds0. Chrome152 SwiftShader20 samples, not GPU FPS
  or a controlled speedup comparison. Forced Canvas and history visuals not inspected.
- Tests: `python -m unittest discover -s tests -q`320 run,319 pass,1 Windows symlink
  skip; `python -m ruff check metropogits scripts tests` passes. `node --test
  tests/access_routes.test.mjs tests/junction_geometry.test.mjs tests/viewer_audit.test.mjs
  tests/camera_navigation.test.mjs tests/role_landmarks.test.mjs`35 pass; changed JS
  parse checks pass. New cases cover deduplication, thresholds, major/unknown
  ownership, kind separation, stable filters, history handoff and SVG width limits.
- Fixes applied and reverified: browser demand assertions caught missing 3D
  Inspector integration (r3 audit); fixed and r4 passes. Updated SVG golden only
  after proving legacy no-profile output retains its old hash and building,
  district and canonical-network SVG groups are identical. No failed test weakened.
- Spec alignment: PASS, technical7–8, FR-007, AC-002/003/006/014, product5.1 and
  DEC-005/006/007. Static demand is not runtime traffic; UCG/City/IDs intact.
- Open risks / next actions: per-segment grades can change at branches and cannot
  reserve wider streets. Implement continuous internal avenue/collector planning
  with frozen bounds and explicit rejected-candidate reasons before curves or
  roundabouts. Major structural boundaries are not asserted deployment services.
- Commits created / pushed (main): docs f4304ae; implementation/tests/checkpoint
  committed after checks. Ordinary upstream push follows under the maintainer's
  explicit owner exception, without force, settings changes or agent attribution.
  Generated private outputs/review scripts and unrelated IDE caches excluded.

## Checkpoint 2026-10-18 — bounded continuous avenue reuse

- Implemented: opt-in `--avenues` third pass preserves evidenced straight spines
  and transfers nearby parallel streets onto remaining pavement. All affected
  routes commit together or roll back; original distance/bend limits stay frozen
  across all three passes. Require increased spine use and no abandoned spine.
  Default build/Action, canonical City/UCG and building positions remain unchanged.
- Fixtures / revisions: GJ3d9b53f and OJb163acd parcel-3d-r2 JSON inputs;
  maintained spring-positive and structural-showcase at parent 3edc0f4. No target
  source code, dependencies or build scripts executed.
- Commands: `python -m scripts.road_consolidation
  ../artifacts/visual/parcel-3d-r2/<gj|oj> --out
  ../artifacts/visual/avenue-reuse-r1/<gj|oj> --avenues`;
  `python -m metropogits build --repo tests/fixtures/repositories/<spring-positive|structural-showcase>
  --out ../artifacts/visual/avenue-reuse-fixtures/<spring|unknown>
  --repo-id fixtures/<spring|unknown>`, followed by the same consolidation CLI
  into `<spring|unknown>-study`. Both fresh fixture builds COMPLETE; no avenue
  candidates in either sparse input, preserving prior geometry.
- Results versus parallel+junction baseline: GJ accepts 107/562 attempts;
  centerline 39210 -> 37666.5 (-3.94%), nearby-parallel length 14066.5 -> 11879
  (-15.55%), junctions 2596 -> 2441. Route length 694542 -> 695823, turns
  23129 -> 22941. OJ accepts 3/192; centerline 9447 -> 9412, parallel length
  3696 -> 3654, junctions 631 -> 630. OJ route length 155878 -> 155913 and turns
  6260 -> 6274: a small bend increase within each original route's +2 limit.
  New-pass popped states 413555/47758; neither new pass hits its resource caps.
  Protected short paths and no-reuse-gain candidates remain unmerged.
- Fidelity / determinism: `python ../artifacts/visual/verify_consolidation.py`
  repeats routing and all 14 packaged after assets byte-for-byte; City/UCG bytes,
  source/target/kind/edge IDs/network IDs and doors unchanged. Pavement is a strict
  subset, every route within its original length/+2-bend limits. Before routing
  equals the previous junction-merge baseline. `node
  ../artifacts/visual/verify_access.mjs ../artifacts/visual/avenue-reuse-r1/<gj|oj>/after`
  confirms 4209/1381 routes, 6157/2243 covered edges, unresolved 0 and pavement/
  building intersections 0. Connected files remain 1273/400.
- Artifacts inspected: `node ../artifacts/visual/parcel_focus_review.mjs` generates
  avenue-reuse-focus-r1. Viewed GJ/OJ before/after focused.png at identical cameras
  and both after showcase.png. GJ redundant foreground/central parallel stretches
  visibly decrease; OJ chosen view changes little. Skyline/composition are stable;
  dense rectilinear topology, district boundaries and some blank areas persist.
  `node ../artifacts/visual/junction_smoke.mjs` generates fresh fixture captures;
  viewed Spring WebGL and unknown-language preview. No new obvious clipping.
- Browser: `node scripts/viewer_audit.mjs <Chrome>
  ../artifacts/visual/avenue-reuse-audit-r1
  ../artifacts/visual/avenue-reuse-r1/gj/after
  ../artifacts/visual/avenue-reuse-r1/oj/after` passes three LODs, real pointer
  selection, source-edge Inspector, single-route drill-down, filter reset, demand
  profiles, camera and Synthetic route checks. Chrome152 SwiftShader, 20 samples:
  synthetic CPU p95 GJ 1.6/1.4/1.2ms and OJ 1.1/1.1/1.1ms; static rebuilds 0
  throughout. These are not GPU FPS or controlled speedup measurements.
- Tests: `python -m unittest discover -s tests -q` 328 run, 327 pass, 1 Windows
  symlink skip; `python -m ruff check metropogits scripts tests` passes;
  `node --test tests/access_routes.test.mjs tests/junction_geometry.test.mjs
  tests/viewer_audit.test.mjs tests/camera_navigation.test.mjs tests/role_landmarks.test.mjs`
  35 pass. Eight new cases cover real transfer, demand/kind separation, protected
  short routes, search budgets, independent bounded-Dijkstra agreement, atomic
  rollback, contiguous spines, deterministic order and package compatibility.
- Spec alignment: PASS, technical 7–8, FR-007, AC-002/003/006/014, product 5.1,
  DEC-005/006/007/011. Static demand is not measured traffic; shared pavement
  creates no new semantic relationship. Public contracts and stable IDs intact.
- Open risks / next actions: this is conservative reuse of existing streets,
  not globally optimal road-first planning or highway geometry. Evaluate opt-in
  road-space reservation within stable directory ownership before gentle curves
  and selective roundabouts. Preserve distance bounds and incremental stability.
- Commits created / pushed (main): implementation, tests and accompanying docs
  form one work unit committed after verification; ordinary upstream push follows
  under the maintainer's reconfirmed owner exception. No force, remote setting
  changes or agent attribution. Private artifacts and unrelated IDE caches excluded.

## Checkpoint 2026-10-18 — local avenue clearance reservation

- Implemented: explicit `scripts.avenue_reservation` pilot inside the existing
  experimental parcel engine. Reserve a real avenue's 2.5-unit width plus lateral
  and endpoint clearance before relocating at most eight blocking parcels within
  their leaf. Preserve through-centerlines/ports and exact memberships; update
  access spurs and certify widths. Reject unsafe candidates atomically, limit
  evaluation to 64, retain baseline if none fit. Default builds and schemas intact.
- Fixtures / revisions: GJ3d9b53f and OJb163acd parcel-3d-r2 JSON inputs;
  spring-positive and structural-showcase at parent d44899a. No target scripts,
  dependencies or application code executed.
- Commands: `python -m scripts.avenue_reservation
  ../artifacts/visual/parcel-3d-r2/<gj|oj> --out
  ../artifacts/visual/avenue-reservation-r2/<gj|oj>`; repeated into
  avenue-reservation-repeat. `python -m metropogits build --repo
  tests/fixtures/repositories/<spring-positive|structural-showcase> --out
  ../artifacts/visual/avenue-reservation-fixtures/<spring|unknown> --repo-id
  fixtures/<spring|unknown>`, then `scripts.parcel_viewer` into *-parcel and the
  reservation command into *-study. Fresh builds COMPLETE; sparse cases unchanged.
- Results: GJ accepts candidate 9 of 89 proposed, moves one building 0.875 units
  to clear a 59.5-unit alignment; certified surface area +18.27. OJ accepts
  candidate 29 of 30, moves three buildings 0.875 each for a 14-unit alignment;
  surface area +24.36. No later candidates searched after the first valid result.
  Most rejections are lack of a local parcel preserving existing roads/ownership;
  unsplit narrow boundary segments and a missed fixed access port also reject.
- Fidelity / stability: `python ../artifacts/visual/verify_reservation.py` compares
  all 28 before/after files per city with repeated generation byte-for-byte.
  UCG, building attributes/dimensions/ownership and all districts unchanged;
  every unselected building fixed. All 4209/1381 file-level through-paths, relation
  IDs, ports and bends unchanged. Canonical aggregate paths change 0/2 in GJ/OJ,
  with identical edge memberships. OJ access pavement +2.625 units and weighted
  route length +57.75; every route's change bounded by its endpoints' movement.
  GJ path lengths unchanged. Junction counts remain 2441/630.
- `node ../artifacts/visual/verify_access.mjs
  ../artifacts/visual/avenue-reservation-r2/<gj|oj>/after` confirms exact coverage
  6157/2243 edges, connected files 1273/400, unresolved 0, pavement/building
  intersections 0. Independent fixture checks retain unrelated coordinates after
  a sparse neighboring file addition; same-structure hints retain all coordinates,
  incompatible membership hints reject explicitly instead of silently relocating.
- Artifacts inspected: `node ../artifacts/visual/parcel_focus_review.mjs
  avenue-reservation-r2 avenue-reservation-focus-r2`; viewed four focused WebGL
  images at identical cameras and both after showcase captures. Width bottlenecks
  improve locally, but changes are small and orthogonal road complexity persists.
  No broad composition improvement claimed. OJ role aggregates regroup 12 -> 13
  while preserving 86 represented files; record small-movement visual sensitivity
  for later correction. `node ../artifacts/visual/junction_smoke.mjs
  avenue-reservation-fixtures`; Spring WebGL and unknown-language SVG inspected.
- Browser: `node scripts/viewer_audit.mjs <Chrome>
  ../artifacts/visual/avenue-reservation-audit-r2
  ../artifacts/visual/avenue-reservation-r2/gj/after
  ../artifacts/visual/avenue-reservation-r2/oj/after` passes three LODs, selection,
  source-edge inspection/drill-down, filters, demand profiles, camera and Synthetic.
  Chrome152 SwiftShader, 20 samples: synthetic CPU p95 GJ 1.4/1.0/1.0ms,
  OJ 1.0/1.1/1.0ms; static rebuilds 0. Not GPU FPS or a controlled speedup claim.
- Tests: `python -m unittest discover -s tests -q` 337 run, 336 pass, 1 Windows
  symlink skip; Ruff passes. Node access_routes, junction_geometry, viewer_audit,
  camera_navigation and role_landmarks suites: 35 pass. Nine new Python cases
  cover actual width gain, exact through geometry/provenance, movement bounds,
  determinism, unrelated additions, duplicate demand, concave/foreign ownership,
  atomic fallback, access-port failures, hints and safe CLI/overwrite refusal.
- Fixes applied and reverified: r1 checked lateral width but not endpoint clearance
  or continuity through boundary-spanning segments. Added both checks; OJ's first
  candidate now rejects and a different bounded candidate passes in r2. No tests
  weakened to preserve the original candidate.
- Spec alignment: PASS, technical 7–8, FR-006/007, AC-002/003/006/014, product 5.1,
  DEC-005/006/007/011 and ADR-017/019. Experimental configuration is recorded in
  decision/manifest; no semantic road, runtime flow or default layout change.
- Open risks / next actions: this widens existing alignments, not city-wide trunk
  planning or curved junctions. Inspect rejected candidates for longer reserved
  avenues with coordinated merger/branch planning; address aggregate sensitivity
  before broad parcel relocation. Cold candidate selection is not a growth hint.
- Commits created / pushed (main): one coherent implementation/test/docs unit
  committed after verification; ordinary upstream push under the maintainer's
  reconfirmed owner exception. No force, remote changes or agent attribution.
  Private review artifacts and unrelated IDE caches remain outside the commit.

## Checkpoint 2026-10-18 — approved urban shared-backbone routing

- Implemented: opt-in `scripts.road_consolidation --urban`, after the existing
  three conservative passes. A unique-evidence-demand corridor forest guides
  whole-network removal and atomic rerouting. Preserve fixed ports, access,
  buildings, relationship IDs and kind; remove only unused existing pavement.
  `--backbone` keeps the older bounds; defaults and public contracts unchanged.
  ADR-019 records the maintainer's explicit urban detour approval before coding:
  max(floor(1.5*N),N+4) original through-steps and original complete-path bends+4.
- Fixtures / revisions: GJ3d9b53f and OJb163acd, parcel-3d-r2 JSON inputs; fresh
  spring-positive and structural-showcase at parent627ea88. No input application
  code, dependencies or build scripts executed. Private artifacts stay local.
- Commands: `python -m scripts.road_consolidation
  ../artifacts/visual/parcel-3d-r2/<gj|oj> --out
  ../artifacts/visual/urban-backbone-r2/<gj|oj> --urban`.
  Fresh fixture pipeline: `python -m metropogits build --repo
  tests/fixtures/repositories/<spring-positive|structural-showcase> --out
  ../artifacts/visual/urban-backbone-fixtures/<spring|unknown> --repo-id
  fixtures/<spring|unknown>`, then the urban comparison into *-study.
  Both fresh builds COMPLETE; sparse Spring keeps its two paths, unknown has
  zero invented roads. Output directory overwrite remains refused.
- Whole-city results vs avenue-only baseline: GJ pavement37666.5->28412.5,
  nearby-parallel11879->5736.5, junctions2441->1582, segments6316->4917.
  OJ pavement9412->7438, parallel3654->1949.5, junctions630->462,
  segments1698->1400. New pass accepts611/904 and135/211 candidates respectively.
  It uses1495745/149126 popped search states, no label/state/attempt cap reached.
  Earlier parallel passes hit1200 attempts and GJ's junction pass hits600;
  therefore this is not exhaustive or globally optimal road planning.
- Tradeoffs: route-distance sums GJ695823->717817 (+3.16%), OJ155913->160701
  (+3.07%); bend sums22941->25671 and6274->7050. Original0.2 step-ratio p50=1,
  p95=1.333 for both. Short-block exceptions exceed1.5 on28/14 routes, with
  maximum ratios2/3; all stay within14 extra world units and original bends+4.
  Do not characterize the short-route exception as a strict universal50% cap.
- Fidelity / determinism: `python ../artifacts/visual/verify_urban_backbone.py
  <gj|oj>` repeats routing and all14 packaged files byte-for-byte per city,
  compares old avenue-only routing exactly, checks every original bound, access
  port and source identity. Original City/UCG bytes and all coordinates identical.
  Repeated consolidation+packaging takes70.33s/16.24s on this machine (not the
  entire analysis pipeline). Generation-time optimization remains necessary.
  `node ../artifacts/visual/verify_access.mjs
  ../artifacts/visual/urban-backbone-r2/<gj|oj>/after` confirms exact6157/2243
  evidenced edges,1273/400 connected files,4209/1381 paths, unresolved0 and
  pavement/building intersections0. This is coverage of scene-backed edges,
  not proof that all possible source relationships have been discovered.
- Artifacts inspected: `node ../artifacts/visual/parcel_focus_review.mjs
  urban-backbone-r2 urban-backbone-focus-r2`; viewed all four focused WebGL
  images at identical cameras and both showcase SVG captures. GJ's repeated
  transverse grid links visibly decrease; OJ's dense buildings partly obscure
  the change. Skyline/layout unchanged; remaining right-angle roads and access
  stubs still look schematic. No claim of curves or roundabouts delivered.
  `node ../artifacts/visual/junction_smoke.mjs urban-backbone-fixtures` captures
  real sparse/unknown WebGL/SVG; inspected Spring WebGL and unknown preview.
- Browser: `node scripts/viewer_audit.mjs <Chrome>
  ../artifacts/visual/urban-backbone-audit-r2
  ../artifacts/visual/urban-backbone-r2/gj/after
  ../artifacts/visual/urban-backbone-r2/oj/after` passes three LODs, actual picking,
  role/source inspection, single-path tracing, filters, stable road grades,
  navigation and Synthetic. Also inspected GJ overview/route inspector and OJ
  preview. Overview still leaves substantial margins; thumbnail fine roads
  remain dense, not a camera/composition redesign. Chrome152 SwiftShader,
  20 samples: Synthetic CPU p95 GJ2.0/1.5/1.3ms, OJ1.7/1.2/1.5ms; static rebuilds0.
  Concurrent validation load and software rendering: not GPU FPS/speedup evidence.
- Tests: `python -m unittest discover -s tests -q`:344 run,343 pass,1 Windows
  symlink skip; `python -m ruff check metropogits scripts tests`:pass. Node suites
  access_routes/junction_geometry/viewer_audit/camera_navigation/role_landmarks:
  35 pass. Seven new tests cover short/long urban detours, original frozen caps,
  exact membership/ports, demand deduplication, bent corridors, semantic isolation,
  bridges, atomic rollback, resource limits, order determinism and packaging.
- Fixes applied and reverified: initial forest ties favored longer corridors and
  retained two long equal-demand sides while trying to remove a necessary short
  connector. Rectangle tests exposed this; ties now prefer shorter connectors.
  Full r2 outputs, suites and repeatability reverified after the correction.
- Spec alignment: PASS, technical7-8, functional AC-002/003/006/014, product
  DEC-005/006/007/011 and approved ADR-019 policy. No source semantics, stable ID,
  public schema, security default, external service or default-layout change.
- Open risks / next actions: reduce new merging turns with continuous alignments
  and junction planning, while retaining verified coverage/clearance. Curves and
  selective roundabouts need real space and shared path geometry, not decoration.
  Profile generation cost before making this experimental mode a default.
- Commits created / pushed (main): one coherent implementation/test/docs unit,
  committed after this checkpoint; normal upstream push under the maintainer's
  previously reconfirmed owner exception. No force, remote-setting changes or
  agent attribution. Private artifacts and unrelated IDE caches excluded.

## Checkpoint 2026-10-18 — bend-preserving urban road continuity

- Implemented: opt-in `--continuity` after the unchanged urban pass. Align paths
  on existing roads without length/bend increases; then reconsider all remaining
  cycle corridors, including former backbone roads. Atomic replacements retain
  original urban distance bounds and may not add bends to any current path.
  Turn cost includes fixed entrance/exit headings. Iterative bridge detection is
  refreshed after accepted deletions; exact route memberships rebuild afterward.
- Fixtures / revisions: GJ3d9b53f and OJb163acd parcel-3d-r2 JSON; fresh
  spring-positive and unsupported structural-showcase at parent8aee6cc. No target
  repository execution, dependency install or private artifact publication.
- Commands: `python -m scripts.road_consolidation
  ../artifacts/visual/parcel-3d-r2/<gj|oj> --out
  ../artifacts/visual/urban-continuity-r2/<gj|oj> --continuity`.
  Fresh `python -m metropogits build --repo
  tests/fixtures/repositories/<spring-positive|structural-showcase> --out
  ../artifacts/visual/urban-continuity-fixtures-r2/<spring|unknown> --repo-id
  fixtures/<spring|unknown>`, then continuity export into *-study. Both builds
  COMPLETE; sparse paths unchanged, unknown input receives no invented roads.
- Results vs prior urban output: GJ bends25671->23501 (-8.45%), pavement
  28412.5->27800 (-2.16%), junctions1582->1507, parallel5736.5->5404;
  OJ bends7050->6712 (-4.79%), pavement7438->7382 (-0.75%), junctions462->456,
  parallel1949.5->1918. Route-distance sums717817->722773 and160701->160918:
  +0.69%/+0.14%, within unchanged original urban bounds for every route.
- Alignment improves712/133 paths; subsequent removal accepts40/4 corridors.
  GJ cycle search stops at2M states after975 attempts (934 bounds/connectivity
  rejections,1 budget rejection); OJ444 attempts/354726 states, no cap hit.
  All incomplete candidates roll back. Earlier passes retain their own caps.
  Refinement from r1: refresh bridges after deletions, skipping55/5 newly required
  connectors. R2 geometry matches r1 here, but avoids provably futile searches.
- Fidelity / determinism: `python ../artifacts/visual/verify_continuity.py
  <gj|oj>` checks original ports/doors, identities, urban bounds and per-path bend
  nonincrease; repeats routing and all14 packaged files per city byte-for-byte.
  Prior `--urban` baseline matches its stored routing exactly; City/UCG bytes and
  every building/district coordinate unchanged.1275/255 paths change;793/138
  have fewer bends. Repeat consolidation+packaging95.18s/19.82s (not full input
  analysis; concurrent load, not a controlled performance comparison).
- `node ../artifacts/visual/verify_access.mjs
  ../artifacts/visual/urban-continuity-r2/<gj|oj>/after`:6157/2243 evidenced edges,
  1273/400 connected files,4209/1381 complete paths; unresolved0 and pavement/
  building intersections0. These are scene-covered relations, not all possible
  source relationships or measured runtime traffic.
- Artifacts inspected: `node ../artifacts/visual/parcel_focus_review.mjs
  urban-continuity-r2 urban-continuity-focus-r2`; all four identical-camera Detail
  captures and both showcase captures viewed. GJ loses a few short side links;
  OJ's selected dense district looks almost unchanged. Composition/skyline,
  remaining right-angle streets and dense fine lines persist. No major aesthetic
  breakthrough claimed. `node ../artifacts/visual/junction_smoke.mjs
  urban-continuity-fixtures-r2`: Spring WebGL and unknown SVG inspected.
- Browser: `node scripts/viewer_audit.mjs <Chrome>
  ../artifacts/visual/urban-continuity-audit-r2
  ../artifacts/visual/urban-continuity-r2/gj/after
  ../artifacts/visual/urban-continuity-r2/oj/after` passes3 LODs, picking,
  source/role inspection, route drill-down, filters, demand profiles, navigation,
  Synthetic. GJ route-inspector capture viewed. Chrome152 SwiftShader,20 samples:
  Synthetic CPU p95 GJ1.6/1.5/1.3ms, OJ1.5/1.2/1.5ms; static rebuilds0.
  This measures CPU submission, not GPU FPS or a speedup claim.
- Tests: `python -m unittest discover -s tests -q`:353 run,352 pass,1 Windows
  symlink skip. Ruff passes. Node access_routes/junction_geometry/viewer_audit/
  camera_navigation/role_landmarks:35 pass. Nine new tests cover actual staircase
  removal, cycle reassignment, semantic isolation, bridge oracle/deep chains,
  weighted-search Dijkstra oracle/heading costs, rollback, caps and determinism.
- Spec alignment: PASS, technical7-8, AC-002/003/006/014, DEC-005/006/007/011,
  ADR-019. No default routing, public contract, source ID or security change.
- Open risks / next actions: improvement is modest, especially OJ. Prioritize
  explicit block-level shared access/collector planning over endless deletion
  passes; define a separate experiment before changing fixed-port policy. Profile
  generation cost. Curves/roundabouts and road-first geography remain unimplemented.
- Commits created / pushed (main): one coherent implementation/test/docs unit
  after verification, normal upstream push under the maintainer's reconfirmed
  owner exception. No force, remote-setting edits or agent attribution; private
  outputs and unrelated IDE caches excluded.

## Checkpoint 2026-10-18 — block collector planning (parent 945af02)
- Implemented: separate `--collectors` comparison, planning local shared trees
  across actual ports/boundary crossings with obstacle-certified new pavement.
  Necessary old paths remain when original urban distance/+4-bend bounds fail.
  Commit a local proposal only if total pavement strictly decreases and junctions/
  nearby parallel length do not increase. Rebuild exact memberships; no fake edges.
- Fixtures / revisions: GJ3d9b53f and OJb163acd parcel JSON, maintained
  spring-positive and unsupported structural-showcase at parent945af02. Target
  repository scripts/dependencies were not executed or installed.
- Commands: private JSON-only `python ../artifacts/visual/collector_trial.py
  <gj|oj>` uses fresh0.2 cached data from road-consolidation-r2 and unchanged
  urban-continuity-r2 routing. Export: `artifacts/visual/block-collectors-r3/
  {gj,oj}/{before,after}`. Fresh pipeline: `python -m metropogits build --repo
  tests/fixtures/repositories/<spring-positive|structural-showcase> --out
  ../artifacts/visual/block-collectors-fixtures-r3/<spring|unknown> --repo-id
  fixtures/<spring|unknown>`, then `python -m scripts.road_consolidation
  ../artifacts/visual/block-collectors-fixtures-r3/<spring|unknown> --out
  ../artifacts/visual/block-collectors-fixtures-r3/<spring|unknown>-study
  --collectors`. Both real builds COMPLETE; sparse paths remain, unknown has no roads.
- GJ:17 accepted block proposals/160 attempts (attempt cap reached),173362
  search expansions. Pavement27800->27579.5 (-0.79%), parallel5404->5204.5,
  junctions1507->1501, route-distance sum722773->724495 (+0.24%), bends23501->23787.
  OJ:3/42 accepted,44558 states, no cap. Pavement7382->7361 (-0.28%),
  parallel1918->1893.5, junctions456->456, route-distance160918->161114 (+0.12%),
  bends6712->6750. The extra turns are an explicit tradeoff, not a continuity gain.
- Fidelity: `node ../artifacts/visual/verify_access.mjs
  ../artifacts/visual/block-collectors-r3/<gj|oj>/after` passes:6157/2243
  scene-backed edges,1273/400 connected files,4209/1381 complete routes, unresolved0,
  full-width pavement/building intersections0. Canonical City/UCG bytes, building
  positions, original doors/access ports and all route identities unchanged.
- Determinism: `python ../artifacts/visual/verify_collectors.py gj oj` repeats
  collector routing and all14 packaged files per city byte-identically, checks
  every route's original bounds and provenance.563/187 paths change; new unit
  lattice edges73/7, removed136/13. Original length ratio p95=1.333 both,
  max2/3 with28/15 short-block exceptions, all within max(floor(1.5*N),N+4).
  This is not a universal50% cap. The cached continuity baseline matches exactly.
- Performance correction: initial candidate trials rebuilt full JSON geometry
  repeatedly. Replace with exact unit-lattice pavement/junction/parallel guards,
  validated against independent full metrics; rebuild only final geometry.
  Initial OJ hybrid run123.12s vs corrected trial5.28s under differing concurrent
  load, not a controlled speedup benchmark. Repeated GJ pass43.29s; profiled OJ
  12.48s. cProfile identifies bend calculations and final ID/JSON generation as
  remaining costs. Stopped the obsolete slow GJ prototype process; no user process
  or artifact was deleted. Private profile is `block-collectors-r3/oj/collector-profile.pstats`.
- Artifacts inspected: `node ../artifacts/visual/parcel_focus_review.mjs
  block-collectors-r3 block-collectors-focus-r4
  Backend/Vm/src/main/java/gj/cloud/vm/application/org
  backend/src/main/java/dev/gamjaoj/account`; all four actual Detail captures and
  both showcase captures viewed, before/after cameras exactly equal. GJ org loses
  a few ladder-like cross-links and shares a straighter local corridor. OJ account
  change is slight. Skyline, density, README composition remain; orthogonal/circuit
  appearance is NOT solved. Earlier unchanged deployment/generation comparison
  is retained separately in block-collectors-focus-r3, not presented as a large gain.
- `node ../artifacts/visual/junction_smoke.mjs block-collectors-fixtures-r3`:
  actual Spring WebGL and unknown SVG inspected. Unknown generic facilities remain
  legible; no invented network. Existing Spring sparse directory layering remains.
- Browser: `node scripts/viewer_audit.mjs
  "C:/Program Files/Google/Chrome/Application/chrome.exe"
  ../artifacts/visual/block-collectors-audit-r3
  ../artifacts/visual/block-collectors-r3/gj/after
  ../artifacts/visual/block-collectors-r3/oj/after` passes three LODs, picking,
  role/source inspection, route drill-down, filters, road grades, navigation and
  Synthetic. Route-inspector screenshot viewed. Chrome152 SwiftShader20 samples:
  Synthetic CPU p95 GJ1.4/1.1/1.0ms, OJ1.1/1.0/1.3ms, static rebuilds0.
  CPU submission measurements are not GPU FPS or a performance improvement claim.
- Tests: `python -m unittest discover -s tests -q`:364 run,363 pass,1 Windows
  symlink skip. Ruff and diff whitespace checks pass. Node access_routes,
  junction_geometry, viewer_audit, camera_navigation, role_landmarks:35 pass.
  Eleven collector tests cover real building clearance/doors, exact memberships,
  repeatability, geometry-guard oracle, mixed network kinds, isolated inputs,
  disconnected graphs, input/budget limits, and invalid provenance/endpoints.
  A mixed-kind zero-through-path test exposed segment-ID remapping in rebuild;
  fixed it and reran the entire suite without weakening assertions.
- Spec alignment: PASS, technical7-8, FR-007, AC-002/003/006/014,
  DEC-005/006/007/011, ADR-019 documented before implementation. Public UCG/City,
  default layout/routing, IDs and security unchanged. This is a bounded optional
  experiment with modest visual gains, not the finished city-road design.
- Open risks / next actions: boundary ports and individual access directions
  still constrain topology. Define road-first block connectors and allowable
  endpoint/parcel adjustments before further implementation; don't simply raise
  caps or add decorative roundabouts. Total bends increased; this remains opt-in.
- Commits created / pushed (main): this checkpoint precedes the coherent
  implementation/test/docs commit and verified normal upstream push under the
  maintainer's owner exception. Git outcome is reported separately after the
  commands succeed. No force, settings edits, agent credit or private artifacts.

## Checkpoint 2026-10-18 — road-first visual frontage (parent 01e4217)
- Implemented: opt-in `--frontage` plans an existing evidenced local collector
  before reorienting a building's visual door. Reconnect all incident relations
  atomically; reject incomplete proposals. Building positions, dimensions,
  districts, canonical City/UCG and semantic identities remain unchanged.
  Prioritize long exclusive approaches, then unique-edge demand. Require strictly
  less pavement and non-increasing junction/nearby-parallel counts. Preserve the
  original urban full-world-distance and +4-bend bounds, including access spurs.
- Fixtures / revisions: GJ3d9b53f and OJb163acd parcel JSON; spring-positive and
  unsupported structural-showcase at parent01e4217. No target code, dependency
  installation or build scripts executed. Public schemas/default routing unchanged.
- Commands: `python ../artifacts/visual/frontage_trial.py <gj|oj>` reads JSON-only
  original0.2 routing from road-consolidation-r2 and reproduces the exact
  block-collectors-r3 baseline. Outputs: `artifacts/visual/road-frontage-r2/
  {gj,oj}/{before,after}`. `python ../artifacts/visual/verify_frontage.py gj oj`
  repeats planning and verifies all14 packaged files per city byte-identically,
  unchanged canonical City/UCG bytes, original budgets, source provenance,
  consistent building-face doors and unchanged paths outside affected frontages.
- GJ:33 accepted frontages,151 affected paths,600 candidate attempts/370170 search
  states. Pavement27579.5->27212 (-1.33%), parallel5204.5->4917.5 (-5.51%),
  junctions1501->1497, bends23787->23726, route-distance724495->724614 (+0.016%).
  OJ:33 frontages,246 affected paths,600 attempts/340464 states. Pavement7361->7165
  (-2.66%), parallel1893.5->1701 (-10.17%), junctions456->450, bends6750->6646,
  route-distance161114->161520 (+0.252%). Both hit the600-proposal cap, not the
  1M-state cap; this is a bounded heuristic, not an exhaustive city optimum.
- Correction: initial demand-first priority accepted11/13 frontages and saved
  only80.5/45.5 pavement units. Exclusive-approach-first priority saves367.5/196
  with the same caps. A reconstructed-approach guard enforces the12-step limit
  even when search labels change. Reverified all outputs after this correction.
- Fidelity: `node ../artifacts/visual/verify_access.mjs
  ../artifacts/visual/road-frontage-r2/<gj|oj>/after` passes:6157/2243 scene-backed
  edges,1273/400 connected files,4209/1381 complete routes, unresolved0,
  full-width pavement/building intersections0. All route IDs, source/target,
  kinds and evidence memberships preserved. Original length ratio p95=1.329/1.326,
  max1.933/2.75 with28/16 short-block exceptions. The approved14-world-unit
  short-route allowance means this is NOT a universal50% ratio cap.
- Fresh end-to-end: `python -m metropogits build --repo
  tests/fixtures/repositories/<spring-positive|structural-showcase> --out
  ../artifacts/visual/road-frontage-fixtures-r2/<spring|unknown> --repo-id
  fixtures/<spring|unknown>`, then `python -m scripts.road_consolidation
  ../artifacts/visual/road-frontage-fixtures-r2/<spring|unknown> --out
  ../artifacts/visual/road-frontage-fixtures-r2/<spring|unknown>-study --frontage`.
  Both COMPLETE. Spring6 buildings/11 districts/2 networks retains2 paths;
  unknown3 buildings/4 districts has no fabricated roads or frontage proposals.
  `node ../artifacts/visual/junction_smoke.mjs road-frontage-fixtures-r2` generated
  real captures; Spring WebGL and unknown SVG inspected.
- Artifacts inspected: `node ../artifacts/visual/parcel_focus_review.mjs
  road-frontage-r2 road-frontage-focus-r2
  Backend/Vm/src/main/java/gj/cloud/vm/application/vm/dto
  backend/src/main/java/dev/gamjaoj/generation/service`. All four before/after
  WebGL captures and both showcase captures viewed; cameras exactly match.
  GJ VM loses several return/zigzag approaches; OJ's dense buildings hide much
  of its road change, so visible improvement is modest. Skyline, density,
  district colors and README composition remain. No observed clipping/overlap
  regression. Orthogonal/circuit appearance remains; no roundabout claim.
- Browser: `node scripts/viewer_audit.mjs
  "C:/Program Files/Google/Chrome/Application/chrome.exe"
  ../artifacts/visual/road-frontage-audit-r2
  ../artifacts/visual/road-frontage-r2/gj/after
  ../artifacts/visual/road-frontage-r2/oj/after` passes three LODs, picking,
  role/source inspection, exact route drill-down, filters, grades, camera and
  Synthetic. Route-inspector capture inspected. Chrome152/SwiftShader20 samples:
  Synthetic CPU p95 GJ1.3/1.1/1.0ms, OJ1.1/1.1/1.4ms; static rebuilds0.
  These are CPU submission measurements, not GPU FPS or a speedup claim.
- Tests: `python -m unittest discover -s tests -q`:375 run,374 pass,1 Windows
  symlink skip. `python -m ruff check metropogits scripts tests` and
  `git diff --check` pass. `node --test tests/access_routes.test.mjs
  tests/junction_geometry.test.mjs tests/viewer_audit.test.mjs
  tests/camera_navigation.test.mjs tests/role_landmarks.test.mjs`:35 pass.
  Eleven frontage tests cover atomic rollback, original bounds, door clearance,
  exact memberships, repeatability/order independence, budget exhaustion,
  no fabricated connectivity, provenance rejection and geometry-guard oracle.
- Spec alignment: PASS, technical7-8, FR-007, AC-002/003/006/014,
  DEC-005/006/007/011, ADR-019 documented before implementation. Derived doors
  are visual routing, not inferred semantic facts. No default/layout/ID/security
  change. Cached planner repeat43.12s GJ/12.4s OJ under local load, not full
  analysis timings or a controlled performance comparison.
- Open risks / next actions: remaining parallel corridors and fixed block
  gateways still constrain topology. Next jointly plan multiple entrances and
  block-boundary merge points; do not just raise caps or add decorative circles.
  This opt-in frontage slice does not complete the city-road design.
- Commits created / pushed (main): checkpoint precedes the coherent code/test/
  documentation commit and verified normal upstream push under the maintainer's
  explicit owner exception. Actual Git outcome is reported after execution.
  No force, remote settings changes, agent attribution or private artifacts.

## Checkpoint 2026-10-18 — shared block gateways (parent 82a4cb5)
- Implemented: optional `--gateways` comparison after frontage. Group nearby
  equally outward-facing directory crossings, choose an evidenced gateway and
  jointly reconnect local route spans. Prefer old pavement; allow certified
  short connectors. Keep necessary old routes when original0.2 world-distance/
  +4-bend bounds fail. Accept only fewer used crossings/less pavement and no
  increase in junctions, nearby parallel length or total bends. Buildings,
  districts, doors, logical relationships and canonical inputs stay unchanged.
- Fixtures / revisions: GJ3d9b53f, OJb163acd parcel JSON; maintained spring-positive
  and unsupported structural-showcase at parent82a4cb5. No target code/build/
  dependency execution. Specs read in technical/functional/product order.
- Commands: `python ../artifacts/visual/gateway_trial.py gj oj` reads JSON-only
  road-frontage-r2 baselines and original0.2 road-consolidation-r2 inputs, exports
  `artifacts/visual/block-gateways-r3/{gj,oj}/{before,after}`. First existing-road-only
  trial joined only one group per city. Obstacle-clear connectors and turn cost200
  improve GJ's result; original route budgets and global acceptance guards unchanged.
- GJ:3 accepted groups (3->1 twice,2->1 once),45 changed paths. Pavement27212->27156
  (-0.21%), parallel4917.5->4826.5, junctions1497 unchanged, bends23726->23682,
  route-distance724614->724502. New/removed unit edges11/27. OJ:1 group (2->1),
  4 changed paths, pavement7165->7161.5 (-0.05%), parallel1701->1680,
  junctions450 unchanged, bends6646->6638, route-distance161520->161499;
  new/removed unit edges6/7. OJ segment count1344->1345 despite less pavement;
  subdivision count is not a physical road-length metric.
- Bounds: both cities hit240 proposals,110/109 patches,207300/209962 search states;
  not the480-patch/1M-state limits. Small-directory-first search is not exhaustive
  or globally optimal. `retainedRoutes` includes unchanged paths already using
  the selected gateway, not just rejected/indispensable paths.
- Fidelity: `node ../artifacts/visual/verify_access.mjs
  ../artifacts/visual/block-gateways-r3/<gj|oj>/after` passes:6157/2243 scene-backed
  edges,1273/400 connected files,4209/1381 routes, unresolved0, full-width
  pavement/building intersections0. Exact route/segment memberships preserved.
  A changed GJ ComposeRouterPlanRequest->ComposeRouterRouteOverride path still
  carries its original edge IDs, including a RESOLVED import; no new
  inferred call or communication. Existing source-inspector capture inspected.
- Repeatability: `python ../artifacts/visual/verify_gateways.py gj oj` checks
  unchanged canonical City/UCG bytes, fixed doors, original route bounds and
  all14 packaged files per city byte-identical on a repeat. Planner29.30s/14.52s
  under local load (not full analysis time or controlled speedup benchmark).
  Original world-length ratio p95=1.329/1.326, max1.933/2.75 with28/16 short-block
  exceptions. Approved14-unit short-route allowance remains; not a universal50% cap.
- Fresh pipeline: `python -m metropogits build --repo
  tests/fixtures/repositories/<spring-positive|structural-showcase> --out
  ../artifacts/visual/block-gateways-fixtures-r3/<spring|unknown> --repo-id
  fixtures/<spring|unknown>`, then `python -m scripts.road_consolidation
  ../artifacts/visual/block-gateways-fixtures-r3/<spring|unknown> --out
  ../artifacts/visual/block-gateways-fixtures-r3/<spring|unknown>-study --gateways`.
  Both builds COMPLETE, Spring2 paths unchanged, unknown0 roads. `node
  ../artifacts/visual/junction_smoke.mjs block-gateways-fixtures-r3` captures real
  WebGL/SVG with no browser exceptions; Spring viewer/unknown preview inspected.
- Artifacts inspected: `node ../artifacts/visual/parcel_focus_review.mjs
  block-gateways-r3 block-gateways-focus-r3
  Backend/Ops/src/test/java/gj/cloud/ops/application/deployment/spec
  backend/src/main/java/dev/gamjaoj/export/service`. All four before/after WebGL
  images and both showcase images viewed; exact camera equality checked. Ops
  loses redundant transverse approaches; OJ one nearby parallel approach shifts
  to a shared street. Changes are local/modest; overall skyline/README framing
  unchanged. No observed new clipping/overlap, but orthogonal circuit appearance
  persists. Unknown fallback retains generic blocks; sparse Spring remains dense.
- Browser: `node scripts/viewer_audit.mjs
  "C:/Program Files/Google/Chrome/Application/chrome.exe"
  ../artifacts/visual/block-gateways-audit-r3
  ../artifacts/visual/block-gateways-r3/gj/after
  ../artifacts/visual/block-gateways-r3/oj/after` passes three LODs, picking,
  role/source inspector, single-route drill-down, filters, grades, navigation and
  Synthetic. Chrome152/SwiftShader20 samples: Synthetic CPU p95 GJ1.3/1.2/1.2ms,
  OJ1.1/1.2/1.2ms, static rebuilds0 throughout. Not GPU FPS or a speedup claim.
- Tests: `python -m unittest discover -s tests -q`:386 run,385 pass,1 Windows
  symlink skip. Eleven gateway tests include joint routing, exact memberships,
  collision checks, rollback, fixed doors after frontage, original budgets,
  deterministic scene ordering, search caps, semantic-kind/normal isolation,
  no unknown fabricated connectivity and provenance/repeated-pass rejection.
  `python -m ruff check metropogits scripts tests` and whitespace checks pass.
  `node --test tests/access_routes.test.mjs tests/junction_geometry.test.mjs
  tests/viewer_audit.test.mjs tests/camera_navigation.test.mjs
  tests/role_landmarks.test.mjs`:35 pass.
- Spec alignment: PASS technical7-8, FR-007, AC-002/003/006/014,
  DEC-005/006/007/011, ADR-019. No schema/semantic-ID/default/security change.
  No curves/roundabouts or finished city-planning claim. Small visual gain is
  explicitly recorded; this experimental stage is not promoted to default.
- Open risks / next actions: fixed entrances still constrain gateway planning.
  Jointly evaluate entrances and boundary gateways, prioritize removable pavement
  instead of small-directory order, and avoid simply raising caps/relaxing bounds.
  Do not accumulate experimental passes in default builds without meaningful gain.
- Commits created / pushed (main): checkpoint precedes the coherent implementation/
  tests/docs commit and normal upstream push under the explicit owner exception.
  Actual Git outcome is reported after execution. No force, remote settings edit,
  agent attribution, private artifacts or unrelated fixture build caches staged.

## Checkpoint 2026-10-18 — rejected joint entrance study (parent 1b32b81)
- Implemented: a private bounded prototype jointly evaluates building entrance
  faces and a shared boundary gateway. Both real cities reject every proposal;
  product source/defaults/CLI remain untouched. This completed work unit is the
  evidence-based documentation decision, not a delivered visual improvement.
  Prototype and seven tests retained in local `artifacts/visual/joint-entrances-study/`.
- Fixtures / revisions: GJ3d9b53f, OJb163acd cached parcel scenes and gateway-r3
  routing; maintained spring-positive and structural-showcase at parent1b32b81.
  No target repository code, builds or dependencies executed. Specs read in
  technical/functional/product order, followed by operating instructions.
- Trials: parallel-pavement-first and spatially interleaved candidate ordering
  each accept0/240 proposals per city. R2 GJ rejection counts: incident constraint87,
  no crossing removed45, no pavement gain95, more bends12, geometry regression1.
  OJ:136/55/47/0/2. Candidate groups935/280; R2 states41887/60619. Both hit the
  proposal cap, not the1M-state cap. This heuristic failure does not prove fixed
  geography impossible. A controlled six-building test changes one door and
  removes two crossings, but is not a real-repository visual gain.
- Commands: `python ../artifacts/visual/joint_trial.py gj oj` exports
  `artifacts/visual/joint-entrances-r2/{gj,oj}/{before,after}`; inputs are parsed
  JSON payloads, not evaluated JavaScript. `python ../artifacts/visual/verify_joint.py
  gj oj` passes exact before/after route, segment, junction and canonical input
  equality, and all14 packaged files per city match a repeat generation.
  GJ/OJ paths4209/1381, pavement27156/7161.5, bends23682/6638 unchanged.
- Fidelity: `node ../artifacts/visual/verify_access.mjs
  ../artifacts/visual/joint-entrances-r2/<gj|oj>/after` passes:6157/2243 scene-backed
  edges,1273/400 connected files, unresolved0, full-width building intersections0.
  These counts are scene-backed coverage, not proof of exhaustive static analysis.
- Fresh pipeline: `python -m metropogits build --repo
  tests/fixtures/repositories/<spring-positive|structural-showcase> --out
  ../artifacts/visual/joint-entrances-fixtures-r2/<spring|unknown> --repo-id
  fixtures/<spring|unknown>`, then `python ../artifacts/visual/joint_fixture.py`
  and `node ../artifacts/visual/junction_smoke.mjs joint-entrances-fixtures-r2`.
  Both COMPLETE, Spring2 paths/6 segments unchanged, unknown0 roads. No browser
  exceptions. Fresh Spring WebGL and unknown SVG preview captures inspected:
  Spring dense towers retained; unknown generic blocks remain sparse, no invented roads.
- Visual comparison: `node ../artifacts/visual/parcel_focus_review.mjs
  joint-entrances-r2 joint-entrances-focus-r2
  Backend/Ops/src/test/java/gj/cloud/ops/application/deployment/spec
  backend/src/main/java/dev/gamjaoj/export/service`. Both after WebGL captures
  and both showcase images inspected; camera equality checked. Each paired
  before/after focused PNG is byte-identical. The busy orthogonal road appearance,
  skyline and README composition remain unchanged; no visual improvement claimed.
- Browser: `node scripts/viewer_audit.mjs
  "C:/Program Files/Google/Chrome/Application/chrome.exe"
  ../artifacts/visual/joint-entrances-audit-r2
  ../artifacts/visual/joint-entrances-r2/gj/after
  ../artifacts/visual/joint-entrances-r2/oj/after` passes three LODs, picking,
  inspectors, filters, navigation and Synthetic. Chrome152/SwiftShader20 samples:
  Synthetic CPU p95 GJ1.5/1.0/1.3ms, OJ1.0/1.3/1.2ms, static rebuilds0 throughout.
  These are CPU submission measurements, not GPU FPS or a speedup comparison.
- Tests: `python -m unittest discover -s tests -q`:386 run,385 pass,1 Windows
  symlink skip. `python ../artifacts/visual/joint-entrances-study/test_joint_entrances.py`:
  7 pass, including atomic door consistency/rollback, exact memberships, collision/
  original bounds, repeatability, scene order, caps, unsupported fallback and provenance.
  `python -m ruff check metropogits scripts tests`:pass.
  `node --test tests/access_routes.test.mjs tests/junction_geometry.test.mjs
  tests/viewer_audit.test.mjs tests/camera_navigation.test.mjs
  tests/role_landmarks.test.mjs`:35 pass.
- Spec alignment: PASS technical7-8, FR-007, AC-002/003/006/014, DEC-005/006/007/011,
  ADR-019. No public schema, stable ID, security, semantic evidence or default change.
  No curves/roundabouts, new layout or completed city-planning claim.
- Fixes applied and reverified: spatially diversify candidate ranking without
  raising budgets; still no real gain. Keep the prototype outside the product.
- Open risks / next actions: diagnose fixed-parcel constraints separately from
  heuristic search limits before proposing road-first parcel reallocation. Preserve
  the working gateway baseline; do not weaken evidence/acceptance to ship a stage.
- Commits created / pushed (main): this checkpoint precedes the documentation-only
  commit and normal upstream push under the maintainer's explicit owner exception.
  Actual Git outcome is reported after execution. No force, remote settings edits,
  attribution, private artifacts or unrelated fixture caches staged.

## Checkpoint 2026-10-18 — complete-trip shared frontage (parent 94165e3)
- Implemented: opt-in `--shared-frontage`; evaluate alternative clear building
  faces with every complete incident trip, rather than fixing outside-patch paths.
  New candidate connectors stay within three lattice steps of alternative faces.
  Preserve original0.2 world-distance/+4-bend bounds, all source relationships,
  canonical City/UCG and buildings. Atomic entrance rollback and final total-bend
  rollback; only actually used obstacle-clear pavement is exported.
- Diagnostic comparisons: private whole-corridor deletion with complete-trip
  rerouting saved GJ0.64%/OJ0.78% pavement. Longest-trip-first reuse saved2.84%/3.27%
  but increased bends; neither prototype promoted. Complete-trip entrance planning
  improves both without parcel relocation. This establishes a search-scope limit,
  not absence of layout issues or global optimality.
- Fixtures / revisions: GJ3d9b53f and OJb163acd cached parcel scenes/gateway-r3;
  fresh maintained spring-positive/structural-showcase at94165e3. No target source
  execution/build/dependency installation. Specs read technical/functional/product,
  followed by AGENTS. ADR-019 scope recorded before product implementation.
- Commands: `python ../artifacts/visual/shared_frontage_trial.py <gj|oj>` reads
  JSON-only cached data and original road-consolidation-r2 bounds. Outputs:
  `artifacts/visual/shared-frontage-r1/{gj,oj}/{before,after}`. GJ401/OJ103 accepted
  entrances. Pavement27156->23957 /7161.5->6167.5, nearby parallel4826.5->2453.5 /
  1680->868, junctions1497->1402 /450->414, bends23682->22642 /6638->6258.
  Total trip distance724502->725867 /161499->162094; no claim every path shortened.
- Bounds: GJ2673 attempts/12M states hits total cap; OJ1170 attempts/2166841 states
  hits10 per-trip caps. GJ160 capped searches includes final total exhaustion.
  Candidate graph36168/9690 unit edges. Failed/capped proposals retain safe routes.
- Fidelity: `node ../artifacts/visual/verify_access.mjs
  ../artifacts/visual/shared-frontage-r1/<gj|oj>/after`:6157/2243 scene-backed
  edges,1273/400 connected files,4209/1381 paths, unresolved0, building intersections0.
  Examined changed AdminAccountDeletionController->AccountDeletionJobResponse:
  same two edge IDs and RESOLVED import evidence, not an inferred runtime call.
- Repeatability: `python ../artifacts/visual/verify_shared_frontage.py gj oj`:
  independent full-width/membership/door/world-budget checks pass; City/UCG bytes
  unchanged and all14 files per city match repeat generation. Counter-based union
  scoring matches expanded geometry oracle and old scorer's real-city output.
  Repeat planner162.88s/23.60s under local load, not controlled speedup/full build time.
- Fresh pipeline: `python -m metropogits build --repo
  tests/fixtures/repositories/<spring-positive|structural-showcase> --out
  ../artifacts/visual/shared-frontage-fixtures-r1/<spring|unknown> --repo-id
  fixtures/<spring|unknown>`; `python -m scripts.road_consolidation
  ../artifacts/visual/shared-frontage-fixtures-r1/<spring|unknown> --out
  ../artifacts/visual/shared-frontage-fixtures-r1/<spring|unknown>-study --shared-frontage`.
  Both COMPLETE; Spring pavement15.5->12, two paths retained; unknown zero roads.
  `node ../artifacts/visual/junction_smoke.mjs shared-frontage-fixtures-r1` passes.
  Actual Spring viewer/unknown preview inspected: dense towers/sparse generic
  fallback retained; no fabricated technology or relationships.
- Visual artifacts inspected: `node ../artifacts/visual/parcel_focus_review.mjs
  shared-frontage-r1 shared-frontage-focus-r1`. All four before/after focus images,
  both showcase images and GJ audit route inspector viewed. Identical camera
  confirmed. Redundant short approaches disappear in Ops deployment/service and
  OJ generation/service. Skyline/README composition unchanged; continuous bright
  paint and orthogonal corridors still look circuit-like. No visual-completion claim.
- Browser: `node scripts/viewer_audit.mjs
  "C:/Program Files/Google/Chrome/Application/chrome.exe"
  ../artifacts/visual/shared-frontage-audit-r1
  ../artifacts/visual/shared-frontage-r1/gj/after
  ../artifacts/visual/shared-frontage-r1/oj/after` passes all three LODs, picking,
  source/route drill-down, filters, grades, navigation and Synthetic. Chrome152 /
  SwiftShader20 samples: Synthetic CPU p95 GJ1.3/1.1/1.1ms, OJ5.7/1.6/1.7ms;
  static rebuilds0 throughout. Concurrent local planner load; not GPU FPS/speedup.
- Tests: `python -m unittest discover -s tests -q`:401 run,400 pass,1 Windows
  symlink skip. Fifteen new tests cover full-trip gain, all-incident rollback,
  final bend rollback, every resource cap, exact geometry/provenance, mixed-kind
  protection, access-only prior trips, canonical packaging, search contraction,
  repeatability, unknown input and union-score oracle. Ruff and whitespace pass.
  Node access_routes/junction_geometry/viewer_audit/camera_navigation/role_landmarks
  suites:35 pass. Prior access-only trips were initially rejected by too-strict
  lattice-set equality; corrected to preserve them and added regression coverage.
- Spec alignment: PASS technical7-8, FR-007, AC-002/003/006/014, DEC-005/006/007/011,
  ADR-019. No schema/default/ID/security change. No curves/roundabouts implemented.
- Open risks / next actions: route generation remains costly/bounded; geometry
  improvement is stronger than its visual impact. Next distinguish asphalt,
  minor accesses, arterial lane paint and junction presentation without hiding roads.
- Commits created / pushed (main): checkpoint precedes this coherent feature/tests/
  docs commit and normal owner-authorized push. Actual Git result checked afterward.
  No attribution, force, remote settings change, private artifacts or unrelated caches.

## Checkpoint 2026-10-18 — asphalt and bounded arterial paint (parent 5ba4e50)
- Implemented: neutral dependency asphalt, subdued minor-road edges, globally
  phase-aligned dashed AVENUE/TRUNK paint in WebGL/Canvas/SVG. Visible junction
  mouths trim paint; selected relationship overlays remain continuous. Grade,
  certified road width, geometry, endpoints and source evidence are unchanged.
  ADR-018 was recorded before implementation. This follows the independently
  committed/pushed complete-trip routing improvement5ba4e50, not another routing pass.
- Fixture(s) / revision(s): same GJ3d9b53f (1324 buildings) and OJb163acd
  (681 buildings), plus maintained spring-positive and structural-showcase.
- Commands run: `python ../artifacts/visual/road_surface_trial.py` repackages
  the verified preceding experiment with current trusted assets. Both canonical
  City/UCG files and complete routing payloads match their preceding outputs;
  all14 packaged files per case are repeat-identical. No target code executed.
- Fresh E2E: `python -m metropogits build --repo
  tests/fixtures/repositories/<spring-positive|structural-showcase> --out
  ../artifacts/visual/road-surface-fixtures-r1/<spring|unknown> --repo-id
  fixtures/<spring|unknown>`; `python -m scripts.road_consolidation
  ../artifacts/visual/road-surface-fixtures-r1/<spring|unknown> --out
  ../artifacts/visual/road-surface-fixtures-r1/<spring|unknown>-study --shared-frontage`.
  Both COMPLETE. `node ../artifacts/visual/junction_smoke.mjs
  road-surface-fixtures-r1` captures real WebGL/SVG without browser exceptions.
- Artifacts inspected: `node ../artifacts/visual/parcel_focus_review.mjs
  road-surface-r1 road-surface-focus-r1`; actual GJ/OJ focused WebGL images and
  both showcase previews viewed, plus fresh unknown WebGL and Spring SVG.
  `artifacts/visual/city-road-review-r1/index.html` links actual old gateway/old
  palette captures and new shared-frontage/new palette captures. Exact camera
  and LOD equality checked against both focus reports; no design mockups.
- Visual findings: fewer redundant approaches and less bright continuous wiring;
  major streets read as asphalt with dashed paint while minor access remains
  visible. Skyline, selected district and README arrangement are unchanged.
  Orthogonal routing and some dense intersections remain; no roundabouts/curves
  or whole-city visual completion claim. No additional topology gain from paint.
- Browser: `node scripts/viewer_audit.mjs
  "C:/Program Files/Google/Chrome/Application/chrome.exe"
  ../artifacts/visual/road-surface-audit-r1
  ../artifacts/visual/road-surface-r1/gj/after
  ../artifacts/visual/road-surface-r1/oj/after`: three LODs, filters, inspection,
  route drill-down, demand grades, navigation and Synthetic pass. Chrome152 /
  SwiftShader20 samples: Synthetic CPU p95 GJ1.4/1.1/1.2ms, OJ1.0/1.0/1.4ms;
  static geometry rebuilds0 throughout. Local CPU timings, not GPU FPS or speedup.
- Fallback: `node ../artifacts/visual/road_surface_fallback.mjs` forces WebGL
  unavailable on trusted bundled output; Canvas and Synthetic operate without
  browser exceptions. Actual fallback screenshot inspected. Its overview's
  yellow aggregate outlines are still crowded: explicit separate correction
  task, not described as visually equivalent to WebGL. Paint is access-frame
  cached; no claim of a full Canvas performance benchmark.
- Tests / determinism / stability: `python -m unittest discover -s tests -q`:
  405 run,404 pass,1 Windows symlink skip. `python -m ruff check .` passes.
  `node --test tests/access_routes.test.mjs tests/junction_geometry.test.mjs
  tests/road_paint.test.mjs tests/viewer_audit.test.mjs
  tests/camera_navigation.test.mjs tests/role_landmarks.test.mjs`:38 pass.
  Shared CPU/browser fixtures check reversal, negative coordinates, phase,
  intersection trims, short/diagonal/capped paint and semantic-kind separation.
- Fixes applied and reverified: legacy fixture without junctions now degrades
  safely. Intentional palette golden change c17e96f3->88439c6b reviewed; a new
  regression test restores the old palette and reconstructs the exact old hash,
  while asserting building/district/network/routing metadata equality. Legacy
  ungraded rendering still passes. No failing assertion was removed.
- Spec alignment: PASS technical7-8, FR-007, AC-002/003/006/014 and
  DEC-005/006/007/011. No public schema, stable ID, evidence or security change.
- Open risks / next actions: remaining repeated right-angle bends require
  geometric planning, not decorative curves. Correct crowded Canvas aggregate
  outlines separately. Planning cost remains bounded and substantial; shared
  frontage stays opt-in. No unrelated target caches or private artifacts staged.
- Commits created / pushed (main): this checkpoint accompanies the renderer
  feature/tests/docs commit. Verify final metadata and ordinary owner-authorized
  push result; no force, attribution or remote-policy modification.

## Checkpoint 2026-10-18 — independent cold source rebuilds (engine1956e78)
- Implemented: no engine change. Rebuilt GJ from source twice without previous
  artifacts/hints; documented reproducible commands and cold-versus-hinted
  geography in REPRODUCIBLE_CITY_BUILD. Existing outputs retained, no deletion.
- Fixture(s) / revision(s): clean GJ-Cloud3d9b53f9dac9af1187ac9754cb3066b27e43b766,
  catalog0.4.0, default local namespace/minimal theme; maintained
  structural-showcase as fresh unknown-language fallback. Target remains clean.
- Commands run, twice with `<run>` = run1/run2 (repo cwd):
  `python -m metropogits build --repo ../visual_test_proj/GJ-Cloud --out
  ../artifacts/visual/clean-rebuild-r1/gj/<run>/base --json`;
  `python -m scripts.parcel_viewer ../artifacts/visual/clean-rebuild-r1/gj/<run>/base
  --out ../artifacts/visual/clean-rebuild-r1/gj/<run>/parcel`;
  `python -m scripts.road_consolidation ../artifacts/visual/clean-rebuild-r1/gj/<run>/parcel
  --out ../artifacts/visual/clean-rebuild-r1/gj/<run>/roads --shared-frontage`.
  All stages succeed; source scan reports COMPLETE with60 info diagnostics,
  including46 unresolved Java and4 JS/TS imports, not universal semantic accuracy.
- Repeatability: `python ../artifacts/visual/clean_rebuild_verify.py`: all13
  default,14 parcel,14 final files identical across independent processes.
  Building1324/district506 coordinate and footprint differences0 between runs.
  Final City SHA256 cd1018be25431bd5c5e9b1dbc2be0283a4e9cdea61fd6d172fa6449df30e8b08;
  UCG1406ff8b73eedfdb141d30c7cb71636034d1a8af67d2de2b5134569c58fe11d3.
- Historical comparison: previous displayed road-surface city differs by58
  Portal building coordinates, no district changes, identical UCG. Separate
  `python -m metropogits generate --graph
  ../artifacts/visual/clean-rebuild-r1/gj/run1/base/graph.ucg.json --out
  ../artifacts/visual/clean-rebuild-r1/gj/hint-check/city.json --previous-scene
  ../artifacts/visual/road-continuity-r2/gj/city.json --json` emits
  LAYOUT_HINT_APPLIED and reproduces previous base City bytes exactly. Historical
  shared-access/generated-output builds recorded previous-scene use. Cold/hinted
  inputs are different; this is not nondeterminism. Parcel stage moves35 Ops
  buildings in both pipelines; not another source of historical differences.
- Roads: exact4209 route identities/source/target/kind/edge membership retained,
  but2681 path polylines differ from the old hinted geography. Fresh final has
  4245 segments/1420 junctions;6157 scene-backed edges/1273 connected files.
  `node ../artifacts/visual/verify_access.mjs
  ../artifacts/visual/clean-rebuild-r1/gj/run1/roads/after`: unresolved0,
  pavement/building intersections0. Independent RoadFrontageTests.check oracle
  confirms original0.2 full-world detour/bend bounds, consistent doors and exact
  segment memberships. Explicit validate_city CLI also passes.
- Metrics: own gateway->shared frontage centerline26865.5->23918.5,
  nearby parallel4742.5->2495.5, bends24263->23341, junctions1517->1420.
  Compared with old displayed city, bends22642->23341, junctions1402->1420,
  centerline23957->23918.5. Mixed tradeoff, not a new optimization claim.
  Fresh shared pass372 accepted doors/2538 proposals,12M state cap,168 capped
  searches. Whole-city replanning can affect routes outside moved directories;
  incremental road locality is not certified by this cold-repeat check.
- Artifacts inspected: `node ../artifacts/visual/clean_rebuild_review.mjs`:
  same-camera Ops/Portal before/fresh captures, actual fresh WebGL overview,
  showcase SVG and unknown WebGL/showcase inspected. Existing density, archetypes
  and inspection remain usable; orthogonal detours/parallel approaches remain.
  Generic sparse fixture remains generic with0 invented roads; large ground
  boundaries and overview aggregate outlines still need separate visual work.
- Browser: initial combined `clean-rebuild-audit-r1` audit fails on the three-file
  fallback because its natural LOD is Detail, not the harness's expected Overview.
  No test weakened. Standalone final GJ audit rerun:
  `node scripts/viewer_audit.mjs "C:/Program Files/Google/Chrome/Application/chrome.exe"
  ../artifacts/visual/clean-rebuild-audit-r2
  ../artifacts/visual/clean-rebuild-r1/gj/run1/roads/after` passes all three LODs,
  selection, filtering, exact-route inspection, navigation and Synthetic.
  Synthetic CPU p95 1.5/1.3/1.3ms, static rebuilds0 (Chrome152/SwiftShader,
  20 samples, local CPU submission timings, not GPU FPS). Unknown fixture is
  separately smoke-captured without exceptions; no full three-LOD audit claim.
- Tests / stability: Python405 run,404 pass,1 Windows symlink skip; Node access,
  junction,paint,audit,camera,landmarks suites38 pass; Ruff and whitespace pass.
  Source-backed AdminAccountDeletionController->AccountDeletionJobResponse still
  carries the same RESOLVED IMPORTS/REFERENCES facts. No target code executed.
- Spec alignment: PASS technical7-8, AC-002/006/014, DEC-003/005/006/007/011.
  Fixed-input reproducibility demonstrated; no algorithm, schema, default, ID,
  security or source mutation. AC-003 under changed input is not newly certified.
- Open risks / next actions: directly improve lingering merges/bends, compare
  cold and hinted geography, measure route-change locality and planning cost.
  Small-fixture natural-LOD audit handling remains a separate harness task.
- Commits created / pushed (main): one documentation/checkpoint work unit;
  verified normal owner-authorized push follows. Private generated outputs and
  pre-existing IDE build caches are not staged; human identity/no agent credit.

## Checkpoint 2026-10-18 — fixed-door trip smoothing and atomic corridor removal

- Implemented: explicit `scripts.road_consolidation --simplify` after shared
  frontage. Smooth complete trips without increasing distance/bends; then move
  every user of a redundant corridor atomically to remaining same-kind pavement.
  Keep fixed doors and original0.2 world-distance/+4-bend limits across stages.
  No new pavement, resurrected discarded roads, invented edges or default change.
  Added eleven tests, resource caps, duplicate/provenance rejection, postcondition
  guards and developer contract/reproduction documentation before promotion.
- Fixture(s) / revisions: GJ-Cloud3d9b53f9dac9af1187ac9754cb3066b27e43b766,
  GamjaOJb163acd2b5fe41edfc1e7fc7d367362851241896; both historical hinted GJ and
  independently cold-rebuilt GJ geography. Maintained spring-positive and
  structural-showcase fixtures at parent d536511; catalog0.4.0.
- Commands run: `python ../artifacts/visual/simplification_trial.py oj gj cold`
  runs the final pass twice per city, compares canonical routing bytes, checks
  original bounds/doors/widths/memberships using RoadFrontageTests.check, and
  packages all renderers under `artifacts/visual/trip-simplification-r4`.
  Earlier r1 smooth-only trial barely removed pavement; r2 export failed on
  tuple-valued report keys. Corrected JSON metadata, tested serialization, and
  regenerated r4 from the unchanged baselines; no failed export is promoted.
- Fresh end-to-end commands: `python -m metropogits build --repo
  tests/fixtures/repositories/<spring-positive|structural-showcase> --out
  ../artifacts/visual/trip-simplification-fixtures/<spring|unknown>`;
  `python -m scripts.road_consolidation <build> --out <name>-study --simplify`.
  Both COMPLETE. Unknown has3 generic buildings/0 routes; Spring6 buildings/
  2 routes. No target code, dependency installer or build script executed.
- Results (historical GJ / OJ / cold GJ): pavement23957->23477.5 /
  6167.5->6101 /23918.5->23337.5; parallel2453.5->2397.5 /868->826 /
  2495.5->2348.5; junctions1402->1367 /414->403 /1420->1367;
  bends22642->22158 /6258->6098 /23341->22797. Total route distance
  725867->734358 /162094->163592 /721695->731495. This trades modest
  bounded detours for shared pavement; not the preceding pass's roughly50% gain.
- Planner: smoothing130/66/176 trips; corridor removals27/7/34. Search states
  2982697/1600853/2844590; proposals1200/767/1200. Both GJ cases reach
  the proposal cap; individual capped searches0. Fixed upper bounds do not
  prove global optimality. A single final-pass run took roughly22/9/21seconds
  locally, excluding artifact rendering, not an end-to-end speed claim.
- Fidelity and stability: independent browser-data oracle
  `node ../artifacts/visual/verify_access.mjs <r4>/<gj|oj|cold>/after` passes;
  4209/1381/4209 exact paths,6157/2243/6157 scene-backed edges and
  1273/400/1273 connected files, unresolved0, full-width intersections0.
  `python -m scripts.validate_city <after>/city.json --ucg <after>/graph.ucg.json`
  passes all three. Actual before/after City and UCG SHA256 match in all cases:
  no building/district movement or semantic edits. Repeated routing bytes match.
  A rerouted AiPartAdvisor->AiPreviewGenerationLogRepository trip retains its
  RESOLVED REFERENCES edge/evidence; inspected corresponding source reference.
  This does not newly certify incremental route stability under changed input.
- Artifacts inspected: `node ../artifacts/visual/parcel_focus_review.mjs
  trip-simplification-r4 trip-simplification-focus-r1` captures identical-camera
  Ops/OJ Detail; same harness with explicit district arguments and `cold` captures
  `trip-simplification-cold-focus-r1`. Viewed before/after WebGL captures and
  actual GJ showcase, plus fresh Spring/unknown WebGL and SVG from
  `node ../artifacts/visual/junction_smoke.mjs trip-simplification-fixtures`.
  Some redundant strips disappear near the focused blocks; overall silhouette,
  directory colors and composition remain stable. This is local cleanup, not a
  dramatic skyline change. Short parallel approaches, angular corners, dense
  labels and large overview aggregate outlines remain visible correction tasks.
- Browser commands: `node scripts/viewer_audit.mjs
  "C:/Program Files/Google/Chrome/Application/chrome.exe"
  ../artifacts/visual/trip-simplification-audit-r1 <r4>/gj/after <r4>/oj/after`;
  repeat with `trip-simplification-cold-audit-r1 <r4>/cold/after`.
  All three LODs, filters, exact route selection, navigation and Synthetic pass.
  Static builds during animation0. Synthetic CPU p95 overview/district/detail:
  GJ1.2/1.1/1.1ms, OJ2.0/1.2/1.4ms, cold1.6/1.1/1.1ms; Chrome/SwiftShader,
  local submission timings, not GPU FPS or a cross-machine speed guarantee.
  Sparse fixtures separately smoke-tested because their natural LOD is Detail.
- Tests / determinism / stability: Python416 run,415 pass,1 Windows symlink skip;
  Node access/junction/paint/audit/camera/landmark suites38 pass; Ruff passes.
  Dedicated tests cover atomic failed-second-user rollback, no-new-pavement,
  no resurrection, mixed kinds, input-order determinism, immutable inputs,
  access-only/empty fallback, original bounds, caps and exact shared membership.
- Spec alignment: PASS technical7-8, FR-007, AC-002/006/014,
  DEC-003/005/006/007/011. Public schemas/stable IDs/security/defaults unchanged;
  derived experimental diagnostic payload documented in CURRENT_BASELINE/ADR-019.
- Open risks / next actions: preserve necessary endpoint access while evaluating
  remaining short parallel corridors and repeated bends locally. No claim that
  curves/roundabouts, road-first parcel reallocation or overall urban design is done.
  GJ hits bounded proposal limits; default promotion requires separate evaluation.
- Commits created / pushed (main): one coherent implementation/test/docs unit;
  verified normal owner-authorized push follows. Private generated artifacts and
  unrelated pre-existing IDE build caches remain outside the commit.

## Checkpoint 2026-10-18 — explain residual corridor constraints

- Implemented: bounded `routeSimplification.constraints` diagnostics separating
  rejected proposals, bridge/unused skips, search-cap unknowns and total-bend
  regressions. First8 samples per reason, at most24; sample geometry capped at64
  keys with explicit full count/truncation. Independent distance-only probes
  have separate5,000-per-trip/100,000-total state limits and cannot change routing.
- Experiments not promoted: geometry-ranked removal prioritization reduced cold
  parallel length2348.5->2299.5 but worsened junctions1367->1370 and total
  bends22797->22835; OJ junctions403->404. Additional refinement of the prior
  result removed only one cold corridor (31.5 pavement units) for3M states,
  with no gain in historical GJ/OJ. Retained the previous planner and viewer;
  this checkpoint delivers diagnostics, **not a new visual improvement**.
- Fixtures / revisions: historical/cold GJ-Cloud3d9b53f9dac9af1187ac9754cb3066b27e43b766;
  GamjaOJb163acd2b5fe41edfc1e7fc7d367362851241896; maintained spring-positive
  and structural-showcase at parent fc0c591, catalog0.4.0. Target code not run.
- Commands: private `python ../artifacts/visual/parallel_priority_trial.py oj cold gj`
  for the two candidate policies; final `python
  ../artifacts/visual/corridor_constraints_review.py oj cold gj` regenerates the
  actual simplification twice per city and exports reports to
  `artifacts/visual/corridor-constraints-r2/{index.html,oj.json,cold.json,gj.json}`.
  Entire routing bytes equal the previous `trip-simplification-r4` after removing
  only the new diagnostic field. Repeated final reports/paths are canonical-byte
  identical. No City/UCG/building/district/source identity changes.
- Observed proposal counts (historical GJ/cold GJ/OJ): attempts1200/1200/767;
  accepted27/34/7; no-admissible-trip1086/1080/715; total-bend-regression87/86/45;
  individual search-cap rejections0. Connectivity bridge skips792/820/430.
  Counters count proposal events across rounds, not unique roads. Both GJ cases
  still hit the overall proposal limit; unattempted candidates remain unknown.
- Distance probe samples: historical GJ8/8, cold7/8, OJ8/8 exceeded the remaining
  original distance allowance. Cold's other sample is distance-feasible but not
  accepted by the original constrained search. Probe states162/166/30; no caps.
  First-per-reason samples are not statistically representative of the city.
  Samples describe the rejection-time graph, not a replayable final graph snapshot.
  Report includes exact route IDs; sampled OJ training-courses.js imports
  thinking-difficulty.js in the source, retaining the same evidenced relationship.
- Fidelity checks: independent RoadFrontageTests.check confirms fixed doors,
  original world-distance/bend bounds, exact memberships and0 full-width building
  intersections for all three cities. Same4209/4209/1381 complete paths and
  6157/6157/2243 scene-backed edges; no lost or fabricated relations.
- Fresh end-to-end: `python -m metropogits build --repo
  tests/fixtures/repositories/<spring-positive|structural-showcase> --out
  ../artifacts/visual/corridor-constraints-fixtures-r2/<spring|unknown>`;
  `python -m scripts.road_consolidation <build> --out <name>-study --simplify`;
  `node ../artifacts/visual/junction_smoke.mjs corridor-constraints-fixtures-r2`.
  Both COMPLETE, actual WebGL/SVG captured without exceptions; Spring6 buildings/
  2 routes and unknown3 generic buildings/0 routes. Viewed final Spring WebGL and
  unknown SVG; earlier same-turn smoke also inspected. Existing sparse composition
  and generic fallback retained, no cosmetic concealment of missing relations.
- Artifacts inspected: real Chrome headless capture of the HTML constraint report
  (`corridor-constraints-r2/report.png`), readable labels/counters/source samples.
  Report links to unchanged verified viewers. No new large-city visual or
  Synthetic performance improvement claimed; rendering code is unchanged.
- Tests / determinism / stability: Python422 run,421 pass,1 Windows symlink skip;
  Node six routing/paint/junction/audit/camera/landmark suites38 pass; Ruff and
  whitespace checks pass. Six added tests cover independent distance oracle,
  disconnection/caps, diagnostic noninterference, proposal accounting, bounded
  samples, explicit truncation, and search-cap unknown vs infeasible distinction.
- Spec alignment: PASS technical7/10, FR-007/015, AC-002/006/009/014,
  DEC-003/005/006/007/011. No public schema, default, evidence, detour or security
  relaxation. Developer diagnostic payload documented in CURRENT_BASELINE/ADR-019.
- Next: local joint access-point/connector experiments around rejected samples,
  preserving source-backed trips and original budgets. Distinguish fixed-access
  constraints from physical parcel constraints before moving buildings or
  increasing detour allowances. Do not hide roads or repeat costly global search
  and label negligible change a redesign.
- Commits / push: one coherent diagnostics/test/documentation work unit on main;
  verified normal owner-authorized push follows. Private reports and existing
  unrelated IDE build caches are not staged; no agent attribution.

## Checkpoint 2026-10-18 — local entrance refinement after rejected corridor merges
- Implemented: opt-in `--refine-frontage`, derived frontage-refinement/0.1.
  Select up to96 nearby connected buildings within21 Manhattan world units of
  sampled rejected-route endpoints; jointly reorient each eligible door and
  every incident complete trip. Compare turn costs25/150 with the same clearance,
  original0.2 world-distance/+4-bend bounds and strict union-pavement reduction.
  Junctions, nearby parallel length and summed bends cannot increase per proposal.
  Only used connectors are exported. No canonical positions, schema, evidence,
  default CLI or rendering code changes. Prior pass reports retain historical meaning.
- Fixtures / revisions: GJ-Cloud3d9b53f9dac9af1187ac9754cb3066b27e43b766,
  both historical-hinted and cold geography; GamjaOJb163acd2b5fe41edfc1e7fc7d367362851241896.
  Maintained spring-positive and structural-showcase fixtures at parent5c5ae61,
  catalog0.4.0. No target dependencies installed or target code executed.
- Commands / real-city artifacts: `python ../artifacts/visual/frontage_refinement_trial.py
  cold oj gj --package` runs the final pass twice, compares canonical routing,
  applies independent RoadFrontageTests.check, and exports
  `artifacts/visual/frontage-refinement-r2/{cold,oj,gj}/{before,after}` and reports.
  The harness uses retained City/UCG and original0.2 routing; it is not a claim of
  fresh source analysis for these three large inputs. Their baseline diagnostics
  came from the prior reproducible corridor-constraints-r2 run.
- Observed results (historical GJ/cold GJ/OJ): changed doors5/5/1;
  pavement23477.5->23446 /23337.5->23302.5 /6101->6076.5;
  junctions1367->1366 /1367->1364 /403->401;
  parallel2397.5->2397.5 /2348.5->2334.5 /826->819;
  total bends22158->22137 /22797->22789 /6098->6092;
  trip distance734358->734253 /731495->731446 /163592->163634.
  These are small local gains (about0.13%/0.15%/0.40% pavement), not a solved
  city-wide layout. OJ's distance increases42 within existing original bounds.
  Attempts366/408/282; popped states558871/745139/207477; no caps hit.
- Fidelity / determinism: each city repeated byte-identically. Original-world
  bounds, consistent doors, exact route/edge/segment membership and full-width
  obstacle oracle pass. Zero building intersections; same4209/4209/1381 routes,
  6157/6157/2243 contributing edges and1273/1273/400 connected files. City/UCG
  hashes equal the prior packages; building and district moves0. Representative
  OJ training-courses.js import of thinking-difficulty.js remains at line7;
  GJ ComponentRegistryEntry.java references RegistryScope at line8. No adjacency
  or shared junction creates a new semantic relationship.
- Fresh end-to-end commands: `python -m metropogits build --repo
  tests/fixtures/repositories/<spring-positive|structural-showcase> --out
  ../artifacts/visual/frontage-refinement-fixtures-r1/<spring|unknown>`;
  `python -m scripts.road_consolidation <build> --out <name>-study --refine-frontage`;
  `node ../artifacts/visual/junction_smoke.mjs frontage-refinement-fixtures-r1`.
  Both COMPLETE; Spring6 buildings/2 routes, unknown3 generic buildings/0 routes.
  Viewed actual Spring WebGL and unknown SVG; generic/no-evidence fallback unchanged.
- Actual visual comparison: `node ../artifacts/visual/parcel_focus_review.mjs
  frontage-refinement-r2 frontage-refinement-cold-focus-r1
  Frontend/portal/components/preview-runtime/blueprints/workflows frontend/app cold`;
  same command with frontage-refinement-focus-r2,
  Backend/Ops/src/main/java/gj/cloud/ops/application/preview/analysis, frontend/app,
  gj,oj. Captured and inspected identical-camera Detail images for cold Portal,
  hinted Ops and OJ frontend; also cold showcase.svg through actual Chrome.
  Some short approaches move to the opposite building face, leaving less unused
  parallel pavement. Overall silhouettes and readability remain essentially the
  same. OJ's broad district view makes the one-door change hard to spot; do not
  claim major thumbnail improvement. Large generic clusters and some vacant
  parcels remain. No cosmetic hiding or added roundabout/curve.
- Browser checkpoint: `node scripts/viewer_audit.mjs
  'C:/Program Files/Google/Chrome/Application/chrome.exe'
  ../artifacts/visual/frontage-refinement-cold-audit-r1
  ../artifacts/visual/frontage-refinement-r2/cold/after`; same audit for gj/oj to
  frontage-refinement-audit-r1. All complete: overview/district/detail, navigation,
  filters and exact-route inspection. Synthetic static rebuilds0 in every LOD.
  Local Synthetic CPU p95 cold1.4/1.1/1.1ms, hinted1.4/1.0/1.1ms,
  OJ1.3/1.0/1.4ms. These are local CPU submission timings, not GPU FPS or an SLA.
- Tests: Python431 run,430 pass,1 Windows symlink skip; Node six maintained
  routing/junction/paint/audit/camera/landmark suites38 pass; Ruff and whitespace
  checks pass. Nine new tests cover positive full-trip entrance changes,
  bounds/memberships, deterministic selection, atomic failure, resource caps,
  absent/empty seeds, malformed/repeated provenance, neighborhood isolation and
  packaging. Initial order test incorrectly compared deliberately preserved
  historical sample ordering; corrected to check exact repeat and order-independent
  new decisions/geometry while retaining the historical report.
- Experiments / fixes: one cost policy missed acceptable low-bend alternatives;
  evaluate two bounded policies and require strict per-proposal bend preservation.
  Candidate connectors restricted solely to the currently changed door lost the
  OJ gain; retained bounded nearby connectors that only appear if real routes use
  them. No relaxed distance budget or weakened geometric acceptance.
- Spec alignment: PASS technical7/8/10, FR-007/012/015, AC-002/006/009/014,
  DEC-003/005/006/007/011. ADR-019, contract baseline, roadmap and reproducible
  commands updated. Public scene and UCG unchanged; existing layout stability
  tests included in the full suite.
- Next: this small improvement does not justify repeated city-wide search.
  Evaluate joint multi-building door changes within one problematic block before
  proposing building relocation; keep every original relationship and bound.
  No global optimality or incremental road locality claim.
- Commit / push: one coherent feature/test/docs work unit on main; normal
  owner-authorized push after final staged review. Generated/private outputs and
  pre-existing .gradle/target IDE caches excluded; no agent attribution.

## Checkpoint 2026-10-18 — ADR-020 structural street prototype
- Implemented: geography-only infrastructure, safe-width per-building access,
  bounded assignment of original evidenced trips, explicit fallback partition,
  opt-in `scripts.street_grid --street-grid`, WebGL/Canvas/SVG structural layer
  and visible disclosure. Original IDs/provenance, City/UCG and normal CLI stay
  unchanged. ADR/plan committed first as0cf8d0e on experiment/street-grid.
- Fixtures / revisions: existing pinned GJ-Cloud3d9b53f9dac9af1187ac9754cb3066b27e43b766
  hinted and cold cities; GamjaOJ b163acd2b5fe41edfc1e7fc7d367362851241896.
  Fresh maintained spring-positive and structural-showcase inputs at basebe6f1c3,
  catalog0.4.0. No target code execution/dependency installation.
- Commands run (repo root):
  `python -m scripts.street_grid ../artifacts/visual/frontage-refinement-r2/NAME/after
  --street-grid --out ../artifacts/visual/street-grid-r1/NAME` for gj/cold/oj;
  `python ../artifacts/visual/street_grid_review.py` repeats assignment, uses an
  independent full-trip/membership/clearance oracle, removes networks to verify
  structural independence, and packages latest-baseline comparisons tostreet-grid-r3.
  `python ../artifacts/visual/street_grid_refresh.py` refreshes those owned
  artifacts after final visible SVG disclosure edits; it does not reroute.
- Fresh source-to-render commands: `python -m metropogits build --repo
  tests/fixtures/repositories/spring-positive --out
  ../artifacts/visual/street-grid-fixtures/spring`; same for structural-showcase
  to unknown. Then `python -m scripts.street_grid BUILD --street-grid --out
  ../artifacts/visual/street-grid-fixtures/NAME-study` and
  `node ../artifacts/visual/junction_smoke.mjs street-grid-fixtures`.
  An initial guessed unknown-language path did not exist; command failed before
  output. Located and used the maintained structural-showcase fixture instead.
- Results (hintedGJ / coldGJ / OJ): assigned2487/4209,2483/4209,547/1381;
  fallback1722/1726/834; structural entrances1324/1324/681; canonical building
  and routing full-width intersections0. Infrastructure one connected component
  in each. Repeated routing identical; unchanged network-free infrastructure.
  Assignment search states1281862/1294438/234734; capped searches0. Local
  assignment time18.405/17.130/3.478s, excluding independent oracle/packaging.
  Spring assigns0/2 and preserves both fallback paths; unknown has0 relationships
  and3 structural entrances. No fabricated dependencies.
- Regression metrics: structural centerline34419.5/34419.5/14393 versus prior
  evidenced pavement23446/23302.5/6076.5 (different coverage/meaning). New
  all-trip geometry including fallback54998.5/55558.5/14522. These overlapping
  lengths must not be added. **Not a road-length reduction or visual victory.**
  Default hides legacy fallbacks with an explicit count; selection/All routes
  exposes them. Fewer displayed trips must not be reported as route simplification.
- Artifacts inspected: actual matched-camera WebGL captures in
  street-grid-focus-r3/{gj,oj}-{before,after}/focused.png;
  street-grid-cold-focus-r1/cold-after/showcase.png (real Chrome SVG rasterization);
  street-grid-gj-focus-r2/gj-{before,after}/focused.png and showcase.png;
  street-grid-fixtures/unknown.png; street-grid-canvas-r1/gj/canvas.png.
  Private captures remain outside Git. Structural surfaces are more continuous
  around some buildings but grid repetition/empty parcels remain; small unknown
  has overly broad grid coverage. Canvas overview's aggregate outlines are noisy.
  Frozen LOD obstacle rectangles prevent unrelated compound silhouette changes.
- Browser commands: `node scripts/viewer_audit.mjs
  'C:/Program Files/Google/Chrome/Application/chrome.exe' OUT INPUT` for
  street-grid-r3/{gj,oj,cold}/after to street-grid-{gj-audit-r2,oj-audit-r1,cold-audit-r1}.
  All pass overview/district/detail, exact-route inspection, filters/navigation.
  Synthetic static rebuilds0; local CPU p95 GJ1.2/1.1/1.5ms,
  OJ1.3/1.2/1.3ms, cold1.3/1.4/1.3ms. CPU submission timings, not GPU FPS/SLA.
  `node ../artifacts/visual/street_grid_canvas.mjs` forces WebGL unavailable and
  captures both real Canvas fallbacks with Synthetic; no browser exceptions.
  `parcel_focus_review.mjs street-grid-r3 street-grid-focus-r3` plus cold Portal
  suffix command verify identical Detail camera per before/after pair.
- Tests / fixes: Python439 run,438 pass,1 existing Windows symlink skip; six
  maintained Node suites39 pass; Ruff/whitespace pass. New tests cover geometry
  independence, caps, clearance/access, exact identities/bounds, fallback honesty,
  deterministic input order/repeat, opt-in rendering and default LOD preservation.
  Fixed strict-JSON Decimal normalization before geometry; fixed missing LOD
  rectangles that changed compound counts; added visible SVG structural labels.
  Initial review harness digest used bytes instead of a document; corrected and
  reran successfully. Early capture attempts before package completion failed
  with missing files; completed matched-camera/audit runs supersede them.
- Spec alignment: approved experimental deviation under ADR-020 from technical7,
  FR-007/AC-006 and product5.1/DEC-011; only non-semantic infrastructure changes
  meaning. AC-002/009/014, source evidence and original trip budgets retained.
  No schema/identity/default changes. No claim of infrastructure incremental
  locality or aggregate-to-street clearance; canonical buildings remain fixed.
- Open risks / next: incomplete assignment and redundant structural loops block
  promotion. Record individual fallback reasons; reduce infrastructure with
  frontage/connectivity constraints independently of dependencies. Evaluate a
  bounded street-first parcel experiment only with explicit stability review.
  Do not resume small frontage tweaks or call the circuit-like problem solved.
- Commit / push: documentation0cf8d0e precedes this coherent prototype/test/docs
  work unit on experiment/street-grid. Final staged review and normal feature
  branch push follow this checkpoint; no main merge, force push, attribution or
  generated/private artifacts. Delivery hash/push result are recorded in handoff.

## Checkpoint 2026-10-18 — structural street fallback diagnostics
- Implemented: additive bounded failure explanations, filtered25-row fallback
  review in WebGL/Canvas, and exact original-path/evidence navigation. No route,
  street, building, UCG or public City geometry changed. Existing artifacts with
  no diagnostics display an explicit unrecorded cause.
- Fixtures / revisions: GJ-Cloud3d9b53f9dac9af1187ac9754cb3066b27e43b766
  (hinted and cold), GamjaOJb163acd2b5fe41edfc1e7fc7d367362851241896;
  maintained spring-positive and structural-showcase at base34a5eb4, catalog0.4.0.
- Commands: `python ../artifacts/visual/street_pruning_probe.py` rejected a
  conservative terminal-free bridge-subtree deletion trial: protecting all
  geometry-eligible access and selected entrances leaves GJ9645/OJ4015 lattice
  edges unchanged. Zero improvement; this pruning pass is not shipped.
  `python ../artifacts/visual/street_diagnostics_review.py` packages
  street-diagnostics-r1/{gj,cold,oj}, asserts canonical routes/segments/junctions
  and infrastructure equality to street-grid-r3 and repeats GJ assignment.
  `python ../artifacts/visual/street_diagnostics_refresh.py` repackages the same
  owned geometry after the long-path CSS fix, without rerouting.
- Results (hintedGJ / coldGJ / OJ): distance_limit1392/1390/706;
  joint_constraints324/331/124; access_only6/5/4. Assignment remains
  2487/4209,2483/4209,547/1381. Independent diagnostic A* states
  166624/168154/74605, below its separate1M cap. No access/disconnection or
  search-cap diagnoses observed. Joint constraints do not prove bend-only
  infeasibility. Capped checks explicitly report unknown, not impossible.
- Fresh source-to-output commands: `python -m metropogits build --repo
  tests/fixtures/repositories/spring-positive --out
  ../artifacts/visual/street-diagnostics-fixtures/spring`; same command for
  structural-showcase to unknown. `python -m scripts.street_grid BUILD
  --street-grid --out ../artifacts/visual/street-diagnostics-fixtures/NAME-study`
  for both. Spring retains2/2 fallback paths; unknown has0 logical relations.
- Browser commands: `node scripts/viewer_audit.mjs
  'C:/Program Files/Google/Chrome/Application/chrome.exe'
  ../artifacts/visual/street-diagnostics-browser-r1
  ../artifacts/visual/street-diagnostics-r1/gj
  ../artifacts/visual/street-diagnostics-r1/oj
  ../artifacts/visual/street-diagnostics-r1/cold` passes three LODs, filters,
  navigation, exact route tracing and Synthetic (static rebuilds0 throughout).
  These are CPU/browser checks, not a hardware GPU FPS claim.
  `node ../artifacts/visual/junction_smoke.mjs street-diagnostics-fixtures`
  renders real WebGL and SVG previews for both fresh fixtures.
  `node ../artifacts/visual/street_diagnostics_ui.mjs OUT INPUT...` runs with
  large gj/oj and small spring-study/after,unknown-study/after inputs to
  street-diagnostics-{large,small}-ui-r2. WebGL and forced Canvas pass reason
  selection, exact-path navigation,25-row bound, pagination, empty state,
  horizontal-overflow assertions and no browser exceptions.
- Artifacts inspected: street-diagnostics-small-ui-r1/webgl-0/selected-fallback.png;
  street-diagnostics-large-ui-r2/webgl-0/fallbacks.png;
  street-diagnostics-large-ui-r1/canvas-1/selected-fallback.png;
  street-diagnostics-fixtures/unknown-preview.png (actual SVG rasterization).
  Initial GJ fallback list clipped long paths; fixed wrapping and reran both
  browser modes with overflow assertions. Panel now legible without horizontal
  scroll. City remains small at overview; Canvas aggregate outlines remain
  crowded and sparse unknown has excessively broad streets. No visual road
  improvement claimed, and these existing issues still block promotion.
- Tests / determinism / stability: Python444 run,443 pass,1 existing Windows
  symlink skip via `python -m unittest discover -s tests -q`; Node40 pass via
  `node --test tests/access_routes.test.mjs tests/junction_geometry.test.mjs
  tests/road_paint.test.mjs tests/viewer_audit.test.mjs
  tests/camera_navigation.test.mjs tests/role_landmarks.test.mjs`.
  Independent seeded unit-graph BFS checks shortest-distance diagnoses. Zero
  diagnostic budget cannot alter routed geometry. Exact repeated GJ output and
  unchanged real-city geometry pass. `python -m ruff check .` and Git diff check
  pass. No neighboring-revision relayout needed: this unit changes no positions.
- Spec alignment: PASS within the approved ADR-020 experiment; technical7,
  FR-007/AC-006 and product5.1/DEC-011 remain the documented experimental
  deviation, not a silently changed default. Source evidence, deterministic
  contracts, unsupported-input behavior and no untrusted execution retained.
- Open risks / next: roughly81% of hintedGJ and85% of OJ fallbacks violate
  distance limits on this skeleton. Further edge deletion cannot shorten paths
  in the same graph. Prioritize a bounded street-first block/access comparison,
  with assignment, infrastructure length and relocation measurements; do not
  replace independent infrastructure with dependency-driven shortcut paving.
- Commit / push: coherent diagnostic capability, tests and findings staged as
  one work unit on experiment/street-grid after verification. Normal upstream
  push follows; exact delivery hash/result recorded in handoff. Private sources,
  captures, generated cities and unrelated IDE caches excluded.

## Checkpoint 2026-10-18 — aligned block street experiment
- Implemented: opt-in `--aligned-blocks` removes the half-cell seed offset and
  joins geometry-neighbor wavefronts with local alternate paths. Derived streets
  version0.2; public City/UCG, buildings, original doors and trip budgets fixed.
  Rejected per-trip entrance reorientation after the existing single-door oracle
  failed. Rejected per-building perimeter roads: even with local loops their
  GJ infrastructure54282 exceeded the prior34419.5. Neither trial is shipped.
- Fixtures / revisions: GJ3d9b53f9dac9af1187ac9754cb3066b27e43b766 (hinted/cold),
  OJb163acd2b5fe41edfc1e7fc7d367362851241896; spring-positive and unsupported
  structural-showcase at base20053f7. Catalog0.4.0.
- Commands: `python ../artifacts/visual/street_access_probe.py` for local
  candidate measurements (latest script reproduces adopted aligned variant).
  `python ../artifacts/visual/aligned_streets_review.py` with PYTHONPATH=.;tests
  repeats all three assignments, checks unchanged canonical scenes, original
  endpoint coordinates, complete budgets, exact segment memberships, no
  full-width building intersections and network-independent infrastructure.
  Packages `aligned-streets-r1/{gj,oj,cold}/{before,after}`. No source repo code
  executed, no dependencies installed, no private artifacts staged.
- Results (GJ/cold/OJ): assigned3642/3642/1113, fallback567/567/268; all
  4209/4209/1381 original routes retained. Street infrastructure COMPLETE,
  entrances1324/1324/681, infrastructure search states44407/44407/17119.
  Assignment search states864991/839707/146564, capped searches0. Full numeric
  before/after table is in STREET_GRID_PLAN. Structural length reduces6.75%/6.75%/
  7.98%, all-trip pavement20.47%/21.39%/13.18%, all-trip junctions27.05%/27.39%/
  18.70%. Complete trip length sums increase1.41%/1.31%/4.22%; original individual
  bounds still pass. Overlapping infrastructure and relation length are not added.
- Fresh E2E: `python -m metropogits build --repo
  tests/fixtures/repositories/spring-positive --out
  ../artifacts/visual/aligned-streets-fixtures/spring`; same for structural-showcase
  to unknown. `python -m scripts.street_grid BUILD --street-grid --aligned-blocks
  --out ../artifacts/visual/aligned-streets-fixtures/NAME-study` for both.
  Spring assignment1/2 (previous0/2); unsupported0 relations, no fabricated trips.
  `node ../artifacts/visual/junction_smoke.mjs aligned-streets-fixtures` passes
  real WebGL and SVG capture without browser exceptions.
- Browser / images: `node ../artifacts/visual/parcel_focus_review.mjs
  aligned-streets-r1 aligned-streets-focus-r1` asserts identical before/after
  camera and Detail LOD. Inspected gj-before/focused.png, gj-after/focused.png,
  oj-after/showcase.png, aligned-streets-fixtures/spring.png and
  unknown-preview.png. Ops has fewer wide parallel surfaces while displaying
  more assigned trips. OJ showcase is readable; sparse unknown still shows abrupt
  safe-width transitions, and city overview whitespace/regular grids remain.
  No universal city-like appearance or default promotion claimed.
- Browser checks: `node scripts/viewer_audit.mjs CHROME OUT INPUT...` with
  CHROME=C:/Program Files/Google/Chrome/Application/chrome.exe and inputs
  aligned-streets-r1/{gj,oj}/after to aligned-streets-audit-r1; cold/after to
  aligned-streets-cold-audit-r1. All three LODs, navigation, filters and exact
  route inspection pass; Synthetic static rebuilds0. CPU submission checks are
  not GPU FPS measurements. `node ../artifacts/visual/street_diagnostics_ui.mjs
  ../artifacts/visual/aligned-streets-canvas-r1 GJ_AFTER OJ_AFTER` verifies WebGL
  and forced Canvas fallback pagination/evidence with no browser exceptions.
- Tests: `python -m unittest discover -s tests -q`:450 run,449 pass,1 existing
  Windows symlink skip. Six maintained Node suites(access_routes,
  junction_geometry,road_paint,viewer_audit,camera_navigation,role_landmarks):40
  pass. `python -m ruff check .` and Git whitespace checks pass. New tests cover
  aligned continuous gap streets, input-order/semantic independence, exact trip
  bounds/doors/membership, bounded wave-neighbor loops, unknown/no-edge output,
  optional legacy mode and no canonical mutation. Repeat large assignments
  identical. All canonical positions unchanged; no claim of incremental locality
  for connector geometry after future building edits.
- Spec alignment: PASS within ADR-020 approved experiment; original semantic
  deviation remains documented under technical7, FR-007/AC-006, DEC-011. No
  schema migration, execution, relaxed evidence or hidden relation deletion.
- Open risks / next: remaining fallbacks and sparse width transitions; improve
  framing without changing geography or hiding entities, then assess block-level
  aesthetics rather than reverting to per-relation shortcut roads.
- Commit / push: separate verified feature unit on experiment/street-grid;
  staged diff and ordinary upstream push follow this checkpoint. Delivery hash
  recorded in handoff; no merge/main push or agent attribution.

## Checkpoint 2026-10-18 — perspective-aware initial city framing
- Implemented: analytic perspective fitting of the unchanged framing point set,
  allowing X/Z target translation instead of backing away from a fixed map
  center. Original yaw/pitch/margins and orbit target height preserved; Reset
  restores the fitted pose. No entity omission, scene change or road rerouting.
- Fixtures / revisions: same GJ/OJ pinned revisions as the preceding checkpoint,
  hinted/cold variants at62c8d22; fresh spring-positive and structural-showcase.
- Commands / artifacts: `node ../artifacts/visual/framing_review.mjs OUT INPUT...`
  captured framing-before-r1 from aligned-streets-r1/{gj,oj}/after and the two
  aligned-streets-fixtures outputs before editing. `python
  ../artifacts/visual/framed_streets_export.py` packages aligned-framing-r2/{gj,oj,cold}
  and asserts unchanged scene/graph/routing bytes. Current captures are
  framing-after-r2 with those gj/oj inputs plus
  aligned-framing-fixtures/{spring,unknown}-ground-pivot/after.
  `node ../artifacts/visual/framing_metrics.mjs` independently projects every
  canonical building corner, checks unchanged LOD/counts/orbit height and zero
  out-of-frustum corners. Private framing-comparison-r1/index.html links captures.
- Visual findings: inspected framing-before-r1/0/initial.png and
  framing-after-r2/0/initial.png (GJ), framing-after-r1/1/initial.png (OJ initial
  candidate), and real Spring/unknown previews from the fresh pipeline. Same
  1500x1000 viewport and Overview membership. Final projected building-bound
  width GJ53.4%→74.4%, OJ65.2%→85.9%; height67.4%→87.5%,69.7%→83.7%.
  Bounding spans, not filled pixel area. All canonical corners remain inside;
  no buildings deleted to manufacture improvement. Broad surfaces/regular grids
  and aggregate silhouettes remain separate visual shortcomings.
- Fixes: initial lateral fit moved the orbit target below ground; corrected by
  sliding the target along its view ray to retain original Y. Added regression
  assertion for orbit height, including low/high pitch. Initial Windows test
  output decoding raised a cp949 reader-thread error despite success status;
  set explicit UTF-8 and reran the full suite without that exception.
- E2E: fresh `python -m metropogits build --repo FIXTURE --out OUTPUT` for
  spring-positive/structural-showcase to aligned-framing-fixtures/spring,unknown;
  `python -m scripts.street_grid BUILD --street-grid --aligned-blocks --out OUT`
  produces *-ground-pivot after the fix. `junction_smoke.mjs aligned-framing-fixtures`
  produced WebGL and SVG captures before the pivot correction (SVG unaffected).
  Fresh default build framing-default-spring-r1 and framing-default-audit-r1
  verify ordinary non-street-mode loading with the corrected camera.
- Browser: `node scripts/viewer_audit.mjs CHROME OUT INPUT...` for final
  aligned-framing-r2/gj,oj → aligned-framing-audit-r2 and cold →
  aligned-framing-cold-audit-r2. Same installed Chrome executable as preceding
  checkpoint. Three LODs, filters, pan/orbit, route inspection and Synthetic pass;
  static rebuilds0. These CPU checks do not establish GPU FPS/performance gains.
- Tests / stability: Python451 run,450 pass,1 existing Windows symlink skip via
  `python -m unittest discover -s tests -q`. Seven Node suites43 pass (prior six
  plus camera_framing). Independent projection tests cover rotations, aspect
  ratios, displaced cities, outliers, degeneracy, near/far clipping and order
  determinism. Ruff and whitespace checks pass. Get-FileHash comparison confirms
  City/UCG/preview.svg/showcase.svg unchanged for GJ/cold/OJ; package comparison
  confirms identical routing. No changed geography requiring neighbor churn tests.
- Spec alignment: PASS, technical8 / FR-012 / AC-011, same structural experiment
  meaning under ADR-020. Public contracts/evidence unchanged. Camera code is shared
  by normal WebGL output; Canvas and CPU previews remain unchanged.
- Open risks / next: improve physical width transitions and block readability;
  framing does not solve these or justify default promotion of the street mode.
- Commit / push: second independently verified work unit on experiment/street-grid;
  stage review and normal upstream push follow. Exact hash/result in handoff.

## Checkpoint 2026-10-18 — structural pavement width continuity

- Implemented: short-bulge suppression and gradual safe width transitions shared
  by WebGL/Canvas/SVG. No route, entrance, evidence or canonical placement edits.
- Fixtures / revisions: GJ3d9b53f9dac9af1187ac9754cb3066b27e43b766 and
  OJb163acd2b5fe41edfc1e7fc7d367362851241896, catalog0.4.0, fixed
  aligned-framing-r2 inputs. Maintained spring-positive and structural-showcase
  at parent61a5986 plus this work unit run through the fresh real pipeline.
- Commands: `python -m metropogits build --repo tests/fixtures/repositories/NAME
  --out ../artifacts/visual/street-width-fixtures-r2/LABEL`, with NAME/LABEL
  spring-positive/spring and structural-showcase/unknown. Then
  `python -m scripts.street_grid BUILD --street-grid --aligned-blocks --out OUT`
  to LABEL-study. `python ../artifacts/visual/street_width_review.py street-width-r2`
  packages GJ/OJ before/after, verifies identical scene/UCG/routing bytes,
  repeated surfaces, and each polygon inside its original cleared rectangle.
- Artifacts inspected: street-width-focus-r3/gj-{before,after}/focused.png,
  oj-after/showcase.png and street-width-fixtures-r2/unknown-preview.png;
  Spring WebGL also inspected. `node ../artifacts/visual/parcel_focus_review.mjs
  street-width-r2 street-width-focus-r3` asserts identical Detail cameras.
  `node ../artifacts/visual/junction_smoke.mjs street-width-fixtures-r2`
  captures actual fresh WebGL/SVG. No target repository code executed.
- Visual findings: sparse streets no longer have isolated broad rectangles;
  sustained expansions taper. Less unpainted slab area in GJ Detail, but dense
  README thumbnail change is modest and grid character remains. Initial r1
  taper-only diamonds rejected; r2 adds short-bulge suppression. First focus
  invocation lost empty PowerShell arguments; rerun without placeholders passed.
- Browser: `node scripts/viewer_audit.mjs CHROME OUT INPUT...` for
  street-width-r2/{gj,oj}/after -> street-width-audit-r2, corresponding before
  -> street-width-before-audit-r2. CHROME:
  C:/Program Files/Google/Chrome/Application/chrome.exe,152.0.7977.84,SwiftShader.
  Three LODs, navigation, filters, relation selection and Synthetic pass; static
  rebuilds0 before/after. GJ Synthetic CPU p95 after1.1-1.3ms, before1.3-1.4ms:
  single-run JS submission timings, not GPU FPS or a speedup conclusion.
- `node ../artifacts/visual/street_diagnostics_ui.mjs OUT INPUT...` on fresh
  Spring/unknown after outputs -> street-width-fallback-audit-r2 verifies real
  WebGL and forced Canvas, exact fallback inspection and empty disclosure.
  No exceptions. Spring assignment1/2; unknown0 relations, not fabricated roads.
- Tests / stability: full Python discovery, seven Node suites43 pass, Ruff and
  diff whitespace checks. Surface tests cover T/X junctions, reversal, order,
  containment, door isolation, caps, legacy rendering, bulges and SVG parity.
  Closing Python discovery:457 run,456 pass,1 Windows symlink skip. Large GJ/OJ retain
  all4209/1381 trips and567/268 fallbacks. Canonical positions and routing bytes
  are identical; no layout churn. All polygon points remain inside old clearance.
- Costs / risks: structural quads GJ3679->4781, OJ1536->1903; extra mesh/storage
  remains despite unchanged static cache behavior. The semantic demand overlay
  still uses rectangular widths and may overlie narrower structural pavement.
  Continuity claims apply to structural surfaces only.
- Spec alignment: PASS under ADR-020, technical8, FR-011/012, AC-002/006/011/014.
  No public schema/ID/evidence changes, external service or default promotion.
  Next: shared layer envelope, then broader block/parcel readability.
- Commit / push: one atomic work unit on experiment/street-grid; normal upstream
  push after closing checks. No private fixture artifacts or IDE caches staged.

## Checkpoint 2026-10-18 — shared structural and dependency pavement

- Implemented: a renderer-only intersection envelope, clipped paint and no
  double shoulders/junction slabs. Every original centerline interval remains;
  unchanged canonical scene/UCG/routing verified on GJ/OJ. Grade and measured
  physical width range are now separately labeled in both inspectors.
- Fixtures: pinned GJ3d9b53f9dac9af1187ac9754cb3066b27e43b766,
  OJb163acd2b5fe41edfc1e7fc7d367362851241896; catalog0.4.0. Fresh maintained
  spring-positive/structural-showcase at parentffbe40a plus this work unit.
- Commands: `python ../artifacts/visual/shared_street_review.py shared-street-r2`;
  `python -m metropogits build --repo tests/fixtures/repositories/NAME --out OUT`
  to shared-street-fixtures/{spring,unknown}; `python -m scripts.street_grid
  BUILD --street-grid --aligned-blocks --out OUT` to spring-r2/unknown-r2 there.
  Repeated polygons, source bytes and full per-segment length/clearance checked.
- Actual visuals: `node ../artifacts/visual/parcel_focus_review.mjs shared-street-r2
  shared-street-focus-r2`. Inspected gj-after/focused.png and oj-after/showcase.png.
  Same cameras asserted; interrupted road-edge strips reduced, but large empty
  parcels, repeated labels and district outlines remain. No grand city-completion
  claim. Shared envelope introduces9209/2632 polygons, not additional relations.
- Browser: `node scripts/viewer_audit.mjs CHROME OUT INPUT...` on GJ/OJ after
  -> shared-street-audit-r2; Chrome152.0.7977.84 at
  C:/Program Files/Google/Chrome/Application/chrome.exe, SwiftShader. Three LODs,
  pan/orbit, filter, route inspection and Synthetic pass; static rebuilds0.
  GJ Synthetic CPU p95=1.2-1.5ms, OJ1.5-1.9ms; not GPU FPS or a speedup claim.
  `street_diagnostics_ui.mjs` on fresh spring-r2/unknown-r2 after directories
  -> shared-street-canvas-r2 verifies real WebGL and forced Canvas, exact fallback
  selection and empty unknown state without exceptions. Fresh WebGL/SVG also
  captured through junction_smoke.mjs shared-street-fixtures.
- Regression:462 Python tests,461 pass/1 existing Windows symlink skip;
  seven Node suites45 pass; Ruff/diff checks. Tests cover complete interval
  preservation, cap/clearance, non-overlapping crossings, legacy modes, source
  metadata, paint clipping, filter-safe membership and Synthetic endpoints.
- Spec alignment: PASS ADR-020/FR-011/012/AC-002/006/011/014. No schema, stable
  ID, grade, route, assignment or source changes. No target code execution.
- Next: default city view should not draw directory boundaries as additional
  roads. Preserve exact selection/overlay access rather than deleting structure.
- Commit/push: independently verified unit on experiment/street-grid; normal
  upstream push after stage review, no private artifacts or agent attribution.

## Checkpoint 2026-10-18 — city context without boundary-as-road clutter

- Implemented: optional aligned-experiment city context, neutral ground,
  major/selected-only directory context and reversible Structure overlay in
  WebGL and Canvas. Showcase omits decorative plot outlines. Detailed preview
  intentionally remains a structural diagram. No buildings or paths removed.
- Fixtures: GJ3d9b53f9dac9af1187ac9754cb3066b27e43b766,
  OJb163acd2b5fe41edfc1e7fc7d367362851241896; catalog0.4.0;
  maintained spring-positive and structural-showcase at parentc241550 plus
  this unit. No target repository code/dependency installation executed.
- Commands: `python ../artifacts/visual/shared_street_review.py urban-street-r1`;
  `python -m metropogits build --repo tests/fixtures/repositories/NAME --out OUT`
  to urban-street-fixtures/{spring,unknown}; `python -m scripts.street_grid
  BUILD --street-grid --aligned-blocks --out OUT` to their -study directories.
  Large canonical scene/UCG/routing equality and full path coverage checked.
- Actual output: `node ../artifacts/visual/parcel_focus_review.mjs urban-street-r1
  urban-street-focus-r1`; `node ../artifacts/visual/city_context_review.mjs
  ../artifacts/visual/urban-context-focus-r1 INPUT...` for GJ/OJ after directories;
  `node ../artifacts/visual/junction_smoke.mjs urban-street-fixtures` for small
  WebGL/SVG. Inspected Portal city/structure and Canvas captures, Ops focus,
  OJ showcase, unknown WebGL/preview. All are actual renderer output.
- Visual findings: Portal labels22->1, line vertices3300->568; OJ29->2 and
  874->196 at identical cameras. Counts of buildings, aggregates, districts,
  networks and camera state remain equal through both toggle transitions.
  Restoring city mode restores exact geometry counts. Less false road/label
  clutter; repeated gray towers, empty parcels and regular grid still visible.
  Unknown fixture retains3 generic buildings and0 source relationships.
- Browser: `node scripts/viewer_audit.mjs CHROME
  ../artifacts/visual/urban-street-audit-r1 INPUT...` on both after directories.
  CHROME=C:/Program Files/Google/Chrome/Application/chrome.exe,
  152.0.7977.84/SwiftShader. All three LODs, navigation, filtering, exact route
  inspection and Synthetic pass; static rebuilds0. CPU Synthetic p95 GJ1.1-2.8ms,
  OJ1.1-1.3ms. These are submission timings, not GPU FPS or a speedup claim.
  Separate real forced-Canvas toggle checks pass without browser exceptions.
- Regression: `python -m unittest discover -s tests -q`:463 run,462 pass,
  1 existing Windows symlink skip; seven Node suites46 pass; Ruff and diff
  checks pass. Optional controls, deterministic packaging, source immutability
  and visibility policy tested. Every GJ/OJ4209/1381 original trip retained;
  assignment/fallback counts3642/567 and1113/268 unchanged. No layout churn.
- Spec alignment: PASS ADR-020, technical8, FR-011/012 and AC-002/006/011/014.
  Renderer-only presentation; no schema, IDs, evidence/security or default-mode
  changes. Next: remaining parcel/skyline readability, not more per-trip tuning.
- Commit/push: preceding pavement unitc241550 pushed normally to
  origin/experiment/street-grid. This independently verified context unit is
  committed/pushed on the same experimental branch after closing stage checks;
  no private artifacts, IDE caches or agent attribution included.

## Checkpoint 2026-10-18 — shared curved street presentation

- Implemented: opt-in --curved-streets on aligned structural streets. Geography
  determines56 GJ and25 OJ clearance-certified degree-two bend supports; branches
  are not replaced with rotaries. Shared pavement, paint, picking, exact-path
  highlight and Synthetic follow the same quadratic map. Public City/UCG and
  original semantic route records remain unchanged. Approach widths are labeled
  separately from the curved cross-section. Default/straight modes remain.
- Fixtures/revisions: GJ3d9b53f9dac9af1187ac9754cb3066b27e43b766,
  OJb163acd2b5fe41edfc1e7fc7d367362851241896, catalog0.4.0; maintained
  spring-positive and structural-showcase on parent0a6c2b4 plus this unit.
- Commands: `python ../artifacts/visual/curve_street_review.py curved-streets-r5`;
  `python -m metropogits build --repo tests/fixtures/repositories/NAME --out OUT`
  -> curved-street-fixtures/{spring,unknown}; `python -m scripts.street_grid
  BUILD --street-grid --aligned-blocks --curved-streets --out OUT`
  -> curved-street-fixtures-r5/{spring,unknown}-study. Targets are read-only;
  no target code/build/dependency installation was run.
- Actual artifacts: curved-streets-r5/{gj,oj}/{before,after}; same-camera gallery
  `artifacts/visual/curved-streets-focus-r7/index.html` from
  `node ../artifacts/visual/curve_focus_review.mjs curved-streets-r5
  curved-streets-focus-r7`. Reviewed GJ/OJ local bend captures and actual OJ
  showcase SVG capture. Unknown WebGL and OJ forced-Canvas also inspected.
- Visual fixes: r1 exposed an outside-corner gap; r3 revealed the added joint
  was backface-culled; r4's square joint produced a spike. r5 uses upward-facing
  round joins inside certified empty supports. Added a winding/support regression
  test. Rounded connections are visible locally, but minor width bulges, empty
  land, orthogonal internal grids and whole staircase chains remain. No claim
  that the skyline/thumbnail is radically transformed. Roundabouts remain0.
  An early review helper captured a missing showcase path; fixed it to capture
  the real artifact, not the viewer-only audit copy. Missing-file capture rejected.
- Geometry: `python ../artifacts/visual/curve_geometry_audit.py curved-streets-r5`
  recomputes identical presentation and checks all rendered triangles, upward
  winding and positive-area building overlaps. GJ28239/OJ9950 total structural+
  demand quads,91884/38410 broad-phase building checks,0 overlaps. Full route
  endpoints, direction and segment continuity checked for all4209/1381 trips.
  Assignment3642/567 and1113/268 unchanged. Sampled trip length sums
  762890->762620.5773 and174351->174342.1762; these are visual lengths, not runtime
  throughput.209 GJ trips grow slightly (maximum0.4295 units) while totals shrink;
  checked against freshly derived original whole-trip allowances:0 violations.
- Browser: `node scripts/viewer_audit.mjs CHROME
  ../artifacts/visual/curved-streets-audit-r5 INPUT...` on both after directories;
  Chrome152.0.7977.84/SwiftShader at
  C:/Program Files/Google/Chrome/Application/chrome.exe. Three LODs, navigation,
  filters, exact-route inspection and Synthetic pass. Static rebuilds0;
  Synthetic CPU p95 GJ1.2-1.7ms/OJ1.1-1.5ms, not GPU FPS. GJ first submission
  1192.6ms/OJ443.2ms; more tessellation is a real cost, not a performance win.
  The focus-r7 harness also clicks actual curved road hit regions and selects
  one contributing route on both cities. All-routes was disabled for exact-only
  assertions; keeping it enabled deliberately retains context, not a product bug.
- Fallbacks: `city_context_review.mjs` -> curved-streets-canvas-r5 verifies
  WebGL/forced Canvas and reversible overlay with unchanged counts/cameras.
  `junction_smoke.mjs curved-street-fixtures-r5` captures fresh small WebGL/SVG;
  `street_diagnostics_ui.mjs` -> curved-street-fixtures-ui-r5 checks exact Spring
  fallback and empty unknown states in both renderers without exceptions.
- Tests: full Python discovery471 run,470 pass/1 existing Windows symlink skip;
  seven Node suites47 pass; Ruff/diff checks pass. Targeted eight curve tests
  re-run after adding pre-allocation sampling caps. Tests cover determinism,
  source immutability, support clearance, branch exclusion, C1 centerline tangent,
  winding, limits, repeated real packaging/SVG and forward/reverse Synthetic.
- Spec alignment: PASS user-approved ADR-020 extension, technical7/8,
  FR-007/011/012 and AC-002/003/006/011/014. No schema/identity/security change,
  no invented relationships, no default promotion. Next: coherent whole-corridor
  staircase replacement and separately certified entry/exit junction geometry.
- Commit/push: one verified curved-street work unit on experiment/street-grid;
  normal upstream push after staged diff/identity review. Private artifacts and
  unrelated IDE caches excluded; no agent attribution.

## Checkpoint 2026-10-18 — cross-repository benchmark

- Implemented: repeatable local benchmark using the real build pipeline, per-language
  adapter/structural coverage, edge type/confidence and unresolved diagnostics,
  profiled stages, unprofiled repeat timing, all-artifact hashes and position checks.
  Optional aligned curved street artifacts are also regenerated twice. No source
  builds, dependency installs or runtime language-support expansion.
- Fixtures/revisions: all seven locally supplied clones pinned in
  CROSS_REPOSITORY_BENCHMARK.md; tracked trees clean. Actual base and street
  artifacts under `artifacts/visual/cross-repository-r2/NAME/{first,repeat,streets}`.
  Full commands and limitations are in that document. All seven repeat identically.
- Browser: `node scripts/viewer_audit.mjs CHROME
  ../artifacts/visual/cross-repository-audit-r7 INPUT...` using all seven streets
  directories. Chrome/SwiftShader,1280x800,DPR1; three explicit LODs, natural-default
  capture, exact common-distance comparison, navigation, JS heap and draw-call
  observations. Actual source-edge drilldown succeeds on Realworld/PocketBase;
  zero-network cases correctly disable Synthetic. Active Synthetic static rebuilds0.
  Measurements are CPU submission and JS heap, NOT GPU FPS or process memory.
- Artifacts inspected: Realworld default and forced Overview, Bat Overview,
  PocketBase Overview/showcase, Lazygit default, SQLite Browser default,
  FastAPI showcase. Cities differ geometrically but remain generic/repetitive.
  Small-city forced aggregates can clip; default Realworld uses Detail correctly.
  No claim of large visual improvement from this measurement tool.
- Audit corrections: replaced large-city-only natural-LOD assumptions with explicit
  comparison LODs; sparse roads can be inspected at a higher local camera angle;
  keyboard guard tests focus enabled controls; zero-network/zero-visible-trajectory
  animation is explicitly not applicable. Existing movement/cache failures still
  block where activity is actually present. Default camera captures stay unmodified.
- Tests: Python475 run,474 pass/1 existing Windows symlink skip; Node48 pass;
  Ruff passed. Fresh spring-positive and structural-showcase builds generated in
  cross-repository-fixtures. The initial supplementary browser regression hit an
  audit assumption about animated paths at forced Overview; recorded/fixed.
  cross-repository-regression-r2 passes GJ plus both maintained fixtures, including
  Spring District/Detail animation and exact-route inspection; generic traffic N/A.
- Findings: Go/Rust/Python/C++ remain structural-only; samples/assets can account
  for JS/Java coverage. Qt `.ts` translation files are incorrectly classified as
  TypeScript in the baseline; prioritized scanner correction next. No universal
  semantic-support or resolution-accuracy claim. Pipeline COMPLETE != L4 coverage.
- Spec alignment: PASS for benchmark/AC-001/002/007/012/014. Public UCG/City,
  source evidence, layout and security defaults unchanged by this tooling unit.
- Commit/push: benchmark tooling/checkpoint committed separately on
  experiment/street-grid; only tracked tool/tests/docs, never corpus/artifacts or
  unrelated IDE caches. Ordinary upstream push after verification.

## Checkpoint 2026-10-18 — Qt translation content-type correction

- Implemented: bounded `.ts` XML/Qt-header discrimination; retain generic FILE
  identities and buildings as language xml, with INFO provenance for the format
  correction. No XML/DTD/entity resolution, target execution or dependency install.
  TypeScript strings/comments/type assertions and TSX remain negative fixtures.
- Fixture/revision: sqlitebrowser ae32df153a64d250de7c77a5057deeff4092a39b;
  new positive/negative scanner and analyzer integration tests; parent660c0e1.
- Commands: `python -m scripts.repository_benchmark --repo
  ../visual_test_proj/sqlitebrowser --out
  ../artifacts/visual/cross-repository-qt-r1 --streets`; browser audit with CHROME,
  output cross-repository-qt-audit-r1 and corrected sqlitebrowser/streets input.
  Full corpus reanalysis compared canonical UCG hashes to cross-repository-r2.
- Results:27 XML documents correctly retained, false adapter count24->0;
 506 buildings/27 districts unchanged in ID, position, size and archetype.
 27 language-derived styleVariant values change to xml; scene ucgDigest changes.
  Zero dependencies remain zero. Structural street routing digest unchanged.
  All base/curved artifacts repeat byte-identically. Other six graph hashes match.
- Actual artifacts inspected: corrected default WebGL capture; same skyline,
  no invented traffic. Three explicit LODs, navigation, preview/showcase captures
  complete without browser exceptions. Synthetic N/A because networks0, not a
  moving-traffic success claim. Updated seven-case gallery is
  cross-repository-reviewed-r1/index.html; historical baseline remains intact.
- Tests: full Python478 run,477 pass/1 existing Windows symlink skip; Node48 pass;
  Ruff and diff checks pass. Small maintained Spring/unknown E2E and large GJ
  browser regression were verified in the preceding checkpoint; full unit suite
  rerun after scanner change. No failing tests suppressed.
- Spec alignment: PASS FR-001/002/003/010/015, AC-001/002/012/014. Existing string
  language contract, stable IDs and canonical layout unchanged. No framework-role
  inference from filenames or new semantic adapter. Bounded sniff limitation
  explicitly documented; headers beyond the window remain unrecognized.
- Open work: oversized forced-Overview aggregates, coherent whole-staircase
  corridor reconstruction, separately certified roundabouts, and language support.
  These are not delivered by this benchmark/bug-fix milestone.
- Commits:660c0e1 benchmark tooling already pushed; Qt fix gets its own conventional
  commit and ordinary upstream push on experiment/street-grid after staged review.
  Private corpus/artifacts and unrelated IDE caches are not staged.

## Checkpoint 2026-10-18 — rejected whole-corridor spike
- Implemented experimentally: common cubic strip deformation, shared CPU/JS
  paint/path map and an opt-in prototype flag. Removed all prototype source,
  flag and tests after actual surface rendering failed the visual gate. Existing
  local bend implementation remains unchanged; no new public/derived contract.
- Inputs: archived GJ/OJ urban-street-r1 scenes and PocketBase cross-repository-r2
  (6f370ea741f33adf889eef02e3c1b884a47aa522); maintained spring-positive fresh build.
- Commands: `python ../artifacts/visual/corridor_review.py corridor-curves-r1`;
  `python ../artifacts/visual/corridor_geometry.py corridor-curves-r1`;
  `node ../artifacts/visual/corridor_focus.mjs corridor-curves-r1 corridor-curves-focus-r1`.
  Fresh E2E: `python -m metropogits build --repo tests/fixtures/repositories/spring-positive
  --out ../artifacts/visual/corridor-e2e-r1/build`, followed by prototype street_grid.
- Actual images inspected: corridor-curves-focus-r1/{before,after}/focus.png.
  The sole accepted PocketBase corridor smoothed its centerline but deformed
  adjacent road surfaces into visible pinches/bulges. Visual gate: FAIL.
  GJ0/4 and OJ0/12 accepted; no citywide improvement claimed.
- Geometry: all canonical graphs/scenes and logical paths unchanged, repeated
  packages identical;28239/9950/13939 polygons checked for GJ/OJ/PocketBase,
  zero building collisions or backfaces. These checks did NOT detect ugliness.
- Prototype validation: Python486 run/485 pass/1 existing Windows symlink skip,
  Node49 pass, Ruff pass; fresh Spring browser three-LOD Synthetic static rebuilds0.
  Prototype-only tests were removed together with the rejected implementation,
  not weakened to approve it. Product baseline tests rerun in the next checkpoint.
- Spec alignment: semantic invariants PASS; visual quality FAIL, so not Done.
  Archive artifacts remain private and clearly described here as rejected.
- Next action: repair cross-repository Overview proportions/framing; future full
  corridor reconstruction must preserve street surfaces and junction mouths.
- Commit: documentation-only record of rejected experiment, separate from the
  subsequent viewer correction; normal feature-branch push at verified checkpoint.

## Checkpoint 2026-10-18 — source-bounded Overview and all-LOD framing
- Implemented: CPU/shared browser ordinary aggregate heights use the constituent
  scene height envelope, not file count. WebGL frames file and aggregate roofs
  together regardless of population. Evidence-backed role facilities, their
  membership, explicit expansion, paths and source records remain unchanged.
- Fixtures/revisions: seven pinned corpus inputs from CROSS_REPOSITORY_BENCHMARK,
  using corrected cross-repository-qt-r1 SQLite; GJ/OJ urban-street-r1 canonical
  snapshots; maintained spring-positive fixture at770689b rebuilt from source.
  Nine large/corpus inputs were repackaged, not freshly rescanned this checkpoint.
- Commands: `python ../artifacts/visual/overview_review.py overview-proportions-r1`
  (nine packages twice, exact canonical scene/UCG/routing equality assertions);
  `node ../artifacts/visual/overview_gallery.mjs` (old/new membership comparison).
  `python -m metropogits build --repo tests/fixtures/repositories/spring-positive
  --out ../artifacts/visual/overview-e2e-r1/build`;
  `python -m scripts.street_grid ../artifacts/visual/overview-e2e-r1/build
  --street-grid --aligned-blocks --curved-streets
  --out ../artifacts/visual/overview-e2e-r1/streets`.
- Actual browser: `node scripts/viewer_audit.mjs
  'C:/Program Files/Google/Chrome/Application/chrome.exe' OUTPUT INPUTS...`:
  overview-small-audit-r1 takes overview-proportions-r1/{realworld,bat};
  overview-corpus-audit-r1 takes {pocketbase,fastapi-realworld-example-app,ratatui,
  lazygit,sqlitebrowser} plus overview-e2e-r1/streets/after;
  overview-gamja-audit-r1 takes overview-proportions-r1/{gj,oj}.
  All paths are under ../artifacts/visual. Reports retain exact expanded inputs,
  browser/environment, asset hashes, natural/forced LOD and timing definitions.
  `node ../artifacts/visual/city_context_review.mjs
  ../artifacts/visual/overview-fallback-r1
  ../artifacts/visual/overview-proportions-r1/realworld
  ../artifacts/visual/overview-proportions-r1/gj` exercises WebGL/forced Canvas.
- Artifacts inspected: old/new RealWorld Overview actual WebGL images, new GJ
  Overview, Ratatui rendered showcase, RealWorld forced Canvas capture. Gallery:
  overview-proportions-reviewed-r1/index.html. RealWorld roof clipping corrected;
  ordinary masses no longer inflate small scenes. GJ role landmarks stand above
  lower generic masses. Flat repeated generic forms and empty plots remain.
  Comparison cameras use each version's fit; no identical-camera claim.
- Quantitative findings: maximum ordinary height25.63->10 RealWorld,
  37.44->10 PocketBase,38.86->18 GJ,37.26->18 OJ. All nine memberships and original
  graph/scene/routing unchanged, repeated package bytes equal. No layout migration.
- Tests: `python -m unittest discover -s tests -q`:478 run/477 pass/1 existing
  Windows symlink skip. `node --test tests/camera_framing.test.mjs
  tests/access_routes.test.mjs tests/junction_geometry.test.mjs tests/road_paint.test.mjs
  tests/viewer_audit.test.mjs tests/camera_navigation.test.mjs
  tests/role_landmarks.test.mjs`:50 pass. Ruff and git diff --check pass.
  CPU/JS projection parity, golden fixtures and deterministic outputs pass without
  changing golden hashes. No tests weakened. Actual browser three-LOD Synthetic
  static rebuilds0 wherever evidenced animation applies; zero-network cases N/A.
  Road selection/exact-route inspection, navigation and Canvas toggle restore pass.
- Spec alignment: PASS technical rendering/LOD and T-01/02/03/05/06/07/08;
  functional structural baseline/repeatability/unknown-tech fallback and product
  evidence-first principles. No runtime dependency, public schema, stable ID or
  semantic classification change. No claim that generic output proves Go/Rust support.
- Open risks/next actions: full-width corridor/junction reconstruction remains
  pending; rejected displacement prototype is not shipped. Improving skyline
  variety must use source-backed roles/metrics, not reintroduce file-count towers.
- Commits:00a2ce6 records the rejected spike separately; this verified viewer fix
  receives its own conventional commit. Push both normally to the existing
  experiment/street-grid upstream after staged review; no main merge/default promotion.

## Checkpoint 2026-10-19 — non-orthogonal structural street reconstruction

- Implemented: ADR-021 and opt-in `--diagonal-streets`. Split geometric crossings
  and overlaps, protect doors/branches/trip endpoints, replace eligible branch-free
  detours with shorter diagonal chords. Certify full-width tapered pavement and
  junction mouths against buildings and other roads. Preserve unrelated geometry;
  bounded fallback widths do not bypass collision checks. No public schema change.
- Fixtures/revisions: SQLite Browser ae32df153a64d250de7c77a5057deeff4092a39b,
  PocketBase 6f370ea741f33adf889eef02e3c1b884a47aa522 (cross-repository snapshots);
  GJ local-sha256-06eb492d57141c16 and OJ local-sha256-c2e80f9d3908fec8 from
  urban-street-r1. These four snapshots were repackaged, not rescanned. Maintained
  spring-positive at parent134ecee was freshly built through the real CLI.
- Commands (all artifact paths under ../artifacts/visual):
  `python ../artifacts/visual/diagonal_review.py diagonal-streets-r2` packages
  before/after twice and checks canonical identity, new surface clearance/winding;
  `node ../artifacts/visual/diagonal_paths.mjs diagonal-streets-r2` checks all trips;
  `python ../artifacts/visual/diagonal_verify.py` verifies final resource-limit
  changes retain exact plans and viewer-data bytes for all four cases.
  `python -m metropogits build --repo tests/fixtures/repositories/spring-positive
  --out ../artifacts/visual/diagonal-e2e-r2/build`;
  `python -m scripts.street_grid ../artifacts/visual/diagonal-e2e-r2/build
  --street-grid --aligned-blocks --diagonal-streets
  --out ../artifacts/visual/diagonal-e2e-r2/streets`.
- Actual browser commands: `node ../artifacts/visual/diagonal_focus.mjs
  diagonal-streets-r2 diagonal-focus-r2` captures four identical-camera pairs.
  `node scripts/viewer_audit.mjs 'C:/Program Files/Google/Chrome/Application/chrome.exe'
  ../artifacts/visual/diagonal-browser-r2` with diagonal-streets-r2/{sqlitebrowser,
  pocketbase,gj,oj}/after as four positional inputs; the same command with output
  diagonal-small-audit-r2 and input diagonal-e2e-r2/streets/after checks the fresh
  fixture. `node ../artifacts/visual/city_context_review.mjs
  ../artifacts/visual/diagonal-fallback-r2` with diagonal-streets-r2/{sqlitebrowser,
  gj}/after exercises WebGL/forced Canvas and reversible structure toggling.
- Artifacts inspected: SQLite before/after focus images, SQLite rendered showcase
  and forced Canvas; PocketBase after focus, GJ after focus/Overview, OJ rendered
  showcase. `diagonal-focus-r2/index.html` links actual viewers and same-camera
  captures. SQLite's large exterior staircase becomes a direct diagonal;
  PocketBase shows an oblique three-way approach. Buildings, labels and framing
  remain unchanged. Broad voids, parallel connectors and inner grids still exist.
- Quantitative outcome: accepted4/45 SQLite,14/86 PocketBase,18/75 GJ,8/54 OJ.
  Replaced-chain lengths259→196.89,416.5→301.40,591.5→456.36,353.5→275.90.
  These are local chain totals, not entire-city percentages. Newly emitted
  polygons60/198/312/123: building intersections0, reversed faces0. Exact repeated
  package bytes and unchanged canonical City/UCG/logical routing in all four.
- Path fidelity: all5,782 trips have continuous mapped geometry, exact complete
  endpoints, original route/edge membership and no increased physical length.
  Only27 GJ trips use changed segments; other replacements in these snapshots
  are unassigned civic streets. SQLite networks0: Synthetic explicitly unavailable.
  Representative changed GJ link ManagedPreviewService→ManagedPreviewProperties
  retains RESOLVED REFERENCES evidence java.type-reference, source line52;
  original evidence ID792c9dda... and full canonical records unchanged.
- Tests: `python -m unittest discover -s tests -q`:487 run,486 pass,1 existing
  Windows symlink skip. `node --test tests/camera_framing.test.mjs
  tests/access_routes.test.mjs tests/junction_geometry.test.mjs tests/road_paint.test.mjs
  tests/viewer_audit.test.mjs tests/camera_navigation.test.mjs
  tests/role_landmarks.test.mjs`:52 pass. Ruff and git diff --check pass.
  Regression coverage includes protected interior doors, crossings, width-edge
  obstacles, unrelated streets, reversal/permutation, exact repeated packaging,
  width transitions, physical paint and forward/reverse Synthetic continuity.
  Browser three-LOD Synthetic static rebuilds0 where applicable; CPU draw submission
  metrics in reports are not GPU frame-rate claims. No failing tests weakened.
- Fixes applied/reverified: first chord prototype used the narrowest section for
  the entire road, producing hairline connectors in actual captures. Replaced it
  with certified width profiles and tapered mouths; regenerated r2 and reran
  geometry, trip, browser and fallback checks. New caps preserve r2 bytes exactly.
- Spec alignment: PASS under ADR-020/021 experiment; technical7/8 and T-01/02/03/
  05/06/07/08/09, functional AC-002/003/006/011, product DEC-005/007/008/011.
  Canonical geography is unchanged; no language-coverage claim, untrusted execution,
  new service dependency, fabricated semantic edge or default-mode promotion.
- Open risks/next actions: branch-free reconstruction does not solve dense internal
  orthogonal topology. Study bounded junction/connector reconfiguration with entry-
  exit tracing next; do not place decorative roundabouts over unmodified paths.
  Resource caps intentionally refuse excessive inputs instead of partial unsafe
  output. Existing experimental streets and fallback assignment limitations remain.
- Commit/push: one atomic feature unit with ADR, implementation, tests and this
  checkpoint; intended upstream origin/experiment/street-grid. Stage explicit paths,
  verify human identity/no agent attribution, then normal push. No main merge.

## Checkpoint 2026-10-19 — bounded oblique three-arm junctions

- Implemented: opt-in `--junction-streets` on the ADR-021 diagonal baseline.
  Reconstruct three arms and their central/outer mouth surfaces atomically, with
  fixed outer terminals, pinned doors, maximum 14-unit center movement, minimum
  35-degree approach separation, no arm length increase and at least 5% total
  local shortening. Full-width collision checks include buildings and retained
  roads. Overlapping proposals are reserved deterministically. Bounded resources;
  no broad displacement field, fabricated junction connectivity or public schema change.
- Fixtures/revisions: SQLite ae32df153a64d250de7c77a5057deeff4092a39b;
  PocketBase 6f370ea741f33adf889eef02e3c1b884a47aa522;
  GJ local-sha256-06eb492d57141c16; OJ local-sha256-c2e80f9d3908fec8.
  Four existing diagonal-streets-r2 snapshots repackaged, not freshly scanned.
  Maintained spring-positive at parent 6291e6a freshly scanned through real CLI.
- Commands (workspace-private helpers/output under ../artifacts/visual):
  `python ../artifacts/visual/junction_review.py oblique-junctions-r1`;
  `node ../artifacts/visual/diagonal_paths.mjs oblique-junctions-r1`;
  `python ../artifacts/visual/junction_verify.py` (final planner and serialization
  exactly match inspected packages after implementation optimization).
  `python -m metropogits build --repo tests/fixtures/repositories/spring-positive
  --out ../artifacts/visual/oblique-junction-e2e-r1/build`;
  `python -m scripts.street_grid ../artifacts/visual/oblique-junction-e2e-r1/build
  --street-grid --aligned-blocks --junction-streets
  --out ../artifacts/visual/oblique-junction-e2e-r1/streets`.
- Actual browser commands: `node ../artifacts/visual/diagonal_focus.mjs
  oblique-junctions-r1 oblique-junction-focus-r1 junction` produces four same-camera
  before/after pairs. `node scripts/viewer_audit.mjs
  'C:/Program Files/Google/Chrome/Application/chrome.exe'
  ../artifacts/visual/oblique-junction-audit-r1` with oblique-junctions-r1/
  {pocketbase,gj,oj}/after as three positional inputs; same audit with output
  oblique-junction-small-audit-r1 and inputs oblique-junctions-r1/sqlitebrowser/after
  and oblique-junction-e2e-r1/streets/after. `node
  ../artifacts/visual/city_context_review.mjs ../artifacts/visual/oblique-junction-fallback-r1`
  with ../artifacts/visual/oblique-junctions-r1/{sqlitebrowser,gj}/after inputs
  exercises actual WebGL, forced Canvas and reversible structure toggling.
- Artifacts inspected: SQLite/PocketBase/OJ before and after focus captures;
  GJ after focus and Overview; actual SVG showcase renders for SQLite/OJ and fresh
  spring preview; forced SQLite Canvas city capture. Gallery:
  `artifacts/visual/oblique-junction-focus-r1/index.html`. Oblique mouths and
  shortened approaches are visible locally, with no new building collision or
  lost junction seam observed. README/Overview silhouettes are essentially
  unchanged; generic repetitive towers, empty gaps and regular inner grids remain.
- Quantitative outcome: one junction per repository, from 18/55/16/16 position
  proposals (SQLite/PocketBase/GJ/OJ). Building rejection 14/49/15/12; remaining
  proposals are reserved or conflict with retained roads. Local arm totals
  66.50→51.00,67.24→60.69,129.50→122.73,61.80→54.52; NOT citywide percentages.
  SQLite/PocketBase/OJ centers move; GJ center stays fixed. Changed polygons
  29/32/37/27: building intersections 0, reversed faces 0. Repeated packages equal
  byte-for-byte, canonical graph/scene and original logical routing unchanged.
- Fidelity/performance: all 5,782 trips continuous, fixed complete endpoints,
  preserved source/target/edge membership and no physical length increase versus
  the previous diagonal baseline (floating-point tolerance 1e-6 world units).
  Six GJ paths change incrementally; other new junctions are civic-only.
  `python ../artifacts/visual/junction_evidence.py` traces one changed GJ trip:
  Frontend/portal/app/admin/docs/page.tsx → components/docs/admin-image-url.ts,
  RESOLVED IMPORTS, original edge b8f040e5... and evidence f5eb04d1... at line 13,
  plus tsconfig path evidence 77fd212a.... Local source import and @/* mapping
  inspected directly; original edge/evidence records are unchanged.
  Synthetic stays unavailable for SQLite's zero-network output. Browser three-LOD
  Synthetic static rebuilds 0 for applicable fixtures. CPU draw submission
  measurements in reports are not GPU FPS or cross-hardware performance claims.
- Tests: `node --test tests/*.test.mjs`: 53 pass. `python -m unittest discover
  -s tests -q`: 494 run,493 pass,1 existing Windows symlink skip. New seven-test
  junction suite also rerun after adding per-arm diagonal-baseline length assertions.
  Ruff and git diff --check pass. Tests cover protected doors, messaging exclusion,
  full-width obstacles, unrelated roads, ordering/reversal, already-straight stars,
  resource limits, incompatible modes, repeated packaging and exact trip pairing.
- Fixes applied/reverified: rejected early proposals whose central join touched an
  unrelated arm; outer-terminal collision exemptions now belong only to that arm.
  New JS endpoint test initially used exact floating-point equality on interpolation
  (residual ~2e-15); corrected to explicit 1e-8 geometric tolerance, then reran both
  Node and Python suites successfully. No connectivity or evidence assertion removed.
- Spec alignment: PASS under ADR-020/021 opt-in experiment; technical7/8 invariants,
  functional AC-002/003/006/011, product DEC-005/007/008/011. Canonical geography,
  provenance, deterministic unsupported-language fallback and local static output
  preserved. No target-repository execution, runtime service or semantic-coverage claim.
- Open risks/next actions: safe acceptance is sparse under fixed footprints;
  this is a local reconstruction capability, not completion of free-form urban
  topology. Study connector/parcel co-planning with explicit stability budgets
  before promising broader changes. No roundabouts, arbitrary multi-junction
  merging, default promotion or main integration in this unit.
- Commit/push: atomic feature unit includes ADR, implementation, tests and this
  checkpoint. Intended verified delivery to existing origin/experiment/street-grid,
  normal push after staged diff and human identity/attribution review. No main merge.

## Checkpoint 2026-10-19 — Street-facing buildings, Phase A (parent 81e13cc)
- Implemented: ADR-022 opt-in `--frontage-parcels`, including existing junction
  streets. Deterministic physical frontage selection, whole-archetype rotation,
  bounded in-owner translation candidates and exact preservation of existing
  civic/relationship doorways. Export derived `street-parcels/0.1` separately;
  no canonical City/UCG field or ID change. A non-semantic facade canopy marks
  the front. WebGL, Canvas, picking/selection and SVG use physical corners.
  Changed-footprint aggregates expand without losing/duplicating members;
  unchanged role compounds remain intact at all LODs.
- Fixtures/revisions: pinned oblique-junctions-r1 snapshots, GJ Cloud
  local-sha256-06eb492d57141c16 (1,324 files), GamjaOJ
  local-sha256-c2e80f9d3908fec8 (681), PocketBase
  6f370ea741f33adf889eef02e3c1b884a47aa522 (664), SQLite Browser
  ae32df153a64d250de7c77a5057deeff4092a39b (506, no evidenced networks).
  Maintained spring-positive at parent81e13cc freshly scanned through the CLI,
  producing local-sha256-645189cce01fc6ab. No target code/dependencies executed.
- Commands run from MetropoGits: `python -m unittest discover -s tests -q`;
  `node --test tests/*.test.mjs`; `python -m ruff check .`; `git diff --check`.
  Fresh E2E: `python -m metropogits build --repo tests/fixtures/repositories/spring-positive
  --out ../artifacts/visual/street-facing-e2e-r2/build`, then `python -m scripts.street_grid
  ../artifacts/visual/street-facing-e2e-r2/build --street-grid --aligned-blocks
  --frontage-parcels --out ../artifacts/visual/street-facing-e2e-r2/street`.
  Local private-snapshot helpers: `python ../artifacts/visual/orientation_review.py
  street-facing-r2` (repeat packages, full building/road collision and owner/door
  checks); `node ../artifacts/visual/diagonal_focus.mjs street-facing-r2
  street-facing-focus-r2 parcels` (same-camera Detail/Overview, all four).
  `node scripts/viewer_audit.mjs CHROME OUT INPUT...` with installed Google Chrome:
  street-facing-audit-r2 covers GJ/PocketBase/SQLite/fresh spring output;
  street-facing-oj-audit-r2 covers OJ. `node ../artifacts/visual/city_context_review.mjs
  ../artifacts/visual/street-facing-context-r2 ../artifacts/visual/street-facing-r2/gj/after`
  checks actual WebGL/forced Canvas and structure-toggle restoration.
- Artifacts: `artifacts/visual/street-facing-r2/{sqlitebrowser,pocketbase,gj,oj}/
  {before,after}`, `street-facing-focus-r2/index.html`, the audit directories above,
  and `street-facing-e2e-r2`. Detailed source-preservation evidence also checked
  in r1 with orientation_verify.py: GJ admin/docs/page.tsx -> admin-image-url.ts,
  RESOLVED IMPORTS edge b8f040e5..., IMPORT evidence f5eb04d1... at line13 and
  configured @/* path evidence77fd212a.... All graph/evidence records identical.
- Quantitative outcome: SQLite/PocketBase/GJ/OJ have 506/664/1,324/681 frontage
  models, of which 429/504/1,005/554 rotate by a nonzero quarter/half turn.
  **All four have zero non-cardinal rotations and zero moved buildings.** The
  existing square plots and pinned entrances prevent oblique relocation; this
  is not an empty-space or density improvement. Full-width road/building
  intersections0; owner escape0; all original doors stay on the perimeter.
  Canonical scene/graph and physical/logical routing are exactly unchanged.
  All5,782 trips retain IDs, endpoints, edge membership and physical geometry.
  Repeated packages match byte-for-byte; footprint area and source dimensions
  remain unchanged. Controlled geometry tests, not the real corpus, establish
  45-degree rotation/translation, rectangular footprint and setback behavior.
- Visual findings: same-camera GJ Detail shows warehouse roof bands and asymmetric
  building parts turned toward different adjacent streets. PocketBase/SQLite
  remain generic without invented roles; GJ/OJ semantic colors remain intact.
  Overview and README retain their existing compositions and aggregates, so the
  thumbnail improvement is small. Large empty gaps and regular block axes are
  still visible. Fresh spring default framing is usable; the audit's forced
  zoomed Detail can enter tall buildings and is not an automatic framing claim.
- Tests/determinism/stability: Python501 run,500 pass,1 existing Windows symlink
  skip; Node54 pass. Seven Python parcel tests cover arbitrary rotation,
  rectangular dimensions, low-height canopy bounds, concave owner clipping,
  protected doors, neighbor overlap, ordering/reversal, distant-addition
  stability, explicit work/index caps and repeated source-preserving packaging.
  New Node test proves partial filters/LODs cannot lose or double-represent files
  when only an affected aggregate is expanded. Full existing stability/golden,
  schema/security and integration suites pass. No tests weakened.
- Fixes applied/reverified: replaced initial all-street/all-building candidate
  comparisons with bounded spatial queries; explicit ranking/index limits fail
  closed. Kept canopy inside original footprint/height. Sorted physical part
  faces together in Canvas/SVG so a rear low canopy cannot simply paint on top
  of the whole front building; regenerated r2 packages/captures after this fix.
  Actual Synthetic audits report0 static geometry rebuilds in all tested LODs;
  SQLite animation remains unavailable without evidenced networks. CPU submission
  timing is not GPU FPS or a cross-machine performance guarantee.
- Spec alignment: PASS under user-approved ADR-022 experiment, building on
  ADR-020/021. Rechecked technical7/8, functional AC-002/003/006/011 and product
  DEC-005/007/008/011. Stable canonical geography, evidence fidelity, local static
  output and unsupported-language fallback preserved. No default promotion,
  untrusted code execution, new runtime service or main merge.
- Open risks/next actions: PhaseB must co-plan block-local parcels and entrances
  to obtain actual oblique placements and better use of space. Do not sell
  cardinal model rotation as that result, shrink buildings to force fits or
  disable collision/door checks. PhaseC corner lots and role-aware hierarchy
  bias follow coordinated parcel work. Arbitrary-angle visual geometry is only
  covered by controlled fixtures here, not accepted real-corpus placements.
- Commit/push: one atomic feature unit with ADR, implementation, regression
  tests and this checkpoint. Verified delivery targets the existing upstream
  origin/experiment/street-grid after final staged review; no main integration.

## Checkpoint 2026-10-19 — coordinated leaf blocks and occupied ground
- Implemented: ADR-023 opt-in `--local-blocks`, whole-group rotation with a fixed
  outer owner boundary and continuous road/paint/trip mapping. Tight derived
  ground supports and LOD mass-sized plinths replace broad normal-view floors.
  Full territory remains available through Structure overlay. This is a bounded
  pilot, not completed block-local subdivision or physical city compaction.
- Fixtures/revisions: reused street-facing-r2 canonical snapshots: GJ
  local-sha256-06eb492d57141c16 (1,324 files), OJ local-sha256-c2e80f9d3908fec8
  (681), PocketBase 6f370ea741f33adf889eef02e3c1b884a47aa522 (664), SQLite Browser
  ae32df153a64d250de7c77a5057deeff4092a39b (506). Fresh maintained spring-positive
  fixture scanned through the real CLI. No clone code or build script executed.
- Commands from MetropoGits: `python -m unittest discover -s tests -q`;
  `node --test tests/*.test.mjs`; `python -m ruff check .`; `git diff --check`.
  `python -m metropogits build --repo tests/fixtures/repositories/spring-positive
  --out ../artifacts/visual/local-blocks-e2e-r1/build`, followed by
  `python -m scripts.street_grid ../artifacts/visual/local-blocks-e2e-r1/build
  --street-grid --aligned-blocks --local-blocks
  --out ../artifacts/visual/local-blocks-e2e-r1/street`.
  Private-snapshot repeat/package helper: `python ../artifacts/visual/local_blocks_review.py
  local-blocks-r3`; full spatial audit: `python ../artifacts/visual/local_blocks_geometry.py
  local-blocks-r3`; comparison: `node ../artifacts/visual/diagonal_focus.mjs
  local-blocks-r3 local-blocks-focus-r3 blocks`.
- Artifacts inspected: `local-blocks-focus-r3/index.html`, GJ same-camera
  before/after Detail and sparse-ground captures; OJ/SQLite Overview;
  `local-blocks-audit-r3/case-{1,3}/showcase.png`, GJ forced-Canvas capture in
  `local-blocks-context-r3/canvas-0/city.png`. Actual WebGL audit via
  `node scripts/viewer_audit.mjs CHROME OUT INPUT...` covers GJ/PocketBase/SQLite/
  fresh spring in local-blocks-audit-r3 and OJ in local-blocks-oj-audit-r3.
  `node ../artifacts/visual/city_context_review.mjs
  ../artifacts/visual/local-blocks-context-r3
  ../artifacts/visual/local-blocks-r3/gj/after
  ../artifacts/visual/local-blocks-r3/oj/after` verifies WebGL/forced Canvas,
  unchanged selection counts/camera and restored geometry after Structure toggle.
- Quantitative outcome: GJ accepts three small two-file groups (-45,-45,-3.81
  degrees); other three repositories accept none. Eight GJ physical route
  segments change, used by48 trips. All5,782 logical trips preserve endpoints by
  identity, evidence and continuity; physical door coordinates may move with their
  blocks. Representative preserved RESOLVED REFERENCES edge9c0ea7a9... remains
  DeploymentEditedComposeTest.java -> DeploymentController.java with original
  evidence3639afeb.... Canonical graphs/scenes remain exactly unchanged.
- Ground metrics: individual occupied-pad area upper bounds are39,799/51,101/
  99,475/52,065 versus allocated root areas62,328/118,286/265,678/98,980 for
  SQLite/PocketBase/GJ/OJ. These are world areas, not pixel coverage or a claim of
  whole-city reduction: pad sums may overlap and exclude aggregate plinths.
  Repeated packages are byte-identical. Geometry audit checks3,175 building
  envelopes against full physical streets/demand pavement: overlaps0, owner
  escapes0, uncovered buildings0; all moved doors remain on building perimeters.
- Visual findings: oversized normal-view owner floors and aggregate platforms
  recede, while source colors and district labels remain recognizable. GJ small
  groups visibly rotate; the whole-city grid and inter-group distances largely
  remain. Vacant space is now dark in some sparse areas instead of filled by a
  slab. This does NOT solve packing or make the city universally more organic.
  Full owner geometry remains inspectable. No decorative fillers were introduced.
- Tests/determinism/stability: Python510 run,509 pass,1 existing Windows symlink
  skip; Node55 pass. New cases cover fixed-boundary positive triangulation,
  rigid interiors, continuous doors, envelope-vs-roof bounds, polygon area,
  reversed input order, unrelated distant owner stability, concave ground
  ownership, exact support membership, repeated packaging and explicit work
  limits. All existing schema/golden/security/stability tests pass. Synthetic
  audits in all three LODs report0 static geometry rebuilds. SQLite still has no
  invented traffic. CPU submission samples are not GPU FPS measurements.
- Fixes applied/reverified: r2 exposed a PocketBase owner escape because the
  inner cage used small roof meshes rather than the full footprint. Included
  full envelopes and doors; rejected that candidate and regenerated r3. Added
  regression coverage rather than weakening collision tolerances. Compact
  aggregate picking now uses the same smaller supports as drawing; supports
  never expand beyond the represented mass. Earlier r1/r2 are not the delivered
  milestone. Corrected an initial helper module path and test invocation.
- Spec alignment: PASS under user-approved ADR-023 experimental scope. Rechecked
  technical7/8, functional AC-002/003/006/011 and product DEC-007/008. No public
  schema, stable ID, semantic evidence, default mode or remote setting changed.
- Open risks/next actions: full parcel subdivision and genuine bounded local
  compaction remain. Whole-group rotation is intentionally narrow; do not claim
  general Phase B completion. Local affine road widths can vary; do not equate
  those variations with traffic demand. Complete long-range packing and corner
  lot handling need separate evidence and acceptance checks.
- Commits created/pushed: one atomic feature unit, reviewed and delivered to
  existing origin/experiment/street-grid; no main integration. Commit outcome is
  checked after staged review and push, not inferred from this log entry.

## Checkpoint 2026-10-19 — incremental performance implementation policy
- Implemented: recorded the user's performance and impact priorities in
  `URBAN_BLOCK_PLAN.md`: retain Python, measure the new engine through existing
  profiling, optimize observed large costs incrementally and avoid low-impact
  tuning loops. Native libraries/Rust remain measured future options.
- Evidence: inspected current definitions of `_pack_shape`, `_shortest_cell_path`,
  `consolidate_routes` and the existing cProfile benchmark. The supplied review
  identifies candidates, not measured bottleneck rankings.
- Validation: documentation diff/whitespace and referenced local paths checked.
  No runtime, schema, dependency, scene or generated output changed; no new
  benchmark, render or runtime test is claimed for this documentation-only unit.
- Spec alignment: existing evidence, deterministic output, resource bounds and
  compatibility requirements retained. World engine/contract choices require
  their own ADR before implementation.
- Next actions: apply this policy during the authorized world-generation work;
  do not start a separate optimization or rewrite from this note.
- Delivery: one documentation commit using the configured human identity;
  push result verified separately before reporting completion.

## Checkpoint 2026-10-19 — first connected procedural flat world
- Implemented: ADR-024 independent `metropogits.world`, isolated deterministic
  seed streams, capacity-guided polygon bisection, shared boundary topology,
  streets reserved before parcels, locally rotated complete building models and
  entrances, source-pair routing on shared infrastructure, bounded validation,
  browser adapter and CPU SVG from the same physical world. The opt-in developer
  command is `python -m scripts.procedural_world BUILD --namespace owner/project
  --out NEW_WORLD`; existing builds and public City/UCG contracts are unchanged.
- Fixtures/revisions: GJ local-sha256-06eb492d57141c16 (1,324 files), OJ
  local-sha256-c2e80f9d3908fec8 (681), PocketBase
  6f370ea741f33adf889eef02e3c1b884a47aa522 (664), SQLite Browser
  ae32df153a64d250de7c77a5057deeff4092a39b (506). Four-corpus inputs are the
  existing local-blocks-r3 canonical snapshots, not newly analyzed revisions.
  Fresh maintained spring-positive and a temporary unsupported Rust fixture also
  run through scanning, UCG and City before World generation. No target code,
  dependency installation or target build script is executed.
- Commands from MetropoGits: `python -m unittest discover -s tests -q`;
  `node --test tests/*.test.mjs`; `python -m ruff check .`; `git diff --check`;
  `python ../artifacts/visual/world_review.py world-flat-reviewed-r2`.
  Fresh pipeline: `python -m metropogits build --repo
  tests/fixtures/repositories/spring-positive --repo-id fixture/world-spring
  --out ../artifacts/visual/world-flat-e2e-r1/build`, followed by
  `python -m scripts.procedural_world ../artifacts/visual/world-flat-e2e-r1/build
  --out ../artifacts/visual/world-flat-e2e-r2/world --namespace fixture/world-spring`.
  Browser audits: `node scripts/viewer_audit.mjs CHROME OUT INPUT...`, using
  C:/Program Files/Google/Chrome/Application/chrome.exe, output
  ../artifacts/visual/world-flat-final-audit-r1 and the four before/after pairs
  under ../artifacts/visual/world-flat-reviewed-r2. The fresh Spring audit is
  ../artifacts/visual/world-flat-e2e-audit-r2. Forced Canvas and Structure toggle:
  `node ../artifacts/visual/city_context_review.mjs
  ../artifacts/visual/world-flat-context-r1
  ../artifacts/visual/world-flat-reviewed-r2/gj/after
  ../artifacts/visual/world-flat-reviewed-r2/oj/after`.
- Artifacts inspected: world-flat-reviewed-r2/index.html and report.json;
  all eight before/after Overview screenshots in world-flat-final-audit-r1;
  after showcase.png for cases 2/4/6/8; case-2/route-inspector.png;
  world-flat-context-r1/canvas-0/city.png. Browser audits additionally exercise
  three LODs, pointer picking, source/road inspectors, route choice, camera,
  filters, preview rendering and Synthetic activity. Eight corpus cases and the
  fresh maintained fixture complete without browser exceptions. These are real
  rendered artifacts, not mockups. Gallery images fit each complete city
  independently; common-scale captures exist separately, so apparent image size
  in the gallery is not a physical density measurement.
- Quantitative outcome: all 3,175 buildings have structurally reachable doors;
  5,782 complete local source-pair trips retain exact contributing graph edges.
  GJ/OJ/PocketBase/SQLite physical zones: 6/6/8/3; trips: 4209/1381/192/0;
  represented local edges: 6157/2243/192/0. Every other non-CONTAINS edge is
  explicitly partitioned into internal or nonlocal coverage, never discarded.
  Zero building collisions, full-width street collisions or owner escapes in
  all four corpora. Original City/UCG bytes and source building sizes, roles,
  IDs and evidence remain unchanged. Complete original directory hierarchies
  remain in logicalDistricts even when multiple directories share a physical zone.
- Area/capacity: new allocated areas are approximately 251306/138820/150427/97208
  versus original 265678/98980/118286/62328. Only GJ is smaller (about 5.4%);
  the other three grow to reserve frontage, circulation and capacity. Do not
  claim universal physical compaction. Capacity recovery increases only failed
  districts' budgets, not the entire city. PocketBase requires four repairs
  near the five-attempt bound; arbitrary inputs/seeds can fail explicitly.
- Tests/determinism/stability: Python 522 run, 521 pass, one existing Windows
  symlink skip; Node 56 pass; Ruff and whitespace checks pass. Full suites include
  existing schema/golden/security/layout cases. Two independent four-corpus
  generations produce byte-identical complete packages. New tests check source
  preservation, seed isolation, revision-independent geography, controlled
  nearby file addition with previous-world placement reuse, polygon topology,
  malformed hints, semantic endpoints, geometry rejection and resource caps.
  Incremental stability is conditional on compatible zone ownership/capacity;
  cold replanning is diagnosed, not promised stable. Synthetic audits report
  zero static geometry rebuilds; SQLite has no invented semantic traffic.
- Performance evidence: GJ unprofiled repeat generation/validation/packaging is
  approximately 5.65/0.89/4.54 seconds. Separately profiled cumulative GJ routing
  is 2.60 seconds, boundary partition 0.007, street atomization 0.20; profile
  times overlap and are not additive or directly comparable to normal timings.
  report.json and gj-world.prof retain the observations outside canonical output.
  These measurements start from existing UCG/City, not a full clone analysis.
  Browser CPU submission samples are not GPU FPS or a memory benchmark.
- Fixes applied/reverified: limited area recovery to deficient districts;
  canonicalized quantized oblique T connections; validated real clipped common
  polygon area instead of treating numerical SAT contact as an overlap; corrected
  model winding and added full-footprint/door/street checks. High-sharing browser
  auditing previously duplicated all path geometry for every selectable road,
  exhausting Chrome diagnostic payloads. Commit 20a829f returns complete choices
  for one requested road without that duplicated payload; regression tests and
  the complete large-corpus audit pass without weakening path checks.
- Visual findings: a connected polygon mainland replaces disconnected floor
  islands; local street axes and full building orientations are visible, with
  named service zones and retained role colors. Overview and CPU exports show
  the same placement. Long regular rows remain, generic-heavy corpora remain
  generic, and extra reserved land is visible. This is one locally rotated GRID
  profile, not Voronoi, organic streets, terrain or completed urban planning.
  New-world role compounds/semantic LOD are not integrated, so all original file
  buildings remain visible. The root-zone browser label can show a raw source
  ID; CPU labels use Root. Record that small polish task without hiding the
  larger planning/LOD limitations behind more isolated cosmetic iterations.
- Spec alignment: PASS within user-authorized ADR-024 experimental scope.
  Rechecked technical contracts/layout/rendering, functional deterministic
  output/source inspection/fallback acceptance, and product DEC-007/008.
  Existing default engine and normalized artifacts remain intact. Separate
  versioned world/0.1-experimental and world-view/0.1 are not City v0.2 documents.
  No new runtime dependency, AI/service requirement, unsafe execution or remote
  setting change. Structural streets are labeled visual infrastructure, not
  invented relationships; only source-backed trips carry semantic evidence.
- Open risks/next actions: integrate rotated role compounds/semantic LOD and
  distinct block planning profiles as visible vertical slices; evaluate
  capacity-efficient land allocation across unknown inputs. Terrain/hydrology,
  bridges/tunnels and weighted Voronoi remain subsequent work. GJ viewer-data
  is about 28 MB; track export size and actual measured costs before adding more
  world detail. Do not claim the whole procedural-world proposal complete.
- Commits created/pushed: ec13478 (world seed/ADR), 20a829f (bounded audit payload)
  and this atomic first-world feature/checkpoint. Current intended branch main;
  the user explicitly retains owner-authorized normal push delivery. Review
  staged paths/identity and confirm the push command result before reporting
  remote delivery. No force push, protection changes or agent attribution.

## Checkpoint 2026-10-19 — orbital streets and district planning
- Implemented: ADR-025 opt-in `--planning mixed|radial|grid`. RADIAL reserves
  clipped orbital streets, three to five spokes and shared boundary connections
  before allocating tangential frontage parcels. Whole building models and
  doors face their actual frontage. Mixed selection uses independent district
  seed streams, never framework/name guesses. Capacity shortage falls back to
  GRID locally and explicitly; forced radial retains bounded repair/failure.
  The existing GRID default and its physical world bytes remain unchanged.
- Fixtures/revisions: same four pinned world-flat-reviewed-r2 City/UCG inputs:
  GJ local-sha256-06eb492d57141c16, OJ local-sha256-c2e80f9d3908fec8, PocketBase
  6f370ea741f33adf889eef02e3c1b884a47aa522, SQLite Browser
  ae32df153a64d250de7c77a5057deeff4092a39b. No new clone revision is implied.
  Also freshly scanned maintained spring-positive plus temporary 40-file TS
  dependency-cycle and 25-file unsupported Rust fixtures; no target execution.
- Commands from MetropoGits: `python -m unittest discover -s tests -q`;
  `node --test tests/*.test.mjs`; `python -m ruff check .`; `git diff --check`;
  `python ../artifacts/visual/world_planning_review.py ignored --probe` then
  `python ../artifacts/visual/world_planning_review.py world-planning-r1`.
  Fresh end-to-end: `python -m metropogits build --repo
  tests/fixtures/repositories/spring-positive --repo-id fixture/world-planning-spring
  --out ../artifacts/visual/world-planning-e2e-r1/build`, followed by
  `python -m scripts.procedural_world ../artifacts/visual/world-planning-e2e-r1/build
  --namespace fixture/world-planning-spring --planning radial
  --out ../artifacts/visual/world-planning-e2e-r1/world` (6 buildings, 2 trips,
  4 represented edges, 60 physical segments, all reachable, no collisions).
- Browser commands: `node scripts/viewer_audit.mjs CHROME OUT INPUT...` against
  all eight world-planning-r1/{gj,oj,pocketbase,sqlitebrowser}/{before,after}
  outputs, writing world-planning-audit-r1; fresh Spring output separately in
  world-planning-e2e-audit-r1. CHROME is C:/Program Files/Google/Chrome/Application/chrome.exe.
  `node ../artifacts/visual/city_context_review.mjs
  ../artifacts/visual/world-planning-context-r1
  ../artifacts/visual/world-planning-r1/gj/after
  ../artifacts/visual/world-planning-r1/oj/after` exercises WebGL/forced Canvas
  plus Structure toggling without changed camera/counts or geometry drift.
- Artifacts inspected: world-planning-r1/index.html and report.json; all eight
  actual before/after Overview PNGs in world-planning-audit-r1; after CPU showcase
  PNGs cases 2/4/6/8; case-2/detail.png and route-inspector.png;
  world-planning-context-r1/canvas-0/city.png. Three LODs, camera controls,
  pointer picking, exact path inspector/edge IDs, filtering and Synthetic pass
  in the browser audit. All runs finish without browser exceptions; Synthetic
  makes zero static geometry rebuilds. SQLite has no invented semantic traffic.
- Visual findings: GJ Ops and Portal visibly change from parallel strips into
  connected orbital/spoke neighborhoods; building silhouettes rotate with each
  lot. Other districts retain their existing grid. PocketBase APIs gains an
  orbital pattern; OJ changes are smaller because only two small zones qualify.
  SQLite stays GRID; do not claim every repository improved visually. Rounded
  orbits are quantized straight polyline pieces, not Bezier road paint hiding
  an orthogonal underlying route. Some open centers and repeated rings remain;
  role compounds, semantic LOD and root-label polish remain open.
- Quantitative comparison: all 3,175 file buildings and 5,782 source-pair trips
  retained; exact edge membership and original City/UCG bytes unchanged. All
  buildings reachable, no building/full-width-road intersections, parcel overlap
  or owner escapes. GRID reproduces the prior world dictionaries exactly for
  all four corpora. Mixed and GRID use identical envelopes and district areas
  on these fixtures. Radial zones: GJ 2/6, OJ 2/6, PocketBase 1/8, SQLite 0/3.
  Final local capacity fallbacks: 2/2/4/1 respectively, explicitly diagnosed.
- Tests/determinism/stability: Python 529 run, 528 pass, one existing Windows
  symlink skip; Node 56 pass. New seven tests cover exact source-backed paths,
  non-cardinal frontage/whole model rotation, repeated schema/package bytes,
  compatible added-file hints, policy-change replanning, legacy defaults,
  local fallback, malformed profile hints, explicit infeasibility, unsupported
  language and resource bounds. Independent parcel containment/overlap rejection
  added and targeted suite rerun after that final negative assertion. Four-corpus
  mixed packages reproduce byte-for-byte. No tests or collision gates weakened.
- Performance: normal GJ/OJ/PocketBase/SQLite generation observed approximately
  6.53/2.34/1.04/0.33 seconds from existing analyzed artifacts, not full scan.
  GJ viewer-data grows from roughly 28 MB to 37.76 MB, physical street segments
  2735 -> 3757; WebGL city triangles 65616 -> 76676. More curved path vertices
  impose a real export cost. Separate command `python -m cProfile -o
  ../artifacts/visual/world-planning-r1/gj-planning.prof -m scripts.procedural_world
  ../artifacts/visual/world-flat-reviewed-r2/gj/after --namespace benchmark/gj-cloud
  --planning mixed --out ../artifacts/visual/world-planning-r1/profile-gj` reports
  cumulative radial_slots 0.81s (8 calls including repair/fallback candidates),
  route_world 4.19s, atomic_streets 0.22s and package_world 20.72s. Instrumented
  cumulative times overlap; do not add them or equate them to normal timings.
  Browser CPU submission timings are not GPU FPS. Prefer measured export/LOD
  improvements next over native rewrites or isolated curve micro-tuning.
- Fixes applied/reverified: prior profile decisions survive compatible hints;
  capacity overflow cannot silently switch planners while claiming reused
  geography. Reject unsupported prior profiles. Bound candidate count, road
  count, clearance work and spatial-index entries. Strengthened independent
  parcel checks; no visible buildings shrunk to fit. Corrected the initial
  non-package unittest module invocation to discovery; final suites pass.
- Spec alignment: PASS under approved World Phase B / ADR-025 additive scope.
  Technical contracts/network provenance/CPU parity, functional AC-002/003/006/
  011/012 and product DEC-004/005/007/008/009/011 rechecked. The experimental
  World schema accepts old and new generator/profile values; City/UCG schemas,
  evidence, source IDs, default builds and runtime dependencies are unchanged.
- Open risks/next actions: planning remains two grammars, not completed Phase B;
  small/skinny zones often use GRID fallback. Land use and central gaps are not
  universally solved. Integrate source-traceable role compounds/semantic LOD
  with rotated parcels and reduce measured export duplication before layering
  terrain detail. No new analyzer, terrain, water or communication inference.
- Commits created/pushed: one atomic world-planning feature, regression tests,
  ADR and checkpoint on current main. Verified normal delivery uses the user's
  standing owner exception; staged paths/identity and actual remote SHA are
  checked before reporting push. No force push or remote-rule change.

## Checkpoint 2026-10-19 — ORGANIC planning grammar
- Implemented: ADR-026 first unit, explicit `--planning organic`, meandering
  local streets and oblique collectors before tangential frontage allocation.
  Shared bounded frontage kernel checks all full-width roads/parcels. Old
  grid/radial/mixed generation stays unchanged; additive flat-planning/0.3 enum.
- Fixtures/revisions: same four pinned world-flat-reviewed-r2 inputs/revisions
  listed in the preceding checkpoint; newly scanned maintained spring-positive
  with repoId fixture/world-grammars, and controlled TS/unknown Rust additions.
- Commands: `python -m unittest discover -s tests -q`; `node --test tests/*.test.mjs`;
  `python -m ruff check .`; `git diff --check`; `python
  ../artifacts/visual/world_grammars_review.py organic world-organic-r1`.
  Fresh build: `python -m metropogits build --repo tests/fixtures/repositories/spring-positive
  --repo-id fixture/world-grammars --out ../artifacts/visual/world-grammars-e2e-r1/build`;
  then `python -m scripts.procedural_world BUILD --namespace fixture/world-grammars
  --planning organic --out ../artifacts/visual/world-grammars-e2e-r1/organic`.
  Actual BUILD above; browser `node scripts/viewer_audit.mjs CHROME
  ../artifacts/visual/world-organic-audit-r1 INPUT...` audits four generated
  corpus directories plus that maintained output; Chrome path as preceding log.
- Artifacts inspected: world-organic-r1/report.json/index.html; actual WebGL
  Overview cases 1/2/3/4 and GJ CPU showcase.png in world-organic-audit-r1.
  Findings: rows/collectors curve and buildings follow local frontage; still a
  strip-based organic grammar, not arbitrary irregular block subdivision.
  Contrast/labels and generic fallback remain usable; root-label issue remains.
- Tests/determinism/stability: Python 532 run/531 pass/one Windows symlink skip;
  Node 56 pass; lint passes. Three new tests cover real nonorthogonal trip graph,
  repeated packages/schema, nearby-file hint preservation and work limits.
  Four corpora repeat byte-identically, conserve all 3,175 buildings/5,782 trips,
  original UCG/City bytes, source ownership, zero road/building/parcel collisions
  and all reachable doors. Browser three-LOD selection/Synthetic checks pass,
  no exceptions, zero static rebuilds. Fresh Spring: six buildings/two trips.
- Performance/land: GJ generation about 6.16s, packaging 5.94s, viewer-data 33.73MB
  on this run (existing analyzed inputs, not scan time or FPS). Areas GJ/OJ/PB/
  SQLite: 251306/154027/142683/113662 versus prior GRID
  251306/138820/150427/97208. Explicit organic sometimes needs more land.
- Spec alignment: PASS, technical 7/8, AC-002/003/006/011 and DEC-004/005/007/008
  rechecked; no source execution/dependency/schema break or invented roles.
- Fixes/reverified: extended the schema enum after its new-version rejection;
  reran full suite and real exports. No validation gates weakened.
- Next actions: INDUSTRIAL and HYBRID, then independently seeded world outline;
  keep these as separate commits and avoid curve micro-tuning.
- Delivery: atomic organic feature/checkpoint on main; normal owner-authorized
  push outcome checked before moving to the next unit. No agent attribution.

## Checkpoint 2026-10-19 — INDUSTRIAL planning grammar
- Implemented: explicit industrial policy, seven-unit spines, four-unit service
  courts with physical dead ends, 9x10 lots and entrance setbacks. Source building
  envelopes/roles unchanged. Demand now budgets these larger lots/circulation.
  Four fixed local axis/phase candidates avoid narrow-corner capacity misses;
  the existing five envelope repairs and all geometry limits remain enforced.
- Fixtures/revisions: four pinned corpus inputs/revisions as ORGANIC checkpoint;
  same newly scanned maintained Spring build, regenerated industrial-r3 output.
- Commands: full Python discovery, Node suite, Ruff and diff checks as above;
  `python ../artifacts/visual/world_grammars_review.py industrial world-industrial-r3`;
  `python -m scripts.procedural_world ../artifacts/visual/world-grammars-e2e-r1/build
  --namespace fixture/world-grammars --planning industrial
  --out ../artifacts/visual/world-grammars-e2e-r1/industrial-r3`;
  browser audit with CHROME into world-industrial-audit-r3 against four corpus
  outputs and maintained industrial-r3, using the preceding audit command form.
- Artifacts inspected: four actual WebGL Overview PNGs and GJ showcase.png in
  world-industrial-audit-r3; world-industrial-r3/report.json/index.html.
  Findings: broad access spines and branching short courts are visible; open
  loading/setback areas increase. Still regular industrial blocks, not different
  inferred warehouse roles. All-industrial is deliberately sparse, not a claim
  of better density or a proposed replacement default. Root label remains rough.
- Tests/determinism/stability: Python 533 run/532 pass/one existing symlink skip;
  Node 56 pass, lint pass. New checks assert real degree-one street ends, width7,
  lot area90 and matching land budget. All 3,175 buildings and 5,782 logical trips
  retained, repeat package bytes match, source City/UCG unchanged, zero collisions
  or owner escapes, all doors reachable. Browser selection, provenance, camera,
  filters and Synthetic pass with zero static rebuilds. Spring six files/two trips.
- Fixes/reverified: r1/r2 PocketBase failed bounded capacity repair. Corrected
  profile-specific budgeting and compared four deterministic local court frames;
  rebuilt r3 and reran full suites/corpus. Did not increase repair limits, remove
  buildings, silently switch to GRID or suppress failed fixtures.
- Performance/land: GJ generation8.61s/package4.63s and viewer28.63MB on this run;
  areas GJ/OJ/PB/SQLite 414984/230100/227073/149868, roughly 51–66% above GRID.
  Times are from analyzed inputs, not end-to-end analysis or GPU FPS.
- Spec alignment: PASS, ADR-026, technical7/8, AC-002/006/011/012 and evidence /
  unknown fallback / directory ownership invariants rechecked; no public contract
  break, new dependency, code execution or invented industrial semantic claim.
- Next actions: actual within-district HYBRID and five-grammar varied policy,
  then seeded exterior shape. Density cost remains an explicit industrial tradeoff.
- Delivery: one atomic industrial feature/checkpoint on main; verify normal
  owner-authorized push result, preserve user caches and zero agent attribution.

## Checkpoint 2026-10-19 — HYBRID regions and five-grammar selection
- Implemented: one HYBRID district contains connected ORGANIC/GRID regions with
  shared boundary streets, explicit region polygons and parcel region/profile
  IDs. Independent validation rejects region area loss, overlap and escaped /
  misassigned parcels. New varied policy chooses all five grammars; original
  mixed remains GRID/RADIAL and source City/UCG contracts remain intact.
- Fixtures/revisions: same four pinned canonical snapshots as prior checkpoints;
  maintained fixture/world-grammars Spring build and controlled TS cycle fixture.
- Commands: full Python discovery/Node/Ruff/diff checks; review helper with
  `hybrid world-hybrid-r1` and `varied world-varied-r1`; procedural-world CLI on
  world-grammars-e2e-r1/build with each policy into sibling hybrid/varied outputs.
  Browser audit CHROME world-hybrid-audit-r1 against the four hybrid outputs,
  four varied outputs and maintained hybrid output (nine cases).
- Artifacts inspected: four hybrid Overview PNGs, GJ/PocketBase varied Overview,
  and GJ hybrid CPU showcase in world-hybrid-audit-r1; both corpus report.json
  files. Findings: street patterns transition within districts instead of being
  two labels on one unchanged grid. Large nested block boundaries add visible
  structure, while regular rows and the flat exterior remain obvious. Root
  labels/role compound LOD remain pending. No claim of five patterns per city:
  final varied may fall back to GRID when a chosen grammar lacks capacity.
- Tests/determinism/stability: Python535 run/534 pass/one Windows symlink skip;
  Node56 pass, lint pass. Schema/repeated byte packages, region ownership
  negative cases and five-way vs legacy two-way selection are covered. Hybrid
  and varied each retain 3,175 buildings/5,782 source-pair trips, every edge
  classification, original source bytes, accessible doors and zero collisions.
  Nine browser cases pass selection/provenance/filter/camera/Synthetic checks
  without exceptions or static rebuilds. Maintained hybrid six files/two trips.
- Land/performance: forced hybrid GJ/OJ/PB/SQLite areas 286446/160192/196162/
  113662; varied 251913/138844/150427/97605. Values are world areas, not pixels.
  GJ hybrid generation6.68s/package5.53s/viewer32.60MB; varied6.62s/6.44s/35.51MB
  from analyzed snapshots. CPU browser timings are not GPU FPS.
- Spec alignment: PASS under ADR-026, technical7/8, AC-002/006/011/012, immutable
  directory ownership and source-evidence rules. Unknown languages retain
  generic buildings. No target execution or runtime dependency introduced.
- Next actions: seeded varied world envelopes and a clearly labeled five-profile
  comparison so local fallback cannot obscure which grammars were implemented.
- Delivery: one atomic hybrid/varied feature/checkpoint on main, normal
  owner-authorized push verified separately; no agent attribution.

## Checkpoint 2026-10-19 — variable outlines and final grammar review
- Implemented: ADR-027 `--outline varied`, independent seeded-convex/1 stream
  and compact/elongated/angular/asymmetric convex land. Vertex count/radii /
  angular spacing, aspect, shear and rotation change actual allocation geometry,
  not a decorative border. Existing ellipse/default worlds remain unchanged.
  Matching hints retain prior land and parcels; policy switches diagnose replan.
- Fixtures/revisions: same four pinned canonical corpora recorded above; same
  freshly scanned maintained Spring build; 80-file TS import-cycle atlas with
  explicit fixture/planning-atlas identity. Atlas files are controlled test input,
  not a claim about a real user's architecture. No source repository executed.
- Commands: `python -m unittest discover -s tests -q`; Node full suite, Ruff and
  diff checks; `python ../artifacts/visual/world_grammars_review.py varied
  world-varied-outline-r1 --varied-outline`; `python
  ../artifacts/visual/world_profile_atlas.py`; procedural-world CLI on
  world-grammars-e2e-r1/build with `--namespace fixture/world-grammars --planning
  varied --outline varied --out ../artifacts/visual/world-grammars-e2e-r1/varied-outline`.
  Browser audit: `node scripts/viewer_audit.mjs CHROME
  ../artifacts/visual/world-outlines-audit-r1 INPUT...` for four new corpus
  outputs, five atlas grammars, four outline atlas seeds and maintained output
  (14 cases). CHROME path as above. Context audit: `node
  ../artifacts/visual/city_context_review.mjs ../artifacts/visual/world-outlines-context-r1
  ../artifacts/visual/world-varied-outline-r1/gj
  ../artifacts/visual/world-varied-outline-r1/pocketbase`.
- Artifacts inspected: world-profile-atlas-r1/index.html/report.json;
  world-varied-outline-r1/report.json; four real corpus Overview PNGs and GJ
  showcase/route-inspector PNGs in world-outlines-audit-r1; CPU showcase PNGs
  cases5–13 (all five grammars and all four outline examples);
  world-outlines-context-r1/canvas-0/city.png. Both render targets reflect the
  same physical world. Atlas full-city framing is independent, not pixel scale.
- Visual findings: actual large worlds no longer share a fixed elliptical
  silhouette. Asymmetric wedges, angular corners and differing proportions are
  visible; planning adapts inside the boundary. Atlas exposes true GRID,
  ORGANIC, RADIAL, INDUSTRIAL and within-district HYBRID differences, including
  the industrial open-space cost. Outline examples intentionally select one
  explicit seed per family (shape-0/1/2/6), not a claimed random sample. Still
  flat convex land: no deep bays, islands, water or organic terrain. Some rows,
  spare lots, root-label roughness and lack of role-compound LOD remain visible.
- Tests/determinism/stability: Python539 run/538 pass/one existing Windows
  symlink skip; Node56 pass; lint/whitespace pass. New tests exercise128 outline
  seeds with convexity and shape diversity, real repeated World/schema/package
  bytes, compatible added-file hints, policy-switch replans and legacy defaults.
  Added industrial/hybrid hint assertions preserve existing parcels. Independent
  four-corpus comparison confirms default GRID world bytes still exactly match
  world-flat-reviewed-r2. All new four-corpus and nine atlas packages repeat
  byte-identically and conserve source City/UCG bytes; original 3,175 corpus
  buildings/5,782 source-pair trips remain, zero collisions/owner escapes, all
  doors reachable. Maintained output six buildings/two trips. Browser14 cases
  pass exact inspection, filters, camera, three LODs and Synthetic with zero
  static rebuilds/no exceptions. Forced Canvas and Structure restoration pass.
- Land/performance: new corpus areas GJ/OJ/PB/SQLite 263078/131658/142683/97605
  versus GRID251306/138820/150427/97208; not a universal density gain. GJ measured
  generation6.92s/package6.30s, viewer-data36.29MB from analyzed snapshots.
  Large route serialization and semantic LOD remain future measured work;
  browser CPU submission samples are not GPU FPS/memory measurements.
- Spec alignment: PASS, authorized ADR-026/027 scope. Rechecked technical7/8,
  functional AC-002/003/006/011/012 and product DEC-004/005/006/007/008/009/011.
  Additive experimental World metadata retains old documents. No City/UCG
  break, stable source ID change, new dependency, AI/API or source execution.
  Structural planning labels never assert new industrial roles or dependencies.
- Open risks/next actions: varied policy deliberately does not guarantee all
  five profiles occur in every repository: capacity fallback is explicit.
  ORGANIC is meandering strips, HYBRID two connected region grammars, not
  completed arbitrary block/polygon planning. Concave coasts and terrain need
  a separate geometry design. Do not resume tiny curve tuning; prioritize
  source-traceable LOD and actual measured export costs for the next milestone.
- Delivery: fourth atomic feature/checkpoint after 1185b1b/19f855b/35bfbff,
  current main, standing owner-authorized normal push. Review final staged paths,
  human identity, upstream and remote SHA before reporting delivery. Preserve
  untracked user build caches; never force-push or add agent attribution.

## Checkpoint 2026-10-19 — evidence-backed internal power zoning

- Implemented: HZ-00/ADR-028 and first HZ-01/02/03 flat vertical slice from the
  hierarchical semantic-zoning proposal. Opt-in `--zoning semantic`, strict
  role-quarter membership/evidence, bounded clipped power area balancing,
  measured-capacity local repair, real connected streets/frontage parcels,
  canonical planning.json, same World-fed CPU/WebGL/Canvas geometry and paged
  neighborhood/member/source inspection. Legacy/default output unchanged.
- Fixtures/revisions: fixed world-flat-reviewed-r2 source snapshots, GJ
  local-sha256-06eb492d57141c16 and OJ local-sha256-c2e80f9d3908fec8 (both
  revision=null, not claimed pinned Git commits); PocketBase6f370ea741f33adf889eef02e3c1b884a47aa522
  and SQLiteBrowserae32df153a64d250de7c77a5057deeff4092a39b. Fresh maintained
  spring-positive at baselineff75c80 through scanner/analyzer/City, plus generated
  72-source mixed-role and30-source unknown Rust unit fixtures. No target code,
  dependency install, target build or outbound analysis service was invoked.
- Commands run (repository cwd): `python -u ../artifacts/visual/semantic_zoning_review.py
  semantic-zoning-r4`; `python -m metropogits build --repo
  tests/fixtures/repositories/spring-positive --repo-id fixture/semantic-zoning
  --out ../artifacts/visual/semantic-zoning-e2e-r1/build`; `python -m
  scripts.procedural_world ../artifacts/visual/semantic-zoning-e2e-r1/build
  --namespace fixture/semantic-zoning --outline varied --zoning semantic
  --out ../artifacts/visual/semantic-zoning-e2e-r2/world`; same World CLI on
  world-flat-reviewed-r2/gj/after, namespace benchmark/gj-cloud, varied outline,
  out semantic-zoning-varied-r1/gj. Full Python/Node suites, Ruff and diff check.
- Browser command: `node scripts/viewer_audit.mjs
  "C:/Program Files/Google/Chrome/Application/chrome.exe"
  ../artifacts/visual/semantic-zoning-reviewed-r1` followed, in order, by
  semantic-zoning-r4/gj/before, gj/after, oj/after, pocketbase/after,
  sqlitebrowser/after, semantic-zoning-e2e-r2/world and semantic-zoning-varied-r1/gj
  (each prefixed ../artifacts/visual/). Forced Canvas:
  `node ../artifacts/visual/semantic_zoning_canvas_review.mjs
  ../artifacts/visual/semantic-zoning-canvas-r1` with r4/gj/after and r4/oj/after.
- Artifacts actually inspected: all four new real WebGL default/overview images,
  GJ district/zone inspector, actual CPU showcase captures for all four, varied
  GJ WebGL default and GJ Canvas inspector. Actual browser runs exercise three
  LODs, camera/pointer/filters, exact source-backed route inspection and Synthetic.
  New browser assertions navigate parent -> neighborhood -> source member ->
  neighborhood, verify original role confidence, exact first/second25-file pages,
  and separate principal district/planning-zone counts. Canvas also verifies
  Structure overlay restoration. Browser7 cases exit0, no exceptions; all
  applicable Synthetic samples have zero static city rebuilds.
- Visual findings: role clusters become contiguous, auditable neighborhoods
  instead of scattered colored buildings. OJ service/storage/test/entry regions
  are distinct at a glance. GJ's large mixed quarters remain repetitive gray
  rows; semantic grouping is visible but full organic block morphology is not
  done. Generic Go/C++ stay neutral, without fabricated DB/auth categories.
  Borders are subdued, selected context and original source evidence remain.
  Existing long inspector paths and float size formatting remain rough edges.
- Geometry/source results:3175 corpus buildings/5782 actual source-pair trips,
  represented edges6157/2243/192/0 respectively, zero parcel/building/road
  collisions or owner escapes, all entrances reachable. All eligible files
  belong to exactly one planning zone; every specialized member's original
  claim is retained. Every canonical City/UCG byte matches its input snapshot.
  GJ13 zones/OJ11; PB8 and SQLite3 all GENERAL_MIXED, no internal tessellation
  when only one cluster exists. Raw cell boundaries are not automatically paved:
  connect required ports and a stable adjacency tree, removing port-free arcs.
- Tests/determinism/stability: Python553 run,552 pass, one existing Windows
  symlink skip; Node56 pass.14 new tests cover real analysis, both schemas,
  exact repeated packages, provenance/membership tampering, clipping/area,
  bounded solver fallback, unsupported land and resource limits, street-port
  omission, weak/tiny/unknown claims, changed seed and malformed hints.
  Hinted one-file addition preserves all72 existing parcel frames and zone/parent
  polygons. All eight four-repository before/after packages repeat identically.
  Independently regenerated legacy default World bytes match all four original
  world-flat-reviewed-r2 baselines. Latest validator membership lookup uses sets,
  avoiding a per-file scan of the whole zone's member list; targeted14 re-pass.
- Corrections: first semantic output inflated GJ/OJ land by58%/55%. Added one
  within-parent measured-capacity redistribution and bounded local GRID fits;
  retained sources, styles and exact access, then re-ran all corpus outputs.
  Final areas251306->271804 GJ (+8.16%),138820->150028 OJ (+8.07%),
  150427->136541 PB (-9.23%),97208->97208 SQLite. Not a universal density gain.
  A rotated quantized-lot contact was corrected with real0.01 parcel clearance
  in new zoning, not a weakened validator or a silent legacy geometry rewrite.
- Performance: unprofiled generation seconds before->after5.67->7.20 GJ,
  2.20->2.89 OJ,0.73->0.99 PB,0.29->0.56 SQLite. Viewer-data28.03->30.16MB GJ,
  10.57->11.29MB OJ. This new opt-in capability costs time/data; not a speedup.
  WebGL orbit submission CPU p95 across the seven cases0.1–3.8ms; not GPU FPS.
  CDP JS heap samples and Synthetic p95 are in the raw report (same browser,
  uncontrolled GC; not independent peak RSS/GPU-memory comparisons). Total
  process RSS and GPU frame-completion p95 were not measured; HZ release gate
  remains open. Varied GJ area260188, actual profiles12GRID/1ORGANIC.
- Spec alignment: PASS under requested opt-in ADR-028 scope; rechecked technical
  sections3/4/7/8/10/12, functional AC-001/002/003/006/008/011/012/014,
  product DEC-004/005/006/007/008/009/011. UCG/City unchanged, existing World
  documents valid, no new dependency, native rewrite, LLM, API or execution.
- Open risks/next actions: first clustering uses verified roles, not graph-affinity
  or full package subclusters. Large unknown quarters still need neutral internal
  structure/LOD. GJ ellipse currently falls back to GRID for all13 neighborhoods;
  OJ retains one ORGANIC/one INDUSTRIAL. Do not claim every category has a unique
  grammar. Concave/holed land, terrain/water/bridges/tunnels, real enclosed block
  polygons and rotated role compounds remain pending. Initial r1 benchmark's
  pre-existing non-zoned GRID+varied GJ failed strict quantized parcel-overlap
  validation; the controlled comparison uses the valid unchanged ellipse
  baseline. New zoned varied GJ passes. That legacy combination still needs an
  explicitly versioned clearance fix, not a claim of all-seed legacy success.
- Delivery: docs commit3520056; feature/checkpoint committed separately after
  staged review. New proposal's protected-branch rule followed with
  feat/semantic-zoning, not direct protected-main integration. Push verified
  commits normally to the existing origin; no force, settings change or agent
  attribution. Unrelated user build caches are preserved.

## Checkpoint 2026-10-19 — graph-aware soft influence over varied geography

- Implemented: ADR-029, opt-in `--zoning soft`, immutable five-grammar/outline
  base, sparse dependency-guided equal-size address exchanges, advisory power
  influence cells, separate center/occupant evidence, planning0.2 and browser
  disclosure/source navigation. No new land, streets, fake roles or relations.
- Fixtures/revisions: same fixed world-flat-reviewed-r2 source snapshots as the
  preceding checkpoint (GJ/OJ local content IDs, revision=null; PocketBase
  6f370ea741f33adf889eef02e3c1b884a47aa522; SQLiteBrowser
  ae32df153a64d250de7c77a5057deeff4092a39b). Fresh maintained spring-positive
  through analysis/UCG/City; real analyzed32-file cross-role and30-file unknown
  unit fixtures. No target dependency installation/build/execution.
- Commands run: `python ../artifacts/visual/soft_zoning_review.py soft-zoning-r1`;
  `python -m metropogits build --repo tests/fixtures/repositories/spring-positive
  --repo-id fixture/soft-zoning-e2e --out ../artifacts/visual/soft-zoning-e2e-r1/build`;
  `python -m scripts.procedural_world ../artifacts/visual/soft-zoning-e2e-r1/build
  --namespace fixture/soft-zoning-e2e --planning varied --outline varied
  --zoning soft --out ../artifacts/visual/soft-zoning-e2e-r1/world`.
  Full Python560 run/559 pass/one existing Windows symlink skip; Node56 pass;
  targeted seven new tests re-pass after final optimizer/validation corrections;
  Ruff and Git diff checks pass. Schemas world0.1/planning0.2 validated.
- Browser commands: viewer_audit.mjs with installed Chrome into
  soft-zoning-reviewed-r2 against soft-zoning-r1/gj/before, gj/after, oj/after,
  pocketbase/after, sqlitebrowser/after, exit0. Actual three LODs, exact route
  evidence, filtering, camera and Synthetic tested. Forced Canvas helper
  semantic_zoning_canvas_review.mjs into soft-zoning-canvas-r2 against GJ after
  and fresh Spring, source navigation/pagination and Structure restoration pass.
- Artifacts inspected: new WebGL defaults for all four repositories; GJ
  district view, route/zone/member evidence captures, GJ/OJ CPU showcase PNGs;
  GJ Canvas inspector and fresh Spring WebGL detail. soft-zoning-r1/index.html
  is the controlled same-base comparison, not the earlier hard-GRID comparison.
  Five existing planning grammars remain available; actual varied profiles on
  GJ are ORGANIC/GRID/ORGANIC/RADIAL/GRID/RADIAL, PB also retains HYBRID.
- Geometry/source/determinism:3175 files,5782 original trips; represented
  edge counts6157/2243/192/0 unchanged. Strict validation reports zero parcel,
  building or road collisions/owner escapes; all entrances reachable. Every
  canonical City/UCG byte, principal polygon, street and occupied physical
  address matches its input/base. All eight packages repeat byte-identically.
  Compatible one-file hint addition keeps every original full physical frame;
  influence region annotation may change, explicitly tested/documented.
- Actual affinity results (weighted Euclidean distances, not runtime latency):
  GJ Auth61.0->23.9, Ops153.3->55.7, User146.3->39.9, Vm87.9->33.5,
  Portal157.0->83.2; OJ backend142.0->53.6, frontend57.3->26.0;
  PB supported ui/src79.7->36.6. SQLite has no supported relationships and
  keeps original addresses. This does not establish new Go/C++ analyzer support.
- Performance: uncontrolled single generation before->after seconds GJ7.08->8.46,
  OJ2.51->3.06, PB0.90->0.93, SQLite0.37->0.41. No optimizer work limits hit.
  GJ viewer-data36.29->31.52MB, OJ14.00->12.23MB (shorter routed geometry,
  not source deletion). Browser orbit CPU p95 across corpus0.4–4.5ms,
  Synthetic static city rebuilds0. Software renderer submission, not GPU FPS.
- Visual findings/corrections: mixed role buildings follow actual affinities
  rather than isolated color quarters, while existing orbital/organic streets
  remain. Derived districts initially suppressed major service names at Overview;
  fixed both renderers to honor explicit principal identities and re-ran audits.
  The actual corrected GJ capture shows Auth/Ops/User/Vm/portal. Colored facades
  and regular base rows still look toy-like; prioritize material/role separation
  next instead of polishing individual bends. Influence labels describe a
  preference center, not guaranteed dominant-role occupancy or a runtime module.
- Diagnostic limitation: initial six-case soft-zoning-reviewed-r1 stopped at
  fresh six-file Spring's shared-road pointer-target assertion after successful
  three-LOD/Synthetic checks; no visible target was available at that audit
  camera. Did not weaken the assertion. Corpus rerun r2 passes all five cases;
  fresh Spring separately passes geometry, CPU generation and real Canvas
  source/evidence/structure navigation. That tiny-camera pointer coverage is
  not claimed verified. Earlier failed artifacts remain for diagnosis.
- Spec alignment: PASS within opt-in ADR-029; technical3/4/7/8/10/12,
  functional AC-001/002/003/006/008/011/012/014, product fixed decisions.
  UCG/City/IDs unchanged, no new runtime dependency/AI/API/unsafe execution.
  Concave outline/terrain/road-enclosed polygons remain outside this slice.
- Delivery: docs9fa3068 followed by this atomic feature/checkpoint on
  feat/semantic-zoning; inspect explicit staged paths/human identity, normal
  upstream push, verify command result before reporting. Preserve user caches.
