# History replay

History replay combines two or more previously generated MetropoGits build
directories into a deterministic static timeline. Each input must contain
`graph.ucg.json` and `city.json`, and its UCG must have a non-empty, unique
repository revision.

Build snapshots in chronological order, then combine them:

```powershell
python -m metropogits build --repo path/to/repo --repo-id owner/project --revision rev-a --out dist/rev-a
python -m metropogits build --repo path/to/repo --repo-id owner/project --revision rev-b --out dist/rev-b
python -m metropogits history --snapshot dist/rev-a --snapshot dist/rev-b --out dist/history
```

Open `dist/history/index.html` and use the revision selector. The viewer reports
added, removed, and semantically changed buildings for each adjacent revision.
It remains a `file:`-compatible static artifact and does not execute repository
code or contact a remote service.

## Identity and lineage

Timeline `history/0.1` uses the stable UCG entity ID as its continuity key and
adds a deterministic lineage ID. Changes compare the entity's semantic facts,
its visual archetype, and its evidenced graph edges; raw source text is not
stored or compared.

A rename changes the v0.1 entity ID, so it appears as one removal and one
addition. MetropoGits deliberately does not guess that similarly shaped or
similarly named files are the same file. Future explicit alias records can link
verified renames without changing the baseline UCG identity contract.

The output contains `history.json`, the static viewer assets, and canonical
copies of every input graph and scene under `revisions/000`, `revisions/001`,
and so on. Frame digests bind the timeline to those exact source artifacts.
