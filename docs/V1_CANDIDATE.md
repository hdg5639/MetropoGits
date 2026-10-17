# v1 candidate status

MetropoGits has reached a locally verified **v1 candidate** milestone. This is
a product-maturity statement, not a `1.0.0` package release, public deployment,
or license grant. The machine-readable source of truth remains
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
- The final repository audit passed 182 tests with one environment-specific
  symlink skip, repeated deterministic builds, and visual inspection of both
  render targets. Exact evidence is recorded in
  [`QUALITY_LOG.md`](QUALITY_LOG.md).

## Conditions for public v1 promotion

The following owner-controlled conditions remain intentionally unresolved:

1. **DEC-009 renderer decision:** either accept the current interactive
   isometric canvas as the v1 renderer through a recorded decision amendment,
   or retain the true-3D requirement and implement it. See
   [`DECISION_AUDIT.md`](DECISION_AUDIT.md).
2. **Project license:** select and add an explicit project license before a
   public release or external contributions are invited.
3. **Pages publication:** explicitly opt into GitHub Pages publication and
   verify the generated viewer at its repository-subpath URL.

Until all three conditions are resolved, the project stays a v1 candidate,
`release/readiness.json` stays `BLOCKED`, and no `v1.0.0` tag or package-version
promotion should be created.
