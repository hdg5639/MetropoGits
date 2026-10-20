# Static analysis support — 2026-10-20

This matrix describes implemented subsets, not complete language compilers or
whole-framework compatibility. The engine never runs a target repository or
installs its dependencies. Unknown files remain structural buildings.

## Language tiers

| Language | Actual analysis | Important limits |
| --- | --- | --- |
| Python | stdlib AST; declarations, local/relative imports, explicit imported references and inheritance, imported call/decorator identities | Host Python grammar; no execution, star re-exports or dynamic dispatch; shadowed names withheld |
| Java | Existing lexical declarations, imports, type references and inheritance; imported annotations/calls, records and main | Not JavaParser or compiler type binding; wildcard/overload resolution remains bounded |
| JavaScript / TypeScript | Static ESM/CommonJS imports and configured aliases; imported calls/decorators; JSX source format | No TypeScript compiler; JSX text/embedded expression subtrees omitted from lexical matching and disclosed |
| Vue / Svelte | Actual script blocks with original lines; static imports and component source-format evidence | No template expression compiler or runtime component dispatch |
| Go | go.mod scope, package imports, unique exported member-to-file references, declarations | Multi-file package import does not imply an edge to every file; no full Go type checking |
| Rust | mod/use trees, crate/self/super paths and aliases, declarations | No macro expansion; macro token trees excluded; ambiguous exports unresolved |
| C / C++ | Explicit include paths, declarations, qualified imported calls and syntactic inheritance | No preprocessor/build execution or guessed include directories; .h remains conservatively C without compiler context |
| C# / Kotlin / Scala | Explicit namespaces/imports and declarations; supported exact type paths | Not compiler binding, implicit project/global imports or complete overload resolution |
| PHP / Ruby / Swift / Dart / Lua | Explicit use/require/import subsets and declarations | Dynamic loaders, metaprogramming and unsupported package configuration remain unresolved |
| Other scanned languages | Structural directories/files and safe generic buildings | No invented semantic role or relationship |

There are 18 processed language labels, including Vue/Svelte and separate C/C++.
"Processed" is not the percentage of symbols correctly bound. Coverage diagnostics,
unresolved edges and skipped-file diagnostics remain part of the output.

## Framework/library evidence

Bundled catalog **0.5.0** contains 158 rules and 122 technology labels (including
standards/source formats). 142 imported-provider usage profiles plus nine explicit
source-format rules extend the seven preserved legacy rules. Each new rule has
positive and near-match negative fact fixtures; every imported-use profile is
also exercised through actual source syntax in `test_framework_bindings.py`.

| Ecosystem | Tested source-signature families |
| --- | --- |
| Python web / models | FastAPI, Flask, Starlette, Django, Django REST Framework, Pydantic, dataclasses |
| Python data / tasks | SQLAlchemy, Redis, PyMongo/Motor, Celery, Minio, Elasticsearch |
| Python tools / compute | Click, Typer, argparse, unittest, pytest, NumPy, pandas, PyTorch, TensorFlow, Streamlit, Gradio |
| Python HTTP / auth | Requests, HTTPX, aiohttp, Passlib |
| JVM | Existing Spring; Jakarta REST/Servlet/Inject, Micronaut, Guice, Dagger, JUnit4/Jupiter, TestNG, picocli, JDBC, HttpClient, JavaFX, Swing, Ktor |
| JS UI / state | React/ReactDOM, Vue, Svelte, JSX, Angular, Redux, Pinia |
| JS server / data | Express, Fastify, Hono, Koa, Nest, TypeORM, Prisma, Mongoose, Sequelize |
| JS adapters / tests | Redis/ioredis, Axios, KafkaJS, amqplib, BullMQ, Passport, Vitest, Jest, Playwright |
| Go | net/http, Gin, Echo, Fiber, Chi, GORM, database/sql, Redis, Cobra, testing |
| Rust | Axum, Actix, Clap, SQLx, Reqwest, Redis, SeaORM, Ratatui |
| .NET | ASP.NET ControllerBase/WebApplication/Authorize, EF DbContext, xUnit, NUnit |
| PHP / Ruby | Laravel Controller/Eloquent, Symfony, PHPUnit; Sinatra, ActiveRecord, Minitest |
| Swift / Dart | SwiftUI, XCTest, Vapor; Flutter, flutter_test, Dio |
| Native | Qt Widgets/SQL, SQLite, GoogleTest |

The exact identifiers and supported call/annotation/inheritance forms are in
`catalog/0.5.0/catalog.json`, not inferred from this marketing-sized list.
An import/dependency alone never creates a service/database/test facility.
Imported-namespace candidate matches (where lexical binding is ambiguous) are
explicitly INFERRED, not disguised as compiler-resolved DIRECT facts.

Plain Java main/record and Python main/dataclass work without Spring. A source
format can prove UI structure without pretending it proves React. No call graph,
HTTP destination, broker topic or database instance is invented from a role.

## Manifests and reproducibility

Existing Maven/Gradle/npm support is joined by bounded pyproject/requirements,
Cargo, go.mod, NuGet, Composer, literal Gemfile and simple pubspec dependencies.
Remote requirements/includes/build hooks are not followed. Unparsed constructs
are disclosed. Source IDs and UCG0.1/City0.2 contracts are unchanged. Catalog0.1
and all prior catalog releases stay immutable; additive catalog0.2 is ADR-055.

Real corpus measurements and limitations are recorded in QUALITY_LOG.md. Tests
for small signatures do not demonstrate whole-framework correctness. C++ include
search paths, implicit framework imports and dynamic registrations are major
remaining coverage gaps. Unsupported syntax is not papered over with fake roles.
