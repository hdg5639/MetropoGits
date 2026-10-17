# Dependency inventory

This inventory covers the pinned Python 3.11 development and CI environment.
Licenses were checked against the metadata and license files installed by the
listed distributions. Package links point to their published Python Package
Index records for independent review.

| Distribution | Version | Purpose | Declared license |
|---|---:|---|---|
| [jsonschema](https://pypi.org/project/jsonschema/4.25.1/) | 4.25.1 | Runtime JSON Schema validation | MIT |
| [attrs](https://pypi.org/project/attrs/25.4.0/) | 25.4.0 | `jsonschema` runtime dependency | MIT |
| [jsonschema-specifications](https://pypi.org/project/jsonschema-specifications/2025.9.1/) | 2025.9.1 | `jsonschema` vocabulary data | MIT |
| [referencing](https://pypi.org/project/referencing/0.37.0/) | 0.37.0 | `jsonschema` reference resolution | MIT |
| [rpds-py](https://pypi.org/project/rpds-py/0.28.0/) | 0.28.0 | Persistent structures used by `referencing` | MIT |
| [typing-extensions](https://pypi.org/project/typing-extensions/4.15.0/) | 4.15.0 | Python <3.13 compatibility dependency | PSF-2.0 |
| [PyYAML](https://pypi.org/project/PyYAML/6.0.2/) | 6.0.2 | Workflow contract tests | MIT |
| [Ruff](https://pypi.org/project/ruff/0.14.2/) | 0.14.2 | Python lint gate | MIT |
| [setuptools](https://pypi.org/project/setuptools/65.5.0/) | 65.5.0 | Pinned build backend | MIT |
| [wheel](https://pypi.org/project/wheel/0.45.1/) | 0.45.1 | Pinned build helper | MIT |

`requirements-dev.txt` declares direct development requirements.
`requirements-lock.txt` pins those requirements and their Python 3.11 runtime
closure. `pyproject.toml` pins the build backend and runtime dependency. The
GitHub Action applies the lock file as a constraint when installing its isolated
runtime.

This is an inventory, not legal advice. Before a public release, regenerate the
environment from the lock, inspect every installed distribution's license
files, review bundled or vendored components, and record the review revision.
The repository itself currently has no `LICENSE`; public release and external
code contributions remain blocked until the owner chooses one.
