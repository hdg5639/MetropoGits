# Procedural architecture catalog

Implementation: `architecture/0.4`, [ADR-059](adr/ADR-059.md),
[height separation ADR-063](adr/ADR-063.md).
Based on the maintainer's `MetropoGits_Procedural_Architecture_Catalog.md` proposal.

## Delivered vocabulary and usage

`--building-style catalog` is an additive experimental World export style.
It compiles85 named recipes from25 shared massing grammars and six primitives:
box, chamfered prism, gable, sawtooth, drum, dome. A shared verification complex
combines the same primitives for certified groups. These are presentation
vocabulary entries, **not85 bespoke models or85 proven analyzer capabilities**.
Stronger semantic names stay dormant without corresponding source evidence.

Forms include street rows, bars, terraces, twin slabs, U-courts, pavilions,
access pylons, glazed halls, loading wings, toothed roofs, archive halls,
round hubs, silos, domes, gantries and modular stacks. Unknown files get neutral
row/midrise/tower/depot choices rather than guessed semantic facilities.

```powershell
python scripts/procedural_world.py <existing-build> --out <new-output> `
  --zoning neighborhoods --pattern-scale adaptive --planning varied --outline varied `
  --street-policy porous --street-hierarchy --campus --campus-style programmed `
  --campus-landmarks --building-style catalog --seed <fixed-seed>
