# MetropoGits Stable IDs 0.1

This document fixes the v0.1 identity procedure used by UCG producers.

## Repository IDs

A portable repository ID SHOULD be supplied explicitly as a namespace such as
`openai/metropogits`. It is case-sensitive, uses `/` separators, and each
segment contains only ASCII letters, digits, `.`, `_`, `~`, or `-`. Empty,
absolute, drive-qualified, and traversal namespaces are rejected.

When no portable namespace exists, a local ID MAY be derived as
`local-sha256-<16 lowercase hex characters>` from the resolved, host-normalized
root path. The absolute path itself is never emitted. This fallback is stable
for the same local root, but callers need an explicit namespace for portable
IDs across machines.

## Entity IDs

Relative paths are Unicode NFC-normalized, use `/`, reject traversal and
absolute paths, and collapse empty or `.` segments. Each path segment is then
UTF-8 percent-encoded with only RFC 3986 unreserved characters left literal.

```text
{repoId}:{lowercase-kind}:{encoded/relative/path}[#{encodedQualifiedSymbol}]
```

Qualified symbols are required only for `SYMBOL` entities. v0.1 renames create
new entity IDs.

## Edge IDs

The tuple `[sourceId, edgeType, targetId, canonicalDiscriminator]` is encoded
with `metropogits-json/0.1`, hashed with SHA-256, and emitted as:

```text
edge:sha256:<64 lowercase hex characters>
```

The discriminator is an explicit deterministic string and defaults to empty.
Changing direction, edge kind, target, or discriminator changes the ID.
