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
city. The bundled Java analyzer recognizes evidence-backed local imports,
inheritance, declarations, and core Spring stereotypes. Unsupported source
languages still produce generic buildings without guessed semantics.

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
