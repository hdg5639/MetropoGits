# Path-derived semantic rules

MetropoGits may attach a direct semantic claim when a source file has an exact,
documented framework or test path convention. These rules inspect normalized
repository-relative paths only. They do not execute source files, inspect file
contents, infer runtime behavior, or turn nearby files into matches.

## Current rules

| Rule | Exact condition | Claims | City form |
| --- | --- | --- | --- |
| `path.nextjs.app-page` | TypeScript `page.tsx` below a directory segment named `app` | `NEXT_JS`, `UI_PAGE`, `UI` | `GATE` |
| `path.nextjs.route-handler` | TypeScript `route.ts` below a directory segment named `app` | `NEXT_JS`, `API_ENDPOINT`, `API` | `PORT` |
| `path.test-source` | Java below `src/test/java`, or JS/TS below `__tests__`, or a JS/TS filename containing `.test.` or `.spec.` | `TEST` role and capability | `LIBRARY` |

Every claim has `DIRECT` confidence and references one `PATH` evidence record
with its source path and rule ID. The path is evidence of the conventional
source role, not evidence that the file executes successfully or receives
production traffic.

## Conservative exclusions

- `application/page.tsx` does not match the Next.js App Router rule.
- `route.tsx` does not match the exact `route.ts` handler rule.
- `src/main/java/**/SomethingTest.java` is not treated as a Java test solely
  because of its filename.
- A directory named `testing` is not interchangeable with `__tests__`.

Positive and negative repository fixtures lock these boundaries. Unsupported
framework paths remain ordinary structural buildings.
