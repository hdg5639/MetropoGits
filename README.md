# MetropoGits

MetropoGits turns source repositories into explorable, architecture-driven
cities. The project is currently establishing its versioned implementation
contracts.

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
