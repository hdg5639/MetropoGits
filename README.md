# MetropoGits

MetropoGits turns source repositories into explorable, architecture-driven
cities. The project is currently establishing its versioned implementation
contracts.

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
technology, and evidence level. The bundled Java analyzer recognizes
evidence-backed local imports, inheritance, declarations, and core Spring
stereotypes. The JavaScript/TypeScript adapter resolves explicit local ESM and
CommonJS module references without running repository code; its conservative
resolution rules are documented in [the JS/TS analyzer guide](docs/JSTS_ANALYZER.md).
Unsupported source languages still produce generic buildings without guessed
semantics.

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

Install the pinned development dependency and run the contract tests:

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

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
python -m metropogits validate --input catalog/0.2.0/catalog.json
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

Render a deterministic CPU-only SVG preview:

```powershell
python -m metropogits.preview --scene city.json --ucg graph.ucg.json --out preview.svg
```
