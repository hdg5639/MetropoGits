# MetropoGits

MetropoGits turns source repositories into explorable, architecture-driven
cities. The project is currently establishing its versioned implementation
contracts.

## UCG contract validation

Install the pinned development dependency and run the contract tests:

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

Validate an individual Universal Code Graph document:

```powershell
python scripts/validate_ucg.py path/to/graph.ucg.json
```
