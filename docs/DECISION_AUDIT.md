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
| DEC-007 — Directory-first geography | Satisfied | `LayoutTests.test_small_change_preserves_existing_positions`. |
| DEC-008 — File as base building | Satisfied | Scene contract and layout tests map file entities to buildings and directories to districts. |
| DEC-009 — Two render targets, including interactive 3D | Review required | The project has deterministic SVG and an interactive static CPU canvas viewer, but the viewer is isometric 2D rather than a WebGL 3D implementation. The maintainer must either accept this as the v1 interpretation through an ADR/decision amendment or require a true 3D renderer. |
| DEC-010 — Isolated analyzers behind UCG | Satisfied | Java and JS/TS adapters enrich the same versioned UCG without owning scene geometry. |
| DEC-011 — Aggregated roads preserve edges | Satisfied | `LayoutTests.test_edges_between_districts_are_aggregated_without_losing_ids`. |
| DEC-012 — Federation is post-MVP | Satisfied | Federation was added as the later `metropolis` command without changing single-repository analysis. |
| DEC-013 — Evidence/test-gated contribution | Satisfied | Versioned declarative catalog fixtures, CI, PR template, and CODEOWNERS. |

## Required decision

DEC-009 is a release blocker. Resolve it with one of these owner decisions:

1. Amend DEC-009 to define the current interactive isometric canvas as the v1
   viewer, retaining SVG as the deterministic preview.
2. Keep DEC-009 unchanged and implement a true interactive 3D viewer with a
   documented non-WebGL fallback.

Until one path is selected and recorded, `release/readiness.json` must keep
`DECISION_COMPLIANCE` in `BLOCKED` state.
