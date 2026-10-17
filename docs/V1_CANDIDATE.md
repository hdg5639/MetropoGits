# v1 candidate status

MetropoGits has reached a locally verified **v1 candidate** milestone. This is
a product-maturity statement, not a `1.0.0` package release or public
deployment. The machine-readable source of truth remains
[`release/readiness.json`](../release/readiness.json).

## Verified candidate boundary

- Every P0 functional requirement has automated evidence in the release
  readiness map.
- A real repository can be scanned without executing its code and converted
  end to end into canonical UCG, City Scene, deterministic SVG, interactive
  static viewer, manifest, and README snippet artifacts.
- Java, JavaScript/TypeScript, Maven, Gradle, npm, and allowlisted Spring
  configuration evidence degrade conservatively when resolution is ambiguous.
- Stable nested geography, previous-scene hints, evidence-linked roads,
  accessible inspection, filtering, and direct `file:` viewing are covered by
  regression tests.
- The composite GitHub Action succeeds on a clean GitHub-hosted runner with
  read-only repository permission.
- The primary viewer renders genuine perspective WebGL geometry with orbit,
  zoom, selection, evidence inspection, and filters. WebGL failure starts the
  isometric 2D fallback from the same static artifact.
- The 2026-10-18 showcase regression run executed 229 tests: 228 passed and one
  Windows symlink test was skipped. The preceding visual checkpoint includes
  repeated deterministic builds and inspection of both render targets on
  GJ-Cloud and GamjaOJ. Exact evidence is recorded in
  [`QUALITY_LOG.md`](QUALITY_LOG.md).
- Builds now emit a traceable isometric `showcase.svg` for README use alongside
  the detailed preview. Four fixture shapes were inspected; controlled WebGL
  interaction benchmarks and broader road/landmark polish remain open.

## Conditions for public v1 promotion

The following promotion condition remains intentionally unresolved:

1. **Deferred Pages publication:** [`ADR-007`](adr/ADR-007.md) selects Pages for
   the eventual public demo. Repository visibility became public on 2026-10-18;
   Pages remains disabled and requires separate publication authorization.
   After deployment, verify the README link and repository-subpath viewer URL.

Until that condition is resolved, the project stays a v1 candidate,
`release/readiness.json` stays `BLOCKED`, and no `v1.0.0` tag or package-version
promotion should be created.

## Visual completion and scope

Automated coverage is not evidence that the city has reached its visual quality
target. The [visual completion roadmap](V1_VISUAL_COMPLETION_PLAN.md) separately
tracks README composition, road and archetype legibility, and controlled
cross-repository comparison. Completing the Pages check alone does not close
those tasks or automatically authorize a version promotion.

P0 FR-001 through FR-016 remain the functional v1 baseline. Existing optional
history, metropolis, and synthetic activity implementations are P2; their early
implementation is recorded in [the decision audit](DECISION_AUDIT.md), and
further expansion is deferred while visual completion is the priority.

See [current contracts](contracts/CURRENT_BASELINE.md) for UCG/City compatibility
and the limits of the original v0.1 specification examples.
