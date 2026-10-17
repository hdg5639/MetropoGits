(() => {
  "use strict";

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
  const activityToggle = document.getElementById("synthetic-activity");
  const activityNote = document.getElementById("synthetic-activity-note");
  const activityEngine = globalThis.METROPOGITS_ACTIVITY;
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

  const scene = data.scene;
  const ucg = data.ucg;
  const entities = new Map(ucg.entities.map((entity) => [entity.id, entity]));
  const edges = new Map(ucg.edges.map((edge) => [edge.id, edge]));
  const evidence = new Map(ucg.evidence.map((item) => [item.evidenceId, item]));
  const districts = new Map(scene.districts.map((district) => [district.id, district]));
  const districtChildren = new Map();
  const districtsWithBuildings = new Set(
    scene.buildings.map((building) => building.districtId),
  );
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

  const colors = {
    CACHE_TOWER: ["#facc15", "#ca8a04", "#713f12"],
    CONTROL_CENTER: ["#a78bfa", "#6d28d9", "#4c1d95"],
    DOCUMENT_DEPOT: ["#fb923c", "#c2410c", "#7c2d12"],
    EXCHANGE: ["#2dd4bf", "#0f766e", "#134e4a"],
    GATE: ["#f472b6", "#be185d", "#831843"],
    GENERIC_BUILDING: ["#94a3b8", "#475569", "#334155"],
    PORT: ["#38bdf8", "#0369a1", "#0c4a6e"],
    SERVICE_OFFICE: ["#60a5fa", "#1d4ed8", "#1e3a8a"],
    STRUCTURED_WAREHOUSE: ["#34d399", "#047857", "#064e3b"],
  };
  const networkColors = {
    DEPENDENCY_ROAD: "#64748b",
    HTTP_HIGHWAY: "#f97316",
    MESSAGING_PATH: "#a855f7",
  };

  const state = {
    angle: -Math.PI / 4,
    activityEpoch: 0,
    dragging: false,
    dragMode: "pan",
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
  let viewportWidth = 1;
  let viewportHeight = 1;
  const reducedMotion = globalThis.matchMedia?.("(prefers-reduced-motion: reduce)");

  const worldBounds = (() => {
    if (!scene.districts.length) return { minX: 0, minZ: 0, maxX: 1, maxZ: 1 };
    return scene.districts.reduce(
      (bounds, district) => ({
        minX: Math.min(bounds.minX, district.x),
        minZ: Math.min(bounds.minZ, district.z),
        maxX: Math.max(bounds.maxX, district.x + district.width),
        maxZ: Math.max(bounds.maxZ, district.z + district.depth),
      }),
      { minX: Infinity, minZ: Infinity, maxX: -Infinity, maxZ: -Infinity },
    );
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

  function selectionIsVisible() {
    if (!state.selected || state.selected.kind === "district") return true;
    if (state.selected.kind === "building") {
      return visibleBuildingIds.has(state.selected.id);
    }
    return visibleNetworkIds.has(state.selected.id);
  }

  function resetInspector(message = "Choose a building, district, or network to inspect the repository facts behind it.") {
    inspector.replaceChildren();
    inspector.append(element("p", "INSPECTOR", "eyebrow"));
    inspector.append(element("h2", "Select a city element"));
    inspector.append(element("p", message, "muted"));
  }

  function applyFilters() {
    const visible = filterIndex.filter(state.filters);
    visibleBuildingIds = new Set(visible.buildingIds);
    visibleNetworkIds = new Set(visible.networkIds);
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
    const points = [
      project(district.x, district.z),
      project(district.x + district.width, district.z),
      project(district.x + district.width, district.z + district.depth),
      project(district.x, district.z + district.depth),
    ];
    polygonPath(points);
    context.fillStyle = selected("district", district.id)
      ? "rgba(14, 165, 233, 0.24)"
      : "rgba(30, 41, 59, 0.72)";
    context.fill();
    context.strokeStyle = selected("district", district.id) ? "#38bdf8" : "#34445e";
    context.lineWidth = selected("district", district.id) ? 2.5 : 1;
    context.stroke();

    context.font = "600 10px ui-sans-serif, system-ui, sans-serif";
    const label = districtCanvasLabel(district);
    const labelPoint = project(district.x + 3, district.z + 3);
    const textWidth = Math.ceil(context.measureText(label).width);
    districtLabelCandidates.push({
      height: 15,
      id: district.id,
      label,
      priority: (districtsWithBuildings.has(district.id) ? 1000 : 0)
        + districtDepths.get(district.id),
      textX: labelPoint.x,
      textY: labelPoint.y - 5,
      width: textWidth + 6,
      x: labelPoint.x - 3,
      y: labelPoint.y - 16,
    });
    hitRegions.push({ kind: "district", id: district.id, points });
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
      context.fillStyle = "rgba(7, 11, 20, 0.82)";
      context.fillRect(candidate.x, candidate.y, candidate.width, candidate.height);
      context.strokeStyle = "rgba(100, 116, 139, 0.55)";
      context.lineWidth = 1;
      context.strokeRect(candidate.x, candidate.y, candidate.width, candidate.height);
      context.fillStyle = "#a8b5c8";
      context.fillText(candidate.label, candidate.textX, candidate.textY);
    }
  }

  function drawNetwork(network) {
    const points = network.path.map((point) => project(point[0], point[1], 0.5));
    context.beginPath();
    context.moveTo(points[0].x, points[0].y);
    for (const point of points.slice(1)) context.lineTo(point.x, point.y);
    context.lineJoin = "round";
    context.lineCap = "round";
    context.strokeStyle = "rgba(3, 7, 18, 0.9)";
    context.lineWidth = selected("network", network.id) ? 9 : 7;
    context.stroke();
    context.strokeStyle = networkColors[network.kind] || networkColors.DEPENDENCY_ROAD;
    context.lineWidth = selected("network", network.id) ? 4 : 2.5;
    context.stroke();
    hitRegions.push({ kind: "network", id: network.id, points });
  }

  function drawSyntheticActivity(timestamp) {
    if (!state.syntheticActivity || !activityEngine) return;
    const elapsed = Math.max(0, timestamp - state.activityEpoch);
    for (const network of scene.networks) {
      if (!visibleNetworkIds.has(network.id)) continue;
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

  function drawBuilding(building) {
    const bottom = [
      project(building.x, building.z),
      project(building.x + building.width, building.z),
      project(building.x + building.width, building.z + building.depth),
      project(building.x, building.z + building.depth),
    ];
    const top = [
      project(building.x, building.z, building.height),
      project(building.x + building.width, building.z, building.height),
      project(building.x + building.width, building.z + building.depth, building.height),
      project(building.x, building.z + building.depth, building.height),
    ];
    const palette = colors[building.archetype] || colors.GENERIC_BUILDING;

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
    context.strokeStyle = selected("building", building.entityId)
      ? "#f8fafc"
      : "rgba(203, 213, 225, 0.62)";
    context.lineWidth = selected("building", building.entityId) ? 2.5 : 1.1;
    context.stroke();
    hitRegions.push({ kind: "building", id: building.entityId, points: outline });
  }

  function render(timestamp = 0) {
    framePending = false;
    hitRegions = [];
    districtLabelCandidates = [];
    context.clearRect(0, 0, viewportWidth, viewportHeight);
    drawGrid();
    for (const district of scene.districts) {
      if (drawableDistrictIds.has(district.id)) drawDistrict(district);
    }
    for (const network of scene.networks) {
      if (visibleNetworkIds.has(network.id)) drawNetwork(network);
    }
    const orderedBuildings = [...scene.buildings].sort(
      (left, right) => buildingDepth(left) - buildingDepth(right) || left.entityId.localeCompare(right.entityId),
    );
    for (const building of orderedBuildings) {
      if (visibleBuildingIds.has(building.entityId)) drawBuilding(building);
    }
    drawDistrictLabels();
    drawSyntheticActivity(timestamp);
    if (state.syntheticActivity && visibleNetworkIds.size > 0) scheduleRender();
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
    state.zoom = Math.max(state.zoom, 1.6);
    const projected = project(x, z);
    state.panX += viewportWidth / 2 - projected.x;
    state.panY += viewportHeight / 2 - projected.y;
    scheduleRender();
  }

  function focusButton(x, z, label) {
    const button = element("button", label, "focus-button");
    button.type = "button";
    button.addEventListener("click", () => focusWorld(x, z));
    return button;
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

    const roles = (entity.roles || []).map((claim) => `${claim.value} · ${claim.confidence}`);
    const technologies = (entity.technologies || []).map(
      (claim) => `${claim.value} · ${claim.confidence}`,
    );
    const capabilities = (entity.capabilities || []).map(
      (claim) => `${claim.value} · ${claim.confidence}`,
    );
    factSection(inspector, "VERIFIED ROLES", roles);
    factSection(inspector, "TECHNOLOGIES", technologies);
    factSection(inspector, "CAPABILITIES", capabilities);
    const evidenceIds = new Set([
      ...(building.evidenceIds || []),
      ...(entity.roles || []).flatMap((claim) => claim.evidenceIds),
      ...(entity.technologies || []).flatMap((claim) => claim.evidenceIds),
      ...(entity.capabilities || []).flatMap((claim) => claim.evidenceIds),
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
    const districtBuildings = scene.buildings.filter((item) => item.districtId === districtId);
    const visibleChildCount = districtBuildings.filter((item) =>
      visibleBuildingIds.has(item.entityId),
    ).length;
    inspector.replaceChildren();
    inspector.append(element("p", "DISTRICT", "eyebrow"));
    inspector.append(element("h2", districtLabel(district)));
    const details = element("dl", undefined, "detail-list");
    detailRow(details, "Buildings", `${visibleChildCount}/${districtBuildings.length} visible`);
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
    const network = scene.networks.find((item) => item.id === networkId);
    inspector.replaceChildren();
    inspector.append(element("p", "NETWORK", "eyebrow"));
    inspector.append(element("h2", network.kind));
    const details = element("dl", undefined, "detail-list");
    detailRow(details, "Graph edges", network.edgeIds.length);
    detailRow(details, "Route points", network.path.length);
    inspector.append(details);
    factSection(
      inspector,
      "UNDERLYING EDGES",
      network.edgeIds.map((id) => {
        const edge = edges.get(id);
        return edge ? `${edge.type}: ${edge.from} → ${edge.to} (${edge.confidence})` : id;
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
    state.selected = { kind: selection.kind, id: selection.id };
    if (selection.kind === "building") showBuilding(selection.id);
    if (selection.kind === "district") showDistrict(selection.id);
    if (selection.kind === "network") showNetwork(selection.id);
    scheduleRender();
  }

  function labelFor(selection) {
    if (selection.kind === "building") {
      const entity = entities.get(selection.id);
      const building = scene.buildings.find((item) => item.entityId === selection.id);
      return `${entity?.path || selection.id} · ${building.archetype}`;
    }
    if (selection.kind === "district") return districtLabel(districts.get(selection.id));
    const network = scene.networks.find((item) => item.id === selection.id);
    return `${network.kind} · ${network.edgeIds.length} edge${network.edgeIds.length === 1 ? "" : "s"}`;
  }

  canvas.addEventListener("pointerdown", (event) => {
    canvas.setPointerCapture(event.pointerId);
    state.dragging = true;
    state.dragMode = event.altKey || event.button === 2 ? "rotate" : "pan";
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
    hoverLabel.style.left = `${Math.min(localX + 14, viewportWidth - 260)}px`;
    hoverLabel.style.top = `${Math.max(8, localY - 34)}px`;
    hoverLabel.hidden = false;
  });

  canvas.addEventListener("pointerup", (event) => {
    const rectangle = canvas.getBoundingClientRect();
    if (!state.moved) showSelection(hitTest(event.clientX - rectangle.left, event.clientY - rectangle.top));
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
    const actions = { q: "rotate-left", e: "rotate-right", "+": "zoom-in", "=": "zoom-in", "-": "zoom-out", r: "reset" };
    const action = actions[event.key.toLowerCase()];
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