```

Keep the usual terrain option if needed. Catalog styling does not regenerate
terrain, change zoning, shift parcels or add routes. Existing `semantic`,
`architectural` and `purposeful` styles retain their prior behavior.

## Evidence and selection

- DIRECT/RESOLVED file-role claims with existing evidence enable semantic recipes.
  The public source archetype is unchanged. Services choose bars/terraces/courts,
  API roles access halls/gates, persistence warehouses, UI galleries/pavilions,
  tests verification labs/inspection halls. Models do not acquire a guessed DB.
- Configuration gets a neutral configuration workshop, not an invented CI or
  Kubernetes facility. Data processing is labeled processing, not research.
- TEST alone never proves simulation/fuzzing/benchmarking; auth alone never
  proves tokens, policy storage or auditing. Such names require explicit roles.
- Kafka/RabbitMQ appearances require a messaging role and local usage evidence;
  manifest/path-only technologies cannot activate them. Proven React/Vue/Svelte
  usage may add glazing to already verified UI roles.
- Inspectors show recipe/version, source-role gate, original evidence and actual
  rendered height inside the old source height envelope.

The versioned registry is `metropogits/world/architecture_catalog.py`, not target
repository code or executable user configuration. Dormant recipes remain
geometry prototypes, not claims that their technologies are recognized.

## Geometry and stability

`hash(worldSeed, stableEntityId, massingSeedVersion)` supplies independent
footprint, facade, roof and prop streams. Role/local-neighbour changes affect
the relevant source, not unrelated forms. This does not fix all underlying
world-allocator placement churn.

The0.2 frontage revision pins `massingSeedVersion` to `architecture/0.1`:
adding an entrance must not reroll every existing silhouette/material/roof.
Ground-floor walls receive a sheltered glazed lobby or, for already evidenced
data/logistics families, a shutter/loading canopy. These are **architectural
metaphors**, not new semantic claims or real doors detected in code. Unknowns
get a neutral sheltered entrance, with no invented role.

Modules face local +Z (the existing frontage yaw), attach to an actual ground
wall, and remain inside the original reserve. Open gateway/courtyard centres
are not filled with a floating lobby. Physical-unit height/projection caps
avoid giant doors on tall narrow lots. Wide public canopies may have two side
posts; the central approach remains clear. When no safe frontage room exists,
the module is omitted rather than moving buildings or intruding into roads.
Certified source complexes use the same treatment without changing membership.
Private `frontageDetail` metadata explicitly labels the treatment decorative;
source entrances and exact dependency paths remain untouched.

Each part stays inside the original rotated footprint and the independently
reconstructed architectural height capacity (0.4 onward). Keep frontage yaw,
original source door, graph IDs and exact source trips. Low
hall/warehouse/row massing is limited by real parcel span, and roof rise by
physical bay width. Drums/domes use physical aspect limits: tall thin legacy
envelopes cannot create needle roofs/domes. The legacy source-scene height is
no longer an architectural ceiling. Props never imply deployed instance counts.

Per-source budgets:18 parts and240 polygon faces. Invalid recipes/budget overflow
fail explicitly instead of dropping files. Certified compounds are restyled in
place, never regrouped; membership, proof, persistent LOD and expansion remain.
Verification complexes combine hall/roof/anchor volumes, not new source facilities.

Certified campus groups additionally use `campus-massing/0.1`: source-program
evidence selects large comb halls, archive wings, application tower/court,
terraced galleries, connected compute volumes or tooling workshops. Generic
groups retain their neutral aggregate; data models alone do not become storage
facilities. These are private export silhouettes, not new catalog entries or
source entities. Wide/deep lot adaptation and physical height caps preserve
the same certified footprint and exact source routes. Their versioned
`architecture.campusMassing` profile discloses layout, program and role evidence.
See [architectural scale plan](ARCHITECTURAL_SCALE_PLAN.md) and
`tests/test_campus_architecture.py` for the explicit limits and checks.

## Shared rendering and compatibility

### Architectural height separation — 0.4

`physical-height/0.1` replaces the minimum with the original source height.
Capacity = smaller actual footprint span × the form's documented aspect ratio;
e.g. tower7, bar3.5, warehouse1.5. A6-unit tower envelope can be42 high, and
a20-unit tower envelope140 high: there is no replacement universal42-unit cap.
These are conservative architectural proportions, not code-size, import-count,
business-importance or deployed-instance facts. Low/round roof aspect limits
remain in the compiler. No new random-height stream or reference multiplier.

Canonical City/World `height` remains unchanged for compatibility. Derived
world-view/0.2 models use architectural `height` and retain `sourceHeight`;
profiles store `heightPolicy` and actual `renderedHeight`. A separate validator
reconstructs the form/capacity and checks every part/mesh plus original ground
geography. CPU/WebGL/camera/LOD/picking/shadows use this same physical model;
the inspector distinguishes legacy height from architectural capacity.

Catalog0.4 also retires reference-skyline massing and the per-Service incoming
count recipe bias. Changing a file's incoming count cannot assign a skyscraper
or HQ. The old module is retained only for historical diagnostic tests/artifacts.
Semantic/purposeful/architectural styles and saved old packages keep their old
meaning. This removes the capacity coupling; it does NOT implement the new
UrbanCharacterProfile or composed master-planned city. See the
[redesign ledger](URBAN_REDESIGN_EXECUTION.md).

### Historical0.3 reference centers — retired from current catalog

The following describes archived0.3 behavior only, not the new planning engine.

Version0.3 adds `reference-skyline/0.1`, a presentation modifier, NOT a real
business district or runtime-load claim. Within existing directory ownership,
an eligible source needs six distinct DIRECT/RESOLVED incoming local files,
eight nearby eligible lots and two actual nearby file neighbours. Fixed radius48,
center separation96 and at most3 centers per owner bound the extent. Manifest
dependencies and unresolved/inferred edges cannot create centers. Duplicate
symbol observations never inflate the unique-file count.

Existing generic/service/interface buildings may participate; unknown sources
remain semantically unknown. Campus source layers, gates, tests, storage and
other specialized facilities retain their previous forms. The center gets a
setback tower, actual linked neighbours get midrise bars/terraces, while nearby
unlinked context retains its existing varied form at a lower height. Proximity
does NOT create a relationship. Private `skyline` profiles disclose tier, center
entity, observed counts, proof and the non-relational context distinction;
the existing source inspector labels the center as static-reference-derived.

All masses remain inside original source footprint/yaw/height capacity. The
budget is capped by2.8 times the smaller span, then multiplied by1/.78 for
core/linked and.66/.42 for high-/low-reference context. No individual source,
source role, district, terrain, street, doorway, campus or exact trip is moved.
This produces relative hierarchy, NOT a skyscraper district or land-use replan.
General program-sized physical envelopes remain unfinished separate work.
Fixed thresholds and local distance avoid repository-wide percentile churn;
spatial work is explicitly capped at300000 checks, with a clear failure.

The maintained plain-Python `reference-center` fixture proves that an ordinary
shared function can produce a structural center without invented Service/DB
roles. The unsupported-Elixir fixture has no evidenced local graph and keeps
its prior neutral architecture. Tests cover confidence negatives, owner/space
separation, repetition/order, budgets, physical bounds and source immutability.

### Common rendering

Offline-compiled private `meshFaces` and material hints feed CPU SVG, Canvas and
WebGL. Renderers do not classify sources independently. Round/angled roofs are
bounded polygon meshes, not a new model library or scene format.

Restyling an existing world keeps UCG/City/World/Planning bytes identical. This
is not the proposal's public scene-field migration. Manifest options record the
architecture version; private profiles retain original entity/evidence references.
CPU previews show new massing but not WebGL shader-texture/shadow parity.

Keep triangle batching, cached lighting and shader window detail; Synthetic
does not rebuild architecture. Additional faces cost initial compile/upload
time. Benchmark the actual runner; do not claim universal FPS. Current WebGL
picking retains conservative source envelopes, not precision GPU picking.

## Verification and remaining scope

`tests/test_architecture_catalog.py` covers85 recipes at multiple yaws, bounds,
normals/dome poles, aspect caps, evidence negatives, limits, deterministic
packages, canonical byte preservation, compound/route fidelity, unrelated
graph edits and a maintained unsupported-Elixir fixture. Real browser reviews
include GJ/OJ/PocketBase/SQLiteBrowser and three LODs, with source controls.

See [QUALITY_LOG](QUALITY_LOG.md) for exact commands/revisions, actual selected
recipe counts, matched/grayscale captures and measured costs. The grayscale
atlas is labeled **geometry prototypes, not a fabricated source-backed city**.

Not delivered: automatic recognition for every specialized proposal category,
new source metrics, binary scene migration, streamed chunks, precise GPU picking,
hardware instancing, or photorealistic assets.85 recipe names do not imply them.
