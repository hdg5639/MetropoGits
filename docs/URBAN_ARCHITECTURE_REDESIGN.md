# MetropoGits — Mandatory Urban Architecture Redesign

**Priority: Critical**

**Task Type:** Architectural redesign, not incremental visual polish.

**Implementation Status:** Required

## 1. Problem Statement

The current implementation does not satisfy the intended product vision.

MetropoGits currently produces small, repetitive structures with minor variations in height, color, and primitive geometry. Recent efforts to introduce downtowns and building hierarchy primarily identified highly referenced source files and emphasized their existing structures.

**THIS IS NOT WHAT THE USER REQUESTED.**

The intended result is a procedurally generated, architecturally convincing city whose urban identity is derived from the analyzed repository.

Depending on its architecture, a repository may produce:

- A massive metropolitan skyline with skyscraper clusters.
- A Pangyo Techno Valley-inspired technology and business district.
- A Gangnam/Seocho-inspired dense commercial and office downtown.
- A Manhattan/Times Square-inspired metropolitan core.
- A conventional mid-rise mixed-use city center.
- A distributed collection of smaller business districts.
- A research-oriented campus with laboratories, open spaces, and connected academic complexes.
- An industrial metropolis with expansive warehouses, logistics facilities, and supporting urban infrastructure.

These are **urban morphology references**, not literal geographical reconstructions.

The generated city must remain evidence-based and deterministic while achieving substantial architectural diversity.

---

## 2. Fundamental Architectural Principle

**Stop designing individual buildings first. Design the city that will contain them.**

The required planning hierarchy is:

```text
Repository Analysis
    ↓
Urban Character Analysis
    ↓
Spatial Demand Estimation
    ↓
World & District Allocation
    ↓
Semantic Zoning
    ↓
Urban Typology Selection
    ↓
Downtown / Campus / Industrial Master Planning
    ↓
Road Network & Urban Blocks
    ↓
Variable-Size Parcels
    ↓
Architectural Compounds & Individual Buildings
    ↓
Skyline Composition
    ↓
Procedural Architectural Detailing
    ↓
WebGL / Showcase Rendering
```

Do not reverse this dependency order.

**Building placement must follow urban planning, not dictate it.**

---

## 3. Implement an Urban Character Engine

Introduce a distinct analysis layer that determines the architectural character of each repository, district, and semantic zone.

The engine must consider normalized, evidence-backed structural indicators.

### Required indicators

- Source entity count and architectural scale.
- Internal and external dependency density.
- Dependency centralization and centrality distribution.
- Community and module structure.
- Semantic role distribution.
- Technology and framework capabilities.
- API exposure and interface concentration.
- Persistence and infrastructure prevalence.
- Module cohesion and coupling.
- Verified research, testing, and computation roles.
- Existing source-backed aggregate candidates.

Do not use raw reference counts as direct building-height assignments.

Do not assume that frequently imported enums, exception classes, shared types, or utilities represent major corporate headquarters.

### Expected output

A versioned, inspectable `UrbanCharacterProfile` describing:

- Degree of centralization.
- Urban density requirements.
- Number and relative importance of urban centers.
- Functional diversity.
- Vertical development potential.
- Industrial and campus development potential.
- Preferred downtown typologies.
- Evidence and decision rationale.

The profile must distinguish verified facts from derived aesthetic planning decisions.

---

## 4. Implement Distinct Downtown Generators

Each downtown typology must have **its own spatial composition rules**.

Changing colors or selecting different building variants is insufficient.

### A. TECHNOLOGY BUSINESS DISTRICT — Pangyo-inspired

Visual characteristics:

- Broad contemporary office buildings.
- Glass curtain-wall architecture.
- Medium-rise headquarters and selected taller landmarks.
- Large technology campuses.
- Connected business complexes.
- Wide streets, landscaped plazas, and pedestrian corridors.
- Strong horizontal architectural composition.
- Generous building footprints and public spaces.

The result should resemble a modern technology-business district, not a traditional CBD with different colors.

### B. DENSE BUSINESS DISTRICT — Gangnam/Seocho-inspired

Visual characteristics:

- Major boulevards lined with office towers.
- Dense concentrations of mid-rise and high-rise buildings.
- Narrower secondary streets.
- Mixed commercial podiums.
- Significant variation in height and frontage width.
- Distinctive corner buildings.
- Dense urban blocks.
- Gradual transitions toward lower-density neighborhoods.

A recognizable skyline must emerge from the relationship between buildings, streets, and block density.

### C. METROPOLITAN CORE — Manhattan-inspired

Visual characteristics:

- Strong vertical skyline.
- Several substantial skyscraper clusters.
- One or more dominant skyline landmarks.
- Dense urban street grid with selected diagonal interventions.
- Large podiums and continuous street walls.
- Major intersections and pedestrian plazas.
- Strong variation between towers, podiums, and surrounding buildings.
- A recognizable transition from the urban core toward less intense districts.

This must not be represented by one tall building surrounded by tiny cubes.

