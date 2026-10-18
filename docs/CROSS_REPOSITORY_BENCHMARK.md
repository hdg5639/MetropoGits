# Cross-repository benchmark

## Purpose and reproducible workflow

Validate AC-001/002/007/012/014 and unknown-language usability beyond the two
Java-heavy repositories. This is not a new language-support claim or promotion
of ADR-020 into the default build. Inputs are read-only local clones; no target
dependencies, build scripts, configuration JS or application code are executed.

From the engine repository, with Git on PATH:

```powershell
python -m scripts.repository_benchmark --repo ../visual_test_proj/realworld --repo ../visual_test_proj/bat --repo ../visual_test_proj/pocketbase --repo ../visual_test_proj/fastapi-realworld-example-app --repo ../visual_test_proj/ratatui --repo ../visual_test_proj/lazygit --repo ../visual_test_proj/sqlitebrowser --out ../artifacts/visual/cross-repository-r2 --streets
```

Always choose a NEW output directory. The script rejects output inside an input,
pins HEAD and tracked dirty state, builds twice with default scan limits, compares
every artifact hash and building position, and optionally derives/packages aligned
curved streets twice. Partial analysis is retained and reported; mismatches/errors
fail the benchmark. Generated data stays outside source control. Eligible untracked
files can be scanned; graph hashes, not HEAD alone, identify the analyzed input.

`report.json` separates scanned FILE denominator, language-adapter processing,
non-structural edge types/confidence, unresolved diagnostics, archetypes, dimensions,
canonical hashes and observed timing. `CONTAINS` and `DECLARES` are not dependency
counts. Manifest-only `DEPENDS_ON` is explicitly separate from code imports.
An unresolved-diagnostic count cannot estimate missing edges or resolution accuracy.

First build has cProfile enabled; named stage times are cumulative and must NOT be
summed or compared directly with the unprofiled second build. Stages are scanning,
structural UCG construction, bundled language/catalog enrichment, layout, access
routing, CPU preview, CPU showcase and viewer packaging. Experimental derivation
and packaging have separate wall times. Measurements are observational Windows
Python 3.11.9 samples, not a cold-cache or exclusive-machine performance benchmark.

For actual WebGL comparison run:

```powershell
node scripts/viewer_audit.mjs "C:/Program Files/Google/Chrome/Application/chrome.exe" ../artifacts/visual/cross-repository-audit-r7 ../artifacts/visual/cross-repository-r2/realworld/streets ../artifacts/visual/cross-repository-r2/bat/streets ../artifacts/visual/cross-repository-r2/pocketbase/streets ../artifacts/visual/cross-repository-r2/fastapi-realworld-example-app/streets ../artifacts/visual/cross-repository-r2/ratatui/streets ../artifacts/visual/cross-repository-r2/lazygit/streets ../artifacts/visual/cross-repository-r2/sqlitebrowser/streets
```

The browser harness verifies bundled JS before running it, captures natural default
framing plus three explicit LODs and a common-world-scale view, exercises navigation
and available evidenced routes, and captures both SVG outputs. Sparse routes may
require a higher camera angle to click through building occlusion; the overview
comparison itself keeps the common yaw/pitch. Unsupported zero-network cities have
Synthetic **not applicable**, not a fabricated moving-traffic pass. Draw calls and
CDP JS heap size are recorded; heap is not process/GPU memory. CPU submission p95
is NOT display FPS or GPU completion. Those remain unmeasured on this headless
SwiftShader setup. Raw timing includes instrumentation and must not become an SLA.

## Initial corpus — 2026-10-18, engine parent 0cdbc83

| Repository | Pinned revision | Buildings / districts | Adapter processed | Non-structural edges | Second build seconds |
|---|---|---:|---:|---|---:|
| realworld | df796708040f5200ec572b28ab7f88ecee5794dd | 42 / 15 | 18 / 42 | 2 imports + 10 declared packages | 0.30 |
| bat | f748c1a467ae161682849949a7d036ab8362f9ba | 142 / 80 | 11 / 142 | 2 imports | 0.97 |
| pocketbase | 6f370ea741f33adf889eef02e3c1b884a47aa522 | 664 / 109 | 207 / 664 | 204 imports + 8 declared packages | 10.67 |
| fastapi-realworld-example-app | 9db981ca40aea36e5aa326a770278d8fe20c0b21 | 60 / 18 | 0 / 60 | 0 | 0.32 |
| ratatui | 0297560d8d77871c0281a39182e4e650856e2ffd | 244 / 117 | 0 / 244 | 0 | 2.38 |
| lazygit | 4e1eebe278790f257a875da6633234391a5a85b3 | 1302 / 94 | 0 / 1302 | 0 | 24.13 |
| sqlitebrowser | ae32df153a64d250de7c77a5057deeff4092a39b | 506 / 27 | **24 / 506, invalid classification** | 0 | 5.09 |

