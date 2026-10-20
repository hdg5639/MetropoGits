# Rich WebGL materials

The static viewer now starts with **Rich materials** enabled. Its toolbar button
switches surface detailing, daylight and shadows off without moving the camera
or changing the source data. Role colours, filters, source inspection, aggregate
expansion and exact relationship paths retain their existing controls.

## Appearance

- Facade-local window bays, floor joints, glazing, punched masonry, fine brick
  joints and metal ribs; stable file identity selects one of four surface families.
- Roof tile seams and edge coping. Existing role accents remain on the roof;
  materials do not infer a technology, purpose, occupancy or actual construction.
- Asphalt grain, paving joints, grass variation, slope-sensitive rock tones and
  static water ripples/Fresnel-like reflection. Water is not a flow simulation.
- Warm directional sunlight, cool sky fill, limited distance haze, and soft sun
  shadows that ground buildings, source complexes and decorative trees.
- Smooth decorative tree crowns within existing tree reserves, not new sites.

Everything is calculated locally from the bundled code. No bitmap downloads,
remote service, AI runtime, texture licence dependency or added renderer library.
This suits arbitrary source footprints and street-facing rotation. Window rows
are visual detail, not source metrics or measured occupied floors.

## Cost and fallbacks

The triangle batch remains a batch: windows are not individual objects/draw calls.
Internal vertices use15 floats instead of9 (position/normal/colour plus local
surface coordinates, material parameters and face extent). This increases vertex
storage and dynamic Synthetic uploads; it is not a cost-free change.

One RGBA8 shadow texture, bounded by device limits and2048 pixels per side, uses
a DEPTH_COMPONENT16 renderbuffer. A five-tap filter softens shadow edges. The
additional shadow draw happens only when the static triangle array changes, not
on camera movement or Synthetic animation. Small casts can look coarse in a very
large city; this is not cascaded, ray-traced or contact-hardening shadowing.

Unsupported fragment highp or an incomplete shadow framebuffer disables only
shadows. A complete1x1 white texture keeps WebGL1 sampler validation safe.
Without OES_standard_derivatives, window smoothing uses a fixed fallback.
If WebGL cannot initialize, the existing Canvas viewer remains available.
Rounded crowns use at most32 quads per tree for at most4096 trees; larger sets
retain the previous bounded tree representation. Turning rich shading off keeps
these decorative crowns but disables the advanced surface/light treatment.

CPU `preview.svg` / `showcase.svg` retain their deterministic geometry-based
appearance. They show the same source city, **not** these shader textures or
shadows. Use an explicitly captured WebGL image when reviewing rich materials;
do not substitute it for the canonical CPU preview or pretend parity.

## Validation

`tests/render_materials.test.mjs` covers arbitrary face rotation, sunlight bounds,
collinear clipped-water normals, bounded outward tree geometry and fallback/cache
guards. The trusted `scripts/viewer_audit.mjs` reports material capability state,
WebGL errors, actual triangle counts, draw calls and static/dynamic uploads.
See [QUALITY_LOG](QUALITY_LOG.md) for actual fixture revisions, commands, matched
captures and measured JS submission costs. Those measurements are not GPU FPS.

Contract decision: [ADR-058](adr/ADR-058.md). Public canonical data is unchanged.
