(() => {
  "use strict";

  const confidenceOrder = ["UNKNOWN", "DECLARED", "HEURISTIC", "DIRECT", "RESOLVED"];

  function sorted(values, preferredOrder = []) {
    const order = new Map(preferredOrder.map((value, index) => [value, index]));
    return [...values].sort((left, right) => {
      const leftOrder = order.get(left) ?? Number.MAX_SAFE_INTEGER;
      const rightOrder = order.get(right) ?? Number.MAX_SAFE_INTEGER;
      return leftOrder - rightOrder || left.localeCompare(right);
    });
  }

  function claims(entity) {
    return [...(entity?.roles || []), ...(entity?.technologies || [])];
  }

  function selectNonOverlappingLabels(candidates, viewportWidth, viewportHeight) {
    const accepted = [];
    const ordered = [...candidates].sort(
      (left, right) =>
        (right.priority || 0) - (left.priority || 0)
        || String(left.id).localeCompare(String(right.id)),
    );
    for (const candidate of ordered) {
      if (
        !Number.isFinite(candidate.x)
        || !Number.isFinite(candidate.y)
        || !Number.isFinite(candidate.width)
        || !Number.isFinite(candidate.height)
        || candidate.width <= 0
        || candidate.height <= 0
        || candidate.x < 0
        || candidate.y < 0
        || candidate.x + candidate.width > viewportWidth
        || candidate.y + candidate.height > viewportHeight
      ) {
        continue;
      }
      const overlaps = accepted.some(
        (item) =>
          candidate.x < item.x + item.width + 4
          && item.x < candidate.x + candidate.width + 4
          && candidate.y < item.y + item.height + 4
          && item.y < candidate.y + candidate.height + 4,
      );
      if (!overlaps) accepted.push(candidate);
    }
    return accepted.map((candidate) => candidate.id);
  }

  function majorDistrictIds(scene) {
    const districts = new Map(scene.districts.map((district) => [district.id, district]));
    const children = new Map(scene.districts.map((district) => [district.id, []]));
    const directBuildings = new Map();
    for (const district of scene.districts) {
      if (district.parentId !== null && children.has(district.parentId)) {
        children.get(district.parentId).push(district.id);
      }
    }
    for (const childIds of children.values()) childIds.sort();
    for (const building of scene.buildings) {
      directBuildings.set(
        building.districtId,
        (directBuildings.get(building.districtId) || 0) + 1,
      );
    }

    const subtreeBuildings = new Map();
    function count(districtId) {
      if (subtreeBuildings.has(districtId)) return subtreeBuildings.get(districtId);
      const total = (directBuildings.get(districtId) || 0)
        + (children.get(districtId) || []).reduce(
          (sum, childId) => sum + count(childId),
          0,
        );
      subtreeBuildings.set(districtId, total);
      return total;
    }
    const roots = scene.districts
      .filter((district) => district.parentId === null)
      .map((district) => district.id)
      .sort();
    for (const rootId of roots) count(rootId);

    const minimum = scene.buildings.length >= 256
      ? Math.max(20, Math.ceil(scene.buildings.length * 0.02))
      : Math.max(1, Math.ceil(scene.buildings.length * 0.1));
    const selected = new Set();
    for (const rootId of roots) {
      const rootChildren = (children.get(rootId) || [])
        .filter((districtId) => count(districtId) >= minimum);
      for (const branchId of rootChildren) {
        const significantChildren = (children.get(branchId) || [])
          .filter((districtId) => count(districtId) >= minimum);
        if (
          significantChildren.length === 1
          && (directBuildings.get(branchId) || 0) < minimum
        ) {
          selected.add(significantChildren[0]);
        } else if (significantChildren.length >= 2) {
          for (const districtId of significantChildren) selected.add(districtId);
        } else {
          selected.add(branchId);
        }
      }
    }
    if (!selected.size) {
      for (const rootId of roots) {
        for (const districtId of children.get(rootId) || []) selected.add(districtId);
      }
    }
    return [...selected].filter((districtId) => districts.has(districtId)).sort();
  }

  function stableBucket(value, bucketCount) {
    let hash = 0x811c9dc5;
    for (const character of String(value)) {
      hash ^= character.codePointAt(0);
      hash = Math.imul(hash, 0x01000193);
    }
    return (hash >>> 0) % bucketCount;
  }

  function aggregateFacilities(scene, majorIds, districts) {
    const groups = new Map();

    function aggregateDistrictId(districtId) {
      const ancestry = [];
      let current = districts.get(districtId);
      while (current) {
        ancestry.push(current.id);
        if (majorIds.has(current.id)) return current.id;
        current = current.parentId === null ? null : districts.get(current.parentId);
      }
      return ancestry.length > 1 ? ancestry.at(-2) : ancestry.at(-1);
    }

    for (const building of scene.buildings) {
      const districtId = aggregateDistrictId(building.districtId);
      if (!districtId) continue;
      const members = groups.get(districtId) || [];
      members.push(building);
      groups.set(districtId, members);
    }

    return [...groups.entries()].map(([districtId, members]) => {
      members.sort((left, right) => left.entityId.localeCompare(right.entityId));
      const district = districts.get(districtId);
      const centerX = members.reduce(
        (sum, building) => sum + building.x + building.width / 2,
        0,
      ) / members.length;
      const centerZ = members.reduce(
        (sum, building) => sum + building.z + building.depth / 2,
        0,
      ) / members.length;
      const margin = Math.min(2, district.width * 0.05, district.depth * 0.05);
      const maxWidth = Math.max(2, district.width - margin * 2);
      const maxDepth = Math.max(2, district.depth - margin * 2);
      const footprint = Math.max(
        8,
        Math.sqrt(members.length) * 2.8,
        Math.min(district.width, district.depth) * 0.28,
      );
      const width = Math.min(maxWidth, footprint);
      const depth = Math.min(maxDepth, footprint * 0.78);
      const x = Math.max(
        district.x + margin,
        Math.min(centerX - width / 2, district.x + district.width - margin - width),
      );
      const z = Math.max(
        district.z + margin,
        Math.min(centerZ - depth / 2, district.z + district.depth - margin - depth),
      );
      const archetypeCounts = new Map();
      for (const building of members) {
        archetypeCounts.set(
          building.archetype,
          (archetypeCounts.get(building.archetype) || 0) + 1,
        );
      }
      return {
        archetypeCounts: [...archetypeCounts]
          .map(([archetype, count]) => ({ archetype, count }))
          .sort(
            (left, right) =>
              right.count - left.count
              || left.archetype.localeCompare(right.archetype),
          ),
        depth,
        districtId,
        height: Math.min(
          120,
          Math.max(
            18 + Math.log2(members.length + 1) * 4,
            footprint * 0.38,
          ),
        ),
        id: `visual:aggregate:${districtId}`,
        memberEntityIds: members.map((building) => building.entityId),
        width,
        x,
        z,
      };
    }).sort((left, right) => left.id.localeCompare(right.id));
  }

  function createLodPolicy(scene) {
    const buildings = new Map(
      scene.buildings.map((building) => [building.entityId, building]),
    );
    const networks = new Map(scene.networks.map((network) => [network.id, network]));
    const districts = new Map(scene.districts.map((district) => [district.id, district]));
    const majorIds = new Set(majorDistrictIds(scene));
    const aggregates = aggregateFacilities(scene, majorIds, districts);
    const aggregateIds = new Set(aggregates.map((aggregate) => aggregate.id));
    const districtDepths = new Map();

    function districtDepth(districtId) {
      if (districtDepths.has(districtId)) return districtDepths.get(districtId);
      const district = districts.get(districtId);
      const depth = !district || district.parentId === null
        ? 0
        : districtDepth(district.parentId) + 1;
      districtDepths.set(districtId, depth);
      return depth;
    }
    for (const district of scene.districts) districtDepth(district.id);

    function levelForZoom(zoomRatio, forceDetail = false) {
      if (forceDetail || scene.buildings.length < 256) return "detail";
      if (zoomRatio >= 2.4) return "detail";
      if (zoomRatio >= 1.35) return "district";
      return "overview";
    }

    function districtVisible(districtId, level) {
      if (level === "detail") return true;
      if (majorIds.has(districtId)) return true;
      const district = districts.get(districtId);
      if (!district) return false;
      if (level === "overview") return district.parentId === null;
      return districtDepths.get(districtId) <= 2;
    }

    function visibility(level, candidateBuildingIds, candidateNetworkIds, selected = null) {
      const candidateBuildings = new Set(candidateBuildingIds);
      const candidateNetworks = new Set(candidateNetworkIds);
      const buildingIds = [...candidateBuildings]
        .filter((id) => {
          const building = buildings.get(id);
          if (!building) return false;
          if (selected?.kind === "building" && selected.id === id) return true;
          if (level === "overview") return false;
          if (level === "detail" || building.archetype !== "GENERIC_BUILDING") return true;
          return stableBucket(id, 3) === 0;
        })
        .sort();

      const visibleAggregateIds = level === "overview"
        ? [...aggregateIds]
        : [];
      if (
        selected?.kind === "aggregate"
        && aggregateIds.has(selected.id)
        && !visibleAggregateIds.includes(selected.id)
      ) {
        visibleAggregateIds.push(selected.id);
      }
      visibleAggregateIds.sort();

      const networkLimit = level === "overview" ? 24 : level === "district" ? 64 : Infinity;
      const rankedNetworks = [...candidateNetworks]
        .map((id) => networks.get(id))
        .filter(Boolean)
        .sort(
          (left, right) =>
            (right.edgeIds?.length || 0) - (left.edgeIds?.length || 0)
            || left.id.localeCompare(right.id),
        );
      const networkIds = rankedNetworks.slice(0, networkLimit).map((network) => network.id);
      if (
        selected?.kind === "network"
        && candidateNetworks.has(selected.id)
        && !networkIds.includes(selected.id)
      ) {
        networkIds.push(selected.id);
        networkIds.sort();
      }

      return { aggregateIds: visibleAggregateIds, buildingIds, networkIds };
    }

    return Object.freeze({
      aggregates,
      districtVisible,
      levelForZoom,
      visibility,
    });
  }

  function entityMatches(entity, filters, relatedConfidences = []) {
    if (!entity) return false;
    if (filters.language && entity.language !== filters.language) return false;
    if (
      filters.role &&
      !(entity.roles || []).some((claim) => claim.value === filters.role)
    ) {
      return false;
    }
    if (
      filters.technology &&
      !(entity.technologies || []).some((claim) => claim.value === filters.technology)
    ) {
      return false;
    }
    if (
      filters.confidence &&
      !claims(entity).some((claim) => claim.confidence === filters.confidence) &&
      !relatedConfidences.includes(filters.confidence)
    ) {
      return false;
    }
    return true;
  }

  function createIndex(scene, ucg) {
    const entities = new Map(ucg.entities.map((entity) => [entity.id, entity]));
    const fileEntitiesByPath = new Map(
      ucg.entities
        .filter((entity) => entity.kind === "FILE" && entity.path)
        .map((entity) => [entity.path, entity]),
    );
    const edges = new Map(ucg.edges.map((edge) => [edge.id, edge]));
    const networkEdgeIds = new Set(scene.networks.flatMap((network) => network.edgeIds));
    function fileEntity(entityId) {
      const entity = entities.get(entityId);
      if (entity?.kind === "FILE") return entity;
      return entity?.path ? fileEntitiesByPath.get(entity.path) || entity : entity;
    }

    const relatedConfidences = new Map();
    for (const edge of ucg.edges.filter((item) => networkEdgeIds.has(item.id))) {
      for (const endpoint of [fileEntity(edge.from), fileEntity(edge.to)]) {
        if (!endpoint) continue;
        if (!relatedConfidences.has(endpoint.id)) relatedConfidences.set(endpoint.id, []);
        relatedConfidences.get(endpoint.id).push(edge.confidence);
      }
    }
    const buildingRecords = scene.buildings.map((building) => ({
      confidences: relatedConfidences.get(building.entityId) || [],
      entity: entities.get(building.entityId),
      id: building.entityId,
    }));

    const networkRecords = scene.networks.map((network) => ({
      edges: network.edgeIds.map((edgeId) => edges.get(edgeId)).filter(Boolean),
      id: network.id,
    }));
    const roles = new Set();
    const languages = new Set();
    const technologies = new Set();
    const confidences = new Set();

    for (const record of buildingRecords) {
      if (record.entity?.language) languages.add(record.entity.language);
      for (const claim of record.entity?.roles || []) {
        roles.add(claim.value);
        confidences.add(claim.confidence);
      }
      for (const claim of record.entity?.technologies || []) {
        technologies.add(claim.value);
        confidences.add(claim.confidence);
      }
    }
    for (const edge of ucg.edges) {
      if (networkEdgeIds.has(edge.id)) confidences.add(edge.confidence);
    }

    function edgeMatches(edge, filters) {
      if (filters.confidence && edge.confidence !== filters.confidence) return false;
      if (!filters.role && !filters.language && !filters.technology) return true;
      return [fileEntity(edge.from), fileEntity(edge.to)].some((entity) =>
        entityMatches(entity, { ...filters, confidence: "" }),
      );
    }

    return Object.freeze({
      options: Object.freeze({
        confidences: sorted(confidences, confidenceOrder),
        languages: sorted(languages),
        roles: sorted(roles),
        technologies: sorted(technologies),
      }),
      filter(filters) {
        return {
          buildingIds: buildingRecords
            .filter((record) =>
              entityMatches(record.entity, filters, record.confidences),
            )
            .map((record) => record.id),
          networkIds: networkRecords
            .filter((record) => record.edges.some((edge) => edgeMatches(edge, filters)))
            .map((record) => record.id),
        };
      },
    });
  }

  function declaredDependenciesForEntity(ucg, entityId) {
    const entities = new Map(ucg.entities.map((entity) => [entity.id, entity]));
    const entity = entities.get(entityId);
    if (entity?.kind !== "FILE" || !entity.path) return [];

    const candidates = ucg.entities
      .filter((item) => item.kind === "MODULE" && item.path)
      .map((module) => {
        const separator = module.path.lastIndexOf("/");
        const directory = separator < 0 ? "" : module.path.slice(0, separator);
        return {
          contains: !directory || entity.path.startsWith(`${directory}/`),
          depth: directory ? directory.split("/").length : 0,
          id: module.id,
        };
      })
      .filter((item) => item.contains);
    if (!candidates.length) return [];

    const closestDepth = Math.max(...candidates.map((item) => item.depth));
    const moduleIds = new Set(
      candidates.filter((item) => item.depth === closestDepth).map((item) => item.id),
    );
    const dependencies = new Map();
    for (const edge of ucg.edges) {
      if (edge.type !== "DEPENDS_ON" || !moduleIds.has(edge.from)) continue;
      const target = entities.get(edge.to);
      if (target?.kind !== "EXTERNAL_PACKAGE" || !target.path) continue;
      let ecosystem = "PACKAGE";
      let coordinate = target.path;
      if (target.path.startsWith("npm/")) {
        ecosystem = "NPM";
        coordinate = target.path.slice(4);
      } else if (target.path.startsWith("maven/")) {
        ecosystem = "MAVEN";
        const parts = target.path.slice(6).split("/");
        coordinate = parts.length > 1
          ? `${parts.slice(0, -1).join(".")}:${parts.at(-1)}`
          : target.path.slice(6);
      }
      const key = `${ecosystem}\u0000${coordinate}`;
      const record = dependencies.get(key) || {
        coordinate,
        ecosystem,
        evidenceIds: [],
      };
      record.evidenceIds = [...new Set([...record.evidenceIds, ...edge.evidenceIds])].sort();
      dependencies.set(key, record);
    }
    return [...dependencies.values()].sort(
      (left, right) =>
        left.ecosystem.localeCompare(right.ecosystem)
        || left.coordinate.localeCompare(right.coordinate),
    );
  }

  globalThis.METROPOGITS_FILTERS = Object.freeze({
    createLodPolicy,
    createIndex,
    declaredDependenciesForEntity,
    majorDistrictIds,
    selectNonOverlappingLabels,
  });
})();
