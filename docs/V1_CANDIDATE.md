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
- The final repository audit passed 182 tests with one environment-specific
  symlink skip, repeated deterministic builds, and visual inspection of both
  render targets. Exact evidence is recorded in
  [`QUALITY_LOG.md`](QUALITY_LOG.md).

## Conditions for public v1 promotion

The following promotion conditions remain intentionally unresolved:

1. **DEC-009 renderer implementation:** [`ADR-005`](adr/ADR-005.md) requires a
   genuine interactive 3D viewer for stable v1. The current isometric renderer
   remains the deterministic preview and non-WebGL fallback.
2. **Pages publication:** explicitly opt into GitHub Pages publication and
   verify the generated viewer at its repository-subpath URL.

Until both conditions are resolved, the project stays a v1 candidate,
`release/readiness.json` stays `BLOCKED`, and no `v1.0.0` tag or package-version
promotion should be created.
