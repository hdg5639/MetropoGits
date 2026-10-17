## Summary

<!-- Explain the user-visible outcome and why it is needed. -->

## Evidence

<!-- List the fixtures, tests, or manual checks that demonstrate the change. -->

## Safety checklist

- [ ] I ran `python -m unittest discover -s tests -v`.
- [ ] I ran `ruff check metropogits scripts tests`.
- [ ] I did not add secrets, raw repository source, or generated `dist/` files.
- [ ] Semantic claims include evidence and confusing near-match negatives.
- [ ] Contract changes use a new schema version and document affected consumers.
- [ ] Catalog changes include authoritative provenance and license information.
- [ ] New dependencies are pinned and recorded in `docs/DEPENDENCY_INVENTORY.md`.
