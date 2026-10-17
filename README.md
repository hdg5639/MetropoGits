# MetropoGits

MetropoGits turns source repositories into explorable, architecture-driven
cities. The implementation is at a v1 candidate milestone: every P0 functional
requirement has automated evidence, while public release remains blocked on the
owner decisions and opt-in deployment listed in `release/readiness.json`. See
[v1 candidate status](docs/V1_CANDIDATE.md) for the verified boundary and the
three promotion conditions.

## Structural preview quick start

Install the local CLI and build a deterministic structural city:

```powershell
python -m pip install -e .
metropogits build --repo . --out dist --theme minimal
```

The command writes the graph and scene contracts, a deterministic SVG preview,
an interactive static viewer, a diagnostic manifest, and a linked README
snippet. Open `dist/index.html` directly to pan, zoom, rotate, and inspect the
city. Buildings and links can be filtered by verified role, language,
technology, and evidence level. District labels are decluttered at each view so
deeper, populated districts remain readable while zooming and rotating. The
bundled Java analyzer recognizes evidence-backed local imports, uniquely
resolved local type references, inheritance, declarations, and core Spring
stereotypes. The JavaScript/TypeScript adapter resolves explicit local ESM and
CommonJS module references without running repository code; its conservative
resolution rules are documented in [the JS/TS analyzer guide](docs/JSTS_ANALYZER.md).
Direct dependencies in Maven `pom.xml`, Gradle `build.gradle` or
`build.gradle.kts`, and npm `package.json` files are recorded as bounded
`MODULE -> EXTERNAL_PACKAGE` declarations with manifest evidence. Dependency
management entries, Maven plugin dependencies, Gradle project/file references,
dynamic JVM coordinates, and npm local/workspace/alias specifiers are not
treated as active external dependencies. A declaration alone does not claim
runtime technology usage. Catalog rules may combine the closest enclosing
manifest declaration with exact code evidence; the resulting claim retains
both provenance classes.

Allowlisted Spring `application*.properties` signatures are parsed without
retaining arbitrary keys or raw secret values. PostgreSQL is classified only
when the exact driver declaration, verified JPA repository inheritance, and
non-secret driver configuration agree. A selected building's inspector lists
its nearest module dependencies under `DECLARED DEPENDENCIES (NOT USAGE)`.

npm `package-lock.json` v2/v3 files contribute only the root package's direct
dependency sections. Nested resolved packages are not promoted to direct
dependencies, and legacy lockfiles without a `packages[""]` entry are rejected
with a diagnostic instead of being guessed.
Unsupported source languages still produce generic buildings without guessed
semantics.

The viewer also offers an opt-in synthetic activity overlay. It is disabled by
default, respects reduced-motion preferences, and never claims to show measured
runtime traffic. See [synthetic activity](docs/SYNTHETIC_ACTIVITY.md) for its
interpretation limits.

For automation, add `--json` before or after a command. Complete, partial,
invalid-input, resource-limit, and internal-error outcomes have stable exit
codes documented in [the CLI result contract](docs/CLI_RESULTS.md).

## GitHub Action

The repository includes a least-privilege composite Action and a pinned Pages
workflow template. Pull requests produce a private artifact without deployment;
push and manual runs may publish only through the separately permissioned Pages
job. See [GitHub Action and Pages publishing](docs/GITHUB_ACTION.md) before
publishing generated repository metadata.

## Contract validation

Install the pinned Python 3.11 development environment and run the contract
tests:

```powershell
python -m pip install -r requirements-lock.txt
python -m unittest discover -s tests -v
```

The same lint, compile, JavaScript parse, dependency consistency, and full test
gates run automatically on pull requests and pushes to `main` through the
least-privilege [quality workflow](.github/workflows/ci.yml). That workflow also
runs the composite Action against a safe fixture on a GitHub-hosted runner and
checks the complete static artifact set.

Validate the versioned P0 and acceptance evidence map:

```powershell
python -m metropogits validate --input release/readiness.json
```

The document remains `BLOCKED` while any release check is unresolved; automated
requirement coverage alone never declares a release ready.

Security reporting, contribution gates, and the reviewed direct/transitive
dependency list are documented in [SECURITY.md](SECURITY.md),
[CONTRIBUTING.md](CONTRIBUTING.md), and the
[dependency inventory](docs/DEPENDENCY_INVENTORY.md). A project license has not
yet been selected, so public release and external contributions remain blocked.

Validate an individual Universal Code Graph document:

```powershell
python scripts/validate_ucg.py path/to/graph.ucg.json
```

Validate a City Scene together with the UCG it was generated from:

```powershell
python scripts/validate_city.py path/to/city.json --ucg path/to/graph.ucg.json
```

Produce canonical contract bytes or inspect their content digest:

```powershell
python scripts/canonical_json.py path/to/graph.ucg.json --output canonical.json
python scripts/canonical_json.py path/to/graph.ucg.json --digest
```

Generate stable repository, entity, and edge identifiers:

```powershell
python scripts/stable_ids.py repository --namespace openai/metropogits
python scripts/stable_ids.py entity --repo-id openai/metropogits --kind FILE --path src/App.java
python scripts/stable_ids.py edge --from-id source --type REFERENCES --to-id target
```

Validate a versioned technology catalog and its positive/negative fixtures:

```powershell
python -m metropogits validate --input catalog/0.4.0/catalog.json
```

See [technology catalog contributions](docs/CATALOG_CONTRIBUTING.md) for the
rule safety levels and contribution checklist.

Generate a bounded structural UCG without executing repository code:

```powershell
python -m metropogits.scanner --repo path/to/repository --repo-id owner/project --out graph.ucg.json
```

Generate a deterministic City Scene from a UCG:

```powershell
python -m metropogits.layout --graph graph.ucg.json --out city.json --theme minimal
```

Preserve unaffected building and district positions across a small change by
supplying the previous generated scene as a non-authoritative layout hint:

```powershell
python -m metropogits build --repo . --out dist --previous-scene dist/city.json
```

The hint is loaded before output is replaced. Unsupported or malformed hints
are ignored, reported in build diagnostics, and never override the current UCG.

Render a deterministic CPU-only SVG preview:

```powershell
python -m metropogits.preview --scene city.json --ucg graph.ucg.json --out preview.svg
```

Combine ordered build directories into an inspectable revision timeline:

```powershell
python -m metropogits history --snapshot dist/rev-a --snapshot dist/rev-b --out dist/history
```

See [history replay](docs/HISTORY_REPLAY.md) for identity rules and output
details.

Combine distinct repository cities through explicitly evidenced service links:

```powershell
python -m metropogits metropolis --member dist/api --member dist/worker --links metropolis-links.json --out dist/metropolis
```

Only verified links become graph edges and visible city networks. Unknown
targets remain explicit unresolved outcomes instead of guessed connections. See
[multi-repository metropolis](docs/MULTI_REPO_METROPOLIS.md) for the manifest
contract and build workflow.
