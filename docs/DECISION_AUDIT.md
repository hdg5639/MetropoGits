# Architecture decision audit

This audit compares DEC-001 through DEC-013 from the product plan with the
current repository. `Satisfied` means repository code or tests demonstrate the
decision. `Review required` means the implementation and decision text are not
clearly aligned; it is not silently treated as compliant.

| Decision | Status | Repository evidence |
|---|---|---|
| DEC-001 — No LLM in the pipeline | Satisfied | Runtime dependencies contain no model client, and the local pipeline is covered by `tests/test_cli.py`. |
| DEC-002 — Local/static first | Satisfied | CLI artifacts and the file-compatible viewer are tested in `tests/test_cli.py` and `tests/test_viewer.py`. |
| DEC-003 — Never execute input by default | Satisfied | Scanner and JS/TS no-execution fixtures are covered by `tests/test_scanner.py` and `tests/test_jsts_analyzer.py`. |
| DEC-004 — Unknowns degrade gracefully | Satisfied | `LayoutTests.test_unknown_languages_receive_generic_buildings`. |
| DEC-005 — Evidence-backed claims | Satisfied | UCG claim/edge validation and positive/negative analyzer fixtures. |
| DEC-006 — Reproducible fixed inputs | Satisfied | Canonical JSON, stable ID, deterministic layout, preview, CLI, history, and metropolis tests. |
| DEC-007 — Directory-first geography | Satisfied | [`ADR-004`](adr/ADR-004.md) drives nested, bounded, non-overlapping district geometry; previous-scene hints preserve unaffected anchors, and fixture gates measure cold and hinted churn. |
| DEC-008 — File as base building | Satisfied | Scene contract and layout tests map file entities to buildings and directories to districts. |
| DEC-009 — Two render targets, including interactive 3D | Satisfied | [`ADR-002`](adr/ADR-002.md) and [`ADR-005`](adr/ADR-005.md) drive a genuine WebGL viewer plus deterministic SVG and automatic isometric fallback. Viewer contracts and the hosted Chrome smoke verify both boundaries. |
| DEC-010 — Isolated analyzers behind UCG | Satisfied | Java and JS/TS adapters enrich the same versioned UCG without owning scene geometry. |
| DEC-011 — Aggregated roads preserve edges | Satisfied | `LayoutTests.test_edges_between_districts_are_aggregated_without_losing_ids`. |
| DEC-012 — Federation is post-MVP | Satisfied with recorded sequencing deviation | Federation remains isolated in the optional `metropolis` command. It was implemented before P0 closed, but P0 requirements are now fully automated and no additional federation expansion occurred during remediation. |
| DEC-013 — Evidence/test-gated contribution | Satisfied | Versioned declarative catalog fixtures, CI, PR template, and CODEOWNERS. |

## Required decisions and remediation

DEC-007 is implemented under [`ADR-004`](adr/ADR-004.md). DEC-012's historical
sequencing deviation remains recorded here; with all P0 requirements automated,
it no longer represents an unresolved product-state decision.

DEC-009 is resolved by [`ADR-005`](adr/ADR-005.md): stable v1 keeps the existing
deterministic preview/fallback and requires a genuine interactive 3D viewer.
That viewer, its evidence inspector, automatic non-WebGL fallback, and hosted
Chrome initialization are now implemented and verified, so DEC-009 no longer
blocks `DECISION_COMPLIANCE`.