### D. CONVENTIONAL MIXED-USE DOWNTOWN

Visual characteristics:

- Mostly mid-rise architecture.
- Moderate density.
- Civic and commercial centers.
- Public squares.
- Mixed building widths and heights.
- Irregular but connected neighborhood blocks.
- Continuous street frontage without excessive skyscrapers.

This should be the neutral fallback when the repository does not justify an extreme urban character.

### E. POLYCENTRIC METROPOLIS

Visual characteristics:

- Multiple recognizable downtowns.
- Distributed architectural landmarks.
- Connected business districts.
- Strong inter-district infrastructure.
- Functional specialization of individual centers.
- No artificially imposed single dominant skyline.

Use when repository structure supports multiple relatively independent architectural centers.

---

## 5. Redesign Campus Generation

The existing CAMPUS implementation must be evaluated against the intended visual outcome.

**A campus is not a rectangular lawn surrounded by repeated 8×8 buildings.**

A proper campus is an integrated spatial composition consisting of:

- Multiple connected or complementary building complexes.
- A recognizable central quad, garden, or pedestrian spine.
- Academic, research, administrative, and supporting architecture where backed by actual code roles.
- Shared outdoor spaces.
- Campus-scale building footprints.
- Landscaped pedestrian routes.
- Limited internal vehicle circulation.
- External road access.
- Variable building orientation.
- Architectural diversity across connected building groups.

Implement visually distinct campus typologies:

1. Academic Quadrangle.
2. Technology Research Park.
3. Urban University Campus.
4. Distributed Innovation Campus.
5. Riverside or Terrain-Adaptive Campus.

**Campus planning must reserve and organize an entire site before individual file buildings are placed.**

Use hierarchical source-backed compounds to reconcile multiple source entities with larger architectural complexes.

Do not fabricate source files, modules, technology roles, or dependencies.

---

## 6. Remove Uniform Building Scale Constraints

Audit and redesign fixed-size parcel assumptions.

The architectural system must support:

- Small standalone structures.
- Medium office buildings.
- Large horizontal headquarters.
- Multi-wing institutional complexes.
- Warehouse-scale industrial facilities.
- Mid-rise commercial blocks.
- High-rise office towers.
- Skyscrapers.
- Tower-on-podium architecture.
- Multiple connected towers.
- Open courtyard buildings.
- Distributed campus compounds.

Parcel size must be derived from architectural demand and available district capacity.

**Not every building should occupy an equivalent lot.**

Support flexible parcel sizes, parcel combination, block subdivision, setback rules, and shared spaces.

If spatial capacity is insufficient, replan the affected area instead of shrinking every architectural design into the same tiny envelope.

---

## 7. Skyline Composition Is Mandatory

Building height variation alone does not create a skyline.

Implement skyline composition at the district level.

Required capabilities:

- Primary and secondary skyline clusters.
- Variable height distributions.
- Architectural focal points.
- Mid-rise transitions.
- Low-rise supporting development.
- Road-aligned building groups.
- Controlled density gradients.
- Distinctive large-footprint structures.
- Multiple centers where structurally justified.

Height should depend on both semantic role and an explicit planning-level vertical hierarchy.

Use normalized repository characteristics so that small and large repositories can generate visually coherent cities.

**Do not equate individual file import count with skyscraper height.**

A source-backed compound may represent a major architectural structure without inventing additional logical code entities.

---

## 8. Architectural Diversity Must Be Structural

The architecture catalog must generate fundamentally different silhouettes.

Required silhouette families include:

- Slender skyscraper.
- Broad curtain-wall tower.
- Stepped setback tower.
- Twin-tower complex.
- Tower-on-podium.
- Mid-rise office slab.
- Courtyard headquarters.
- Connected campus buildings.
- Low industrial shed.
- Large logistics warehouse.
- Data-center complex.
- Research laboratory.
- Civic gateway structure.
- Pavilion cluster.
- Public atrium.
- Terraced or hillside building.

A different color, roof ornament, or additional cube does **not** count as a fundamentally different silhouette.

Architectural distinction must remain visible:

- In grayscale.
- From overview distance for major landmarks.
- At district level.
- From street-level camera perspectives.

Do not add hundreds of catalog entries that ultimately resolve to visually equivalent meshes.

Prefer a smaller number of substantially differentiated, composable building systems.

---

## 9. Required Spatial Composition

Buildings must belong to recognizable urban spaces.

Generate coherent relationships among:

- Arterial roads.
- Collector streets.
- Local streets.
- Service alleys.
- Pedestrian paths.
- Urban blocks.
- Corner parcels.
- Public plazas.
- Shared courtyards.
- Landscaped setbacks.
- Campus grounds.
- Industrial yards.
- Waterfront corridors.

Building orientation must follow its parcel and frontage geometry.

The same architectural design must adapt to the surrounding road and terrain context.

Preserve continuity between neighboring zones with different planning grammars.

---

## 10. Visual Reference Requirements

