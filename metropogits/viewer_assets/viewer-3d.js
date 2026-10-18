(() => {
  "use strict";

  function multiply(left, right) {
    const result = new Array(16).fill(0);
    for (let column = 0; column < 4; column += 1) {
      for (let row = 0; row < 4; row += 1) {
        for (let index = 0; index < 4; index += 1) {
          result[column * 4 + row] += left[index * 4 + row] * right[column * 4 + index];
        }
      }
    }
    return result;
  }

  function perspective(fieldOfView, aspect, near, far) {
    const scale = 1 / Math.tan(fieldOfView / 2);
    const range = 1 / (near - far);
    return [
      scale / aspect, 0, 0, 0,
      0, scale, 0, 0,
      0, 0, (far + near) * range, -1,
      0, 0, 2 * far * near * range, 0,
    ];
  }

  function subtract(left, right) {
    return [left[0] - right[0], left[1] - right[1], left[2] - right[2]];
  }

  function normalize(vector) {
    const length = Math.hypot(...vector) || 1;
    return vector.map((value) => value / length);
  }

  function cross(left, right) {
    return [
      left[1] * right[2] - left[2] * right[1],
      left[2] * right[0] - left[0] * right[2],
      left[0] * right[1] - left[1] * right[0],
    ];
  }

  function lookAt(eye, target, up) {
    const forward = normalize(subtract(eye, target));
    const right = normalize(cross(up, forward));
    const cameraUp = cross(forward, right);
    return [
      right[0], cameraUp[0], forward[0], 0,
      right[1], cameraUp[1], forward[1], 0,
      right[2], cameraUp[2], forward[2], 0,
      -right.reduce((sum, value, index) => sum + value * eye[index], 0),
      -cameraUp.reduce((sum, value, index) => sum + value * eye[index], 0),
      -forward.reduce((sum, value, index) => sum + value * eye[index], 0),
      1,
    ];
  }

  function transformPoint(matrix, point) {
    const [x, y, z] = point;
    return [
      matrix[0] * x + matrix[4] * y + matrix[8] * z + matrix[12],
      matrix[1] * x + matrix[5] * y + matrix[9] * z + matrix[13],
      matrix[2] * x + matrix[6] * y + matrix[10] * z + matrix[14],
      matrix[3] * x + matrix[7] * y + matrix[11] * z + matrix[15],
    ];
  }

  function projectPoint(matrix, point, width, height) {
    const clip = transformPoint(matrix, point);
    if (clip[3] <= 0) return null;
    return {
      depth: clip[2] / clip[3],
      x: (clip[0] / clip[3] * 0.5 + 0.5) * width,
      y: (1 - (clip[1] / clip[3] * 0.5 + 0.5)) * height,
    };
  }

  function fitPerspective(points, camera, policy, aspect, minimumDistance = 8) {
    if (!points.length) return {...camera};
    const cy = Math.cos(camera.yaw), sy = Math.sin(camera.yaw);
    const cp = Math.cos(camera.pitch), sp = Math.sin(camera.pitch);
    const right = [cy, 0, -sy], up = [-sp * sy, cp, -sp * cy];
    const forward = [cp * sy, sp, cp * cy];
    const dot = (a,b) => a.reduce((sum,value,i)=>sum+value*b[i],0);
    const horizontal = Math.tan(policy.fieldOfView / 2) * aspect * policy.horizontalMargin;
    const vertical = Math.tan(policy.fieldOfView / 2) * policy.verticalMargin;
    let left = Infinity, rightmost = -Infinity, bottom = Infinity, top = -Infinity, nearest = -Infinity;
    for (const point of points) {
      const x=dot(point,right), y=dot(point,up), z=dot(point,forward);
      left=Math.min(left,x-horizontal*z); rightmost=Math.max(rightmost,x+horizontal*z);
      bottom=Math.min(bottom,y-vertical*z); top=Math.max(top,y+vertical*z);
      nearest=Math.max(nearest,z);
    }
    const x=(rightmost+left)/2, y=(top+bottom)/2;
    // Slide the orbit target along the view ray to preserve its ground-relative
    // height. Otherwise a good initial fit can put the zoom pivot underground.
    const depth=Math.abs(sp)>1e-6 ? (camera.targetY-up[1]*y)/sp
      : dot([camera.targetX,camera.targetY,camera.targetZ],forward);
    // Intersect perspective-frustum inequalities, allowing lateral framing to
    // move. Keeping the world AABB center fixed can waste half the viewport.
    const eyeDepth=Math.max((rightmost-left)/(2*horizontal),(top-bottom)/(2*vertical),
      depth+minimumDistance,nearest+Math.max(1,minimumDistance/100));
    const target=right.map((value,i)=>value*x+up[i]*y+forward[i]*depth);
    return {...camera,targetX:target[0],targetY:target[1],targetZ:target[2],distance:(eyeDepth-depth)*1.01};
  }

  function lodFramingPoints(buildings, facilities) {
    // Fit the union of all LOD silhouettes. A small scene can still contain a
    // promoted role facility; changing LOD must not reveal a clipped roof.
    return [...buildings.map(b => ({...b, top:b.height})),
      ...facilities.map(f => ({...f, top:f.height+2.4}))].flatMap(b => [
      [b.x,b.top,b.z], [b.x+b.width,b.top,b.z],
      [b.x+b.width,b.top,b.z+b.depth], [b.x,b.top,b.z+b.depth],
    ]);
  }

  function stableVariant(value, count) {
    let hash = 2166136261;
    for (const character of String(value)) {
      hash ^= character.codePointAt(0);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0) % count;
  }

  function buildingParts(building, simplified = false) {
    if (building.aggregateRole) return globalThis.METROPOGITS_FILTERS.roleVolumes(building);
    if (simplified === true && building.archetype === "GENERIC_BUILDING") {
      return [{...building, y: 0, shade: 0}];
    }
    const x = building.x;
    const z = building.z;
    const width = building.width;
    const depth = building.depth;
    const height = building.height;
    const part = (offsetX, offsetY, offsetZ, partWidth, partHeight, partDepth, shade = 0) => ({
      depth: partDepth,
      height: partHeight,
      shade,
      width: partWidth,
      x: x + offsetX,
      y: offsetY,
      z: z + offsetZ,
    });
    switch (building.archetype) {
      case "GATE": {
        const pillarWidth = width * 0.24;
        return [
          part(0, 0, depth * 0.12, pillarWidth, height * 0.82, depth * 0.76),
          part(width - pillarWidth, 0, depth * 0.12, pillarWidth, height * 0.82, depth * 0.76, 0.08),
          part(0, height * 0.68, depth * 0.12, width, height * 0.18, depth * 0.76, 0.2),
          part(width * 0.42, height * 0.86, depth * 0.34, width * 0.16, height * 0.14, depth * 0.32, 0.35),
        ];
      }
      case "SERVICE_OFFICE":
        return [
          part(0, 0, 0, width, height * 0.16, depth),
          part(width * 0.08, height * 0.16, depth * 0.08, width * 0.84, height * 0.62, depth * 0.84, 0.08),
          part(width * 0.2, height * 0.78, depth * 0.2, width * 0.6, height * 0.22, depth * 0.6, 0.26),
        ];
      case "STRUCTURED_WAREHOUSE":
        return [
          part(0, 0, 0, width, height * 0.56, depth),
          part(width * 0.08, height * 0.56, depth * 0.08, width * 0.2, height * 0.1, depth * 0.84, 0.2),
          part(width * 0.4, height * 0.56, depth * 0.08, width * 0.2, height * 0.1, depth * 0.84, 0.2),
          part(width * 0.72, height * 0.56, depth * 0.08, width * 0.2, height * 0.1, depth * 0.84, 0.2),
        ];
      case "DOCUMENT_DEPOT":
        return [
          part(0, 0, 0, width, height * 0.28, depth),
          part(width * 0.06, height * 0.3, depth * 0.06, width * 0.88, height * 0.2, depth * 0.88, 0.1),
          part(width * 0.12, height * 0.52, depth * 0.12, width * 0.76, height * 0.18, depth * 0.76, 0.22),
        ];
      case "CACHE_TOWER":
        return [
          part(0, 0, 0, width, height * 0.12, depth),
          part(width * 0.16, height * 0.14, depth * 0.16, width * 0.68, height * 0.24, depth * 0.68, 0.04),
          part(width * 0.12, height * 0.4, depth * 0.12, width * 0.76, height * 0.24, depth * 0.76, 0.14),
          part(width * 0.2, height * 0.66, depth * 0.2, width * 0.6, height * 0.34, depth * 0.6, 0.28),
        ];
      case "EXCHANGE":
        return [
          part(0, 0, 0, width, height * 0.12, depth),
          part(width * 0.08, height * 0.12, depth * 0.12, width * 0.3, height * 0.68, depth * 0.76, 0.05),
          part(width * 0.62, height * 0.12, depth * 0.12, width * 0.3, height * 0.88, depth * 0.76, 0.18),
          part(width * 0.36, height * 0.48, depth * 0.34, width * 0.28, height * 0.12, depth * 0.32, 0.32),
        ];
      case "PORT":
        return [
          part(0, 0, depth * 0.52, width, height * 0.22, depth * 0.48),
          part(0, 0, 0, width * 0.24, height * 0.3, depth * 0.86, 0.08),
          part(width * 0.58, height * 0.2, depth * 0.08, width * 0.3, height * 0.8, depth * 0.34, 0.24),
        ];
      case "CONTROL_CENTER":
        return [
          part(0, 0, 0, width, height * 0.26, depth),
          part(width * 0.2, height * 0.26, depth * 0.2, width * 0.6, height * 0.5, depth * 0.6, 0.12),
          part(width * 0.44, height * 0.76, depth * 0.44, width * 0.12, height * 0.24, depth * 0.12, 0.36),
        ];
      case "LIBRARY":
        return [
          part(0, 0, depth * 0.08, width * 0.38, height * 0.58, depth * 0.84),
          part(width * 0.62, 0, depth * 0.08, width * 0.38, height * 0.58, depth * 0.84, 0.08),
          part(width * 0.32, height * 0.58, depth * 0.3, width * 0.36, height * 0.2, depth * 0.4, 0.28),
        ];
      default: {
        const variant = stableVariant(building.entityId, 4);
        if (variant === 1) {
          return [
            part(0, 0, depth * 0.08, width * 0.42, height * 0.78, depth * 0.84),
            part(width * 0.58, 0, depth * 0.08, width * 0.42, height, depth * 0.84, 0.12),
          ];
        }
        if (variant === 2) {
          return [
            part(0, 0, 0, width, height * 0.44, depth),
            part(width * 0.14, height * 0.44, depth * 0.14, width * 0.72, height * 0.32, depth * 0.72, 0.1),
            part(width * 0.3, height * 0.76, depth * 0.3, width * 0.4, height * 0.24, depth * 0.4, 0.22),
          ];
        }
        if (variant === 3) {
          return [
            part(0, 0, 0, width, height * 0.48, depth),
            part(width * 0.58, height * 0.48, depth * 0.08, width * 0.34, height * 0.52, depth * 0.44, 0.18),
          ];
        }
        return [
          part(width * 0.05, 0, depth * 0.05, width * 0.9, height * 0.82, depth * 0.9),
          part(width * 0.3, height * 0.82, depth * 0.3, width * 0.4, height * 0.18, depth * 0.4, 0.18),
        ];
      }
    }
  }

  const networkProfiles = Object.freeze({
    DEPENDENCY_ROAD: Object.freeze({ marking: 0.16, shoulder: 1.6, surface: 0.9 }),
    HTTP_HIGHWAY: Object.freeze({ marking: 0.3, shoulder: 2.5, surface: 1.6 }),
    MESSAGING_PATH: Object.freeze({ marking: 0.32, shoulder: 1.3, surface: 0.65 }),
  });
  const cameraPolicy = Object.freeze({
    fieldOfView: Math.PI / 4,
    horizontalMargin: 0.94,
    pitch: 0.62,
    verticalMargin: 0.92,
    yaw: -0.68,
  });

  globalThis.METROPOGITS_WEBGL_MATH = Object.freeze({
    fitPerspective,
    lodFramingPoints,
    lookAt,
    multiply,
    perspective,
    projectPoint,
    transformPoint,
  });
  globalThis.METROPOGITS_BUILDING_FORMS = Object.freeze({
    partsFor: buildingParts,
  });
  globalThis.METROPOGITS_NETWORK_STYLES = networkProfiles;
  globalThis.METROPOGITS_CAMERA_POLICY = cameraPolicy;

  function createGeometryCache() {
    let savedKey;
    let saved;
    return (key, build) => {
      if (!saved || key !== savedKey) {
        saved = build();
        savedKey = key;
      }
      return saved;
    };
  }
  globalThis.METROPOGITS_GEOMETRY_CACHE = createGeometryCache;

  function createPickProjection(descriptors) {
    const unique = new Map(), vertices = [], projectedPoints = [];
    const regions = descriptors.map(descriptor => ({id:descriptor.id, kind:descriptor.kind,
      priority:descriptor.priority, minX:0, minY:0, maxX:0, maxY:0, depth:0,
      points: descriptor.points.map(point => {
        const key = point.join(',');
        let index = unique.get(key);
        if (index === undefined) {
          index = vertices.length;
          unique.set(key, index);
          vertices.push(point.slice());
          projectedPoints.push({x:0, y:0, depth:0, valid:false});
        }
        return projectedPoints[index];
      })}));
    // Regions and vertices belong to this cache. Consumers use them only until
    // the next projection; no scene/graph object is mutated.
    function project(matrix, width, height) {
      for (let i=0; i<vertices.length; i+=1) {
        const [x,y,z] = vertices[i], point = projectedPoints[i];
        const w = matrix[3]*x + matrix[7]*y + matrix[11]*z + matrix[15];
        point.valid = w > 0;
        if (!point.valid) continue;
        point.x = ((matrix[0]*x+matrix[4]*y+matrix[8]*z+matrix[12])/w*.5+.5)*width;
        point.y = (1-((matrix[1]*x+matrix[5]*y+matrix[9]*z+matrix[13])/w*.5+.5))*height;
        point.depth = (matrix[2]*x+matrix[6]*y+matrix[10]*z+matrix[14])/w;
      }
      const visible = [];
      for (const region of regions) {
        let minX=Infinity, minY=Infinity, maxX=-Infinity, maxY=-Infinity, depth=Infinity, valid=true;
        for (const point of region.points) {
          if (!point.valid) { valid=false; break; }
          minX=Math.min(minX,point.x); minY=Math.min(minY,point.y);
          maxX=Math.max(maxX,point.x); maxY=Math.max(maxY,point.y);
          depth=Math.min(depth,point.depth);
        }
        if (!valid) continue;
        const margin = region.kind === 'network' ? 8 : 0;
        if (maxX < -margin || maxY < -margin || minX > width+margin || minY > height+margin) continue;
        region.minX=minX-margin; region.minY=minY-margin;
        region.maxX=maxX+margin; region.maxY=maxY+margin; region.depth=depth;
        visible.push(region);
      }
      return visible.sort((a,b)=>b.priority-a.priority || a.depth-b.depth);
    }
    return Object.freeze({project, vertexCount:vertices.length, regionCount:regions.length});
  }
  globalThis.METROPOGITS_PICK_PROJECTION = createPickProjection;

  if (typeof document === "undefined") return;

  const data = globalThis.METROPOGITS_DATA;
  const orientedBuildings = data?.routing?.parcelPlan?.buildings || {};
  const filterEngine = globalThis.METROPOGITS_FILTERS;
  const activityEngine = globalThis.METROPOGITS_ACTIVITY;
  const canvas = document.getElementById("city-canvas");
  const rendererMode = document.getElementById("renderer-mode");
  if (!data?.scene || !data?.ucg || !filterEngine || !canvas) return;

  const gl = canvas.getContext("webgl", {
    alpha: false,
    antialias: true,
    depth: true,
    preserveDrawingBuffer: true,
  });
  if (!gl) {
    if (rendererMode) rendererMode.textContent = "2D fallback";
    return;
  }

  function restoreCanvasForFallback() {
    const replacement = canvas.cloneNode(false);
    canvas.replaceWith(replacement);
    if (rendererMode) rendererMode.textContent = "2D fallback";
  }

  function compileShader(type, source) {
    const shader = gl.createShader(type);
    gl.shaderSource(shader, source);
    gl.compileShader(shader);
    if (!gl.getShaderParameter(shader, gl.COMPILE_STATUS)) {
      const message = gl.getShaderInfoLog(shader) || "unknown shader error";
      gl.deleteShader(shader);
      throw new Error(message);
    }
    return shader;
  }

  function createProgram() {
    const vertex = compileShader(gl.VERTEX_SHADER, `
      attribute vec3 a_position;
      attribute vec3 a_normal;
      attribute vec3 a_color;
      uniform mat4 u_view_projection;
      varying vec3 v_color;
      varying float v_light;
      void main() {
        vec3 light_direction = normalize(vec3(0.45, 0.85, 0.35));
        v_light = 0.46 + max(dot(normalize(a_normal), light_direction), 0.0) * 0.54;
        v_color = a_color;
        gl_Position = u_view_projection * vec4(a_position, 1.0);
      }
    `);
    const fragment = compileShader(gl.FRAGMENT_SHADER, `
      precision mediump float;
      varying vec3 v_color;
      varying float v_light;
      void main() {
        gl_FragColor = vec4(v_color * v_light, 1.0);
      }
    `);
    const linked = gl.createProgram();
    gl.attachShader(linked, vertex);
    gl.attachShader(linked, fragment);
    gl.linkProgram(linked);
    gl.deleteShader(vertex);
    gl.deleteShader(fragment);
    if (!gl.getProgramParameter(linked, gl.LINK_STATUS)) {
      throw new Error(gl.getProgramInfoLog(linked) || "unknown program link error");
    }
    return linked;
  }

  let program;
  try {
    program = createProgram();
  } catch {
    restoreCanvasForFallback();
    return;
  }

  globalThis.METROPOGITS_RENDERER = "webgl";
  canvas.setAttribute("aria-label", "Interactive 3D repository city");
  if (rendererMode) rendererMode.textContent = "WebGL 3D";

  const scene = data.scene;
  const ucg = data.ucg;
  const inspector = document.getElementById("inspector-content");
  const hoverLabel = document.getElementById("hover-label");
  const labelLayer = document.getElementById("scene-labels");
  const repositoryName = document.getElementById("repository-name");
  const cityStats = document.getElementById("city-stats");
  const clearFilters = document.getElementById("clear-filters");
  const filterSummary = document.getElementById("filter-summary");
  const detailLevel = document.getElementById("detail-level");
  const activityToggle = document.getElementById("synthetic-activity");
  const activityNote = document.getElementById("synthetic-activity-note");
  const toolbarHelp = document.getElementById("toolbar-help");
  const filterControls = new Map(
    [...document.querySelectorAll("[data-filter]")].map((control) => [
      control.dataset.filter,
      control,
    ]),
  );
  const entities = new Map(ucg.entities.map((entity) => [entity.id, entity]));
  const edges = new Map(ucg.edges.map((edge) => [edge.id, edge]));
  const evidence = new Map(ucg.evidence.map((item) => [item.evidenceId, item]));
  const districts = new Map(scene.districts.map((district) => [district.id, district]));
  const districtTerritories = new Map(
    (data.territories?.districts || []).map((territory) => [territory.id, territory]),
  );
  const streetRectangles = data.streets?.surfaces || data.streets?.rectangles || [];
  const accessPolicy = filterEngine.createAccessPolicy(data.routing, data.roadHierarchy, data.streetDemand, data.streetCurves);
  let accessFrame = null;
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
    const depth = district?.parentId === null ? 0 : districtDepth(district.parentId) + 1;
    districtDepths.set(districtId, depth);
    return depth;
  }
  for (const district of scene.districts) districtDepth(district.id);
  const metropolis = globalThis.METROPOGITS_METROPOLIS;
  const repositoriesByRootDistrict = new Map(
    (metropolis?.repositories || []).map((repository) => [
      repository.rootDistrictId,
      repository,
    ]),
  );
  const filterIndex = filterEngine.createIndex(scene, ucg);
  const majorDistrictIds = new Set(data.majorDistrictIds || filterEngine.majorDistrictIds(scene));
  const lodPolicy = filterEngine.createLodPolicy(scene, data.territories, data.streets, ucg);
  const expandedAggregateIds = new Set();
  let showAllNetworks = false;
  let structureOverlay = false;
  const urbanContext = data.cityContext;
  function contextVisible(id) {
    return filterEngine.contextDetailVisible(Boolean(urbanContext),structureOverlay,
      majorDistrictIds.has(id),id,state.selected?.kind==='district' ? state.selected.id : null);
  }
  const aggregateFacilities = new Map(
    lodPolicy.aggregates.map((aggregate) => [aggregate.id, aggregate]),
  );
  const majorDistrictColors = ["#18324a", "#2d284a", "#183d37", "#3b2b20", "#35243f"];
  const majorDistrictColorById = new Map(
    [...majorDistrictIds].sort().map((districtId, index) => [
      districtId,
      majorDistrictColors[index % majorDistrictColors.length],
    ]),
  );
  const framingDistricts = scene.buildings.length >= 256 && majorDistrictIds.size
    ? [...majorDistrictIds].map((districtId) => districts.get(districtId)).filter(Boolean)
    : scene.districts;
  const worldBounds = framingDistricts.map(districtTerritory).reduce(
    (bounds, territory) => ({
      maxX: Math.max(bounds.maxX, territory.bounds.maxX),
      maxZ: Math.max(bounds.maxZ, territory.bounds.maxZ),
      minX: Math.min(bounds.minX, territory.bounds.minX),
      minZ: Math.min(bounds.minZ, territory.bounds.minZ),
    }),
    { maxX: -Infinity, maxZ: -Infinity, minX: Infinity, minZ: Infinity },
  );
  if (!Number.isFinite(worldBounds.minX)) {
    Object.assign(worldBounds, { maxX: 1, maxZ: 1, minX: 0, minZ: 0 });
  }
  const worldSpan = Math.max(
    worldBounds.maxX - worldBounds.minX,
    worldBounds.maxZ - worldBounds.minZ,
    24,
  );
  const worldDiagonal = Math.hypot(
    worldBounds.maxX - worldBounds.minX,
    worldBounds.maxZ - worldBounds.minZ,
  );
  const tallestBuilding = Math.max(8, ...scene.buildings.map((building) => building.height));
  const initialCamera = {
    distance: Math.max(worldSpan * 1.35, worldDiagonal * 1.05, tallestBuilding * 4),
    pitch: cameraPolicy.pitch,
    targetX: (worldBounds.minX + worldBounds.maxX) / 2,
    targetY: tallestBuilding * 0.12,
    targetZ: (worldBounds.minZ + worldBounds.maxZ) / 2,
    yaw: cameraPolicy.yaw,
  };
  const state = {
    ...initialCamera,
    activityEpoch: 0,
    dragging: false,
    dragMode: "orbit",
    moveMode: false,
    filters: { confidence: "", language: "", role: "", technology: "" },
    moved: false,
    pointerX: 0,
    pointerY: 0,
    selected: null,
    syntheticActivity: false,
  };
  const reducedMotion = globalThis.matchMedia?.("(prefers-reduced-motion: reduce)");
  const triangleBuffer = gl.createBuffer();
  const lineBuffer = gl.createBuffer();
  const accessOverlayBuffer = gl.createBuffer();
  const activityBuffer = gl.createBuffer();
  const positionLocation = gl.getAttribLocation(program, "a_position");
  const normalLocation = gl.getAttribLocation(program, "a_normal");
  const colorLocation = gl.getAttribLocation(program, "a_color");
  const matrixLocation = gl.getUniformLocation(program, "u_view_projection");
  let framePending = false;
  let cameraFitted = false;
  let hitRegions = [];
  let viewProjection = null;
  let viewportWidth = 1;
  let viewportHeight = 1;
  let visibleBuildingIds = new Set(scene.buildings.map((building) => building.entityId));
  let visibleNetworkIds = new Set(scene.networks.map((network) => network.id));
  let renderedAggregateIds = new Set();
  let renderedBuildingIds = new Set(visibleBuildingIds);
  let renderedDistrictIds = new Set(drawableDistrictIds);
  let renderedNetworkIds = new Set(visibleNetworkIds);
  let currentDetailLevel = "detail";
  let lodCacheKey = "";
  let visibilityVersion = 0;

  const colors = {
    CACHE_TOWER: "#facc15",
    CONTROL_CENTER: "#a78bfa",
    DOCUMENT_DEPOT: "#fb923c",
    EXCHANGE: "#2dd4bf",
    GATE: "#f472b6",
    GENERIC_BUILDING: "#94a3b8",
    LIBRARY: "#facc15",
    PORT: "#38bdf8",
    SERVICE_OFFICE: "#60a5fa",
    STRUCTURED_WAREHOUSE: "#34d399",
  };
  const networkColors = {
    DEPENDENCY_ROAD: "#a8b5c8",
    HTTP_HIGHWAY: "#f97316",
    MESSAGING_PATH: "#a855f7",
  };

  function color(value) {
    const hex = value.startsWith("#") ? value.slice(1) : value;
    return [0, 2, 4].map((offset) => Number.parseInt(hex.slice(offset, offset + 2), 16) / 255);
  }

  function lighten(value, amount) {
    return value.map((channel) => channel + (1 - channel) * amount);
  }

  function vertex(target, position, normal, vertexColor) {
    target.push(...position, ...normal, ...vertexColor);
  }

  function quad(target, corners, normal, vertexColor) {
    for (const index of [0, 1, 2, 0, 2, 3]) vertex(target, corners[index], normal, vertexColor);
  }

  function box(target, x, y, z, width, height, depth, vertexColor) {
    const x1 = x + width;
    const y1 = y + height;
    const z1 = z + depth;
    quad(target, [[x, y1, z], [x, y1, z1], [x1, y1, z1], [x1, y1, z]], [0, 1, 0], vertexColor);
    quad(target, [[x, y, z1], [x, y1, z1], [x, y1, z], [x, y, z]], [-1, 0, 0], vertexColor);
    quad(target, [[x1, y, z], [x1, y1, z], [x1, y1, z1], [x1, y, z1]], [1, 0, 0], vertexColor);
    quad(target, [[x, y, z], [x, y1, z], [x1, y1, z], [x1, y, z]], [0, 0, -1], vertexColor);
    quad(target, [[x1, y, z1], [x1, y1, z1], [x, y1, z1], [x, y, z1]], [0, 0, 1], vertexColor);
    quad(target, [[x, y, z1], [x, y, z], [x1, y, z], [x1, y, z1]], [0, -1, 0], vertexColor);
  }

  function line(target, start, end, vertexColor) {
    vertex(target, start, [0, 1, 0], vertexColor);
    vertex(target, end, [0, 1, 0], vertexColor);
  }

  function orientedBox(target, footprint, y, height, vertexColor) {
    const top=footprint.map(([x,z])=>[x,y+height,z]);
    quad(target,[top[0],top[3],top[2],top[1]],[0,1,0],vertexColor);
    for(let i=0;i<4;i++) {
      const a=footprint[i],b=footprint[(i+1)%4],length=Math.hypot(b[0]-a[0],b[1]-a[1]);
      quad(target,[[a[0],y,a[1]],top[i],top[(i+1)%4],[b[0],y,b[1]]],
        [(b[1]-a[1])/length,0,(a[0]-b[0])/length],vertexColor);
    }
  }

  function roadSegment(target, start, end, width, y, vertexColor) {
    const deltaX = end[0] - start[0];
    const deltaZ = end[1] - start[1];
    const length = Math.hypot(deltaX, deltaZ) || 1;
    const offsetX = -deltaZ / length * width / 2;
    const offsetZ = deltaX / length * width / 2;
    quad(target, [
      [start[0] + offsetX, y, start[1] + offsetZ],
      [end[0] + offsetX, y, end[1] + offsetZ],
      [end[0] - offsetX, y, end[1] - offsetZ],
      [start[0] - offsetX, y, start[1] - offsetZ],
    ], [0, 1, 0], vertexColor);
  }

  function cameraMatrixAtDistance(distance) {
    const horizontal = Math.cos(state.pitch) * distance;
    const eye = [
      state.targetX + Math.sin(state.yaw) * horizontal,
      state.targetY + Math.sin(state.pitch) * distance,
      state.targetZ + Math.cos(state.yaw) * horizontal,
    ];
    const view = lookAt(eye, [state.targetX, state.targetY, state.targetZ], [0, 1, 0]);
    const projection = perspective(
      cameraPolicy.fieldOfView,
      Math.max(0.1, viewportWidth / viewportHeight),
      Math.max(0.1, distance / 250),
      distance * 10 + tallestBuilding * 4,
    );
    return multiply(projection, view);
  }

  function cameraMatrix() {
    return cameraMatrixAtDistance(state.distance);
  }

  function fitInitialDistance() {
    const points = [];
    const fitDistricts = scene.buildings.length >= 256 ? framingDistricts : scene.districts;
    for (const district of fitDistricts) {
      for (const rectangle of districtTerritory(district).rectangles) {
        points.push(
          [rectangle.x, 0, rectangle.z],
          [rectangle.x + rectangle.width, 0, rectangle.z],
          [rectangle.x + rectangle.width, 0, rectangle.z + rectangle.depth],
          [rectangle.x, 0, rectangle.z + rectangle.depth],
        );
      }
    }
    for (const point of lodFramingPoints(scene.buildings,[...aggregateFacilities.values()])) points.push(point);
    for(const parcel of Object.values(orientedBuildings))for(const part of parcel.parts)
      for(const [x,z] of part.footprint)points.push([x,part.y+part.height,z]);
    const fitted=fitPerspective(points,state,cameraPolicy,viewportWidth/viewportHeight,Math.max(8,tallestBuilding));
    for (const key of ['targetX','targetY','targetZ']) {
      state[key]=fitted[key];
      initialCamera[key]=fitted[key];
    }
    return fitted.distance;
  }

  function selected(kind, id) {
    return state.selected?.kind === kind && state.selected.id === id;
  }

  const geometryCache = createGeometryCache();
  const uploadedGeometry = new WeakMap();

  function buildGeometry(timestamp) {
    return geometryCache(lodCacheKey, () => buildUncachedGeometry(timestamp));
  }

  function buildUncachedGeometry(timestamp) {
    const triangles = [];
    const lines = [];
    const accessOverlay = [];
    if(data.occupiedGround && !structureOverlay) {
      const majorOrder=[...majorDistrictIds].sort();
      for(const pad of data.occupiedGround.pads) {
        let owner=districts.get(pad.districtId);
        while(owner && !majorDistrictIds.has(owner.id))owner=districts.get(owner.parentId);
        const tint=color(pad.color || (owner?urbanContext.majorColors[majorOrder.indexOf(owner.id)%urbanContext.majorColors.length]:urbanContext.ground));
        for(const p of pad.polygons)for(let i=1;i<p.length-1;i++)
          quad(triangles,[p[0],p[i],p[i+1],p[i+1]].map(([x,z])=>[x,-.03,z]),[0,1,0],tint);
      }
    }
    for (const district of framingDistricts) {
      if(data.occupiedGround && !structureOverlay) continue;
      for (const rectangle of districtTerritory(district).rectangles) {
        box(
          triangles,
          rectangle.x,
          -0.55,
          rectangle.z,
          rectangle.width,
          0.5,
          rectangle.depth,
          color(urbanContext && !structureOverlay ? urbanContext.ground : "#182337"),
        );
      }
    }

    for (const districtId of [...majorDistrictIds].sort()) {
      if(data.occupiedGround && !structureOverlay) continue;
      const district = districts.get(districtId);
      if (!district) continue;
      const territory = districtTerritory(district);
      const index=[...majorDistrictIds].sort().indexOf(districtId);
      const districtColor = color(urbanContext && !structureOverlay
        ? urbanContext.majorColors[index % urbanContext.majorColors.length] : majorDistrictColorById.get(districtId));
      for (const rectangle of territory.rectangles) {
        box(
          triangles,
          rectangle.x,
          -0.03,
          rectangle.z,
          rectangle.width,
          0.12,
          rectangle.depth,
          districtColor,
        );
      }
      const borderColor = lighten(districtColor, 0.48);
      for (const segment of territory.boundary) {
        if (urbanContext && !structureOverlay) {
          line(lines,[segment[0][0],.09,segment[0][1]],[segment[1][0],.09,segment[1][1]],borderColor);
          continue;
        }
        roadSegment(triangles, segment[0], segment[1], 1.2, 0.09, borderColor);
      }
    }

    const streetColors = {
      ALLEY: "#263447",
      BOULEVARD: "#0b1320",
      ROUTE_ACCESS: "#1c293b",
      STREET: "#172437",
    };
    for (const rectangle of streetRectangles) {
      if (accessPolicy && !data.streets?.structural) break;
      if (!filterEngine.corridorVisible(rectangle, renderedNetworkIds)) continue;
      if (rectangle.points) {
        quad(triangles, rectangle.points.map(([x,z]) => [x, rectangle.elevation ?? 0.08, z]),
          [0,1,0], color(rectangle.color || streetColors.STREET));
        continue;
      }
      roadSegment(
        triangles,
        [rectangle.x, rectangle.z + rectangle.depth / 2],
        [rectangle.x + rectangle.width, rectangle.z + rectangle.depth / 2],
        rectangle.depth,
        rectangle.elevation ?? 0.08,
        color(rectangle.color || streetColors[rectangle.tier] || streetColors.STREET),
      );
    }

    if (currentDetailLevel === "detail" && (!urbanContext || structureOverlay)) {
      for (const block of civicBlocks) {
        const blockColor = color("#243248");
        const curbColor = color("#52637b");
        box(
          triangles,
          block.minX,
          -0.04,
          block.minZ,
          block.maxX - block.minX,
          0.1,
          block.maxZ - block.minZ,
          blockColor,
        );
        const corners = [
          [block.minX, block.minZ],
          [block.maxX, block.minZ],
          [block.maxX, block.maxZ],
          [block.minX, block.maxZ],
          [block.minX, block.minZ],
        ];
        for (let index = 1; index < corners.length; index += 1) {
          roadSegment(triangles, corners[index - 1], corners[index], 0.42, 0.07, curbColor);
        }
      }
    }

    for (const district of scene.districts) {
      if (!renderedDistrictIds.has(district.id)) continue;
      if (!contextVisible(district.id)) continue;
      const depth = districtDepths.get(district.id) || 0;
      const y = 0.06 + depth * 0.025;
      const districtColor = selected("district", district.id)
        ? color("#38bdf8")
        : lighten(color("#40516c"), Math.min(0.18, depth * 0.025));
      const territory = districtTerritory(district);
      for (const segment of territory.boundary) {
        line(
          lines,
          [segment[0][0], y, segment[0][1]],
          [segment[1][0], y, segment[1][1]],
          districtColor,
        );
      }
      if (selected("district", district.id)) {
        for (const segment of territory.boundary) {
          roadSegment(
            triangles,
            segment[0],
            segment[1],
            0.5,
            y + 0.02,
            color("#38bdf8"),
          );
        }
      }
    }

    const roadStyles = new Map((accessFrame?.segments || []).map(segment => [segment.id, filterEngine.accessRoadStyle(segment)]));
    const junctionGeometry = filterEngine.accessJunctionGeometry(accessFrame);
    for (const segment of accessFrame?.segments || []) {
      if (segment.highlighted) {
        for(let i=1;i<segment.path.length;i++) {
          const a=segment.path[i-1],b=segment.path[i];
          line(accessOverlay,[a[0],.22,a[1]],[b[0],.22,b[1]],color("#67d7ff"));
        }
      }
      const style = roadStyles.get(segment.id), width = style.width;
      if (segment.pavement) {
        for (const piece of segment.pavement) {
          quad(triangles, piece.points.map(([x,z]) => [x,.14,z]), [0,1,0], color(style.surface));
        }
      } else {
        roadSegment(triangles, segment.start, segment.end, width, 0.11, color(style.shoulder));
        roadSegment(triangles, segment.start, segment.end, width * 0.82, 0.14, color(style.surface));
      }
      for (const marking of filterEngine.accessMarkingSegments(segment, junctionGeometry.trims)) {
        roadSegment(triangles, marking.start, marking.end, Math.min(0.13, width * 0.12), 0.18,
          color(segment.kind === "DEPENDENCY_ROAD" ? style.marking : networkColors[segment.kind]));
      }
    }
    for (const surface of junctionGeometry.surfaces) {
      for (const [x0,z0,x1,z1] of surface.rectangles) {
        roadSegment(triangles, [x0,(z0+z1)/2], [x1,(z0+z1)/2], z1-z0, 0.16, color(surface.surface));
      }
    }
    for (const network of accessPolicy ? [] : scene.networks) {
      if (!renderedNetworkIds.has(network.id)) continue;
      const roadColor = selected("network", network.id)
        ? color("#f8fafc")
        : color(networkColors[network.kind] || networkColors.DEPENDENCY_ROAD);
      const profile = networkProfiles[network.kind] || networkProfiles.DEPENDENCY_ROAD;
      const weightScale = 1 + Math.min(0.8, Math.log2(network.edgeIds.length + 1) * 0.12);
      const selectionScale = weightScale * (selected("network", network.id) ? 1.28 : 1);
      for (let index = 1; index < network.path.length; index += 1) {
        roadSegment(
          triangles,
          network.path[index - 1],
          network.path[index],
          profile.shoulder * selectionScale,
          0.1,
          color("#080d16"),
        );
        roadSegment(
          triangles,
          network.path[index - 1],
          network.path[index],
          profile.surface * selectionScale,
          0.14,
          color(network.kind === "HTTP_HIGHWAY" ? "#4b3a31" : "#354256"),
        );
        roadSegment(
          triangles,
          network.path[index - 1],
          network.path[index],
          profile.marking * selectionScale,
          0.18,
          roadColor,
        );
      }
    }

    for (const building of scene.buildings) {
      if (!renderedBuildingIds.has(building.entityId)) continue;
      const baseColor = color(colors[building.archetype] || colors.GENERIC_BUILDING);
      const selectedColor = selected("building", building.entityId)
        ? lighten(baseColor, 0.62)
        : baseColor;
      const oriented=orientedBuildings[building.entityId];
      for (const part of oriented?.parts || buildingParts(building, currentDetailLevel === "district")) {
        if (part.footprint) {
          orientedBox(triangles,part.footprint,.2+part.y,part.height,part.shade ? lighten(selectedColor,part.shade) : selectedColor);
          continue;
        }
        box(
          triangles,
          part.x,
          0.2 + part.y,
          part.z,
          part.width,
          part.height,
          part.depth,
          part.shade ? lighten(selectedColor, part.shade) : selectedColor,
        );
      }
      if (selected("building", building.entityId)) {
        if (oriented) {
          for(let i=0;i<4;i++) {
            const a=oriented.footprint[i],b=oriented.footprint[(i+1)%4];
            for(const y of [.24,building.height+.65])line(lines,[a[0],y,a[1]],[b[0],y,b[1]],color("#f8fafc"));
          }
          continue;
        }
        const x0 = building.x - 0.45;
        const x1 = building.x + building.width + 0.45;
        const z0 = building.z - 0.45;
        const z1 = building.z + building.depth + 0.45;
        const y0 = 0.24;
        const y1 = building.height + 0.65;
        const highlight = color("#f8fafc");
        for (const [start, end] of [
          [[x0, y0, z0], [x1, y0, z0]],
          [[x1, y0, z0], [x1, y0, z1]],
          [[x1, y0, z1], [x0, y0, z1]],
          [[x0, y0, z1], [x0, y0, z0]],
          [[x0, y1, z0], [x1, y1, z0]],
          [[x1, y1, z0], [x1, y1, z1]],
          [[x1, y1, z1], [x0, y1, z1]],
          [[x0, y1, z1], [x0, y1, z0]],
          [[x0, y0, z0], [x0, y1, z0]],
          [[x1, y0, z0], [x1, y1, z0]],
          [[x1, y0, z1], [x1, y1, z1]],
          [[x0, y0, z1], [x0, y1, z1]],
        ]) line(lines, start, end, highlight);
      }
    }
    for (const aggregateId of [...renderedAggregateIds].sort()) {
      const facility = aggregateFacilities.get(aggregateId);
      const selectedMember = state.selected?.kind === "building"
        && facility.memberEntityIds.includes(state.selected.id)
        ? scene.buildings.find(b => b.entityId === state.selected.id) : null;
      const isSelected = selected("aggregate", facility.id) || Boolean(selectedMember);
      for (const plot of filterEngine.aggregateGroundPlots(facility,Boolean(data.occupiedGround && !structureOverlay))) {
        box(
          triangles,
          plot.x,
          0.16,
          plot.z,
          plot.width,
          2.2,
          plot.depth,
          color(isSelected ? "#f8fafc" : "#475569"),
        );
      }
      for (const aggregatePart of filterEngine.aggregateParts(facility)) {
        const baseColor = color(
          colors[aggregatePart.archetype] || colors.GENERIC_BUILDING,
        );
        const partColor = isSelected ? lighten(baseColor, 0.45) : baseColor;
        for (const part of buildingParts(aggregatePart)) {
          box(
            triangles,
            part.x,
            2.4 + part.y,
            part.z,
            part.width,
            part.height,
            part.depth,
            part.shade ? lighten(partColor, part.shade) : partColor,
          );
        }
      }
      const borderColor = color(isSelected ? "#f8fafc" : "#fbbf24");
      for (const plot of filterEngine.aggregateGroundPlots(facility,Boolean(data.occupiedGround && !structureOverlay))) {
        const x0 = plot.x - 0.55;
        const x1 = plot.x + plot.width + 0.55;
        const z0 = plot.z - 0.55;
        const z1 = plot.z + plot.depth + 0.55;
        for (const [start, end] of [
          [[x0, 0.2, z0], [x1, 0.2, z0]],
          [[x1, 0.2, z0], [x1, 0.2, z1]],
          [[x1, 0.2, z1], [x0, 0.2, z1]],
          [[x0, 0.2, z1], [x0, 0.2, z0]],
        ]) line(lines, start, end, borderColor);
      }
      if (selectedMember) {
        const b = selectedMember, y = facility.height + 3;
        const corners = [[b.x, y, b.z], [b.x + b.width, y, b.z],
          [b.x + b.width, y, b.z + b.depth], [b.x, y, b.z + b.depth]];
        for (let i = 0; i < 4; i += 1) line(lines, corners[i], corners[(i + 1) % 4], color("#22d3ee"));
      }
    }

    return { lines, triangles, accessOverlay };
  }

  function buildActivityGeometry(timestamp) {
    const triangles = [];
    if (accessFrame) {
      if (state.syntheticActivity && activityEngine) {
        const elapsed = Math.max(0, timestamp - state.activityEpoch);
        for (const route of accessFrame.animated) {
          const progress = (elapsed / 6000 + activityEngine.phaseForId(route.id)) % 1;
          const sample = accessPolicy.position(route, progress);
          if (!sample || !accessFrame.segmentIds.has(sample.segmentId)) continue;
          box(triangles, sample.point[0]-0.22, 0.25, sample.point[1]-0.22, 0.44, 0.44, 0.44, color("#f8fafc"));
        }
      }
      return triangles;
    }
    if (state.syntheticActivity && activityEngine) {
      const elapsed = Math.max(0, timestamp - state.activityEpoch);
      for (const network of scene.networks) {
        if (!renderedNetworkIds.has(network.id)) continue;
        const progress = (elapsed / 6000 + activityEngine.phaseForId(network.id)) % 1;
        const point = activityEngine.pointAlongPath(network.path, progress);
        if (point) {
          box(triangles, point[0] - 0.45, 0.8, point[1] - 0.45, 0.9, 0.9, 0.9, color("#f8fafc"));
        }
      }
    }
    return triangles;
  }

  function bindAndDraw(buffer, values, primitive, usage = gl.STATIC_DRAW) {
    if (!values.length) return;
    gl.bindBuffer(gl.ARRAY_BUFFER, buffer);
    if (uploadedGeometry.get(buffer) !== values) {
      gl.bufferData(gl.ARRAY_BUFFER, new Float32Array(values), usage);
      uploadedGeometry.set(buffer, values);
    }
    const stride = 9 * Float32Array.BYTES_PER_ELEMENT;
    gl.enableVertexAttribArray(positionLocation);
    gl.vertexAttribPointer(positionLocation, 3, gl.FLOAT, false, stride, 0);
    gl.enableVertexAttribArray(normalLocation);
    gl.vertexAttribPointer(normalLocation, 3, gl.FLOAT, false, stride, 3 * 4);
    gl.enableVertexAttribArray(colorLocation);
    gl.vertexAttribPointer(colorLocation, 3, gl.FLOAT, false, stride, 6 * 4);
    gl.drawArrays(primitive, 0, values.length / 9);
  }

  function districtLabel(district) {
    const entity = entities.get(district?.id);
    const member = repositoriesByRootDistrict.get(district?.id);
    return entity?.path
      || district?.label
      || member?.id
      || (district?.parentId === null ? ucg.repository.id : district?.id)
      || "Unknown district";
  }

  function districtCanvasLabel(district) {
    const label = districtLabel(district);
    return label.split("/").filter(Boolean).at(-1) || label;
  }

  function projected(point) {
    return projectPoint(viewProjection, point, viewportWidth, viewportHeight);
  }

  const pickCache = createGeometryCache();
  function buildPickDescriptors() {
    const regions = [];
    for (const district of scene.districts) {
      if (!renderedDistrictIds.has(district.id)) continue;
      for (const rectangle of districtTerritory(district).rectangles) {
        const points = [
          [rectangle.x, 0.08, rectangle.z],
          [rectangle.x + rectangle.width, 0.08, rectangle.z],
          [rectangle.x + rectangle.width, 0.08, rectangle.z + rectangle.depth],
          [rectangle.x, 0.08, rectangle.z + rectangle.depth],
        ];
        if (points.every(Boolean)) {
          regions.push({
            id: district.id,
            kind: "district",
            points,
            priority: districtDepths.get(district.id) || 0,
          });
        }
      }
    }
    for (const network of accessFrame ? accessFrame.segments.map(s => ({id: s.id, path: s.path})) : scene.networks) {
      if (!accessFrame && !renderedNetworkIds.has(network.id)) continue;
      const points = network.path.map((point) => [point[0], 0.22, point[1]]);
      if (points.every(Boolean)) {
        regions.push({
          id: network.id,
          kind: "network",
          points,
          priority: 100,
        });
      }
    }
    for (const building of scene.buildings) {
      if (!renderedBuildingIds.has(building.entityId)) continue;
      const corners = [];
      const oriented=orientedBuildings[building.entityId];
      if(oriented) {
        for(const [x,z] of oriented.footprint)for(const y of [.2,building.height+.2])corners.push([x,y,z]);
      } else {
      for (const x of [building.x, building.x + building.width]) {
        for (const y of [0.2, building.height + 0.2]) {
          for (const z of [building.z, building.z + building.depth]) {
            corners.push([x, y, z]);
          }
        }
      }
      }
      if (corners.length === 8) {
        regions.push({
          id: building.entityId,
          kind: "building",
          points: corners,
          priority: 200,
        });
      }
    }
    for (const aggregateId of renderedAggregateIds) {
      const facility = aggregateFacilities.get(aggregateId);
      for (const plot of filterEngine.aggregateGroundPlots(facility,Boolean(data.occupiedGround && !structureOverlay))) {
        const corners = [];
        for (const x of [plot.x, plot.x + plot.width]) {
          for (const y of [0.2, facility.height + 2.4]) {
            for (const z of [plot.z, plot.z + plot.depth]) {
              corners.push([x, y, z]);
            }
          }
        }
        if (corners.length === 8) {
          regions.push({
            id: facility.id,
            kind: "aggregate",
            points: corners,
            priority: 250,
          });
        }
      }
    }
    return createPickProjection(regions);
  }

  function buildHitRegions() {
    if (!projectionDirty) return hitRegions;
    return pickCache(lodCacheKey, buildPickDescriptors).project(viewProjection, viewportWidth, viewportHeight);
  }

  function pointInPolygon(x, y, points) {
    let inside = false;
    for (let index = 0, previous = points.length - 1; index < points.length; previous = index++) {
      const currentPoint = points[index];
      const previousPoint = points[previous];
      const crosses = currentPoint.y > y !== previousPoint.y > y
        && x < ((previousPoint.x - currentPoint.x) * (y - currentPoint.y))
          / (previousPoint.y - currentPoint.y) + currentPoint.x;
      if (crosses) inside = !inside;
    }
    return inside;
  }

  function distanceToSegment(x, y, start, end) {
    const deltaX = end.x - start.x;
    const deltaY = end.y - start.y;
    const lengthSquared = deltaX * deltaX + deltaY * deltaY;
    if (!lengthSquared) return Math.hypot(x - start.x, y - start.y);
    const fraction = Math.max(0, Math.min(
      1,
      ((x - start.x) * deltaX + (y - start.y) * deltaY) / lengthSquared,
    ));
    return Math.hypot(
      x - (start.x + fraction * deltaX),
      y - (start.y + fraction * deltaY),
    );
  }

  function hitTest(x, y) {
    for (const region of hitRegions) {
      if (region.kind === "building" || region.kind === "aggregate") {
        if (x >= region.minX && x <= region.maxX && y >= region.minY && y <= region.maxY) return region;
      } else if (region.kind === "network") {
        if (x < region.minX || x > region.maxX || y < region.minY || y > region.maxY) continue;
        for (let index = 1; index < region.points.length; index += 1) {
          if (distanceToSegment(x, y, region.points[index - 1], region.points[index]) <= 8) return region;
        }
      } else if (pointInPolygon(x, y, region.points)) {
        return region;
      }
    }
    return null;
  }

  function renderLabels() {
    if (!projectionDirty) return;
    if (!labelLayer) return;
    const candidates = [];
    for (const district of scene.districts) {
      if (!renderedDistrictIds.has(district.id)) continue;
      if (!contextVisible(district.id)) continue;
      const territory = districtTerritory(district);
      const anchor = projected([
        territory.labelAnchor[0],
        0.35,
        territory.labelAnchor[1],
      ]);
      if (!anchor || anchor.depth < -1 || anchor.depth > 1) continue;
      const label = districtCanvasLabel(district);
      candidates.push({
        height: majorDistrictIds.has(district.id) ? 20 : 17,
        id: district.id,
        label,
        major: majorDistrictIds.has(district.id),
        priority: (majorDistrictIds.has(district.id) ? 10000 : 0)
          + (districtsWithBuildings.has(district.id) ? 1000 : 0)
          + (districtDepths.get(district.id) || 0),
        width: majorDistrictIds.has(district.id)
          ? Math.min(220, Math.max(54, label.length * 8 + 18))
          : Math.min(180, Math.max(24, label.length * 6 + 10)),
        x: anchor.x,
        y: anchor.y - 18,
      });
    }
    for (const aggregateId of renderedAggregateIds) {
      if (!selected("aggregate", aggregateId)) continue;
      const facility = aggregateFacilities.get(aggregateId);
      const anchor = projected([
        facility.labelX ?? facility.x + facility.width / 2,
        facility.height + 5,
        facility.labelZ ?? facility.z + facility.depth / 2,
      ]);
      if (!anchor || anchor.depth < -1 || anchor.depth > 1) continue;
      const label = `${districtCanvasLabel(districts.get(facility.districtId))} · ${facility.memberEntityIds.length} files`;
      candidates.push({
        aggregate: true,
        height: 20,
        id: facility.id,
        label,
        priority: 20000,
        width: Math.min(240, Math.max(90, label.length * 7 + 18)),
        x: anchor.x - Math.min(240, Math.max(90, label.length * 7 + 18)) / 2,
        y: anchor.y - 18,
      });
    }
    const visibleIds = new Set(
      filterEngine.selectNonOverlappingLabels(candidates, viewportWidth, viewportHeight),
    );
    labelLayer.replaceChildren(...candidates
      .filter((candidate) => visibleIds.has(candidate.id))
      .map((candidate) => {
        const node = document.createElement("span");
        node.className = candidate.aggregate
          ? "scene-label aggregate"
          : candidate.major
            ? "scene-label major"
            : "scene-label";
        node.style.left = `${candidate.x}px`;
        node.style.top = `${candidate.y}px`;
        node.style.maxWidth = `${candidate.width}px`;
        node.textContent = candidate.label;
        return node;
      }));
  }

  let lastProjectionKey = null;
  let projectionDirty = true;
  function render(timestamp = 0) {
    framePending = false;
    updateLodVisibility();
    viewProjection = cameraMatrix();
    const geometry = buildGeometry(timestamp);
    gl.viewport(0, 0, canvas.width, canvas.height);
    gl.clearColor(0.027, 0.043, 0.075, 1);
    gl.clear(gl.COLOR_BUFFER_BIT | gl.DEPTH_BUFFER_BIT);
    gl.enable(gl.DEPTH_TEST);
    gl.enable(gl.CULL_FACE);
    gl.cullFace(gl.BACK);
    gl.useProgram(program);
    gl.uniformMatrix4fv(matrixLocation, false, new Float32Array(viewProjection));
    bindAndDraw(triangleBuffer, geometry.triangles, gl.TRIANGLES);
    bindAndDraw(activityBuffer, buildActivityGeometry(timestamp), gl.TRIANGLES, gl.DYNAMIC_DRAW);
    gl.disable(gl.CULL_FACE);
    bindAndDraw(lineBuffer, geometry.lines, gl.LINES);
    // Selection-only x-ray trace: same ground path, visible behind tall buildings.
    gl.disable(gl.DEPTH_TEST);
    bindAndDraw(accessOverlayBuffer, geometry.accessOverlay, gl.LINES);
    const projectionKey = `${lodCacheKey}:${viewportWidth}:${viewportHeight}:${viewProjection.join(',')}`;
    projectionDirty = projectionKey !== lastProjectionKey;
    hitRegions = buildHitRegions();
    renderLabels();
    lastProjectionKey = projectionKey;
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
    if (!cameraFitted && viewportWidth > 10 && viewportHeight > 10) {
      state.distance = fitInitialDistance();
      initialCamera.distance = state.distance;
      cameraFitted = true;
    }
    scheduleRender();
  }

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
    const zoomRatio = initialCamera.distance / Math.max(0.01, state.distance);
    const nextDetailLevel = lodPolicy.levelForZoom(zoomRatio, filtered);
    const selectionKey = state.selected
      ? `${state.selected.kind}:${state.selected.id}:${state.selected.routeId || ""}`
      : "none";
    const nextCacheKey = `${nextDetailLevel}:${visibilityVersion}:${selectionKey}:${showAllNetworks}:${structureOverlay}:${[...expandedAggregateIds].sort().join('|')}`;
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

  function resetInspector(message = "Choose a building, visual block, district, or network to inspect the repository facts behind it.") {
    inspector.replaceChildren();
    inspector.append(element("p", "INSPECTOR", "eyebrow"));
    inspector.append(element("h2", "Select a city element"));
    inspector.append(element("p", message, "muted"));
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
    return state.selected.kind === "building"
      ? visibleBuildingIds.has(state.selected.id)
      : visibleNetworkIds.has(state.selected.id) || Boolean(accessPolicy?.segments.has(state.selected.id));
  }

  function applyFilters() {
    const visible = filterIndex.filter(state.filters);
    visibleBuildingIds = new Set(visible.buildingIds);
    visibleNetworkIds = new Set(visible.networkIds);
    visibilityVersion += 1;
    const activeCount = activeFilterCount();
    cityStats.replaceChildren();
    addStat(data.semanticZoning ? majorDistrictIds.size : scene.districts.length, "districts");
    if (data.semanticZoning) addStat(Object.keys(data.semanticZoning).length, "planning zones");
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
      if (!["http:", "https:"].includes(url.protocol)) return null;
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

  function focusButton(x, y, z, distance, label, beforeFocus = null) {
    const button = element("button", label, "focus-button");
    button.type = "button";
    button.addEventListener("click", () => {
      beforeFocus?.();
      hoverLabel.hidden = true;
      state.targetX = x;
      state.targetY = y;
      state.targetZ = z;
      state.distance = distance;
      scheduleRender();
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
      facility.height / 2,
      facility.z + facility.depth / 2,
      facility.role
        ? Math.max(48, Math.hypot(facility.width, facility.depth, facility.height) * 2.2)
        : Math.min(Math.max(26, Math.hypot(facility.width, facility.depth) * 1.1), initialCamera.distance / 2.6),
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
    const parcel=orientedBuildings[entityId];
    if(parcel) {
      detailRow(details,"Street-facing rotation",`${(parcel.angle*180/Math.PI).toFixed(1)}° · visual, not geographic north`);
      detailRow(details,"Local displacement",`${parcel.displacement.toFixed(2)} world units`);
      detailRow(details,"Frontage street",parcel.streetId);
    }
    detailRow(details, "District", districtLabel(districts.get(building.districtId)));
    inspector.append(details);
    if (data.semanticZoning?.[building.districtId]) {
      const button = element('button', 'Inspect planning neighborhood', 'focus-button'); button.type = 'button';
      button.addEventListener('click', () => showSelection({kind: 'district', id: building.districtId})); inspector.append(button);
      inspector.append(element('p', `Source directory: ${entities.get(parcel?.sourceDistrictId)?.path || parcel?.sourceDistrictId}`, 'muted'));
    }
    const facility = lodPolicy.facilityForEntity(entityId);
    if (facility) {
      inspector.append(element("p", `${facility.title}: selected constituent. Cyan outline marks its original footprint above the compound; it is not another building. Routes are aggregates containing this file's actual edges.`, "aggregate-disclosure"));
      facilityControls(inspector, facility);
    }
    factSection(inspector, "VERIFIED ROLES", (entity.roles || []).map(
      (claim) => `${claim.value} · ${claim.confidence}`,
    ));
    factSection(inspector, "TECHNOLOGIES", (entity.technologies || []).map(
      (claim) => `${claim.value} · ${claim.confidence}`,
    ));
    factSection(inspector, "CAPABILITIES", (entity.capabilities || []).map(
      (claim) => `${claim.value} · ${claim.confidence}`,
    ));
    const dependencies = filterEngine.declaredDependenciesForEntity(ucg, entityId);
    factSection(inspector, "DECLARED DEPENDENCIES (NOT USAGE)", dependencies.map(
      (item) => `${item.coordinate} · ${item.ecosystem} · DECLARED`,
    ));
    const evidenceIds = new Set([
      ...(building.evidenceIds || []),
      ...(entity.roles || []).flatMap((claim) => claim.evidenceIds),
      ...(entity.technologies || []).flatMap((claim) => claim.evidenceIds),
      ...(entity.capabilities || []).flatMap((claim) => claim.evidenceIds),
      ...dependencies.flatMap((item) => item.evidenceIds),
    ]);
    factSection(inspector, "EVIDENCE", [...evidenceIds].map(evidenceLabel));
    const link = sourceLink(entity);
    if (link) inspector.append(link);
    inspector.append(focusButton(
      building.x + building.width / 2,
      building.height / 2,
      building.z + building.depth / 2,
      Math.max(22, building.height * 2.4),
      "Focus building",
    ));
  }

  function showDistrict(districtId, offset = 0) {
    const district = districts.get(districtId);
    const districtBuildings = filterEngine.districtBuildings(scene, districtId);
    const visibleCount = districtBuildings.filter((item) => visibleBuildingIds.has(item.entityId)).length;
    inspector.replaceChildren();
    inspector.append(element("p", "DISTRICT", "eyebrow"));
    inspector.append(element("h2", districtLabel(district)));
    const details = element("dl", undefined, "detail-list");
    detailRow(details, "Files (including subdistricts)", `${visibleCount}/${districtBuildings.length} match filters`);
    detailRow(details, "Parent", district.parentId
      ? districtLabel(districts.get(district.parentId))
      : "City root");
    detailRow(details, "Size", `${district.width} × ${district.depth}`);
    inspector.append(details);
    showZoningDetails(districtId, offset);
    inspector.append(focusButton(
      district.x + district.width / 2,
      tallestBuilding * 0.12,
      district.z + district.depth / 2,
      Math.max(32, Math.hypot(district.width, district.depth) * 1.15),
      "Focus district",
    ));
  }

  function showZoningDetails(districtId, offset) {
    const zone = data.semanticZoning?.[districtId];
    if (!zone) {
      for (const child of Object.values(data.semanticZoning || {}).filter(z => z.parentId === districtId)) {
        const button = element('button', `${child.label} · ${child.memberEntityIds.length} files`, 'focus-button');
        button.type = 'button'; button.addEventListener('click', () => showSelection({kind: 'district', id: child.id}));
        inspector.append(button);
      }
      return;
    }
    inspector.append(element('p', 'Derived planning neighborhood, not a source module or runtime service. Unknown members remain unclassified.', 'muted'));
    factSection(inspector, 'ZONING BASIS', [zone.classification.status, `${zone.planningProfile} · ${zone.allocation.algorithm}`, ...zone.classification.ruleIds]);
    factSection(inspector, 'GROUPING EVIDENCE', zone.classification.evidenceIds.map(evidenceLabel));
    inspector.append(element('h3', `MEMBER FILES · ${offset + 1}–${Math.min(offset + 25, zone.memberEntityIds.length)} / ${zone.memberEntityIds.length}`, 'section-title'));
    for (const id of zone.memberEntityIds.slice(offset, offset + 25)) {
      const button = element('button', entities.get(id)?.path || id, 'focus-button zoning-member');
      button.type = 'button'; button.dataset.entityId = id;
      button.addEventListener('click', () => showSelection({kind: 'building', id})); inspector.append(button);
    }
    for (const [label, next] of [['Previous members', offset - 25], ['Next members', offset + 25]]) {
      if (next < 0 || next >= zone.memberEntityIds.length) continue;
      const button = element('button', label, 'focus-button'); button.type = 'button';
      button.addEventListener('click', () => showDistrict(districtId, next)); inspector.append(button);
    }
  }

  function showStreetDiagnostics(offset=0, reason='') {
    if (!data.routing?.streetGrid) return;
    const page=accessPolicy.failurePage(visibleBuildingIds,visibleNetworkIds,offset,reason);
    inspector.replaceChildren();
    inspector.append(element('p','STREET ASSIGNMENT','eyebrow'));
    inspector.append(element('h2','Original paths retained'));
    inspector.append(element('p','These relationships are not lost. Select a path to inspect its original source, destination and evidence. Counts respect the current filters.','muted'));
    for (const item of [{reason:'',label:'All fallback reasons',count:null},...page.counts]) {
      const button=element('button',item.label+(item.count===null?'':` · ${item.count}`),'focus-button');
      button.type='button';
      button.addEventListener('click',()=>showStreetDiagnostics(0,item.reason));
      inspector.append(button);
    }
    inspector.append(element('p',page.total?`${page.offset+1}–${page.offset+page.rows.length} of ${page.total} paths`:'No fallback paths match these filters.','section-title'));
    for (const route of page.rows) {
      const button=element('button',`${entities.get(route.source)?.path || route.source} → ${entities.get(route.target)?.path || route.target}`,'focus-button fallback-route');
      button.type='button';
      button.dataset.routeId=route.id;
      button.addEventListener('click',()=>showSelection({kind:'network',
        id:route.networkIds.find(id=>visibleNetworkIds.has(id)),routeId:route.id}));
      inspector.append(button,element('p',accessPolicy.assignmentReason(route.id).label,'muted'));
    }
    for (const [label,next] of [['Previous',page.offset-25],['Next',page.offset+25]]) {
      if (next<0 || next>=page.total) continue;
      const button=element('button',label,'focus-button');
      button.type='button';button.addEventListener('click',()=>showStreetDiagnostics(next,reason));
      inspector.append(button);
    }
  }
  document.getElementById('street-diagnostics')?.addEventListener('click',()=>showStreetDiagnostics());

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
    if (chosen && data.routing?.streetGrid) {
      const diagnostic=accessPolicy.assignmentReason(chosen.id);
      detailRow(details,'Street assignment',diagnostic.label);
      if (diagnostic.latticeStepLimit !== undefined) detailRow(details,'Street-grid distance limit (steps)',diagnostic.latticeStepLimit);
      if (diagnostic.shortestLatticeSteps !== undefined) detailRow(details,'Shortest street-grid distance (steps)',diagnostic.shortestLatticeSteps);
    }
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
      const pavementWidth=accessPolicy?.network(networkId)?.pavementWidth;
      detailRow(details, pavementWidth ? "Demand cap / target width" : "Rendered / target width", `${demand.width} / ${demand.targetWidth}${demand.clearanceLimited ? ' · clearance limited' : ''}`);
      if (pavementWidth) detailRow(details,data.streetCurves ? "Approach width range" : "Physical width range",`${pavementWidth.min.toFixed(2)} – ${pavementWidth.max.toFixed(2)} · shared street envelope`);
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
    factSection(inspector, "UNDERLYING EDGES", network.edgeIds.map((id) => {
      const edge = edges.get(id);
      return edge ? `${id} · ${edge.type}: ${edge.from} → ${edge.to} (${edge.confidence})` : id;
    }));
    factSection(inspector, "EVIDENCE", network.edgeIds.flatMap((id) => {
      const edge = edges.get(id);
      return (edge?.evidenceIds || []).map(evidenceLabel);
    }));
    const middle = network.path[Math.floor(network.path.length / 2)];
    const networkWidth = Math.max(...network.path.map((point) => point[0]))
      - Math.min(...network.path.map((point) => point[0]));
    const networkDepth = Math.max(...network.path.map((point) => point[1]))
      - Math.min(...network.path.map((point) => point[1]));
    inspector.append(focusButton(
      middle[0],
      1,
      middle[1],
      Math.max(28, Math.hypot(networkWidth, networkDepth) * 1.25),
      "Focus network",
    ));
  }

  function showSelection(selection) {
    if (!selection) return;
    hoverLabel.hidden = true;
    state.selected = { id: selection.id, kind: selection.kind, routeId: selection.routeId || "" };
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

  function runAction(action) {
    if (action === "toggle-structure" && urbanContext) {
      structureOverlay = !structureOverlay;
      document.querySelector('[data-action="toggle-structure"]').setAttribute('aria-pressed',String(structureOverlay));
      projectionDirty = true;
    }
    if (action === "toggle-pan") {
      state.moveMode = !state.moveMode;
      document.querySelector('[data-action="toggle-pan"]').setAttribute("aria-pressed", String(state.moveMode));
      canvas.classList.toggle("move-mode", state.moveMode);
    }
    const step = Math.min(viewportWidth, viewportHeight) * 0.12;
    const delta = {"pan-left":[step,0], "pan-right":[-step,0], "pan-up":[0,step], "pan-down":[0,-step]}[action];
    if (delta) panGround(...delta);
    if (action === "toggle-routes") {
      showAllNetworks = !showAllNetworks;
      document.querySelector('[data-action="toggle-routes"]').setAttribute("aria-pressed", String(showAllNetworks));
    }
    if (action === "rotate-left") state.yaw -= Math.PI / 8;
    if (action === "rotate-right") state.yaw += Math.PI / 8;
    if (action === "zoom-in") state.distance = Math.max(8, state.distance / 1.2);
    if (action === "zoom-out") state.distance = Math.min(worldSpan * 8, state.distance * 1.2);
    if (action === "reset") Object.assign(state, initialCamera);
    scheduleRender();
  }

  function panGround(dx, dy) {
    const delta = filterEngine.groundPan(state, dx, dy, viewportHeight, cameraPolicy.fieldOfView);
    state.targetX += delta.x;
    state.targetZ += delta.z;
    hoverLabel.hidden = true;
  }

  canvas.addEventListener("pointerdown", (event) => {
    if (![0, 1, 2].includes(event.button)) return;
    event.preventDefault();
    canvas.focus({preventScroll: true});
    canvas.setPointerCapture(event.pointerId);
    state.dragging = true;
    state.dragMode = state.moveMode || event.altKey || event.shiftKey || event.button !== 0 ? "pan" : "orbit";
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
      if (state.dragMode === "orbit") {
        state.yaw -= deltaX * 0.008;
        state.pitch = Math.max(0.16, Math.min(1.42, state.pitch + deltaY * 0.006));
      } else {
        panGround(deltaX, deltaY);
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
  canvas.addEventListener("wheel", (event) => {
    event.preventDefault();
    state.distance = Math.max(8, Math.min(
      worldSpan * 8,
      state.distance * Math.exp(event.deltaY * 0.001),
    ));
    scheduleRender();
  }, { passive: false });

  document.querySelectorAll("[data-action]").forEach((button) => {
    button.addEventListener("click", () => runAction(button.dataset.action));
  });
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
    state.targetX = district.x + district.width / 2;
    state.targetZ = district.z + district.depth / 2;
    state.targetY = tallestBuilding * 0.12;
    state.distance = Math.max(32, Math.hypot(district.width, district.depth) * 1.15);
    hoverLabel.hidden = true;
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
        ? "Synthetic illustration unavailable · this city has no networks"
        : "Illustration only · not measured runtime traffic";
    scheduleRender();
  }

  activityToggle.addEventListener("change", () => {
    state.syntheticActivity = activityToggle.checked;
    state.activityEpoch = globalThis.performance.now();
    activityNote.textContent = state.syntheticActivity
      ? "Synthetic illustration active · not measured runtime traffic"
      : "Illustration only · not measured runtime traffic";
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

  repositoryName.textContent = ucg.repository.id;
  document.title = `${ucg.repository.id} · MetropoGits`;
  if (toolbarHelp) {
    toolbarHelp.textContent = "Move mode / Shift / right drag: move · WASD / arrows: move · Q/E: orbit · Wheel: zoom · R: reset";
  }
  populateFilter("role", filterIndex.options.roles);
  populateFilter("language", filterIndex.options.languages);
  populateFilter("technology", filterIndex.options.technologies);
  populateFilter("confidence", filterIndex.options.confidences);
  new ResizeObserver(resize).observe(canvas);
  updateActivityAvailability();
  applyFilters();
  resize();
})();
