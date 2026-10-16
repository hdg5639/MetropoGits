(() => {
  "use strict";

  const metropolis = globalThis.METROPOGITS_METROPOLIS;
  if (!metropolis) return;
  const repositoryLabel = document.getElementById("metropolis-repositories");
  const linkSelect = document.getElementById("metropolis-link");
  const summary = document.getElementById("metropolis-link-summary");
  if (!repositoryLabel || !linkSelect || !summary) return;

  const verifiedCount = metropolis.links.filter((link) => link.status === "VERIFIED").length;
  const unresolvedCount = metropolis.links.length - verifiedCount;
  repositoryLabel.textContent = `${metropolis.repositories.length} repositories`;

  if (!metropolis.links.length) {
    const option = document.createElement("option");
    option.textContent = "No declared links";
    option.value = "";
    linkSelect.append(option);
    linkSelect.disabled = true;
    summary.textContent = "0 verified · 0 unresolved";
    return;
  }

  for (const link of metropolis.links) {
    const option = document.createElement("option");
    const target = link.to.repositoryId || link.to.label;
    option.value = link.id;
    option.textContent = `${link.status} · ${link.type} · ${link.from.repositoryId} → ${target}`;
    linkSelect.append(option);
  }

  function showLink() {
    const link = metropolis.links.find((item) => item.id === linkSelect.value);
    if (!link) return;
    const target = link.to.entityId || link.to.label;
    const evidence = link.evidenceRefs
      .map((item) => `${item.repositoryId}:${item.evidenceId}`)
      .join(", ");
    summary.textContent = `${link.status} · ${target} · ${evidence}`;
  }

  linkSelect.addEventListener("change", showLink);
  showLink();
  repositoryLabel.title = `${verifiedCount} verified · ${unresolvedCount} unresolved`;
})();
