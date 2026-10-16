# CLI result contract

MetropoGits distinguishes a complete result, a usable partial result, an input
failure, a configured resource limit, and an unexpected internal failure. The
same codes apply to human-readable and JSON output.

| Code | Name | Meaning |
|---:|---|---|
| `0` | Complete | The command completed without warning or error diagnostics. |
| `1` | Partial | Usable output was written, but one or more inputs were safely skipped. |
| `2` | Invalid input | Arguments, paths, contracts, or requested options were invalid. |
| `3` | Resource limit | Usable partial output was written after a configured scan limit was reached. |
| `4` | Internal error | An unexpected implementation failure prevented a reliable result. |

Codes `1` and `3` can accompany valid artifacts. Callers that accept partial
analysis should inspect `manifest.json` before deciding whether to continue.
The manifest includes deterministic counts by diagnostic code as well as its
`COMPLETE` or `PARTIAL` status.

## Structured CI output

Pass `--json` before or after the command to emit exactly one JSON result:

```bash
metropogits build --repo . --out dist --json
```

A successful or partial result includes `command`, `status`, `exitCode`,
`message`, `output`, and, where available, a diagnostic summary. A failure uses
the same envelope and adds an `error` object with a stable category:

```json
{"command":"build","error":{"category":"INVALID_INPUT","message":"repository root does not exist"},"exitCode":2,"status":"FAILED"}
```

The JSON record contains no timestamps or raw source contents. Unexpected
internal failures report only the exception class rather than arbitrary
exception text, reducing the chance of leaking repository data into CI logs.
