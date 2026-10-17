(() => {
  "use strict";

  function phaseForId(identifier) {
    let hash = 2166136261;
    for (let index = 0; index < identifier.length; index += 1) {
      hash ^= identifier.charCodeAt(index);
      hash = Math.imul(hash, 16777619);
    }
    return (hash >>> 0) / 4294967296;
  }

  function pointAlongPath(path, progress) {
    if (!Array.isArray(path) || path.length === 0) return null;
    if (path.length === 1) return [...path[0]];

    const lengths = [];
    let totalLength = 0;
    for (let index = 1; index < path.length; index += 1) {
      const length = Math.hypot(
        path[index][0] - path[index - 1][0],
        path[index][1] - path[index - 1][1],
      );
      lengths.push(length);
      totalLength += length;
    }
    if (totalLength === 0) return [...path[0]];

    let remaining = Math.max(0, Math.min(1, progress)) * totalLength;
    for (let index = 0; index < lengths.length; index += 1) {
      const length = lengths[index];
      if (remaining <= length || index === lengths.length - 1) {
        const fraction = length === 0 ? 0 : remaining / length;
        return [
          path[index][0] + (path[index + 1][0] - path[index][0]) * fraction,
          path[index][1] + (path[index + 1][1] - path[index][1]) * fraction,
        ];
      }
      remaining -= length;
    }
    return [...path[path.length - 1]];
  }

  globalThis.METROPOGITS_ACTIVITY = Object.freeze({ phaseForId, pointAlongPath });
})();
