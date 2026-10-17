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

  function aggregateFacilities(scene, majorIds, districts, territories) {
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

    function center(building, axis) {
      const origin = Number(building[axis]);
      const size = Number(building[axis === "x" ? "width" : "depth"]);
      return Number.isFinite(origin) && Number.isFinite(size)
        ? origin + size / 2
        : 0;
    }

    function spatialPartitions(members, count) {
      if (count <= 1 || members.length <= 1) return [[...members]];
      const spreads = ["x", "z"].map((axis) => {
        const values = members.map((building) => center(building, axis));
        return { axis, spread: Math.max(...values) - Math.min(...values) };
      });
      spreads.sort(
        (left, right) => right.spread - left.spread || left.axis.localeCompare(right.axis),
      );
      const leftGroups = Math.floor(count / 2);
      const rightGroups = count - leftGroups;
      const ideal = Math.round(members.length * leftGroups / count);
      let selected = null;
      for (const { axis } of spreads) {
        const otherAxis = axis === "x" ? "z" : "x";
        const sizeKey = axis === "x" ? "width" : "depth";
        const ordered = [...members].sort(
          (left, right) =>
            center(left, axis) - center(right, axis)
            || center(left, otherAxis) - center(right, otherAxis)
            || left.entityId.localeCompare(right.entityId),
        );
        const leftEnds = [];
        let leftEnd = Number.NEGATIVE_INFINITY;
        for (const building of ordered) {
          leftEnd = Math.max(leftEnd, Number(building[axis]) + Number(building[sizeKey]));
          leftEnds.push(leftEnd);
        }
        const rightStarts = Array(ordered.length);
        let rightStart = Number.POSITIVE_INFINITY;
        for (let index = ordered.length - 1; index >= 0; index -= 1) {
          rightStart = Math.min(rightStart, Number(ordered[index][axis]));
          rightStarts[index] = rightStart;
        }
        const candidates = [];
        for (let split = leftGroups; split <= ordered.length - rightGroups; split += 1) {
          if (leftEnds[split - 1] <= rightStarts[split]) candidates.push(split);
        }
        if (candidates.length) {
          candidates.sort((left, right) => Math.abs(left - ideal) - Math.abs(right - ideal) || left - right);
          selected = { ordered, split: candidates[0] };
          break;
        }
      }
      const ordered = selected?.ordered || [...members].sort(
        (left, right) => left.entityId.localeCompare(right.entityId),
      );
      const split = selected?.split
        || Math.max(leftGroups, Math.min(ordered.length - rightGroups, ideal));
      return [
        ...spatialPartitions(ordered.slice(0, split), leftGroups),
        ...spatialPartitions(ordered.slice(split), rightGroups),
      ];
    }

    function commonDistrictId(members, fallbackId) {
      const ancestry = (districtId) => {
        const result = [];
        let current = districts.get(districtId);
        while (current) {
          result.unshift(current.id);
          current = current.parentId === null ? null : districts.get(current.parentId);
        }
        return result;
      };
      const paths = members.map((building) => ancestry(building.districtId));
      if (!paths.length || paths.some((path) => !path.length)) return fallbackId;
      let common = paths[0][0];
      for (let index = 0; index < Math.min(...paths.map((path) => path.length)); index += 1) {
        if (paths.every((path) => path[index] === paths[0][index])) common = paths[0][index];
        else break;
      }
      return common || fallbackId;
    }

    function occupiedBounds(members, districtId) {
      const positioned = members.filter((building) =>
        [building.x, building.z, building.width, building.depth].every(Number.isFinite),
      );
      if (positioned.length) {
        const x = Math.min(...positioned.map((building) => building.x));
        const z = Math.min(...positioned.map((building) => building.z));
        return {
          depth: Math.max(...positioned.map((building) => building.z + building.depth)) - z,
          width: Math.max(...positioned.map((building) => building.x + building.width)) - x,
          x,
          z,
        };
      }
      const district = districts.get(districtId);
      const territory = territories.get(districtId);
      return territory?.landmarkPlot || territory?.rectangles?.[0] || district;
    }

    function clippedPlots(placement, majorDistrictId) {
      const rectangles = territories.get(majorDistrictId)?.rectangles || [];
      const maxX = placement.x + placement.width;
      const maxZ = placement.z + placement.depth;
      const plots = rectangles.map((rectangle) => {
        const x = Math.max(placement.x, rectangle.x);
        const z = Math.max(placement.z, rectangle.z);
        return {
          depth: Math.min(maxZ, rectangle.z + rectangle.depth) - z,
          width: Math.min(maxX, rectangle.x + rectangle.width) - x,
          x,
          z,
        };
      }).filter((plot) => plot.width > 0 && plot.depth > 0);
      return (plots.length ? plots : [placement]).sort(
        (left, right) => left.z - right.z || left.x - right.x
          || left.depth - right.depth || left.width - right.width,
      );
    }

    const targetBlockCount = Math.min(
      48,
      Math.max(12, Math.round(Math.sqrt(scene.buildings.length))),
    );
    const targetPopulation = Math.max(1, scene.buildings.length / targetBlockCount);
    const facilities = [];
    for (const [majorDistrictId, majorMembers] of [...groups.entries()].sort()) {
      majorMembers.sort((left, right) => left.entityId.localeCompare(right.entityId));
      const partitionCount = Math.min(
        majorMembers.length,
        Math.max(1, Math.round(majorMembers.length / targetPopulation)),
      );
      const partitions = spatialPartitions(majorMembers, partitionCount)
        .sort((left, right) => {
          const leftZ = Math.min(...left.map((building) => center(building, "z")));
          const rightZ = Math.min(...right.map((building) => center(building, "z")));
          const leftX = Math.min(...left.map((building) => center(building, "x")));
          const rightX = Math.min(...right.map((building) => center(building, "x")));
          return leftZ - rightZ || leftX - rightX
            || left[0].entityId.localeCompare(right[0].entityId);
        });
      partitions.forEach((members, index) => {
        members.sort((left, right) => left.entityId.localeCompare(right.entityId));
        const districtId = commonDistrictId(members, majorDistrictId);
        const placement = occupiedBounds(members, districtId);
        const plots = clippedPlots(placement, majorDistrictId);
        const x = Math.min(...plots.map((plot) => plot.x));
        const z = Math.min(...plots.map((plot) => plot.z));
        const maxX = Math.max(...plots.map((plot) => plot.x + plot.width));
        const maxZ = Math.max(...plots.map((plot) => plot.z + plot.depth));
        const labelPlot = [...plots].sort(
          (left, right) => right.width * right.depth - left.width * left.depth
            || left.z - right.z || left.x - right.x,
        )[0];
        const archetypeCounts = new Map();
        for (const building of members) {
          const archetype = building.archetype || "GENERIC_BUILDING";
          archetypeCounts.set(archetype, (archetypeCounts.get(archetype) || 0) + 1);
        }
        facilities.push({
          archetypeCounts: [...archetypeCounts]
            .map(([archetype, count]) => ({ archetype, count }))
            .sort(
              (left, right) =>
                right.count - left.count
                || left.archetype.localeCompare(right.archetype),
            ),
          depth: Math.max(2, maxZ - z),
          districtId,
          height: Math.min(64, 14 + Math.log2(members.length + 1) * 4.5),
          id: `visual:block:${majorDistrictId}:${String(index).padStart(3, "0")}`,
          labelX: labelPlot.x + labelPlot.width / 2,
          labelZ: labelPlot.z + labelPlot.depth / 2,
          majorDistrictId,
          memberDistrictIds: [...new Set(members.map((building) => building.districtId))].sort(),
          memberEntityIds: members.map((building) => building.entityId),
          plots,
          width: Math.max(2, maxX - x),
          x,
          z,
        });
      });
    }
    return facilities.sort((left, right) => left.id.localeCompare(right.id));
  }

  function aggregateParts(facility) {
    const targetCount = Math.min(
      12,
      Math.max(
        facility.archetypeCounts.length,
        Math.ceil(Math.sqrt(facility.memberEntityIds.length) / 2),
      ),
    );
    const allocations = new Map(
      facility.archetypeCounts
        .slice(0, targetCount)
        .map((item) => [item.archetype, 1]),
    );
    while ([...allocations.values()].reduce((sum, count) => sum + count, 0) < targetCount) {
      const selected = facility.archetypeCounts
        .filter((item) => allocations.has(item.archetype))
        .sort((left, right) => {
          const leftScore = left.count / (allocations.get(left.archetype) + 1);
          const rightScore = right.count / (allocations.get(right.archetype) + 1);
          return rightScore - leftScore || left.archetype.localeCompare(right.archetype);
        })[0];
      allocations.set(selected.archetype, allocations.get(selected.archetype) + 1);
    }

    const parts = [];
    for (const item of facility.archetypeCounts) {
      const count = allocations.get(item.archetype) || 0;
      for (let index = 0; index < count; index += 1) {
        parts.push({
          archetype: item.archetype,
          entityId: `${facility.id}:${item.archetype}:${index}`,
          representedCount: Math.floor(item.count / count)
            + (index < item.count % count ? 1 : 0),
        });
      }
    }
    parts.sort(
      (left, right) =>
        stableBucket(left.entityId, 2_147_483_647)
        - stableBucket(right.entityId, 2_147_483_647)
        || left.entityId.localeCompare(right.entityId),
    );

    const plots = [...(facility.plots || [facility])]
      .sort(
        (left, right) => right.width * right.depth - left.width * left.depth
          || left.z - right.z || left.x - right.x,
      )
      .slice(0, parts.length);
    const plotCounts = plots.map((plot) => ({ count: 1, plot }));
    while (plotCounts.reduce((sum, item) => sum + item.count, 0) < parts.length) {
      plotCounts.sort(
        (left, right) =>
          right.plot.width * right.plot.depth / (right.count + 1)
          - left.plot.width * left.plot.depth / (left.count + 1)
          || left.plot.z - right.plot.z || left.plot.x - right.plot.x,
      );
      plotCounts[0].count += 1;
    }
    const slots = plotCounts.flatMap(({ count, plot }) => {
      const aspect = plot.width / Math.max(1, plot.depth);
      const columns = Math.max(1, Math.ceil(Math.sqrt(count * aspect)));
      const rows = Math.ceil(count / columns);
      const marginX = plot.width * 0.07;
      const marginZ = plot.depth * 0.07;
      const gapX = plot.width * 0.035;
      const gapZ = plot.depth * 0.035;
      const width = (plot.width - marginX * 2 - gapX * Math.max(0, columns - 1)) / columns;
      const depth = (plot.depth - marginZ * 2 - gapZ * Math.max(0, rows - 1)) / rows;
      return Array.from({ length: count }, (_, index) => ({
        depth,
        width,
        x: plot.x + marginX + (index % columns) * (width + gapX),
        z: plot.z + marginZ + Math.floor(index / columns) * (depth + gapZ),
      }));
    });
    const largest = Math.max(...parts.map((part) => part.representedCount));
    return parts.map((part, index) => ({
      ...part,
      ...slots[index],
      height: facility.height * (
        0.48 + Math.sqrt(part.representedCount / largest) * 0.52
      ),
    }));
  }

  function createLodPolicy(scene, territoryData = null) {
    const buildings = new Map(
      scene.buildings.map((building) => [building.entityId, building]),
    );
    const networks = new Map(scene.networks.map((network) => [network.id, network]));
    const districts = new Map(scene.districts.map((district) => [district.id, district]));
    const territories = new Map(
      (territoryData?.districts || []).map((territory) => [territory.id, territory]),
    );
    const majorIds = new Set(majorDistrictIds(scene));
    const aggregates = aggregateFacilities(scene, majorIds, districts, territories);
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
        ? aggregates
          .filter((aggregate) => aggregate.memberEntityIds.some((id) => candidateBuildings.has(id)))
          .map((aggregate) => aggregate.id)
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
    aggregateParts,
    createLodPolicy,
    createIndex,
    declaredDependenciesForEntity,
    majorDistrictIds,
    selectNonOverlappingLabels,
  });
})();
