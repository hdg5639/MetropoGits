# Multi-repository metropolis

MetropoGits can combine two or more completed build directories into one
inspectable metropolis. Each repository remains a distinct city, while an
explicit link manifest controls which cross-repository relationships are drawn.

The composer does not infer service-to-service links. A `VERIFIED` link must
name existing `FILE` entities in two different repositories and reference
evidence already present in a member UCG. An `UNRESOLVED` link records a known
external dependency without inventing a target entity; it appears in the
viewer and diagnostics, but no graph edge or city network is generated for it.

## Link manifest

Create a `metropolis-links/0.1` JSON document. Link IDs and evidence references
must be in canonical ascending order.

```json
{
  "links": [
    {
      "evidenceRefs": [
        {
          "evidenceId": "evidence-id-from-api-ucg",
          "repositoryId": "example/api"
        }
      ],
      "from": {
        "entityId": "file-entity-id-from-api-ucg",
        "label": null,
        "repositoryId": "example/api"
      },
      "id": "api.calls.worker",
      "status": "VERIFIED",
      "to": {
        "entityId": "file-entity-id-from-worker-ucg",
        "label": null,
        "repositoryId": "example/worker"
      },
      "type": "HTTP_CALL"
    },
    {
      "evidenceRefs": [
        {
          "evidenceId": "another-api-evidence-id",
          "repositoryId": "example/api"
        }
      ],
      "from": {
        "entityId": "another-api-file-entity-id",
        "label": null,
        "repositoryId": "example/api"
      },
      "id": "api.search.unknown",
      "status": "UNRESOLVED",
      "to": {
        "entityId": null,
        "label": "search-service",
        "repositoryId": null
      },
      "type": "HTTP_CALL"
    }
  ],
  "schemaVersion": "metropolis-links/0.1"
}
```

Supported link types are `HTTP_CALL`, `PUBLISHES`, and `SUBSCRIBES`.

Validate the manifest before composing:

```powershell
python -m metropogits validate --input metropolis-links.json
```

## Build

First build every member repository separately. Repository IDs must be unique.

```powershell
python -m metropogits build --repo path/to/api --repo-id example/api --out dist/api
python -m metropogits build --repo path/to/worker --repo-id example/worker --out dist/worker
```

Then compose the member directories:

```powershell
python -m metropogits metropolis `
  --member dist/api `
  --member dist/worker `
  --links metropolis-links.json `
  --out dist/metropolis
```

Member argument order does not affect the result. The composer sorts members by
repository ID, namespaces their evidence records, and places the cities on a
deterministic grid. It rejects missing repositories, entities, or evidence and
also rejects an output directory that overlaps a member directory.

The output contains:

- `metropolis.json`: repositories, explicit links, and merged artifact digests
- `graph.ucg.json`: merged UCG plus verified cross-repository edges
- `city.json`: merged scene plus verified cross-repository networks
- `index.html` and `assets/`: offline viewer with repository and link status UI

The viewer preserves each member repository's source URL and revision when it
constructs source links. Open `dist/metropolis/index.html` directly; no server
is required.
