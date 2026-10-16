# GitHub Action and Pages publishing

MetropoGits ships a composite Action that builds the same static artifacts as
the local CLI. It installs the released Action code into an isolated runner
environment and never invokes the analyzed repository's build, package hooks,
or source files.

## Install

1. Copy [`examples/github-pages.yml`](../examples/github-pages.yml) to
   `.github/workflows/metropogits.yml` in the repository to analyze.
2. Replace `hdg5639/MetropoGits@v0.1.0` with the immutable release version or
   full commit SHA selected for that repository. The example tag is the planned
   first release and is not available until the release is published.
3. In repository settings, select **GitHub Actions** as the Pages source.
4. Run the workflow manually or push to `main`.

Pull requests use only `contents: read` and upload a private workflow artifact;
they do not receive Pages, identity-token, or deployment permissions. The
separate deployment job receives those permissions only for pushes to `main`
and explicit manual runs. Checkout credentials are not persisted.

## Action inputs

The common inputs are:

- `repository`: source directory below `GITHUB_WORKSPACE`, default `.`.
- `output`: artifact directory below `GITHUB_WORKSPACE`, default
  `metropogits-dist`.
- `theme`: city theme, default `minimal`.
- `repo-id`, `revision`, `source-url`: optional provenance overrides; GitHub
  context values are used by default.
- `max-entries`, `max-files`, `max-file-bytes`, `max-total-bytes`, and
  `max-depth`: scanner resource bounds.

Repository and output inputs are confined to `GITHUB_WORKSPACE`. Absolute
paths, traversal outside the workspace, newline injection, and output at the
workspace root are rejected.

## README link

Publishing never edits the repository. After the first deployment, copy and
adapt the generated `README_SNIPPET.md` with the Pages URL, for example:

```markdown
[![MetropoGits city](https://OWNER.github.io/REPOSITORY/preview.svg)](https://OWNER.github.io/REPOSITORY/)
```

Generated metadata exposes filenames and architecture. Review the complete
artifact before enabling Pages, especially for private repositories.

## Pinned workflow dependencies

The template pins every GitHub-maintained Action to a full commit SHA and keeps
the human-readable release beside it. Review and update both together. The
current pins are `actions/checkout` v7.0.1, `actions/setup-python` v7.0.0,
`actions/upload-artifact` v7.0.2, `actions/upload-pages-artifact` v5.0.0, and
`actions/deploy-pages` v5.0.1.
