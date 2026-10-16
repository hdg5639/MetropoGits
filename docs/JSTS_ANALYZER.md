# JavaScript and TypeScript analyzer

The bundled JS/TS adapter performs bounded static module analysis. It reads
scanner-approved UTF-8 files and never invokes Node.js, package managers,
transpilers, repository scripts, or imported modules.

## Supported evidence

The adapter recognizes literal module specifiers in:

- ESM `import` declarations and side-effect imports;
- ESM `export ... from` re-exports;
- dynamic `import("...")` calls with a plain string literal;
- direct CommonJS `require("...")` calls with a plain string literal.

Relative specifiers become `RESOLVED` `IMPORTS` edges only when they match one
scanned JS/TS file unambiguously. Extensionless paths and directory `index`
files are compared against a fixed extension set and must yield exactly one
match. Bare specifiers create `DIRECT` facts for the referenced npm package
namespace; they do not prove that the dependency is installed, initialized, or
used successfully at runtime.

Supported extensions are `.js`, `.jsx`, `.mjs`, `.cjs`, `.ts`, `.tsx`, `.mts`,
and `.cts`.

## Deliberate limits

This first adapter does not interpret `tsconfig.json` aliases, package export
maps, bundler aliases, URL imports, `#` package imports, escaped specifiers, or
template-literal specifiers. It does not infer framework roles, calls, runtime
traffic, or technology usage from package names.

An ambiguous local path produces `JSTS_IMPORT_AMBIGUOUS`; an unsupported or
missing target produces `JSTS_IMPORT_UNRESOLVED`. Malformed source is isolated
to its file with `JSTS_ANALYSIS_SKIPPED`, while safe files continue through the
pipeline. `JSTS_ANALYZER_COVERAGE` records the adapter capability level in the
UCG diagnostics.
