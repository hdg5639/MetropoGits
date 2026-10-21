# Procedural architecture catalog

Implementation: `architecture/0.2`, [ADR-059](adr/ADR-059.md).
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

Each part stays inside the original rotated footprint/height capacity. Keep
frontage yaw, original source door, graph IDs and exact source trips. Low
hall/warehouse/row massing is limited by real parcel span, and roof rise by
physical bay width. Drums/domes use physical aspect limits: tall thin legacy
envelopes cannot create needle roofs/domes. Original height is a capacity bound,
not a mandatory visible roof top. Props never imply deployed instance counts.

Per-source budgets:18 parts and240 polygon faces. Invalid recipes/budget overflow
fail explicitly instead of dropping files. Certified compounds are restyled in
place, never regrouped; membership, proof, persistent LOD and expansion remain.
Verification complexes combine hall/roof/anchor volumes, not new source facilities.

## Shared rendering and compatibility

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
