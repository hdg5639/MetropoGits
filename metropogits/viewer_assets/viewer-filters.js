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

  function aggregateFacilities(scene, majorIds, districts, territories, streets = []) {
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

    function isStrictDescendant(districtId, ancestorId) {
      let current = districts.get(districtId);
      while (current?.parentId !== null) {
        if (current.parentId === ancestorId) return true;
        current = districts.get(current.parentId);
      }
      return false;
    }

    function subtractRectangle(plot, blocker) {
      const overlapX = Math.max(plot.x, blocker.x);
      const overlapZ = Math.max(plot.z, blocker.z);
      const overlapMaxX = Math.min(plot.x + plot.width, blocker.x + blocker.width);
      const overlapMaxZ = Math.min(plot.z + plot.depth, blocker.z + blocker.depth);
      if (overlapX >= overlapMaxX || overlapZ >= overlapMaxZ) return [plot];
      return [
        {
          depth: overlapZ - plot.z,
          width: plot.width,
          x: plot.x,
          z: plot.z,
        },
        {
          depth: plot.z + plot.depth - overlapMaxZ,
          width: plot.width,
          x: plot.x,
          z: overlapMaxZ,
        },
        {
          depth: overlapMaxZ - overlapZ,
          width: overlapX - plot.x,
          x: plot.x,
          z: overlapZ,
        },
        {
          depth: overlapMaxZ - overlapZ,
          width: plot.x + plot.width - overlapMaxX,
          x: overlapMaxX,
          z: overlapZ,
        },
      ].filter((part) => part.width > 0 && part.depth > 0);
    }

    function clippedPlots(placement, majorDistrictId) {
      const rectangles = territories.get(majorDistrictId)?.rectangles || [];
      const maxX = placement.x + placement.width;
      const maxZ = placement.z + placement.depth;
      let plots = rectangles.map((rectangle) => {
        const x = Math.max(placement.x, rectangle.x);
        const z = Math.max(placement.z, rectangle.z);
        return {
          depth: Math.min(maxZ, rectangle.z + rectangle.depth) - z,
          width: Math.min(maxX, rectangle.x + rectangle.width) - x,
          x,
          z,
        };
      }).filter((plot) => plot.width > 0 && plot.depth > 0);
      const nestedMajorRectangles = [...majorIds]
        .filter((districtId) => isStrictDescendant(districtId, majorDistrictId))
        .flatMap((districtId) => territories.get(districtId)?.rectangles || []);
      for (const blocker of nestedMajorRectangles) {
        plots = plots.flatMap((plot) => subtractRectangle(plot, blocker));
      }
      for (const blocker of streets) {
        plots = plots.flatMap((plot) => subtractRectangle(plot, blocker));
      }
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

  // Presentation only: no entity, role, relationship or canonical site is changed.
  function roleFacilities(blocks, scene, ucg, streets = []) {
    if (!ucg) return blocks;
    const evidence = new Map(ucg.evidence.map(item => [item.evidenceId, item]));
    const buildings = new Map(scene.buildings.map(item => [item.entityId, item]));
    const entities = new Map(ucg.entities.map(item => [item.id, item]));
    const modules = ucg.entities.filter(item => item.kind === "MODULE")
      .sort((a, b) => b.path.length - a.path.length || a.id.localeCompare(b.id));
    const owner = building => {
      const path = entities.get(building.entityId)?.path || "";
      return modules.find(item => path.startsWith(`${item.path}/`))?.id || "";
    };
    const overlap = (a, b) => a.x < b.x + b.width && b.x < a.x + a.width
      && a.z < b.z + b.depth && b.z < a.z + a.depth;
    const areaInside = (a, b) => Math.max(0, Math.min(a.x + a.width, b.x + b.width) - Math.max(a.x, b.x))
      * Math.max(0, Math.min(a.z + a.depth, b.z + b.depth) - Math.max(a.z, b.z));
    const bounds = members => {
      const x = Math.min(...members.map(b => b.x));
      const z = Math.min(...members.map(b => b.z));
      return { x, z, width: Math.max(...members.map(b => b.x + b.width)) - x,
        depth: Math.max(...members.map(b => b.z + b.depth)) - z };
    };
    function key(building) {
      const rules = (building.evidenceIds || []).map(id => evidence.get(id)?.ruleId);
      if (building.archetype === "LIBRARY" && rules.includes("path.test-source")) return "TEST";
      if (building.archetype !== "GATE") return null;
      if (rules.includes("path.nextjs.app-page")) return "PAGE";
      if (rules.includes("path.nextjs.route-handler")) return "API";
      // Do not merge unknown or differently evidenced gate roles.
      const spring = rules.filter(rule => rule?.startsWith("spring.controller"));
      return spring.length ? `GATE:${spring.sort().join(",")}` : null;
    }
    function subtract(a, b) {
      if (!overlap(a, b)) return [a];
      const x = Math.max(a.x, b.x), z = Math.max(a.z, b.z);
      const endX = Math.min(a.x + a.width, b.x + b.width);
      const endZ = Math.min(a.z + a.depth, b.z + b.depth);
      return [
        { x: a.x, z: a.z, width: a.width, depth: z - a.z },
        { x: a.x, z: endZ, width: a.width, depth: a.z + a.depth - endZ },
        { x: a.x, z, width: x - a.x, depth: endZ - z },
        { x: endX, z, width: a.x + a.width - endX, depth: endZ - z },
      ].filter(p => p.width > 0 && p.depth > 0);
    }
    const result = [];
    for (const block of blocks) {
      const members = block.memberEntityIds.map(id => buildings.get(id));
      const available = new Set(members.filter(b => key(b)).map(b => b.entityId));
      const promoted = [];
      for (const seed of members) {
        if (!available.has(seed.entityId)) continue;
        const cluster = [seed];
        let plot = bounds(cluster);
        const candidates = members.filter(b => b !== seed && available.has(b.entityId)
          && key(b) === key(seed) && owner(b) === owner(seed))
          .sort((a, b) => Math.hypot(a.x - seed.x, a.z - seed.z) - Math.hypot(b.x - seed.x, b.z - seed.z)
            || a.entityId.localeCompare(b.entityId));
        for (const candidate of candidates) {
          if (cluster.includes(candidate)) continue;
          const rectangle = bounds([...cluster, candidate]);
          // Absorb all same-role occupants of the enlarged footprint together;
          // never draw a compound over an omitted file in the next row.
          const next = scene.buildings.filter(b => overlap(rectangle, b));
          if (next.some(b => !members.includes(b) || !available.has(b.entityId)
            || key(b) !== key(seed) || owner(b) !== owner(seed))) continue;
          if (next.some(b => b.x < rectangle.x || b.z < rectangle.z
            || b.x + b.width > rectangle.x + rectangle.width
            || b.z + b.depth > rectangle.z + rectangle.depth)) continue;
          if (Math.max(rectangle.width, rectangle.depth) > 56) continue;
          if (!cluster.some(b => Math.hypot(b.x - candidate.x, b.z - candidate.z) <= 15)) continue;
          if (next.reduce((sum, b) => sum + b.width * b.depth, 0) / (rectangle.width * rectangle.depth) < 0.55) continue;
          if (Math.abs(block.plots.reduce((sum, p) => sum + areaInside(rectangle, p), 0)
            - rectangle.width * rectangle.depth) > 0.001) continue;
          if (streets.some(street => overlap(rectangle, street))) continue;
          cluster.splice(0, cluster.length, ...next.sort((a, b) => a.entityId.localeCompare(b.entityId)));
          plot = rectangle;
        }
        if (cluster.length < 4) continue;
        for (const b of cluster) available.delete(b.entityId);
        const role = key(seed), count = cluster.length;
        const tier = count >= 12 ? "campus" : "center";
        const title = role === "TEST" ? `Test ${tier}`
          : role === "PAGE" ? `Page ${tier === "campus" ? "terminal" : "hall"}`
          : `${role === "API" || role.includes(".rest") ? "API" : "Entry"} ${tier === "campus" ? "terminal" : "hall"}`;
        promoted.push({ ...block, ...plot, plots: [plot], role, tier, title,
          id: `visual:role:${seed.entityId}`, height: Math.min(30, 12 + Math.log2(count) * 3),
          labelX: plot.x + plot.width / 2, labelZ: plot.z + plot.depth / 2,
          archetypeCounts: [{ archetype: seed.archetype, count }],
          evidenceIds: [...new Set(cluster.flatMap(b => b.evidenceIds))].sort(),
          memberEntityIds: cluster.map(b => b.entityId).sort(),
          memberDistrictIds: [...new Set(cluster.map(b => b.districtId))].sort(),
        });
      }
      if (!promoted.length) { result.push(block); continue; }
      const grouped = new Set(promoted.flatMap(p => p.memberEntityIds));
      const remainder = members.filter(b => !grouped.has(b.entityId));
      if (remainder.length) {
        let plots = block.plots;
        for (const p of promoted) plots = plots.flatMap(plot => subtract(plot, p));
        const counts = new Map();
        for (const b of remainder) counts.set(b.archetype, (counts.get(b.archetype) || 0) + 1);
        result.push({ ...block, plots, memberEntityIds: remainder.map(b => b.entityId),
          memberDistrictIds: [...new Set(remainder.map(b => b.districtId))].sort(),
          archetypeCounts: [...counts].map(([archetype, count]) => ({ archetype, count }))
            .sort((a, b) => b.count - a.count || a.archetype.localeCompare(b.archetype)),
        });
      }
      result.push(...promoted);
    }
    return result.sort((a, b) => a.id.localeCompare(b.id));
  }

  function aggregateParts(facility) {
    if (facility.role) return [{ ...facility, entityId: facility.id,
      archetype: facility.archetypeCounts[0].archetype,
      representedCount: facility.memberEntityIds.length, aggregateRole: facility.role }];
    const targetCount = Math.min(
      16,
      Math.max(
        facility.archetypeCounts.length,
        Math.ceil(Math.sqrt(facility.memberEntityIds.length)),
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

    const sourcePlots = [...(facility.plots || [facility])];
    const usablePlots = sourcePlots.filter((plot) => plot.width >= 2 && plot.depth >= 2);
    const candidates = (usablePlots.length >= Math.min(parts.length, sourcePlots.length)
      ? usablePlots
      : sourcePlots).map((plot) => ({
        ...plot,
        area: plot.width * plot.depth,
        centerX: plot.x + plot.width / 2,
        centerZ: plot.z + plot.depth / 2,
      }));
    const targetPlotCount = Math.min(parts.length, candidates.length);
    const spanX = Math.max(1, facility.width);
    const spanZ = Math.max(1, facility.depth);
    const largestArea = Math.max(...candidates.map((plot) => plot.area));
    const selectedPlots = [];
    while (selectedPlots.length < targetPlotCount) {
      const remaining = candidates.filter((plot) => !selectedPlots.includes(plot));
      remaining.sort((left, right) => {
        function score(plot) {
          const areaBonus = Math.sqrt(plot.area / largestArea) * 0.08;
          const normalizedX = (plot.centerX - facility.x) / spanX;
          const normalizedZ = (plot.centerZ - facility.z) / spanZ;
          if (!selectedPlots.length) {
            const centerDistance = Math.hypot(normalizedX - 0.5, normalizedZ - 0.5);
            return -centerDistance + areaBonus;
          }
          const separation = Math.min(...selectedPlots.map((selected) => Math.hypot(
            (plot.centerX - selected.centerX) / spanX,
            (plot.centerZ - selected.centerZ) / spanZ,
          )));
          const selectedCenterX = selectedPlots.reduce(
            (sum, selected) => sum + (selected.centerX - facility.x) / spanX,
            normalizedX,
          ) / (selectedPlots.length + 1);
          const selectedCenterZ = selectedPlots.reduce(
            (sum, selected) => sum + (selected.centerZ - facility.z) / spanZ,
            normalizedZ,
          ) / (selectedPlots.length + 1);
          const centerDrift = Math.hypot(selectedCenterX - 0.5, selectedCenterZ - 0.5);
          return separation + areaBonus - centerDrift * 0.85;
        }
        return score(right) - score(left) || right.area - left.area
          || stableBucket(
            `${facility.id}:${left.x}:${left.z}`,
            2_147_483_647,
          ) - stableBucket(
            `${facility.id}:${right.x}:${right.z}`,
            2_147_483_647,
          )
          || left.z - right.z || left.x - right.x;
      });
      selectedPlots.push(remaining[0]);
    }
    const plots = selectedPlots.sort(
      (left, right) => left.z - right.z || left.x - right.x
        || right.area - left.area,
    );
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
      return Array.from({ length: count }, (_, index) => {
        const row = Math.floor(index / columns);
        const column = index % columns;
        const itemsInRow = Math.min(columns, count - row * columns);
        const occupiedWidth = itemsInRow * width + Math.max(0, itemsInRow - 1) * gapX;
        const rowOffset = (plot.width - occupiedWidth) / 2;
        return {
          depth,
          width,
          x: plot.x + rowOffset + column * (width + gapX),
          z: plot.z + marginZ + row * (depth + gapZ),
        };
      });
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

  function roleVolumes(building) {
    const { x, z, width: w, depth: d, height: h } = building;
    const part = (px, py, pz, pw, ph, pd, shade = 0) => ({
      x: x + px * w, y: py * h, z: z + pz * d,
      width: pw * w, height: ph * h, depth: pd * d, shade,
      archetype: building.archetype,
    });
    const count = building.tier === "campus" ? 4 : 2;
    if (building.aggregateRole === "TEST") {
      // Shared low laboratory spine, separate wings, one central test tower.
      return [part(.08, 0, .38, .84, .22, .24),
        ...Array.from({length: count}, (_, i) => part(.08 + i * .84 / count, 0, .08,
          .66 / count, .4, .84, .1)),
        part(.39, .4, .37, .22, .6, .26, .3)];
    }
    // Terminal concourse with bounded entrance bays, not one giant gate.
    return [part(.06, 0, .3, .88, .38, .62), part(.04, .38, .26, .92, .12, .68, .25),
      ...Array.from({length: count}, (_, i) => part(.1 + i * .8 / count, 0, .06,
        .52 / count, .26, .25, .12)), part(.7, .5, .5, .18, .5, .3, .35)];
  }

  function aggregateLabel(facility, entities) {
    const paths = facility.memberEntityIds.slice(0, 3).map(id => entities.get(id)?.path || id);
    const rest = facility.memberEntityIds.length - paths.length;
    return `${facility.title || "City block"} · ${facility.memberEntityIds.length} files · visual aggregate\n`
      + paths.join("\n") + (rest > 0 ? `\n+${rest} more — click to inspect` : "");
  }

  function createLodPolicy(scene, territoryData = null, streetData = null, ucg = null) {
    const buildings = new Map(
      scene.buildings.map((building) => [building.entityId, building]),
    );
    const networks = new Map(scene.networks.map((network) => [network.id, network]));
    const districts = new Map(scene.districts.map((district) => [district.id, district]));
    const territories = new Map(
      (territoryData?.districts || []).map((territory) => [territory.id, territory]),
    );
    const majorIds = new Set(majorDistrictIds(scene));
    const aggregates = roleFacilities(
      aggregateFacilities(scene, majorIds, districts, territories, streetData?.rectangles || []), scene, ucg,
      streetData?.rectangles || [],
    );
    const aggregateIds = new Set(aggregates.map((aggregate) => aggregate.id));
    const roleByMember = new Map(aggregates.filter(a => a.role)
      .flatMap(a => a.memberEntityIds.map(id => [id, a])));
    const edges = new Map((ucg?.edges || []).map(edge => [edge.id, edge]));
    const routesByMember = new Map();
    for (const network of scene.networks) {
      for (const edgeId of network.edgeIds) {
        const edge = edges.get(edgeId);
        if (!edge) continue;
        for (const id of [edge.from, edge.to]) {
          if (!routesByMember.has(id)) routesByMember.set(id, new Set());
          routesByMember.get(id).add(network.id);
        }
      }
    }
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

    function visibility(level, candidateBuildingIds, candidateNetworkIds, selected = null,
      expandedAggregateIds = new Set(), showAllNetworks = false) {
      const candidateBuildings = new Set(candidateBuildingIds);
      const candidateNetworks = new Set(candidateNetworkIds);
      let buildingIds = [...candidateBuildings]
        .filter((id) => {
          const building = buildings.get(id);
          if (!building) return false;
          if (selected?.kind === "building" && selected.id === id) return true;
          if (level === "overview") return false;
          // District simplifies meshes, not file coverage. Sampling generic
          // files here left holes at the same physical scale as Detail.
          return true;
        })
        .sort();

      const visibleAggregateIds = aggregates.filter(aggregate =>
        (level === "overview" || aggregate.role)
        && !expandedAggregateIds.has(aggregate.id)
        && aggregate.memberEntityIds.every(id => candidateBuildings.has(id))
        && !(!aggregate.role && selected?.kind === "building" && aggregate.memberEntityIds.includes(selected.id)),
      ).map(aggregate => aggregate.id);
      // Partial filters must never reintroduce hidden members through an aggregate.
      if (level === "overview") {
        const represented = new Set(aggregates.filter(a => visibleAggregateIds.includes(a.id)).flatMap(a => a.memberEntityIds));
        buildingIds = [...candidateBuildings].filter(id => buildings.has(id) && !represented.has(id)).sort();
      }
      if (
        selected?.kind === "aggregate"
        && aggregateIds.has(selected.id)
        && !expandedAggregateIds.has(selected.id)
        && !visibleAggregateIds.includes(selected.id)
        && aggregates.find(a => a.id === selected.id).memberEntityIds.every(id => candidateBuildings.has(id))
      ) {
        visibleAggregateIds.push(selected.id);
      }
      visibleAggregateIds.sort();
      const groupedMembers = new Set(aggregates.filter(a => visibleAggregateIds.includes(a.id)).flatMap(a => a.memberEntityIds));
      buildingIds = buildingIds.filter(id => !groupedMembers.has(id));

      const networkLimit = showAllNetworks ? Infinity : level === "overview" ? 24 : 64;
      const rankedNetworks = [...candidateNetworks]
        .map((id) => networks.get(id))
        .filter(Boolean)
        .sort(
          (left, right) =>
            (right.edgeIds?.length || 0) - (left.edgeIds?.length || 0)
            || left.id.localeCompare(right.id),
        );
      const networkIds = selected?.kind === "building" && ucg && !showAllNetworks
        ? rankedNetworks.filter(network => routesByMember.get(selected.id)?.has(network.id)).map(network => network.id)
        : rankedNetworks.slice(0, networkLimit).map((network) => network.id);
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
      facilityForEntity: id => roleByMember.get(id),
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

  function corridorVisible(rectangle, renderedNetworkIds) {
    return !rectangle.networkIds || rectangle.networkIds.some(id => renderedNetworkIds.has(id));
  }

  function createAccessPolicy(routing, hierarchy = null) {
    if (!routing) return null;
    const assigned = routing.streetGrid ? new Set(routing.streetGrid.assignment.assignedRouteIds) : null;
    const fallbackIds = new Set(routing.streetGrid?.assignment.fallbackRouteIds || []);
    const fallbackReasons = new Map((routing.streetGrid?.assignment.fallbackReasons || []).map(r=>[r.routeId,r]));
    const reasonLabels = {
      assigned:'Assigned to structural streets', distance_limit:'Street detour exceeds distance limit',
      joint_constraints:'Distance fits; no path found under combined bend/simple-path constraints',
      missing_access:'Endpoint has no street access', disconnected_streets:'Endpoints lie on disconnected streets',
      connector_search_limit:'Access search capped; feasibility unknown', route_search_limit:'Route search capped; feasibility unknown',
      diagnostic_search_limit:'Diagnostic search capped; cause unknown', access_only:'Original path has no lattice road segment',
      no_structural_streets:'No structural street geometry', unrecorded:'Legacy artifact: cause not recorded',
    };
    function assignmentReason(id) {
      if (!assigned || !routes.has(id)) return null;
      const record = assigned.has(id) ? {reason:'assigned'} : fallbackReasons.get(id) || {reason:'unrecorded'};
      return {...record, label:reasonLabels[record.reason] || reasonLabels.unrecorded};
    }
    function failurePage(buildingIds, networkIds, offset=0, reason='') {
      const failures = [...routes.values()].filter(r=>fallbackIds.has(r.id) && buildingIds.has(r.source)
        && buildingIds.has(r.target) && r.networkIds.some(id=>networkIds.has(id))).sort((a,b)=>a.id.localeCompare(b.id));
      const counts = {};
      for (const route of failures) {
        const key=assignmentReason(route.id).reason;
        counts[key]=(counts[key] || 0)+1;
      }
      const matching=failures.filter(r=>!reason || assignmentReason(r.id).reason===reason);
      const start=Math.max(0,Math.min(Math.floor(Number.isFinite(offset)?offset:0),Math.max(0,matching.length-1)));
      return {total:matching.length, offset:start, rows:matching.slice(start,start+25),
        counts:Object.keys(counts).sort().map(key=>({reason:key,label:reasonLabels[key] || reasonLabels.unrecorded,count:counts[key]}))};
    }
    const routes = new Map(routing.routes.map(route => [route.id, route]));
    const segments = new Map(routing.segments.map(segment => [segment.id,
      {...segment, demand: hierarchy?.segments?.[segment.id]}]));
    const trajectories = new Map(routing.routes.map(route => {
      let distance = 0;
      const steps = route.path.slice(1).map((end, i) => {
        const start = route.path[i], length = Math.hypot(end[0]-start[0], end[1]-start[1]);
        const step = {start, end, length, distance, segmentId: route.segmentIds[i]};
        distance += length;
        return step;
      });
      return [route.id, {steps, distance}];
    }));
    function frame(level, buildingIds, networkIds, selected, showAll = false, members = []) {
      const selectedSegment = selected?.kind === 'network' ? segments.get(selected.id) : null;
      const selectedRoutes = selectedSegment ? new Set(selectedSegment.routeIds) : null;
      const memberIds = new Set(members);
      const candidates = routing.routes.filter(route => buildingIds.has(route.source) && buildingIds.has(route.target)
        && route.networkIds.some(id => networkIds.has(id)));
      const related = candidates.filter(route => (selected?.kind !== 'building' || route.source === selected.id || route.target === selected.id)
        && (selected?.kind !== 'aggregate' || memberIds.has(route.source) || memberIds.has(route.target))
        && (selected?.kind !== 'network' || ((selectedRoutes ? selectedRoutes.has(route.id) : route.networkIds.includes(selected.id))
          && (!selected.routeId || selected.routeId === route.id))));
      const focused = ['building', 'network', 'aggregate'].includes(selected?.kind);
      const eligible = (showAll ? candidates : related).filter(route =>
        !assigned || focused || showAll || assigned.has(route.id));
      const routeIds = new Set(eligible.map(route => route.id));
      const highlighted = new Set(focused ? related.map(route => route.id) : []);
      const visibleSegments = [...segments.values()].map(segment => {
        const active = segment.routeIds.filter(id => routeIds.has(id));
        return {...segment, routeIds: active, highlighted: active.some(id => highlighted.has(id))};
      }).filter(segment => segment.routeIds.length &&
        (assigned || level !== 'overview' || focused || showAll || (!segment.access && segment.routeIds.length >= 4)));
      const segmentIds = new Set(visibleSegments.map(segment => segment.id));
      const representedRoutes = new Set(visibleSegments.flatMap(segment => segment.routeIds));
      const animated = eligible.filter(route => representedRoutes.has(route.id));
      const stride = Math.max(1, Math.ceil(animated.length / 96));
      return {routes: eligible, routeIds, segments: visibleSegments, segmentIds, focused,
        networkIds: new Set(eligible.flatMap(route => route.networkIds)),
        animated: animated.filter((_, i) => i % stride === 0),
        junctions: routing.junctions.filter(j => j.segmentIds.filter(id => segmentIds.has(id)).length >= 3)};
    }
    function network(id, activeRouteIds = null) {
      const segment = segments.get(id);
      if (!segment) return null;
      const contributing = segment.routeIds.filter(key => !activeRouteIds || activeRouteIds.has(key));
      return {id, kind: segment.kind, path: [segment.start, segment.end], routeIds: contributing, demand:segment.demand,
        edgeIds: [...new Set(contributing.flatMap(key => routes.get(key).edgeIds))].sort()};
    }
    function choices(id, buildingIds, networkIds) {
      const segment = segments.get(id);
      return routing.routes.filter(route => buildingIds.has(route.source) && buildingIds.has(route.target)
        && route.networkIds.some(key => networkIds.has(key))
        && (segment ? segment.routeIds.includes(route.id) : route.networkIds.includes(id)));
    }
    function position(route, phase) {
      const trajectory = trajectories.get(route.id);
      const distance = Math.max(0, Math.min(1, phase)) * trajectory.distance;
      const step = trajectory.steps.find(item => distance <= item.distance + item.length) || trajectory.steps.at(-1);
      if (!step) return null;
      const fraction = step.length ? (distance - step.distance) / step.length : 0;
      return {segmentId: step.segmentId, point: [step.start[0] + (step.end[0]-step.start[0])*fraction,
        step.start[1] + (step.end[1]-step.start[1])*fraction]};
    }
    return Object.freeze({frame, network, choices, position, segments, routes, assignmentReason, failurePage, status: routing.status,
      streetStatus: assigned ? ` · Street assignment ${assigned.size}/${routing.routes.length} · ${routing.streetGrid.assignment.fallbackRouteIds.length} legacy paths: select a building or All routes` : '',
      unresolved: routing.unresolvedEdgeIds.length});
  }

  function accessRoadStyle(segment) {
    if (segment.demand) {
      const profile = segment.demand, shared = ['AVENUE', 'TRUNK'].includes(profile.grade);
      const surface = {HTTP_HIGHWAY:'#f97316', MESSAGING_PATH:'#a855f7'}[segment.kind] || profile.surface;
      return {shared, width:Math.min(segment.width, profile.width), surface,
        shoulder:profile.shoulder || (shared?'#8c9aa8':'#4e6072'),
        marking:profile.marking || (shared?'#bac8d4':'#748a9e')};
    }
    const shared = !segment.access && segment.routeIds.length >= 4;
    return {shared, width:Math.min(segment.width, .7+Math.log2(segment.routeIds.length+1)*.5),
      surface:shared?'#52677b':'#33465a', shoulder:shared?'#8c9aa8':'#617284',
      marking:shared?'#bac8d4':'#748a9e'};
  }

  // Presentation only: inset the union of existing approach rectangles. Never
  // bridge empty corners, create a route, or widen the certified road footprint.
  function accessJunctionGeometry(frame) {
    const segments = new Map((frame?.segments || []).map(s => [s.id, s]));
    const trims = new Map(), surfaces = [];
    const unique = values => [...new Set(values.map(v => Math.round(v * 1e8) / 1e8))].sort((a,b) => a-b);
    for (const junction of [...(frame?.junctions || [])].sort((a,b)=>a.id.localeCompare(b.id))) {
      const groups = new Map();
      for (const id of [...junction.segmentIds].sort()) {
        const segment = segments.get(id);
        if (!segment) continue;
        if (!groups.has(segment.kind)) groups.set(segment.kind, []);
        groups.get(segment.kind).push(segment);
      }
      for (const [kind, incident] of groups) {
        if (incident.length < 3) continue;
        const [x,z] = junction.point;
        const widths = incident.map(s => accessRoadStyle(s).width);
        const inset = Math.min(...widths) * .12, reach = Math.max(...widths) / 2 + inset;
        const rectangles = [];
        for (const segment of incident) {
          const side = segment.start[0] === x && segment.start[1] === z ? 0 :
            segment.end[0] === x && segment.end[1] === z ? 1 : -1;
          if (side < 0) continue;
          const other = side ? segment.start : segment.end;
          const dx = other[0]-x, dz = other[1]-z;
          if ((dx === 0) === (dz === 0)) continue;
          const length = Math.abs(dx || dz), extent = Math.min(length, reach);
          const half = accessRoadStyle(segment).width / 2;
          const endX = Math.sign(dx)*extent, endZ = Math.sign(dz)*extent;
          rectangles.push(dx ? [Math.min(0,endX),-half,Math.max(0,endX),half] :
            [-half,Math.min(0,endZ),half,Math.max(0,endZ)]);
          const trim = trims.get(segment.id) || [0,0];
          trim[side] = Math.max(trim[side], extent);
          trims.set(segment.id, trim);
        }
        if (rectangles.length < 3) continue;
        const inside = (a,b) => rectangles.some(r => a>r[0]-1e-9 && a<r[2]+1e-9 && b>r[1]-1e-9 && b<r[3]+1e-9);
        const xs = unique(rectangles.flatMap(r => [r[0],r[2]]));
        const zs = unique(rectangles.flatMap(r => [r[1],r[3]]));
        const boundaries = [];
        for (let i=0;i<xs.length-1;i++) for (let j=0;j<zs.length-1;j++) {
          const a=xs[i], b=zs[j], c=xs[i+1], d=zs[j+1];
          if (!inside((a+c)/2,(b+d)/2)) continue;
          if (!inside(a-1e-7,(b+d)/2)) boundaries.push([a,b,a,d]);
          if (!inside(c+1e-7,(b+d)/2)) boundaries.push([c,b,c,d]);
          if (!inside((a+c)/2,b-1e-7)) boundaries.push([a,b,c,b]);
          if (!inside((a+c)/2,d+1e-7)) boundaries.push([a,d,c,d]);
        }
        const cutsX = unique(boundaries.flatMap(r => [r[0]-inset,r[0]+inset,r[2]-inset,r[2]+inset]));
        const cutsZ = unique(boundaries.flatMap(r => [r[1]-inset,r[1]+inset,r[3]-inset,r[3]+inset]));
        const tiles = [], open = new Map();
        for (let j=0;j<cutsZ.length-1;j++) {
          const b=cutsZ[j], d=cutsZ[j+1], active = new Set();
          let start = null;
          for (let i=0;i<cutsX.length;i++) {
            const a=cutsX[i], c=cutsX[i+1], mx=(a+c)/2, mz=(b+d)/2;
            const keep = i<cutsX.length-1 && inside(mx,mz) && boundaries.every(r =>
              Math.max(r[0]-mx, mx-r[2], r[1]-mz, mz-r[3]) >= inset-1e-9);
            if (keep && start === null) start=a;
            if (!keep && start !== null) {
              const key=`${start},${a}`, previous=open.get(key);
              if (previous && Math.abs(previous[3]-b)<1e-8) previous[3]=d;
              else {const tile=[start,b,a,d]; tiles.push(tile); open.set(key,tile);}
              active.add(key); start=null;
            }
          }
          for (const key of open.keys()) if (!active.has(key)) open.delete(key);
        }
        const principal = [...incident].sort((a,b)=>(b.demand?.targetWidth || 0)-(a.demand?.targetWidth || 0)
          || Number(accessRoadStyle(b).shared)-Number(accessRoadStyle(a).shared) || a.id.localeCompare(b.id))[0];
        surfaces.push({kind, segmentIds:incident.map(s=>s.id), surface:accessRoadStyle(principal).surface,
          rectangles:tiles.map(r=>[r[0]+x,r[1]+z,r[2]+x,r[3]+z])});
      }
    }
    return {surfaces, trims};
  }

  function accessMarkingSegment(segment, trims) {
    const [a,b]=trims.get(segment.id) || [0,0];
    const dx=segment.end[0]-segment.start[0], dz=segment.end[1]-segment.start[1];
    const length=Math.hypot(dx,dz);
    if (length <= a+b+1e-8) return null;
    return {start:[segment.start[0]+dx*a/length,segment.start[1]+dz*a/length],
      end:[segment.end[0]-dx*b/length,segment.end[1]-dz*b/length]};
  }

  function accessMarkingSegments(segment, trims) {
    const style=accessRoadStyle(segment), run=accessMarkingSegment(segment,trims);
    if (!run || segment.access || !style.shared || style.width<1.25) return [];
    if (segment.kind!=='DEPENDENCY_ROAD') return [run];
    if (segment.demand?.lanePattern==='NONE') return [];
    const horizontal=run.start[1]===run.end[1], axis=horizontal?0:1;
    if (!horizontal && run.start[0]!==run.end[0]) return [];
    const lo=Math.min(run.start[axis],run.end[axis]), hi=Math.max(run.start[axis],run.end[axis]);
    const period=4, dash=1.6, first=Math.floor(lo/period), last=Math.floor(hi/period);
    if (!Number.isFinite(lo+hi) || last-first>512) return []; // paint-only bound
    const pieces=[];
    for(let i=first;i<=last;i++) {
      const a=Math.max(lo,i*period), b=Math.min(hi,i*period+dash);
      if (b-a<1e-8) continue;
      const start=[...run.start], end=[...run.start];start[axis]=a;end[axis]=b;
      pieces.push({start,end});
    }
    return pieces;
  }

  function districtBuildings(scene, districtId) {
    const children = new Map(scene.districts.map(d => [d.id, []]));
    for (const district of scene.districts) children.get(district.parentId)?.push(district.id);
    const ids = new Set(), pending = [districtId];
    while (pending.length) {
      const id = pending.pop();
      if (ids.has(id)) continue;
      ids.add(id);
      pending.push(...(children.get(id) || []));
    }
    return scene.buildings.filter(b => ids.has(b.districtId));
  }

  // Translate the orbit target on X/Z, never its height. Drag distances are pixels.
  function groundPan(camera, dx, dy, viewportHeight, fieldOfView) {
    const scale = 2 * camera.distance * Math.tan(fieldOfView / 2) / Math.max(1, viewportHeight);
    const forward = dy / Math.max(0.15, Math.sin(camera.pitch));
    return {x: (-dx * Math.cos(camera.yaw) - forward * Math.sin(camera.yaw)) * scale,
      z: (dx * Math.sin(camera.yaw) - forward * Math.cos(camera.yaw)) * scale};
  }

  function cameraKeyAction(event) {
    if (event.defaultPrevented || event.ctrlKey || event.metaKey || event.altKey
      || event.target?.isContentEditable
      || event.target?.closest?.('input, select, textarea, [contenteditable], [role="textbox"]')) return null;
    return {w:'pan-up', arrowup:'pan-up', s:'pan-down', arrowdown:'pan-down',
      a:'pan-left', arrowleft:'pan-left', d:'pan-right', arrowright:'pan-right',
      q:'rotate-left', e:'rotate-right', '+':'zoom-in', '=':'zoom-in', '-':'zoom-out', r:'reset'}[event.key.toLowerCase()] || null;
  }

  globalThis.METROPOGITS_FILTERS = Object.freeze({
    accessJunctionGeometry,
    accessMarkingSegment,
    accessMarkingSegments,
    accessRoadStyle,
    districtBuildings,
    groundPan,
    cameraKeyAction,
    createAccessPolicy,
    corridorVisible,
    aggregateParts,
    aggregateLabel,
    roleVolumes,
    createLodPolicy,
    createIndex,
    declaredDependenciesForEntity,
    majorDistrictIds,
    selectNonOverlappingLabels,
  });
})();
