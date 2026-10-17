# README showcase

`build` now emits two CPU-rendered static SVG files from the same validated
`city.json` and `graph.ucg.json`:

| File | Purpose |
| --- | --- |
| `showcase.svg` | 3/4 isometric README composition, major labels, visual block aggregates and bounded routes |
| `preview.svg` | Detailed top-down structural view and existing viewer fallback link |

`README_SNIPPET.md` links the showcase to `index.html`. Both SVG files are
listed with their size and SHA-256 in `manifest.json`. The composite Action
returns the same artifact-directory output as before, now including showcase.

```powershell
metropogits build --repo path/to/project --out dist
metropogits render --scene dist/city.json --graph dist/graph.ucg.json --mode showcase --out showcase.svg --width 1200 --height 675
```

The default `render` mode remains `detail`. Standalone render does not update
a build manifest; rerun `build` when regenerating a complete artifact bundle.
Rendering requires neither a browser nor Node, GPU, network access, or target
repository execution. A browser is used only to inspect development captures.

## What the image means

Below 256 files, real file buildings are shown. At 256 or more, the same
ADR-012 blocks used by WebGL overview produce representative masses. These
summarize complete member lists and are explicitly visual aggregates. Their
heights are aggregate massing, not source line counts or runtime activity.

Archetype cuboids match the WebGL forms. Unsupported languages retain generic
file buildings; geometry alone does not establish a service or technology.
Major labels come from directory structure. Duplicate short labels include
path context, and overlapping labels are suppressed with their IDs recorded.

Neutral street surfaces describe space between code districts. Evidence routes
keep canonical polylines and exact edge lists; inter-major-district routes rank
first, then distinct edge count and stable ID. At most 24 routes are displayed.
They are not literal links to each relocated aggregate mass. The original graph
and all networks remain available in the viewer.

## Trace metadata

The SVG's `metadata#showcase-metadata` element contains escaped, non-executable
JSON with `projectionVersion: showcase/0.1`, the UCG digest, and `mappings`.
Each `data-map-id` on rendered geometry indexes this mapping:

- `file`: canonical entity and district IDs;
- `visual-block`: complete sorted member file/district IDs and owning district;
- `network`: existing network identity and exact `edgeIds`;
- `district`: canonical district identity;
- `structural-streets`: explicit `semantic: false`.

`hiddenNetworkIds` discloses omitted routes. Labels, omitted label IDs, selected
quarter-turn camera and fitted bounds are recorded too. `boundingBoxOccupancy`
measures the fitted geometry envelope divided by the content area.
`paintedAreaOccupancy` is a deterministic 160x90 center-sampled estimate of
polygon coverage, including terrain and buildings but excluding text and route
strokes. These metrics are distinct: bounding-box fit is not land density.

SVG titles and descriptions disclose context; the image does not embed an
interactive evidence inspector. Use the linked static viewer for that task.
Metadata has the same source-path sensitivity as the graph.

## Verification and limitations

Python/JavaScript parity tests cover block membership, plot geometry,
representative placement and all existing building forms. Numeric geometry
uses tolerance; fixed Python builds and SVG bytes must match exactly. Browser
locale list ordering is not treated as a geometric difference.

The camera selects among four fixed quarter-turns, fits every visible surface
and building top, and protects the header/footer. No canonical coordinates are
repacked. Tall input can still leave unused space; this is a presentation
improvement, not a new allocator. Dense plots and thin routes may still benefit
from the remaining road/landmark work in the visual roadmap.

The new artifact does not activate Pages or publish external test repositories.
See [ADR-013](adr/ADR-013.md) for the contract and rollout rationale.