Use the following as conceptual morphology targets:

| Reference | Critical visual characteristics |
|---|---|
| Pangyo Techno Valley | Large modern office campuses, horizontal massing, landscaping |
| Gangnam/Seocho | Dense office streets, towers, commercial podiums, mixed scales |
| Manhattan / Times Square | Dramatic skyline, tightly integrated skyscraper clusters, landmarks |
| Conventional downtown | Medium-rise mixed-use blocks, civic spaces, balanced density |
| Research campus | Multi-building composition, pedestrian axes, greens, courtyards |
| Industrial district | Vast horizontal facilities, loading yards, service infrastructure |

Do not copy recognizable landmark buildings literally.

Use these environments to define **urban morphology**, not arbitrary theme labels.

---

## 11. Mandatory Acceptance Demonstration

The following is required before implementation can be declared complete.

### Test A — Distinct Typologies

Generate test scenes for every downtown typology using controlled architectural profiles.

All scenes must share a consistent neutral rendering style.

A reviewer must be able to distinguish the typologies primarily by:

- Skyline.
- Street layout.
- Density.
- Building footprints.
- Architectural massing.
- Open-space organization.

**Changing the color palette must not be the main difference.**

### Test B — Real Repository Results

Generate and inspect:

- GJ-Cloud.
- GamjaOJ.
- PocketBase.
- SQLiteBrowser.

Capture identical viewport sizes and camera policies at overview, district, and street-level scales.

Report the selected urban profile for each repository and the code-derived evidence supporting it.

Do not require every repository to generate a metropolitan skyscraper center.

### Test C — Campus Demonstration

Produce a recognizable campus with:

- Multiple different building complexes.
- A central landscape or pedestrian organizing feature.
- Coherent circulation.
- Architectural scale variation.
- No repetitive rings of identical small structures.

A campus without these properties is not complete.

### Test D — Integrity

Verify:

- No invented source entities.
- No fabricated relationships.
- All original source entities remain inspectable.
- Stable IDs are preserved.
- Deterministic generation remains intact.
- Road and building overlap constraints remain satisfied.
- Existing canonical data contracts remain compatible or are properly versioned.

### Test E — Performance

Measure:

- World generation time.
- Memory consumption.
- Generated geometry size.
- Draw calls.
- Browser frame times.
- LOD transitions.

Use instancing, shared geometry, offline mesh generation, and hierarchical representation where practical.

Do not sacrifice urban composition merely to preserve uniform building sizes.

---

## 12. Implementation Order

Follow these dependencies rather than implementing isolated decorative improvements:

1. Urban Character Profile.
2. Distinct downtown and campus master planners.
3. Flexible land and parcel allocation.
4. Source-backed architectural compounds.
5. District-scale skyline composition.
6. Architectural silhouette families.
7. Shared terrain, roads, and public-space integration.
8. Viewer and showcase rendering improvements.
9. Cross-repository visual and performance validation.

Do not replace the existing canonical analysis system.

Integrate new planning decisions through versioned, derived world-generation data.

---

## 13. Strict Definition of Done

The task is **NOT complete** when:

- High-reference files have been selected.
- A small number of buildings have been made taller.
- New architectural labels have been added.
- Additional primitive cube combinations have been implemented.
- Unit tests pass.
- Canonical hashes remain identical.
- A screenshot exists but has not been critically reviewed.

The task is complete only when:

1. Distinct urban typologies are visually recognizable.
2. The central business district resembles a plausible urban center.
3. Campus areas resemble actual campuses.
4. Large architectural complexes coexist with smaller buildings.
5. The resulting skyline has meaningful architectural hierarchy.
6. The city remains traceable to its repository.
7. Performance and determinism are validated.
8. Actual rendered outputs demonstrate substantial improvement.

If visual quality fails, identify the underlying architectural or planning limitation and revise it. Do not hide structural deficiencies through additional decorations or color adjustments.

---

## 14. Agent Operating Rules

Follow the repository's `AGENTS.md`, specifications, ADRs, and branch protection requirements.

- Work in isolated, reviewable tasks.
- Use the prescribed Conventional Commit format with bullet-point descriptions.
- Validate each implementation step.
- Review actual rendered artifacts regularly.
- Automatically push verified improvements only to authorized working branches.
- Never independently bypass protected `main`.
- Never add agent or AI co-author attribution.
- Do not invent success metrics or claim visual acceptance without inspecting the corresponding renders.
- Record before/after visual evidence and unresolved limitations.

**Do not claim the entire redesign is complete based on the first successful architectural change.**

---

## 15. Final Instruction

**Build an urban morphology generation system, not a reference-count visualization feature.**

The goal is for a developer to examine a generated city and recognize a convincing downtown, technology district, campus, or industrial region before inspecting the code metadata.

The architecture must be sufficiently distinctive that removing all category colors still leaves recognizable differences.

**A skyline is a composition of architecture. A downtown is a composition of urban spaces. A city is a composition of distinct districts.**

Implement accordingly.
