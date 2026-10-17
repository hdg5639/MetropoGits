# Security policy

## Supported versions

MetropoGits has not published its first release. Security fixes currently
target the `main` branch only. This section will list supported release lines
when versioned packages are published.

## Report a vulnerability

Do not open a public issue for a suspected vulnerability. Use the repository's
[private security advisory form](https://github.com/hdg5639/MetropoGits/security/advisories/new)
and include:

- the affected revision and operating system;
- a minimal reproduction using non-sensitive fixture data;
- the expected and observed security boundary;
- potential impact, especially source disclosure or code execution; and
- any known workaround.

Do not include real credentials, private source code, or personal data. No
response deadline is promised before the first release; the maintainer will
coordinate disclosure and credit through the private advisory.

## Security boundaries

The default pipeline must never execute analyzed repository code, install its
dependencies, follow escaping symlinks, or publish generated metadata. Reports
about path traversal, secret exposure, viewer injection, unbounded resource
use, workflow privilege escalation, or supply-chain substitution are in scope.
Incorrect technology classification without a security impact belongs in the
normal issue tracker after the project begins accepting public reports.
