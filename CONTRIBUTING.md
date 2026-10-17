# Contributing

MetropoGits accepts maintainer-reviewed changes that preserve evidence-backed
semantics, deterministic artifacts, and the no-execution security boundary.

## License status

The project owner has not selected a project license yet. Until a root
`LICENSE` file is published, do not submit external code or documentation
contributions. This explicit gate avoids implying rights or contribution terms
that have not been chosen. Security reports may still be submitted privately
using [SECURITY.md](SECURITY.md).

## Development setup

Use Python 3.11 or newer. For the reproducible Python 3.11 CI environment:

```powershell
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps -e .
python -m pip check
ruff check metropogits scripts tests
python -m compileall -q metropogits scripts tests
python -m unittest discover -s tests -v
```

Generated `dist/` content is ignored and must not be committed.

## Change requirements

- Keep one independently reviewable task per commit.
- Use `feat(scope): short summary` followed by bullet points describing the
  work.
- Add positive, negative, and malformed-input tests where relevant.
- Never infer a semantic role, technology usage, or relationship without
  evidence represented in the UCG.
- Do not execute target repository code, builds, package managers, or tests.
- Version contract changes and update every producer, consumer, fixture, and
  validator in the same change.
- Follow [the catalog contribution guide](docs/CATALOG_CONTRIBUTING.md) for
  catalog rules.
- Update the dependency inventory and lock whenever dependencies change.

The pull request template records these gates. CODEOWNERS identifies sensitive
paths, but required review must also be enabled in repository branch protection
once collaboration begins.