All seven repeat base artifact bytes, building positions and experimental street
artifacts match. All buildings are generic. This is useful structural fallback,
not seven successful semantic analyzers. `COMPLETE` means pipeline completion,
not complete language understanding. Baseline realworld/bat/sqlitebrowser are
PARTIAL; others COMPLETE, with limitations still present in diagnostics.

Important interpretation:

- Realworld: 24 Svelte files are structural-only. 26 unresolved import diagnostics
  and unsupported generated-config inheritance are visible. No SvelteKit semantic
  recognition claim. `$lib` resolution needs a separately evidenced solution,
  never running `svelte.config.js` or generating `.svelte-kit` as a side effect.
- Bat: 62 Rust files have no adapter. Java/JS/TS processing comes from test/sample
  files, not Rust support. One TS sample is skipped. The two imports do not form
  local building-to-building networks; there are zero animated networks.
- PocketBase: all 457 Go files are structural-only; the 207 processed files are
  JS/TS. 23 unresolved imports remain. The experiment assigns 140/192 existing
  file trips to streets, retaining 52 explicit legacy fallbacks.
- FastAPI/Ratatui/Lazygit: no Python/Rust/Go relationship extraction. An absence
  of dependency edges is a capability limitation, NOT architectural isolation.
- SQLite Browser: `.ts` Qt translation XML was misidentified as TypeScript.
  This is a real scanner bug, not coverage. Fix it before citing this row as
  analyzer performance; retain the baseline for comparison.

Structural street segment counts are 125/402/1908/155/758/3211/1044 in table
order; local bend supports 4/15/44/3/10/52/16. Street infrastructure is explicitly
visual/non-semantic and exists independently of relationships. Whole staircase
replacement and roundabouts remain unimplemented; these runs do not claim them.

## Visual findings and next gates

The captured cities have different silhouettes: Realworld is a small sparse
campus, Bat is elongated with a large sample district, and PocketBase/Lazygit
are broader multi-block cities. Neutral generic masses still dominate. The
common-scale gallery prevents treating individual auto-fit zoom as equal scale.
Forced Overview on small cities exposes oversized aggregate silhouettes and
clipping; their actual default naturally uses Detail and does not show that
forced-LOD defect. Track this as a LOD composition correction, not a claim that
the default is broken. PocketBase's actual showcase is legible but remains gray
and repetitive. Curves are local accents, not a transformed city model.

Next priorities:

1. Correct Qt translation discrimination with negative TypeScript fixtures (done below).
2. Make aggregate geometry/framing respect small-city scale across LODs.
3. Continue coherent corridor/staircase replacement under unchanged provenance,
   comparing large relation-rich GJ/OJ and at least one new low-semantic case.
4. Consider language adapters as separate, explicitly tested work. Do not hide
   missing relationships with invented traffic or infer services from names.
5. Re-run this corpus after changes; record shifted coordinates and changed
   canonical facts separately from the presentation-only curve experiment.

## Qt translation correction — same corpus revision

The scanner now recognizes XML declarations or explicit Qt TS document headers
within its existing bounded sniff buffer for `.ts` files. It never loads a DTD,
expands an entity or executes source. Detected documents retain their FILE IDs
and generic buildings with language `xml`, plus an INFO diagnostic. Strings,
TypeScript comments/generics/type assertions and `.tsx` are negative fixtures.
This is content-type disambiguation, not Qt framework or C++ semantic support.
Headers beyond the sniff window are not claimed to be detected.

```powershell
python -m scripts.repository_benchmark --repo ../visual_test_proj/sqlitebrowser --out ../artifacts/visual/cross-repository-qt-r1 --streets
node scripts/viewer_audit.mjs "C:/Program Files/Google/Chrome/Application/chrome.exe" ../artifacts/visual/cross-repository-qt-audit-r1 ../artifacts/visual/cross-repository-qt-r1/sqlitebrowser/streets
```

All27 translation documents are now XML; adapter processed24->0, structural-only
506/506, networks0, statusPARTIAL->COMPLETE (the spurious JS/TS skip warnings
disappear). This status change does NOT mean C++ support. Repeated base and curved
artifacts match. All506 building IDs, ownership, positions, sizes and archetypes
and all27 district bounds match the baseline. The27 language-derived styleVariant
strings correctly change typescript->xml; the UCG digest changes accordingly.
Street routing digest,1044 structural segments and16 bends stay unchanged.
Unprofiled second build2.38s versus baseline5.09s is an observed sample, not a
controlled performance claim. Reanalysis of the other six repositories yields
exactly the previous canonical graph hashes.

Updated local entry page: `artifacts/visual/cross-repository-reviewed-r1/index.html`.
It preserves the original seven-case benchmark and links the corrected SQLite
viewer separately. Browser capture confirms the same city shape and zero-network
Synthetic unavailable state. Documentation/tooling commit660c0e1 is pushed to
experiment/street-grid; this scanner correction is a separate work unit.
