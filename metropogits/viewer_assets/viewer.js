(() => {
  "use strict";

  if (globalThis.METROPOGITS_RENDERER === "webgl") return;

  const data = globalThis.METROPOGITS_DATA;
  const filterEngine = globalThis.METROPOGITS_FILTERS;
  const canvas = document.getElementById("city-canvas");
  const context = canvas.getContext("2d");
  const inspector = document.getElementById("inspector-content");
  const hoverLabel = document.getElementById("hover-label");
  const repositoryName = document.getElementById("repository-name");
  const cityStats = document.getElementById("city-stats");
  const clearFilters = document.getElementById("clear-filters");
  const filterSummary = document.getElementById("filter-summary");
  const detailLevel = document.getElementById("detail-level");
  const activityToggle = document.getElementById("synthetic-activity");
  const activityNote = document.getElementById("synthetic-activity-note");
  const activityEngine = globalThis.METROPOGITS_ACTIVITY;
  const rendererMode = document.getElementById("renderer-mode");
  const MAX_INITIAL_SCALE = 11;
  const filterControls = new Map(
    [...document.querySelectorAll("[data-filter]")].map((control) => [
      control.dataset.filter,
      control,
    ]),
  );

  if (!data || !data.scene || !data.ucg || !context || !filterEngine) {
    repositoryName.textContent = "Viewer data unavailable";
    return;
  }

  globalThis.METROPOGITS_RENDERER = "canvas-2d";
  canvas.setAttribute("aria-label", "Interactive isometric 2D repository city fallback");
  if (rendererMode) rendererMode.textContent = "2D fallback";

  const scene = data.scene;
  const ucg = data.ucg;
  const entities = new Map(ucg.entities.map((entity) => [entity.id, entity]));
  const edges = new Map(ucg.edges.map((edge) => [edge.id, edge]));
  const evidence = new Map(ucg.evidence.map((item) => [item.evidenceId, item]));
  const districts = new Map(scene.districts.map((district) => [district.id, district]));
  const districtTerritories = new Map(
    (data.territories?.districts || []).map((territory) => [territory.id, territory]),
  );
  const streetRectangles = data.streets?.surfaces || data.streets?.rectangles || [];
  const accessPolicy = filterEngine.createAccessPolicy(data.routing, data.roadHierarchy);
  let accessFrame = null;
  let accessPaint = new Map();
  function networkForId(id) {
    return accessPolicy?.network(id, accessFrame?.routeIds) || scene.networks.find(network => network.id === id);
  }
  function districtTerritory(district) {
    return districtTerritories.get(district.id) || {
      boundary: [
        [[district.x, district.z], [district.x + district.width, district.z]],
        [[district.x + district.width, district.z], [district.x + district.width, district.z + district.depth]],
        [[district.x + district.width, district.z + district.depth], [district.x, district.z + district.depth]],
        [[district.x, district.z + district.depth], [district.x, district.z]],
      ],
      bounds: {
        maxX: district.x + district.width,
        maxZ: district.z + district.depth,
        minX: district.x,
        minZ: district.z,
      },
      labelAnchor: [district.x + 2, district.z + 2],
      rectangles: [{
        depth: district.depth,
        width: district.width,
        x: district.x,
        z: district.z,
      }],
    };
  }
  const districtChildren = new Map();
  const districtsWithBuildings = new Set(
    scene.buildings.map((building) => building.districtId),
  );
  const buildingsByDistrict = new Map();
  for (const building of scene.buildings) {
    const members = buildingsByDistrict.get(building.districtId) || [];
    members.push(building);
    buildingsByDistrict.set(building.districtId, members);
  }
  const civicBlocks = [...buildingsByDistrict.entries()]
    .map(([districtId, members]) => ({
      districtId,
      maxX: Math.max(...members.map((building) => building.x + building.width)) + 1.1,
      maxZ: Math.max(...members.map((building) => building.z + building.depth)) + 1.1,
      minX: Math.min(...members.map((building) => building.x)) - 1.1,
      minZ: Math.min(...members.map((building) => building.z)) - 1.1,
    }))
    .sort((left, right) => left.districtId.localeCompare(right.districtId));
  for (const district of scene.districts) {
    if (district.parentId === null) continue;
    const children = districtChildren.get(district.parentId) || [];
    children.push(district.id);
    districtChildren.set(district.parentId, children);
  }
  const drawableDistrictIds = new Set(
    scene.districts
      .filter((district) => {
        const children = districtChildren.get(district.id) || [];
        if (districtsWithBuildings.has(district.id) || children.length !== 1) return true;
        const child = districts.get(children[0]);
        return !child
          || district.x !== child.x
          || district.z !== child.z
          || district.width !== child.width
          || district.depth !== child.depth;
      })
      .map((district) => district.id),
  );
  const districtDepths = new Map();
  function districtDepth(districtId) {
    if (districtDepths.has(districtId)) return districtDepths.get(districtId);
    const district = districts.get(districtId);
    const depth = district?.parentId === null
      ? 0
      : districtDepth(district.parentId) + 1;
    districtDepths.set(districtId, depth);
    return depth;
  }
  for (const district of scene.districts) districtDepth(district.id);
  const metropolis = globalThis.METROPOGITS_METROPOLIS;
  const repositoriesByRootDistrict = new Map(
    (metropolis?.repositories || []).map((repository) => [repository.rootDistrictId, repository]),
  );
  const filterIndex = filterEngine.createIndex(scene, ucg);
  const majorDistrictIds = new Set(filterEngine.majorDistrictIds(scene));
  const lodPolicy = filterEngine.createLodPolicy(scene, data.territories, data.streets, ucg);
  const expandedAggregateIds = new Set();
  let showAllNetworks = false;
  const aggregateFacilities = new Map(
    lodPolicy.aggregates.map((aggregate) => [aggregate.id, aggregate]),
  );
  const majorDistrictColors = [
    [24, 50, 74],
    [45, 40, 74],
    [24, 61, 55],
    [59, 43, 32],
    [53, 36, 63],
  ];
  const majorDistrictColorById = new Map(
    [...majorDistrictIds].sort().map((districtId, index) => [
      districtId,
      majorDistrictColors[index % majorDistrictColors.length],
    ]),
  );

  const colors = {
    CACHE_TOWER: ["#facc15", "#ca8a04", "#713f12"],
    CONTROL_CENTER: ["#a78bfa", "#6d28d9", "#4c1d95"],
    DOCUMENT_DEPOT: ["#fb923c", "#c2410c", "#7c2d12"],
    EXCHANGE: ["#2dd4bf", "#0f766e", "#134e4a"],
    GATE: ["#f472b6", "#be185d", "#831843"],
    GENERIC_BUILDING: ["#94a3b8", "#475569", "#334155"],
    LIBRARY: ["#facc15", "#a16207", "#713f12"],
    PORT: ["#38bdf8", "#0369a1", "#0c4a6e"],
    SERVICE_OFFICE: ["#60a5fa", "#1d4ed8", "#1e3a8a"],
    STRUCTURED_WAREHOUSE: ["#34d399", "#047857", "#064e3b"],
  };
  const networkColors = {
    DEPENDENCY_ROAD: "#a8b5c8",
    HTTP_HIGHWAY: "#f97316",
    MESSAGING_PATH: "#a855f7",
  };
  const networkProfiles = {
    DEPENDENCY_ROAD: { marking: 1.2, shoulder: 5, surface: 3 },
    HTTP_HIGHWAY: { marking: 2, shoulder: 8, surface: 5.5 },
    MESSAGING_PATH: { marking: 1.5, shoulder: 4, surface: 2.2 },
  };

  const state = {
    angle: -Math.PI / 4,
    activityEpoch: 0,
    dragging: false,
    dragMode: "pan",
    moveMode: true,
    filters: {
      confidence: "",
      language: "",
      role: "",
      technology: "",
    },
    moved: false,
    panX: 0,
    panY: 0,
    pointerX: 0,
    pointerY: 0,
    selected: null,
    syntheticActivity: false,
    zoom: 1,
  };
  let hitRegions = [];
  let districtLabelCandidates = [];
  let framePending = false;
  let visibleBuildingIds = new Set(scene.buildings.map((building) => building.entityId));
  let visibleNetworkIds = new Set(scene.networks.map((network) => network.id));
  let renderedAggregateIds = new Set();
  let renderedBuildingIds = new Set(visibleBuildingIds);
  let renderedDistrictIds = new Set(drawableDistrictIds);
  let renderedNetworkIds = new Set(visibleNetworkIds);
  let currentDetailLevel = "detail";
  let lodCacheKey = "";
  let visibilityVersion = 0;
  let viewportWidth = 1;
  let viewportHeight = 1;
  const reducedMotion = globalThis.matchMedia?.("(prefers-reduced-motion: reduce)");

  const worldBounds = (() => {
    if (!scene.districts.length) return { minX: 0, minZ: 0, maxX: 1, maxZ: 1 };
    const framingDistricts = scene.buildings.length >= 256 && majorDistrictIds.size
      ? [...majorDistrictIds].map((districtId) => districts.get(districtId)).filter(Boolean)
      : scene.districts;
    const bounds = framingDistricts.map(districtTerritory).reduce(
      (result, territory) => ({
        minX: Math.min(result.minX, territory.bounds.minX),
        minZ: Math.min(result.minZ, territory.bounds.minZ),
        maxX: Math.max(result.maxX, territory.bounds.maxX),
        maxZ: Math.max(result.maxZ, territory.bounds.maxZ),
      }),
      { minX: Infinity, minZ: Infinity, maxX: -Infinity, maxZ: -Infinity },
    );
    return Number.isFinite(bounds.minX)
      ? bounds
      : { minX: 0, minZ: 0, maxX: 1, maxZ: 1 };
  })();
  const worldCenter = {
    x: (worldBounds.minX + worldBounds.maxX) / 2,
    z: (worldBounds.minZ + worldBounds.maxZ) / 2,
  };

  function element(tagName, text, className) {
    const node = document.createElement(tagName);
    if (text !== undefined) node.textContent = String(text);
    if (className) node.className = className;
    return node;
  }

  function addStat(value, label) {
    cityStats.append(element("span", `${value} ${label}`, "stat"));
  }

  function displayValue(value) {
    return value.replaceAll("_", " ");
  }

  function populateFilter(name, values) {
    const control = filterControls.get(name);
    if (!control) return;
    const labels = {
      confidence: "evidence levels",
      language: "languages",
      role: "roles",
      technology: "technologies",
    };
    const allOption = element("option", `All ${labels[name]}`);
    allOption.value = "";
    control.append(allOption);
    for (const value of values) {
      const option = element("option", displayValue(value));
      option.value = value;
      control.append(option);
    }
    control.disabled = values.length === 0;
  }

  function activeFilterCount() {
    return Object.values(state.filters).filter(Boolean).length;
  }

  function updateLodVisibility() {
    const filtered = activeFilterCount() > 0;
    const nextDetailLevel = lodPolicy.levelForZoom(state.zoom, filtered);
    const selectionKey = state.selected
      ? `${state.selected.kind}:${state.selected.id}:${state.selected.routeId || ""}`
      : "none";
    const nextCacheKey = `${nextDetailLevel}:${visibilityVersion}:${selectionKey}:${showAllNetworks}:${[...expandedAggregateIds].sort().join('|')}`;
    if (nextCacheKey === lodCacheKey) return;
    currentDetailLevel = nextDetailLevel;
    lodCacheKey = nextCacheKey;
    const visible = lodPolicy.visibility(
      currentDetailLevel,
      visibleBuildingIds,
      visibleNetworkIds,
      state.selected,
      expandedAggregateIds,
      showAllNetworks,
    );
    renderedAggregateIds = new Set(visible.aggregateIds);
    renderedBuildingIds = new Set(visible.buildingIds);
    renderedNetworkIds = new Set(visible.networkIds);
    if (accessPolicy) {
      accessFrame = accessPolicy.frame(currentDetailLevel, visibleBuildingIds, visibleNetworkIds, state.selected,
        showAllNetworks, aggregateFacilities.get(state.selected?.id)?.memberEntityIds || []);
      const junctionGeometry=filterEngine.accessJunctionGeometry(accessFrame);
      accessPaint=new Map(accessFrame.segments.map(segment=>
        [segment.id,filterEngine.accessMarkingSegments(segment,junctionGeometry.trims)]));
      renderedNetworkIds = accessFrame.networkIds;
    }
    renderedDistrictIds = new Set(
      scene.districts
        .filter((district) => (
          drawableDistrictIds.has(district.id)
          && lodPolicy.districtVisible(district.id, currentDetailLevel)
        ))
        .map((district) => district.id),
    );
    if (state.selected?.kind === "district") renderedDistrictIds.add(state.selected.id);
    if (detailLevel) {
      const label = filtered
        ? "Filtered detail"
        : `${currentDetailLevel[0].toUpperCase()}${currentDetailLevel.slice(1)}`;
      const representedFiles = [...renderedAggregateIds].reduce(
        (sum, id) => sum + aggregateFacilities.get(id).memberEntityIds.length,
        0,
      );
      const subject = renderedAggregateIds.size
        ? `${renderedAggregateIds.size} aggregates (${representedFiles} files) + ${renderedBuildingIds.size} buildings`
        : `${renderedBuildingIds.size}/${visibleBuildingIds.size} buildings`;
      const routeLabel = state.selected?.kind === "building" && !showAllNetworks ? "related routes" : "routes";
      const routingStatus = accessFrame
        ? `${accessFrame.routes.length} relation paths / ${accessFrame.segments.length} shared segments${accessPolicy.unresolved ? ` · ${accessPolicy.unresolved} unrouted edges` : ""}`
        : `${renderedNetworkIds.size}/${visibleNetworkIds.size} ${routeLabel}`;
      const status = `${label} · ${subject} · ${routingStatus}${accessFrame?.focused ? " · Selected paths (x-ray)" : ""}${accessPolicy?.streetStatus || ''}`;
      if (detailLevel.textContent !== status) detailLevel.textContent = status;
    }
  }

  function selectionIsVisible() {
    if (!state.selected || state.selected.kind === "district") return true;
    if (state.selected.kind === "network" && accessPolicy) {
      return accessPolicy.choices(state.selected.id, visibleBuildingIds, visibleNetworkIds)
        .some(route => !state.selected.routeId || route.id === state.selected.routeId);
    }
    if (state.selected.kind === "aggregate") {
      return activeFilterCount() === 0 && aggregateFacilities.has(state.selected.id);
    }
    if (state.selected.kind === "building") {
      return visibleBuildingIds.has(state.selected.id);
    }
    return visibleNetworkIds.has(state.selected.id) || Boolean(accessPolicy?.segments.has(state.selected.id));
  }

  function resetInspector(message = "Choose a building, visual block, district, or network to inspect the repository facts behind it.") {
    inspector.replaceChildren();
    inspector.append(element("p", "INSPECTOR", "eyebrow"));
    inspector.append(element("h2", "Select a city element"));
    inspector.append(element("p", message, "muted"));
  }

  function applyFilters() {
    const visible = filterIndex.filter(state.filters);
    visibleBuildingIds = new Set(visible.buildingIds);
    visibleNetworkIds = new Set(visible.networkIds);
    visibilityVersion += 1;
    const activeCount = activeFilterCount();

    cityStats.replaceChildren();
    addStat(scene.districts.length, "districts");
    addStat(`${visibleBuildingIds.size}/${scene.buildings.length}`, "buildings");
    addStat(`${visibleNetworkIds.size}/${scene.networks.length}`, "networks");
    filterSummary.textContent = activeCount
      ? `${visibleBuildingIds.size} buildings and ${visibleNetworkIds.size} links match ${activeCount} filter${activeCount === 1 ? "" : "s"}`
      : "Showing the complete city";
    clearFilters.disabled = activeCount === 0;
    hoverLabel.hidden = true;
    if (!selectionIsVisible()) {
      state.selected = null;
      resetInspector("The previous selection is hidden by the active filters.");
    } else if (state.selected?.kind === "network") {
      showNetwork(state.selected.id);
    }
    scheduleRender();
  }

  repositoryName.textContent = ucg.repository.id;
  document.title = `${ucg.repository.id} · MetropoGits`;
  populateFilter("role", filterIndex.options.roles);
  populateFilter("language", filterIndex.options.languages);
  populateFilter("technology", filterIndex.options.technologies);
  populateFilter("confidence", filterIndex.options.confidences);

  function baseScale() {
    const corners = [
      rotatePoint(worldBounds.minX, worldBounds.minZ),
      rotatePoint(worldBounds.maxX, worldBounds.minZ),
      rotatePoint(worldBounds.maxX, worldBounds.maxZ),
      rotatePoint(worldBounds.minX, worldBounds.maxZ),
    ];
    const projectedXs = corners.map((point) => (point.x - point.z) * 0.72);
    const projectedYs = corners.map((point) => (point.x + point.z) * 0.36);
    const spanX = Math.max(...projectedXs) - Math.min(...projectedXs) || 1;
    const spanY = Math.max(...projectedYs) - Math.min(...projectedYs) || 1;
    const tallestBuilding = Math.max(0, ...scene.buildings.map((building) => building.height));
    return Math.max(
      0.45,
      Math.min(
        MAX_INITIAL_SCALE,
        Math.max(1, viewportWidth - 100) / spanX,
        Math.max(1, viewportHeight - 120) / (spanY + tallestBuilding * 0.72),
      ),
    );
  }

  function rotatePoint(x, z) {
    const centeredX = x - worldCenter.x;
    const centeredZ = z - worldCenter.z;
    const cosine = Math.cos(state.angle);
    const sine = Math.sin(state.angle);
    return {
      x: centeredX * cosine - centeredZ * sine,
      z: centeredX * sine + centeredZ * cosine,
    };
  }

  function project(x, z, height = 0) {
    const rotated = rotatePoint(x, z);
    const scale = baseScale() * state.zoom;
    return {
      x: viewportWidth / 2 + state.panX + (rotated.x - rotated.z) * 0.72 * scale,
      y:
        viewportHeight / 2 +
        state.panY +
        (rotated.x + rotated.z) * 0.36 * scale -
        height * 0.72 * scale,
    };
  }

  function polygonPath(points) {
    context.beginPath();
    context.moveTo(points[0].x, points[0].y);
    for (const point of points.slice(1)) context.lineTo(point.x, point.y);
    context.closePath();
  }

  function pointInPolygon(x, y, points) {
    let inside = false;
    for (let index = 0, previous = points.length - 1; index < points.length; previous = index++) {
      const currentPoint = points[index];
      const previousPoint = points[previous];
      const crosses =
        currentPoint.y > y !== previousPoint.y > y &&
        x <
          ((previousPoint.x - currentPoint.x) * (y - currentPoint.y)) /
            (previousPoint.y - currentPoint.y) +
            currentPoint.x;
      if (crosses) inside = !inside;
    }
    return inside;
  }

  function distanceToSegment(x, y, start, end) {
    const deltaX = end.x - start.x;
    const deltaY = end.y - start.y;
    const lengthSquared = deltaX * deltaX + deltaY * deltaY;
    if (!lengthSquared) return Math.hypot(x - start.x, y - start.y);
    const fraction = Math.max(
      0,
      Math.min(1, ((x - start.x) * deltaX + (y - start.y) * deltaY) / lengthSquared),
    );
    return Math.hypot(x - (start.x + fraction * deltaX), y - (start.y + fraction * deltaY));
  }

  function selected(kind, id) {
    return state.selected && state.selected.kind === kind && state.selected.id === id;
  }

  function drawGrid() {
    context.fillStyle = "#070b14";
    context.fillRect(0, 0, viewportWidth, viewportHeight);
    context.strokeStyle = "rgba(56, 189, 248, 0.075)";
    context.lineWidth = 1;
    const spacing = Math.max(24, 42 * state.zoom);
    for (let offset = -viewportHeight; offset < viewportWidth + viewportHeight; offset += spacing) {
      context.beginPath();
      context.moveTo(offset, 0);
      context.lineTo(offset + viewportHeight, viewportHeight);
      context.stroke();
      context.beginPath();
      context.moveTo(offset, viewportHeight);
      context.lineTo(offset + viewportHeight, 0);
      context.stroke();
    }
  }

  function districtLabel(district) {
    const entity = entities.get(district.id);
    const member = repositoriesByRootDistrict.get(district.id);
    return entity?.path || member?.id || (district.parentId === null ? ucg.repository.id : district.id);
  }

  function districtCanvasLabel(district) {
    const label = districtLabel(district);
    const segments = label.split("/").filter(Boolean);
    return segments.at(-1) || label;
  }

  function drawDistrict(district) {
    const territory = districtTerritory(district);
    context.fillStyle = selected("district", district.id)
      ? "rgba(14, 165, 233, 0.24)"
      : "rgba(30, 41, 59, 0.72)";
    for (const rectangle of territory.rectangles) {
      const points = [
        project(rectangle.x, rectangle.z),
        project(rectangle.x + rectangle.width, rectangle.z),
        project(rectangle.x + rectangle.width, rectangle.z + rectangle.depth),
        project(rectangle.x, rectangle.z + rectangle.depth),
      ];
      polygonPath(points);
      context.fill();
      hitRegions.push({ kind: "district", id: district.id, points });
    }
    context.strokeStyle = selected("district", district.id) ? "#38bdf8" : "#34445e";
    context.lineWidth = selected("district", district.id) ? 2.5 : 1;
    for (const segment of territory.boundary) {
      const start = project(segment[0][0], segment[0][1]);
      const end = project(segment[1][0], segment[1][1]);
      context.beginPath();
      context.moveTo(start.x, start.y);
      context.lineTo(end.x, end.y);
      context.stroke();
    }

    const major = majorDistrictIds.has(district.id);
    context.font = major
      ? "800 12px ui-sans-serif, system-ui, sans-serif"
      : "600 10px ui-sans-serif, system-ui, sans-serif";
    const label = districtCanvasLabel(district);
    const labelPoint = project(...territory.labelAnchor);
    const textWidth = Math.ceil(context.measureText(label).width);
    districtLabelCandidates.push({
      height: major ? 19 : 15,
      id: district.id,
      label,
      major,
      priority: (major ? 10000 : 0)
        + (districtsWithBuildings.has(district.id) ? 1000 : 0)
        + districtDepths.get(district.id),
      textX: labelPoint.x,
      textY: labelPoint.y - 5,
      width: textWidth + (major ? 16 : 6),
      x: labelPoint.x - 3,
      y: labelPoint.y - (major ? 19 : 16),
    });
  }

  function drawMajorDistrict(district) {
    const territory = districtTerritory(district);
    const channels = majorDistrictColorById.get(district.id) || [24, 50, 74];
    context.fillStyle = `rgba(${channels.join(", ")}, 0.24)`;
    for (const rectangle of territory.rectangles) {
      polygonPath([
        project(rectangle.x, rectangle.z, 0.04),
        project(rectangle.x + rectangle.width, rectangle.z, 0.04),
        project(rectangle.x + rectangle.width, rectangle.z + rectangle.depth, 0.04),
        project(rectangle.x, rectangle.z + rectangle.depth, 0.04),
      ]);
      context.fill();
    }
    context.strokeStyle = `rgba(${channels.map((value) => Math.min(255, value + 90)).join(", ")}, 0.95)`;
    context.lineWidth = 3;
    for (const segment of territory.boundary) {
      const start = project(segment[0][0], segment[0][1], 0.04);
      const end = project(segment[1][0], segment[1][1], 0.04);
      context.beginPath();
      context.moveTo(start.x, start.y);
      context.lineTo(end.x, end.y);
      context.stroke();
    }
  }

  function drawDistrictLabels() {
    const selectedIds = new Set(
      filterEngine.selectNonOverlappingLabels(
        districtLabelCandidates,
        viewportWidth,
        viewportHeight,
      ),
    );
    context.font = "600 10px ui-sans-serif, system-ui, sans-serif";
    for (const candidate of districtLabelCandidates) {
      if (!selectedIds.has(candidate.id)) continue;
      context.font = candidate.major || candidate.aggregate
        ? "800 12px ui-sans-serif, system-ui, sans-serif"
        : "600 10px ui-sans-serif, system-ui, sans-serif";
      context.fillStyle = candidate.aggregate
        ? "rgba(37, 26, 8, 0.94)"
        : candidate.major
        ? "rgba(8, 18, 32, 0.94)"
        : "rgba(7, 11, 20, 0.82)";
      context.fillRect(candidate.x, candidate.y, candidate.width, candidate.height);
      context.strokeStyle = candidate.aggregate
        ? "#fbbf24"
        : candidate.major
          ? "#38bdf8"
          : "rgba(100, 116, 139, 0.55)";
      context.lineWidth = candidate.major || candidate.aggregate ? 2 : 1;
      context.strokeRect(candidate.x, candidate.y, candidate.width, candidate.height);
      context.fillStyle = candidate.aggregate
        ? "#fef3c7"
        : candidate.major
          ? "#e0f2fe"
          : "#a8b5c8";
      context.fillText(candidate.label, candidate.textX, candidate.textY);
    }
  }

  function drawCivicBlock(block) {
    const points = [
      project(block.minX, block.minZ, 0.08),
      project(block.maxX, block.minZ, 0.08),
      project(block.maxX, block.maxZ, 0.08),
      project(block.minX, block.maxZ, 0.08),
    ];
    polygonPath(points);
    context.fillStyle = "rgba(36, 50, 72, 0.94)";
    context.fill();
    context.strokeStyle = "rgba(82, 99, 123, 0.92)";
    context.lineWidth = 1.4;
    context.stroke();
  }

  function drawStructuralStreet(rectangle) {
    if (!filterEngine.corridorVisible(rectangle, renderedNetworkIds)) return;
    const colors = {
      ALLEY: "#263447",
      BOULEVARD: "#0b1320",
      ROUTE_ACCESS: "#1c293b",
      STREET: "#172437",
    };
    const points = [
      project(rectangle.x, rectangle.z, 0.09),
      project(rectangle.x + rectangle.width, rectangle.z, 0.09),
      project(rectangle.x + rectangle.width, rectangle.z + rectangle.depth, 0.09),
      project(rectangle.x, rectangle.z + rectangle.depth, 0.09),
    ];
    polygonPath(points);
    context.fillStyle = rectangle.color || colors[rectangle.tier] || colors.STREET;
    context.fill();
  }

  function drawNetwork(network) {
    const points = network.path.map((point) => project(point[0], point[1], 0.5));
    const trace = () => {
      context.beginPath();
      context.moveTo(points[0].x, points[0].y);
      for (const point of points.slice(1)) context.lineTo(point.x, point.y);
    };
    const profile = networkProfiles[network.kind] || networkProfiles.DEPENDENCY_ROAD;
    const weightScale = 1 + Math.min(0.8, Math.log2(network.edgeIds.length + 1) * 0.12);
    const selectionScale = weightScale * (selected("network", network.id) ? 1.24 : 1);
    context.lineJoin = "round";
    context.lineCap = "round";
    trace();
    context.strokeStyle = "rgba(3, 7, 18, 0.9)";
    context.lineWidth = profile.shoulder * selectionScale;
    context.stroke();
    trace();
    context.strokeStyle = network.kind === "HTTP_HIGHWAY" ? "#4b3a31" : "#354256";
    context.lineWidth = profile.surface * selectionScale;
    context.stroke();
    trace();
    context.strokeStyle = networkColors[network.kind] || networkColors.DEPENDENCY_ROAD;
    context.lineWidth = profile.marking * selectionScale;
    context.setLineDash(network.kind === "MESSAGING_PATH" ? [6, 4] : []);
    context.stroke();
    context.setLineDash([]);
    hitRegions.push({ kind: "network", id: network.id, points });
  }

  function drawSyntheticActivity(timestamp) {
    if (!state.syntheticActivity || !activityEngine) return;
    const elapsed = Math.max(0, timestamp - state.activityEpoch);
    if (accessFrame) {
      for (const route of accessFrame.animated) {
        const phase = (elapsed / 6000 + activityEngine.phaseForId(route.id)) % 1;
        const sample = accessPolicy.position(route, phase);
        if (!sample || !accessFrame.segmentIds.has(sample.segmentId)) continue;
        const point = project(...sample.point, 0.6);
        context.beginPath();
        context.arc(point.x, point.y, 2, 0, Math.PI * 2);
        context.fillStyle = "#f8fafc";
        context.fill();
      }
      return;
    }
    for (const network of scene.networks) {
      if (!renderedNetworkIds.has(network.id)) continue;
      const phase = (elapsed / 6000 + activityEngine.phaseForId(network.id)) % 1;
      const point = activityEngine.pointAlongPath(network.path, phase);
      if (!point) continue;
      const projected = project(point[0], point[1], 1.25);
      context.beginPath();
      context.arc(projected.x, projected.y, 4, 0, Math.PI * 2);
      context.fillStyle = "#f8fafc";
      context.shadowColor = networkColors[network.kind] || "#38bdf8";
      context.shadowBlur = 9;
      context.fill();
      context.shadowBlur = 0;
    }
  }

  function buildingDepth(building) {
    const rotated = rotatePoint(
      building.x + building.width / 2,
      building.z + building.depth / 2,
    );
    return rotated.x + rotated.z;
  }

  function drawVolume(building, palette, outlineColor, lineWidth) {
    const bottom = [
      project(building.x, building.z, building.y || 0),
      project(building.x + building.width, building.z, building.y || 0),
      project(building.x + building.width, building.z + building.depth, building.y || 0),
      project(building.x, building.z + building.depth, building.y || 0),
    ];
    const top = [
      project(building.x, building.z, building.height + (building.y || 0)),
      project(building.x + building.width, building.z, building.height + (building.y || 0)),
      project(building.x + building.width, building.z + building.depth, building.height + (building.y || 0)),
      project(building.x, building.z + building.depth, building.height + (building.y || 0)),
    ];
    polygonPath([top[1], bottom[1], bottom[2], top[2]]);
    context.fillStyle = palette[1];
    context.fill();
    polygonPath([top[2], bottom[2], bottom[3], top[3]]);
    context.fillStyle = palette[2];
    context.fill();
    polygonPath([top[0], top[1], top[2], top[3]]);
    context.fillStyle = palette[0];
    context.fill();

    const outline = [top[0], top[1], bottom[1], bottom[2], bottom[3], top[3]];
    polygonPath(outline);
    context.strokeStyle = outlineColor;
    context.lineWidth = lineWidth;
    context.stroke();
    return outline;
  }

  function drawBuilding(building) {
    const outline = drawVolume(
      building,
      colors[building.archetype] || colors.GENERIC_BUILDING,
      selected("building", building.entityId)
        ? "#f8fafc"
        : "rgba(203, 213, 225, 0.62)",
      selected("building", building.entityId) ? 2.5 : 1.1,
    );
    hitRegions.push({ kind: "building", id: building.entityId, points: outline });
  }

  function drawAggregateFacility(facility) {
    const selectedMember = state.selected?.kind === "building"
      && facility.memberEntityIds.includes(state.selected.id)
      ? scene.buildings.find(b => b.entityId === state.selected.id) : null;
    const isSelected = selected("aggregate", facility.id) || Boolean(selectedMember);
    const outlines = (facility.plots || [facility]).map((plot) => drawVolume(
      { ...plot, height: 2.2 },
      ["#475569", "#263449", "#172033"],
      isSelected ? "#f8fafc" : "#fbbf24",
      isSelected ? 3.2 : 2.2,
    ));
    for (const part of filterEngine.aggregateParts(facility)
      .flatMap(part => part.aggregateRole ? filterEngine.roleVolumes(part) : [part]).sort(
      (left, right) => buildingDepth(left) - buildingDepth(right),
    )) {
      const outline = drawVolume(
        part,
        colors[part.archetype] || colors.GENERIC_BUILDING,
        isSelected ? "#f8fafc" : "rgba(226, 232, 240, 0.8)",
        isSelected ? 2.8 : 1.4,
      );
      outlines.push(outline);
    }
    if (selectedMember) {
      const b = selectedMember, y = facility.height + 3;
      polygonPath([project(b.x, b.z, y), project(b.x + b.width, b.z, y),
        project(b.x + b.width, b.z + b.depth, y), project(b.x, b.z + b.depth, y)]);
      context.strokeStyle = "#22d3ee";
      context.lineWidth = 2;
      context.stroke();
    }
    if (isSelected) {
      const label = `${districtCanvasLabel(districts.get(facility.districtId))} · ${facility.memberEntityIds.length} files`;
      const labelPoint = project(
        facility.labelX ?? facility.x + facility.width / 2,
        facility.labelZ ?? facility.z + facility.depth / 2,
        facility.height + 4,
      );
      context.font = "800 12px ui-sans-serif, system-ui, sans-serif";
      const labelWidth = Math.min(240, Math.ceil(context.measureText(label).width) + 16);
      districtLabelCandidates.push({
        aggregate: true,
        height: 20,
        id: facility.id,
        label,
        priority: 20000,
        textX: labelPoint.x,
        textY: labelPoint.y - 5,
        width: labelWidth,
        x: labelPoint.x - labelWidth / 2,
        y: labelPoint.y - 20,
      });
    }
    for (const points of outlines) {
      hitRegions.push({ kind: "aggregate", id: facility.id, points });
    }
  }

  function render(timestamp = 0) {
    framePending = false;
    updateLodVisibility();
    hitRegions = [];
    districtLabelCandidates = [];
    context.clearRect(0, 0, viewportWidth, viewportHeight);
    drawGrid();
    for (const district of scene.districts) {
      if (renderedDistrictIds.has(district.id)) drawDistrict(district);
    }
    for (const districtId of [...majorDistrictIds].sort()) {
      const district = districts.get(districtId);
      if (district) drawMajorDistrict(district);
    }
    if (currentDetailLevel === "detail") {
      for (const block of civicBlocks) drawCivicBlock(block);
    }
    for (const rectangle of accessPolicy && !data.streets?.structural ? [] : streetRectangles) drawStructuralStreet(rectangle);
    for (const segment of accessFrame?.segments || []) {
      const points = [segment.start, segment.end].map(p => project(...p, 0.15));
      const style = filterEngine.accessRoadStyle(segment), width = style.width;
      context.beginPath();
      context.moveTo(points[0].x, points[0].y);
      context.lineTo(points[1].x, points[1].y);
      context.lineCap = "butt";
      context.lineWidth = Math.max(0.5, width * baseScale() * state.zoom * 0.65);
      context.strokeStyle = segment.highlighted ? "#67d7ff" : segment.kind === "DEPENDENCY_ROAD" ? style.surface : networkColors[segment.kind];
      context.stroke();
      hitRegions.push({kind: "network", id: segment.id, points});
    }
    for (const segment of accessFrame?.segments || []) {
      const style=filterEngine.accessRoadStyle(segment);
      for (const paint of accessPaint.get(segment.id) || []) {
        const a=project(...paint.start,.18), b=project(...paint.end,.18);
        context.beginPath();context.moveTo(a.x,a.y);context.lineTo(b.x,b.y);
        context.lineWidth=Math.max(.3,.13*baseScale()*state.zoom*.65);
        context.strokeStyle=segment.kind==='DEPENDENCY_ROAD'?style.marking:networkColors[segment.kind];
        context.stroke();
      }
    }
    for (const network of accessPolicy ? [] : scene.networks) {
      if (renderedNetworkIds.has(network.id)) drawNetwork(network);
    }
    const orderedBuildings = [...scene.buildings].sort(
      (left, right) => buildingDepth(left) - buildingDepth(right) || left.entityId.localeCompare(right.entityId),
    );
    for (const building of orderedBuildings) {
      if (renderedBuildingIds.has(building.entityId)) drawBuilding(building);
    }
    for (const aggregateId of [...renderedAggregateIds].sort()) {
      drawAggregateFacility(aggregateFacilities.get(aggregateId));
    }
    for (const segment of accessFrame?.segments || []) {
      if (!segment.highlighted) continue;
      const a=project(...segment.start,0.22), b=project(...segment.end,0.22);
      context.beginPath();
      context.moveTo(a.x,a.y); context.lineTo(b.x,b.y);
      context.lineWidth=1.5; context.strokeStyle="#67d7ff"; context.stroke();
    }
    drawDistrictLabels();
    drawSyntheticActivity(timestamp);
    if (state.syntheticActivity && renderedNetworkIds.size > 0) scheduleRender();
  }

  function scheduleRender() {
    if (!framePending) {
      framePending = true;
      requestAnimationFrame(render);
    }
  }

  function resize() {
    const rectangle = canvas.getBoundingClientRect();
    const ratio = Math.min(globalThis.devicePixelRatio || 1, 2);
    viewportWidth = Math.max(1, rectangle.width);
    viewportHeight = Math.max(1, rectangle.height);
    canvas.width = Math.round(viewportWidth * ratio);
    canvas.height = Math.round(viewportHeight * ratio);
    context.setTransform(ratio, 0, 0, ratio, 0, 0);
    scheduleRender();
  }

  function hitTest(x, y) {
    for (let index = hitRegions.length - 1; index >= 0; index -= 1) {
      const region = hitRegions[index];
      if (region.kind === "network") {
        for (let pointIndex = 1; pointIndex < region.points.length; pointIndex += 1) {
          if (distanceToSegment(x, y, region.points[pointIndex - 1], region.points[pointIndex]) <= 7) {
            return region;
          }
        }
      } else if (pointInPolygon(x, y, region.points)) {
        return region;
      }
    }
    return null;
  }

  function detailRow(list, label, value) {
    const wrapper = element("div", undefined, "detail-row");
    wrapper.append(element("dt", label), element("dd", value ?? "Unknown"));
    list.append(wrapper);
  }

  function factSection(parent, title, values) {
    parent.append(element("h3", title, "section-title"));
    if (!values.length) {
      parent.append(element("p", "No verified facts", "muted"));
      return;
    }
    const list = element("ul", undefined, "fact-list");
    for (const value of values) list.append(element("li", value));
    parent.append(list);
  }

  function aggregateMembersSection(parent, facility) {
    const details = element("details", undefined, "aggregate-members");
    details.append(element(
      "summary",
      `Constituent files (${facility.memberEntityIds.length})`,
    ));
    const list = element("ul", undefined, "fact-list");
    for (const entityId of facility.memberEntityIds) {
      const item = element("li");
      const button = element("button", entities.get(entityId)?.path || entityId, "focus-button");
      button.type = "button";
      button.addEventListener("click", () => showSelection({ kind: "building", id: entityId }));
      item.append(button);
      list.append(item);
    }
    details.append(list);
    parent.append(details);
  }

  function aggregateDistrictsSection(parent, facility) {
    const labels = (facility.memberDistrictIds || [])
      .map((districtId) => districtLabel(districts.get(districtId)))
      .sort();
    factSection(parent, "CONSTITUENT DISTRICTS", labels);
  }

  function evidenceLabel(evidenceId) {
    const item = evidence.get(evidenceId);
    if (!item) return evidenceId;
    const range = item.startLine
      ? `${item.sourcePath}:${item.startLine}${item.endLine !== item.startLine ? `-${item.endLine}` : ""}`
      : item.sourcePath;
    return `${item.summary} · ${item.kind} · ${range}`;
  }

  function sourceLink(entity) {
    const member = (metropolis?.repositories || []).find((repository) =>
      entity?.id?.startsWith(`${repository.id}:`),
    );
    const sourceUrl = member?.sourceUrl || ucg.repository.sourceUrl;
    const revision = member?.revision || ucg.repository.revision;
    if (!sourceUrl || !revision || !entity?.path) return null;
    try {
      const url = new URL(sourceUrl);
      if (!['http:', 'https:'].includes(url.protocol)) return null;
      const encodedPath = entity.path.split("/").map(encodeURIComponent).join("/");
      url.pathname = `${url.pathname.replace(/\/$/, "")}/blob/${encodeURIComponent(revision)}/${encodedPath}`;
      const link = element("a", "Open source at revision", "source-link");
      link.href = url.toString();
      link.target = "_blank";
      link.rel = "noreferrer";
      return link;
    } catch {
      return null;
    }
  }

  function focusWorld(x, z) {
    state.zoom = Math.max(state.zoom, 2.6);
    const projected = project(x, z);
    state.panX += viewportWidth / 2 - projected.x;
    state.panY += viewportHeight / 2 - projected.y;
    scheduleRender();
  }

  function focusButton(x, z, label, beforeFocus = null) {
    const button = element("button", label, "focus-button");
    button.type = "button";
    button.addEventListener("click", () => {
      beforeFocus?.();
      hoverLabel.hidden = true;
      focusWorld(x, z);
    });
    return button;
  }

  function facilityControls(parent, facility) {
    const expanded = expandedAggregateIds.has(facility.id);
    const toggle = element("button", expanded ? "Collapse facility" : "Expand constituent files", "focus-button");
    toggle.type = "button";
    toggle.dataset.facilityAction = "toggle";
    toggle.setAttribute("aria-expanded", String(expanded));
    toggle.addEventListener("click", () => {
      if (expandedAggregateIds.has(facility.id)) expandedAggregateIds.delete(facility.id);
      else expandedAggregateIds.add(facility.id);
      showSelection({ kind: "aggregate", id: facility.id });
    });
    parent.append(toggle);
    if (state.selected?.kind === "building") {
      const back = element("button", "Inspect facility", "focus-button");
      back.type = "button";
      back.dataset.facilityAction = "inspect";
      back.addEventListener("click", () => showSelection({ kind: "aggregate", id: facility.id }));
      parent.append(back);
    }
  }

  function showAggregate(aggregateId) {
    const facility = aggregateFacilities.get(aggregateId);
    inspector.replaceChildren();
    inspector.append(element("p", facility.role ? "ROLE LANDMARK · VISUAL AGGREGATE" : "CITY BLOCK · VISUAL AGGREGATE", "eyebrow"));
    inspector.append(element("h2", facility.title || districtLabel(districts.get(facility.districtId))));
    inspector.append(element(
      "p",
      facility.role ? "Visual compound of evidenced files, not a new service. Zoom keeps this facility intact. Only Expand constituent files reveals individual buildings."
        : "This overview block groups real file buildings and districts. It is not a code entity or inferred service.",
      "aggregate-disclosure",
    ));
    const details = element("dl", undefined, "detail-list");
    detailRow(details, "Files", facility.memberEntityIds.length);
    detailRow(details, "Owning district", districtLabel(districts.get(facility.districtId)));
    detailRow(details, "Districts", facility.memberDistrictIds?.length || 0);
    detailRow(details, "Representation", "Deterministic visual block aggregate");
    inspector.append(details);
    if (facility.role) facilityControls(inspector, facility);
    if (facility.role) factSection(inspector, "GROUPING EVIDENCE", facility.evidenceIds.map(evidenceLabel));
    factSection(
      inspector,
      "ARCHETYPE COMPOSITION",
      facility.archetypeCounts.map(
        (item) => `${displayValue(item.archetype)} · ${item.count} files`,
      ),
    );
    aggregateDistrictsSection(inspector, facility);
    aggregateMembersSection(inspector, facility);
    inspector.append(focusButton(
      facility.x + facility.width / 2,
      facility.z + facility.depth / 2,
      facility.role ? "Focus facility" : "Explore constituent buildings",
      () => {
        if (!facility.role) state.selected = null;
      },
    ));
  }

  function showBuilding(entityId) {
    const building = scene.buildings.find((item) => item.entityId === entityId);
    const entity = entities.get(entityId) || {};
    inspector.replaceChildren();
    inspector.append(element("p", "BUILDING", "eyebrow"));
    inspector.append(element("h2", entity.path || entityId));
    const details = element("dl", undefined, "detail-list");
    detailRow(details, "Archetype", building.archetype);
    detailRow(details, "Language", entity.language || "Unknown");
    detailRow(details, "Height", building.height);
    detailRow(details, "District", districtLabel(districts.get(building.districtId)));
    inspector.append(details);
    const facility = lodPolicy.facilityForEntity(entityId);
    if (facility) {
      inspector.append(element("p", `${facility.title}: selected constituent. Cyan outline marks its original footprint above the compound; it is not another building. Routes are aggregates containing this file's actual edges.`, "aggregate-disclosure"));
      facilityControls(inspector, facility);
    }

    const roles = (entity.roles || []).map((claim) => `${claim.value} · ${claim.confidence}`);
    const technologies = (entity.technologies || []).map(
      (claim) => `${claim.value} · ${claim.confidence}`,
    );
    const capabilities = (entity.capabilities || []).map(
      (claim) => `${claim.value} · ${claim.confidence}`,
    );
    const declaredDependencies = filterEngine.declaredDependenciesForEntity(
      ucg,
      entityId,
    );
    factSection(inspector, "VERIFIED ROLES", roles);
    factSection(inspector, "TECHNOLOGIES", technologies);
    factSection(inspector, "CAPABILITIES", capabilities);
    factSection(
      inspector,
      "DECLARED DEPENDENCIES (NOT USAGE)",
      declaredDependencies.map(
        (dependency) => `${dependency.coordinate} · ${dependency.ecosystem} · DECLARED`,
      ),
    );
    const evidenceIds = new Set([
      ...(building.evidenceIds || []),
      ...(entity.roles || []).flatMap((claim) => claim.evidenceIds),
      ...(entity.technologies || []).flatMap((claim) => claim.evidenceIds),
      ...(entity.capabilities || []).flatMap((claim) => claim.evidenceIds),
      ...declaredDependencies.flatMap((dependency) => dependency.evidenceIds),
    ]);
    factSection(
      inspector,
      "EVIDENCE",
      [...evidenceIds].map(evidenceLabel),
    );
    const link = sourceLink(entity);
    if (link) inspector.append(link);
    inspector.append(
      focusButton(
        building.x + building.width / 2,
        building.z + building.depth / 2,
        "Focus building",
      ),
    );
  }

  function showDistrict(districtId) {
    const district = districts.get(districtId);
    const districtBuildings = filterEngine.districtBuildings(scene, districtId);
    const visibleChildCount = districtBuildings.filter((item) =>
      visibleBuildingIds.has(item.entityId),
    ).length;
    inspector.replaceChildren();
    inspector.append(element("p", "DISTRICT", "eyebrow"));
    inspector.append(element("h2", districtLabel(district)));
    const details = element("dl", undefined, "detail-list");
    detailRow(details, "Files (including subdistricts)", `${visibleChildCount}/${districtBuildings.length} match filters`);
    detailRow(details, "Parent", district.parentId ? districtLabel(districts.get(district.parentId)) : "City root");
    detailRow(details, "Size", `${district.width} × ${district.depth}`);
    inspector.append(details);
    inspector.append(
      focusButton(
        district.x + district.width / 2,
        district.z + district.depth / 2,
        "Focus district",
      ),
    );
  }

  function showNetwork(networkId) {
    const choices = accessPolicy?.choices(networkId, visibleBuildingIds, visibleNetworkIds) || [];
    const chosen = choices.find(route => route.id === state.selected?.routeId);
    const activeIds = new Set(choices.map(route => route.id));
    const network = chosen || accessPolicy?.network(networkId, activeIds) || networkForId(networkId);
    inspector.replaceChildren();
    inspector.append(element("p", "NETWORK", "eyebrow"));
    inspector.append(element("h2", network.kind));
    const details = element("dl", undefined, "detail-list");
    detailRow(details, "Graph edges", network.edgeIds.length);
    detailRow(details, "Route points", network.path.length);
    if (network.routeIds) {
      detailRow(details, "Shared relation paths", network.routeIds.length);
      inspector.append(element("p", "Shared geometry does not create new relationships. Highlighted paths retain their own source and destination.", "muted"));
    }
    const demand = accessPolicy?.network(networkId)?.demand;
    if (demand) {
      detailRow(details, "Road grade", demand.label);
      detailRow(details, "Full-road unique edges", demand.edgeCount);
      detailRow(details, "Source / destination files", `${demand.sourceCount} / ${demand.targetCount}`);
      detailRow(details, "Distinct endpoint files", demand.buildingCount);
      detailRow(details, "Major structural districts", demand.majorDistrictCount);
      detailRow(details, "Cross-major edges", demand.crossDistrictEdgeCount);
      detailRow(details, "Files outside major districts", demand.unassignedBuildingCount);
      detailRow(details, "Rendered / target width", `${demand.width} / ${demand.targetWidth}${demand.clearanceLimited ? ' · clearance limited' : ''}`);
      inspector.append(element("p", "Grade uses full-road static dependency demand, not runtime traffic. Filters and path selection do not change it. Trunk demand does not imply highway geometry.", "muted"));
    }
    inspector.append(details);
    if (choices.length) {
      const label = element("label", "Trace one source → destination path", "section-title");
      label.htmlFor = "route-choice";
      const control = element("select", undefined, "route-choice");
      control.id = "route-choice";
      const all = element("option", `All ${choices.length} paths through this road`);
      all.value = "";
      control.append(all);
      for (const route of choices) {
        const option = element("option", `${entities.get(route.source)?.path || route.source} → ${entities.get(route.target)?.path || route.target} · ${route.edgeIds.length} edges`);
        option.value = route.id;
        control.append(option);
      }
      control.value = chosen?.id || "";
      control.addEventListener("change", () => {
        showSelection({kind:"network", id:networkId, routeId:control.value});
        document.getElementById("route-choice")?.focus();
      });
      inspector.append(label, control);
    }
    if (chosen) {
      inspector.append(element("p", "One evidenced file-pair path. Shared crossings do not add destinations; this is not measured runtime traffic.", "muted"));
      for (const [label, id] of [["Source", chosen.source], ["Destination", chosen.target]]) {
        const button = element("button", `${label}: ${entities.get(id)?.path || id}`, "focus-button route-endpoint");
        button.type = "button";
        button.addEventListener("click", () => showSelection({kind:"building", id}));
        inspector.append(button);
      }
      detailRow(details, "Path ID", chosen.id);
    }
    factSection(
      inspector,
      "UNDERLYING EDGES",
      network.edgeIds.map((id) => {
        const edge = edges.get(id);
        return edge ? `${id} · ${edge.type}: ${edge.from} → ${edge.to} (${edge.confidence})` : id;
      }),
    );
    const evidenceSummaries = network.edgeIds.flatMap((id) => {
      const edge = edges.get(id);
      return (edge?.evidenceIds || []).map(evidenceLabel);
    });
    factSection(inspector, "EVIDENCE", evidenceSummaries);
    const middle = network.path[Math.floor(network.path.length / 2)];
    inspector.append(focusButton(middle[0], middle[1], "Focus network"));
  }

  function showSelection(selection) {
    if (!selection) return;
    hoverLabel.hidden = true;
    state.selected = { kind: selection.kind, id: selection.id, routeId: selection.routeId || "" };
    if (selection.kind === "aggregate") showAggregate(selection.id);
    if (selection.kind === "building") showBuilding(selection.id);
    if (selection.kind === "district") showDistrict(selection.id);
    if (selection.kind === "network") showNetwork(selection.id);
    scheduleRender();
  }

  function labelFor(selection) {
    if (selection.kind === "aggregate") {
      const facility = aggregateFacilities.get(selection.id);
      return filterEngine.aggregateLabel(facility, entities);
    }
    if (selection.kind === "building") {
      const entity = entities.get(selection.id);
      const building = scene.buildings.find((item) => item.entityId === selection.id);
      return `${entity?.path || selection.id} · ${building.archetype}`;
    }
    if (selection.kind === "district") return districtLabel(districts.get(selection.id));
    const network = networkForId(selection.id);
    return `${network.kind} · ${network.edgeIds.length} edge${network.edgeIds.length === 1 ? "" : "s"}`;
  }

  canvas.addEventListener("pointerdown", (event) => {
    if (![0, 1, 2].includes(event.button)) return;
    event.preventDefault();
    canvas.focus({preventScroll: true});
    canvas.setPointerCapture(event.pointerId);
    state.dragging = true;
    state.dragMode = state.moveMode || event.altKey || event.shiftKey || event.button !== 0 ? "pan" : "rotate";
    state.pointerX = event.clientX;
    state.pointerY = event.clientY;
    state.moved = false;
    canvas.classList.add("dragging");
  });

  canvas.addEventListener("pointermove", (event) => {
    const rectangle = canvas.getBoundingClientRect();
    const localX = event.clientX - rectangle.left;
    const localY = event.clientY - rectangle.top;
    if (state.dragging) {
      const deltaX = event.clientX - state.pointerX;
      const deltaY = event.clientY - state.pointerY;
      state.moved ||= Math.abs(deltaX) + Math.abs(deltaY) > 2;
      if (state.dragMode === "rotate") state.angle += deltaX * 0.008;
      else {
        state.panX += deltaX;
        state.panY += deltaY;
      }
      state.pointerX = event.clientX;
      state.pointerY = event.clientY;
      hoverLabel.hidden = true;
      scheduleRender();
      return;
    }
    const hovered = hitTest(localX, localY);
    if (!hovered) {
      hoverLabel.hidden = true;
      return;
    }
    hoverLabel.textContent = labelFor(hovered);
    hoverLabel.hidden = false;
    hoverLabel.style.left = `${Math.max(8, Math.min(localX + 14, viewportWidth - hoverLabel.offsetWidth - 8))}px`;
    hoverLabel.style.top = `${Math.max(8, localY - hoverLabel.offsetHeight - 8)}px`;
  });

  canvas.addEventListener("pointerup", (event) => {
    const rectangle = canvas.getBoundingClientRect();
    if (!state.moved && event.button === 0) showSelection(hitTest(event.clientX - rectangle.left, event.clientY - rectangle.top));
    state.dragging = false;
    canvas.classList.remove("dragging");
  });
  canvas.addEventListener("pointercancel", () => {
    state.dragging = false;
    canvas.classList.remove("dragging");
  });
  canvas.addEventListener("contextmenu", (event) => event.preventDefault());
  canvas.addEventListener(
    "wheel",
    (event) => {
      event.preventDefault();
      state.zoom = Math.max(0.35, Math.min(5, state.zoom * Math.exp(-event.deltaY * 0.001)));
      scheduleRender();
    },
    { passive: false },
  );

  function runAction(action) {
    if (action === "toggle-pan") {
      state.moveMode = !state.moveMode;
      document.querySelector('[data-action="toggle-pan"]').setAttribute("aria-pressed", String(state.moveMode));
      canvas.classList.toggle("move-mode", state.moveMode);
    }
    const step = Math.min(viewportWidth, viewportHeight) * 0.12;
    const delta = {"pan-left":[step,0], "pan-right":[-step,0], "pan-up":[0,step], "pan-down":[0,-step]}[action];
    if (delta) { state.panX += delta[0]; state.panY += delta[1]; hoverLabel.hidden = true; }
    if (action === "toggle-routes") {
      showAllNetworks = !showAllNetworks;
      document.querySelector('[data-action="toggle-routes"]').setAttribute("aria-pressed", String(showAllNetworks));
    }
    if (action === "rotate-left") state.angle -= Math.PI / 8;
    if (action === "rotate-right") state.angle += Math.PI / 8;
    if (action === "zoom-in") state.zoom = Math.min(5, state.zoom * 1.2);
    if (action === "zoom-out") state.zoom = Math.max(0.35, state.zoom / 1.2);
    if (action === "reset") {
      state.angle = -Math.PI / 4;
      state.panX = 0;
      state.panY = 0;
      state.zoom = 1;
    }
    scheduleRender();
  }

  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => runAction(button.dataset.action));
  });
  document.querySelector('[data-action="toggle-pan"]').setAttribute("aria-pressed", "true");
  canvas.classList.add("move-mode");
  document.getElementById("toolbar-help").textContent = "Move mode / Shift / right drag: move · WASD / arrows: move · Q/E: rotate · Wheel: zoom · R: reset";
  const districtJump = document.getElementById("district-jump");
  for (const id of [...majorDistrictIds].sort()) {
    const option = element("option", districtLabel(districts.get(id)));
    option.value = id;
    districtJump.append(option);
  }
  districtJump.disabled = majorDistrictIds.size === 0;
  districtJump.addEventListener("change", () => {
    const district = districts.get(districtJump.value);
    if (!district) return;
    focusWorld(district.x + district.width / 2, district.z + district.depth / 2);
    showSelection({kind: "district", id: district.id});
    districtJump.value = "";
  });
  for (const [name, control] of filterControls) {
    control.addEventListener("change", () => {
      state.filters[name] = control.value;
      applyFilters();
    });
  }
  clearFilters.addEventListener("click", () => {
    for (const [name, control] of filterControls) {
      control.value = "";
      state.filters[name] = "";
    }
    applyFilters();
  });
  function updateActivityAvailability() {
    const motionReduced = reducedMotion?.matches === true;
    const noNetworks = scene.networks.length === 0;
    const unavailable = motionReduced || noNetworks || !activityEngine;
    activityToggle.disabled = unavailable;
    if (unavailable) {
      activityToggle.checked = false;
      state.syntheticActivity = false;
    }
    activityNote.textContent = motionReduced
      ? "Synthetic illustration disabled by reduced-motion preference"
      : noNetworks
        ? "Synthetic illustration unavailable — this city has no networks"
        : "Illustration only — not measured runtime traffic";
    scheduleRender();
  }
  activityToggle.addEventListener("change", () => {
    state.syntheticActivity = activityToggle.checked;
    state.activityEpoch = globalThis.performance.now();
    activityNote.textContent = state.syntheticActivity
      ? "Synthetic illustration active — not measured runtime traffic"
      : "Illustration only — not measured runtime traffic";
    scheduleRender();
  });
  reducedMotion?.addEventListener?.("change", updateActivityAvailability);
  document.addEventListener("keydown", (event) => {
    const action = filterEngine.cameraKeyAction(event);
    if (action) {
      event.preventDefault();
      runAction(action);
    }
  });

  new ResizeObserver(resize).observe(canvas);
  updateActivityAvailability();
  applyFilters();
  resize();
})();
