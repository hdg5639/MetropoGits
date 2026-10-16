(() => {
  "use strict";

  const data = globalThis.METROPOGITS_DATA;
  const canvas = document.getElementById("city-canvas");
  const context = canvas.getContext("2d");
  const inspector = document.getElementById("inspector-content");
  const hoverLabel = document.getElementById("hover-label");
  const repositoryName = document.getElementById("repository-name");
  const cityStats = document.getElementById("city-stats");

  if (!data || !data.scene || !data.ucg || !context) {
    repositoryName.textContent = "Viewer data unavailable";
    return;
  }

  const scene = data.scene;
  const ucg = data.ucg;
  const entities = new Map(ucg.entities.map((entity) => [entity.id, entity]));
  const edges = new Map(ucg.edges.map((edge) => [edge.id, edge]));
  const evidence = new Map(ucg.evidence.map((item) => [item.evidenceId, item]));
  const districts = new Map(scene.districts.map((district) => [district.id, district]));

  const colors = {
    CONTROL_CENTER: ["#a78bfa", "#6d28d9", "#4c1d95"],
    GATE: ["#f472b6", "#be185d", "#831843"],
    GENERIC_BUILDING: ["#94a3b8", "#475569", "#334155"],
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
    dragging: false,
    dragMode: "pan",
    moved: false,
    panX: 0,
    panY: 0,
    pointerX: 0,
    pointerY: 0,
    selected: null,
    zoom: 1,
  };
  let hitRegions = [];
  let framePending = false;
  let viewportWidth = 1;
  let viewportHeight = 1;

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

  repositoryName.textContent = ucg.repository.id;
  document.title = `${ucg.repository.id} · MetropoGits`;
  addStat(scene.districts.length, "districts");
  addStat(scene.buildings.length, "buildings");
  addStat(scene.networks.length, "networks");

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
    return entity?.path || (district.parentId === null ? ucg.repository.id : district.id);
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

    const labelPoint = project(district.x + 3, district.z + 3);
    context.fillStyle = "#8292aa";
    context.font = "600 10px ui-sans-serif, system-ui, sans-serif";
    context.fillText(districtLabel(district), labelPoint.x, labelPoint.y - 5);
    hitRegions.push({ kind: "district", id: district.id, points });
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
    context.strokeStyle = selected("building", building.entityId) ? "#f8fafc" : "#0f172a";
    context.lineWidth = selected("building", building.entityId) ? 2.5 : 0.8;
    context.stroke();
    hitRegions.push({ kind: "building", id: building.entityId, points: outline });
  }

  function render() {
    framePending = false;
    hitRegions = [];
    context.clearRect(0, 0, viewportWidth, viewportHeight);
    drawGrid();
    for (const district of scene.districts) drawDistrict(district);
    for (const network of scene.networks) drawNetwork(network);
    const orderedBuildings = [...scene.buildings].sort(
      (left, right) => buildingDepth(left) - buildingDepth(right) || left.entityId.localeCompare(right.entityId),
    );
    for (const building of orderedBuildings) drawBuilding(building);
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
    const sourceUrl = ucg.repository.sourceUrl;
    const revision = ucg.repository.revision;
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
    factSection(inspector, "VERIFIED ROLES", roles);
    factSection(inspector, "TECHNOLOGIES", technologies);
    const evidenceIds = new Set([
      ...(building.evidenceIds || []),
      ...(entity.roles || []).flatMap((claim) => claim.evidenceIds),
      ...(entity.technologies || []).flatMap((claim) => claim.evidenceIds),
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
    const childCount = scene.buildings.filter((item) => item.districtId === districtId).length;
    inspector.replaceChildren();
    inspector.append(element("p", "DISTRICT", "eyebrow"));
    inspector.append(element("h2", districtLabel(district)));
    const details = element("dl", undefined, "detail-list");
    detailRow(details, "Buildings", childCount);
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
  document.addEventListener("keydown", (event) => {
    const actions = { q: "rotate-left", e: "rotate-right", "+": "zoom-in", "=": "zoom-in", "-": "zoom-out", r: "reset" };
    const action = actions[event.key.toLowerCase()];
    if (action) {
      event.preventDefault();
      runAction(action);
    }
  });

  new ResizeObserver(resize).observe(canvas);
  resize();
})();
