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
