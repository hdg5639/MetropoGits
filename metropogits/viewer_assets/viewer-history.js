(() => {
  "use strict";

  const history = globalThis.METROPOGITS_HISTORY;
  if (!history || !Array.isArray(history.frames) || history.frames.length < 2) return;

  const requestedRevision = new URLSearchParams(globalThis.location.hash.slice(1)).get("revision");
  const requestedIndex = history.frames.findIndex(
    (frame) => frame.revision === requestedRevision,
  );
  const selectedIndex = requestedIndex >= 0 ? requestedIndex : history.frames.length - 1;
  const selected = history.frames[selectedIndex];
  globalThis.METROPOGITS_DATA = { scene: selected.scene, ucg: selected.ucg };

  const revisionSelect = document.getElementById("history-revision");
  const summary = document.getElementById("history-summary");
  if (!revisionSelect || !summary) return;

  history.frames.forEach((frame, index) => {
    const option = document.createElement("option");
    option.value = frame.revision;
    option.textContent = `${index + 1}/${history.frames.length} · ${frame.revision}`;
    revisionSelect.append(option);
  });
  revisionSelect.value = selected.revision;

  if (selectedIndex === 0) {
    summary.textContent = `${selected.scene.buildings.length} buildings · initial frame`;
  } else {
    const transition = history.timeline.transitions[selectedIndex - 1];
    summary.textContent = [
      `${selected.scene.buildings.length} buildings`,
      `+${transition.addedEntityIds.length}`,
      `−${transition.removedEntityIds.length}`,
      `Δ${transition.changedEntityIds.length}`,
    ].join(" · ");
  }

  revisionSelect.addEventListener("change", () => {
    globalThis.location.hash = `revision=${encodeURIComponent(revisionSelect.value)}`;
    globalThis.location.reload();
  });
})();
