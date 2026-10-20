# Source-role facilities

2026-10-21. This extends source analysis with actual distinct silhouettes rather
than coloring every new role on a generic cube. Existing nine semantic forms
are joined by eleven families (20 explicit forms, plus generic variants).

| Source role | Archetype | Spatial form |
| --- | --- | --- |
| API_ENDPOINT | API_HUB | Two-wing arrivals hall with a continuous canopy |
| UI_COMPONENT | UI_PAVILION | Front portico and overhanging exhibition roof |
| CLI_ENTRYPOINT | CLI_TERMINAL | Concourse with a separate signal tower |
| DATA_MODEL | MODEL_ARCHIVE | Three progressively stepped archive stacks |
| DATA_PROCESSOR | DATA_LAB | Three processing halls on a shared podium |
| ML_COMPONENT | COMPUTE_LAB | Paired research towers linked by a bridge |
| AUTH_CONFIGURATION | SECURITY_STATION | Two checkpoint towers with a connecting gate |
| TASK_WORKER | WORKER_WORKSHOP | Multi-bay workshop roof and exhaust stack |
| OBJECT_STORAGE_ADAPTER | STORAGE_SILOS | Two independent storage stacks on a shared base |
| SEARCH_ADAPTER | SEARCH_LIBRARY | Courtyard wings and a rear indexing bridge |
| STATE_STORE | STATE_HUB | Three state towers under a connecting roof |

These facilities denote source roles, not a real university, processor cluster,
database instance or deployed runtime service. One analyzed file still owns one
building ID/envelope, possibly multiple cuboid parts; no fake files/entities are
created. All parts fit within the existing bounded file footprint and height.
Unknown evidence still produces generic buildings.

The authoritative new geometry and color table is
`metropogits/viewer_assets/facility-models.json`, packaged with the Python wheel.
CPU showcase, ordinary WebGL and Canvas fallback share the exact parts. World
rendering rotates those same parts using its existing frontage/terrain pipeline;
it does not rotate merely the enclosing box. Preview roof marks use the same
part footprints. History and metropolis viewer data retain the table. Older
saved viewer bundles keep their existing fallback behavior.

Neutral architectural wall tones and highest-roof role accents remain available
in World (`--building-style architectural`). Selection/filtering can restore
semantic color; changing colors never changes the evidence. Source lines,
confidence and imported-provider proof remain inspectable.

ENTRYPOINT/UI_PAGE retain GATE and TEST retains LIBRARY so persistent promoted
facilities are not removed. Inbound API_ENDPOINT now differs from outbound
HTTP_CLIENT (PORT); API envelope/height remain identical to the former PORT.
No wholesale re-layout is needed to demonstrate new building models.

Validation: real multi-language `polyglot-facilities` source fixture generates all
11 families, one generic package file, and real imports/references. Tests assert
complete source membership, provenance, unique bounded silhouettes, deterministic
generation, CPU/browser geometry parity and preservation of the previous API
envelope. QUALITY_LOG.md records real repository and World/browser inspections.

Not claimed: bespoke high-detail models for all 122 catalog technologies. Redis,
SQLAlchemy, Hibernate etc. correctly share a role family when evidence establishes
the same function. Additional silhouettes should improve comprehension, not add
technology logos or fabricate infrastructure.

## Source-purpose precincts and massing (ADR-056)

Use `--campus-style programmed --building-style purposeful` with adaptive
neighborhood/campus options. `campus-plan/0.7` derives validation, interface,
application, data, compute/tooling or neutral collaboration programs from actual
member role evidence. Programmed nonradial commons and role-plus-relationship
anchor selection retain mixed members; source-role sorting is not the objective.
Unknown/cohesive code is not renamed a research lab. Inspectors enumerate actual
role counts, anchor roles, supporting evidence and original members.

Unsafe or undersized forms retain a connected complete fabric neighborhood with
an explicit `programFallback`, or the original planning grammar. No geography is
enlarged to force a successful-looking tiny campus. All prior campus styles keep
their old meaning and source membership/road continuity gates.

The independent `purposeful` building presentation derives massing from existing
archetypes, unique observed local incoming/outgoing file neighbours, declaration
counts and real campus anchor membership. Shared service towers differ from
multi-target service courts; verification halls/benches/pavilions, galleries,
archive wings and storage/task halls provide bounded within-role variation.
These names explain static evidence, not exact runtime orchestration/test types.
Stable path variation supplies additional architectural handedness/form variety.

Rotated parts stay inside each original file footprint/height. This export-only
view does not change world.json, UCG, City, source doors, roads, trips or persistent
gate/test compounds. CPU, Canvas and WebGL consume the same compiled parts. The
inspector discloses derived form, neighbour counts and declaration counts.
Neutral walls/highest-roof role accents remain, with explicit full-role tint.
It is still low-poly massing, not detailed material assets or a runtime profiler.

## Campus-scale landmarks (ADR-057)

Add `--campus-landmarks` to a routed campus World export. This is independent
of per-file `purposeful` massing. A few certified complexes use the complete
clear parcel envelopes of actual nearby related files, rather than preserving
every tiny individual footprint. Maximum four per campus,16 members per complex,
56-unit span/36-unit height; insufficiently related or obstructed candidates
remain individual buildings. Counts are caps, not quotas.

Direct static edges and shared **local file targets** establish visual affinity.
For example, two tests using the same judge can share a verification hall even
without depending on one another. `sharedTargetIds` and exact `sourceEdgeIds`
preserve that distinction; this does not create a peer dependency. Module/zone
ownership stays separate; unknown roles are retained in accurate mixed counts.
External package popularity alone does not generate an anchor. Co-reference
candidate expansion is capped at128 contributors per local target.

Purpose-sensitive halls/podiums/anchor towers express validation, data,
application, interface, tooling, compute or neutral collaboration. They are
visual aggregates, not additional files, services, universities or departments.
World/City/UCG/Planning JSON and original source trips are unchanged. Public and
pedestrian streets, courts, nature and unrelated parcels remain clear; existing
constituent-only entrance spurs can terminate inside their shared facility.
Decorative trees are cleared from enlarged complexes, never used to mask errors.

CPU/Canvas/WebGL share compiled oriented geometry. Complexes persist at every
LOD until explicit expansion; filters restore only the actual matching members.
Inspectors disclose derived purpose, source/shared-target counts, evidence and
all original members. High-detail textures or realistic architectural assets
are not claimed by this change.
