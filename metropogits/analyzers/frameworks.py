"""Import-bound framework identities, not name/suffix-based service guessing."""

from collections import Counter, defaultdict
import re

from .common import AnalysisError, GraphWriter, read_source
from .lexical import qualified, tokenize
from metropogits.catalog import load_bundled_catalog

EXTRACTOR = "framework-bindings/0.1"
MAX_BINDINGS = 2048


def _js_bindings(tokens):
    bindings = {}
    providers = []
    for i, token in enumerate(tokens):
        if token.kind != "IDENT":
            continue
        if (
            token.value == "import"
            and i + 1 < len(tokens)
            and tokens[i + 1].value not in {"(", "."}
        ):
            if tokens[i + 1].kind == "STRING":
                providers.append((tokens[i + 1].value, token.line))
                continue
            end = i + 1
            while end < min(len(tokens) - 1, i + 256) and tokens[end].value not in {
                "from",
                ";",
            }:
                end += 1
            if (
                end >= len(tokens) - 1
                or tokens[end].value != "from"
                or tokens[end + 1].kind != "STRING"
            ):
                continue
            provider = tokens[end + 1].value
            providers.append((provider, token.line))
            if tokens[i + 1].value == "type":
                continue
            j = i + 1
            if tokens[j].kind == "IDENT":
                bindings[tokens[j].value] = provider + ".default"
                j += 1
            while j < end:
                if (
                    tokens[j].value == "*"
                    and j + 2 < end
                    and tokens[j + 1].value == "as"
                ):
                    bindings[tokens[j + 2].value] = provider
                    j += 3
                elif tokens[j].kind == "IDENT" and tokens[j].value not in {
                    "type",
                    "as",
                }:
                    name = tokens[j].value
                    alias = (
                        tokens[j + 2].value
                        if j + 2 < end and tokens[j + 1].value == "as"
                        else name
                    )
                    bindings[alias] = provider + "." + name
                    j += 3 if alias != name else 1
                else:
                    j += 1
        elif (
            token.value == "require"
            and i >= 2
            and i + 3 < len(tokens)
            and tokens[i - 1].value == "="
            and tokens[i - 2].kind == "IDENT"
            and tokens[i + 1].value == "("
            and tokens[i + 2].kind == "STRING"
            and tokens[i + 3].value == ")"
        ):
            provider = tokens[i + 2].value
            providers.append((provider, token.line))
            bindings[tokens[i - 2].value] = provider + ".default"
    return bindings, providers


def _blocked_names(tokens, bindings, language):
    blocked = set()
    for i, token in enumerate(tokens):
        if token.kind != "IDENT" or token.value not in bindings:
            continue
        previous = tokens[i - 1].value if i else ""
        following = tokens[i + 1].value if i + 1 < len(tokens) else ""
        if previous in {
            "class",
            "interface",
            "object",
            "struct",
            "enum",
            "trait",
            "protocol",
            "def",
            "function",
            "fn",
            "fun",
        }:
            blocked.add(token.value)
        if following == "=" and previous not in {"using", "as"}:
            # The CommonJS declaration is the binding, not a reassignment.
            if not (
                language == "javascript"
                and i + 2 < len(tokens)
                and tokens[i + 2].value == "require"
            ):
                blocked.add(token.value)
        if (
            language == "go"
            and following != "."
            and i + 1 < len(tokens)
            and tokens[i + 1].kind != "STRING"
        ):
            blocked.add(token.value)
    # Function/method parameter shadows invalidate the file-wide binding. This
    # deliberately under-classifies rather than inventing scope/type resolution.
    stack = []
    for i, token in enumerate(tokens):
        if token.value == "(":
            stack.append(i)
        elif token.value == ")" and stack:
            start = stack.pop()
            tail = i + 1
            if tail < len(tokens) and tokens[tail].value == ":":
                while tail < len(tokens) and tokens[tail].value not in {"{", ";", "="}:
                    tail += 1
            is_definition = tail < len(tokens) and (
                tokens[tail].value == "{"
                or (
                    tokens[tail].value == "="
                    and tail + 1 < len(tokens)
                    and tokens[tail + 1].value == ">"
                )
            )
            if is_definition:
                for position in range(start + 1, i):
                    t = tokens[position]
                    if t.kind != "IDENT" or t.value not in bindings:
                        continue
                    if tokens[position + 1].value in {".", ":", "\\"} or tokens[
                        position - 1
                    ].value in {".", ":", "\\"}:
                        continue
                    if (
                        language in {"java", "csharp"}
                        and tokens[position + 1].kind == "IDENT"
                    ):
                        continue
                    blocked.add(t.value)
    return blocked


def _usage_facts(writer, path, language, tokens, bindings, namespaces, declared):
    facts = []
    relevant = {
        (s["kind"], s["value"])
        for rule in load_bundled_catalog()["rules"]
        for s in rule["match"]["codeSignatures"]
    }
    emitted = set()
    bindings = {
        name: identity
        for name, identity in bindings.items()
        if name not in _blocked_names(tokens, bindings, language)
    }
    declared = set(declared)
    inferred = set()

    def remember(line, kind, identity):
        value = language + ":" + identity
        key = (line, kind, value)
        if (kind, value) not in relevant or key in emitted:
            return
        emitted.add(key)
        if len(facts) >= 4096:
            raise AnalysisError("framework fact limit")
        facts.append(
            writer.fact(
                path,
                line,
                kind,
                value,
                inferred=identity in inferred,
            )
        )

    def identities(name):
        first, _, tail = name.partition(".")
        if first in declared:
            return []
        if first in bindings:
            identity = bindings[first]
            if language == "javascript" and tail and identity.endswith(".default"):
                identity = identity[:-8]
            return [identity + ("." + tail if tail else "")]
        candidates = [
            name if name.startswith(provider + ".") else provider + "." + name
            for provider in namespaces
        ]
        inferred.update(identity for identity in candidates if identity != name)
        return candidates

    for i, token in enumerate(tokens):
        if token.kind != "IDENT" or (i and tokens[i - 1].value in {".", ":", "\\"}):
            continue
        name, end = qualified(tokens, i, (".", ":", "\\"))
        if end < len(tokens) and tokens[end].value == "(":
            kind = "ANNOTATION" if i and tokens[i - 1].value == "@" else "CALL"
            for identity in identities(name):
                remember(token.line, kind, identity)
        elif i and tokens[i - 1].value == "@":
            for identity in identities(name):
                remember(token.line, "ANNOTATION", identity)
        elif language == "csharp" and i and tokens[i - 1].value == "[":
            for identity in identities(name):
                remember(token.line, "ANNOTATION", identity)
        if language == "go" and "." in name:
            for identity in identities(name):
                remember(token.line, "AST", identity)
    # Class/interface conformance is syntactic inheritance, not runtime service use.
    for i, token in enumerate(tokens[:-1]):
        if token.value not in {"class", "struct", "interface", "object", "enum"}:
            continue
        j = i + 2
        while j < min(len(tokens), i + 96) and tokens[j].value not in {"{", ";"}:
            if tokens[j].value == "<" and language != "ruby":
                depth = 1
                j += 1
                while j < min(len(tokens), i + 96) and depth:
                    depth += (tokens[j].value == "<") - (tokens[j].value == ">")
                    j += 1
                continue
            if tokens[j].value in {"extends", "implements", ":"} or (
                tokens[j].value == "<" and language == "ruby"
            ):
                j += 1
                while j < len(tokens) and tokens[j].value in {
                    "public",
                    "protected",
                    "private",
                }:
                    j += 1
                if j < len(tokens):
                    name, end = qualified(tokens, j, (".", ":", "\\"))
                    for identity in identities(name):
                        remember(tokens[j].line, "INHERITANCE", identity)
                    j = max(j, end)
            j += 1
            if language == "ruby" and j < len(tokens) and tokens[j].line > token.line:
                break
    return facts


def enrich_framework_graph(root, scan, graph, limits):
    # Import here to keep module adapters independent of framework rule loading.
    from .java import _parse_unit, _mask_non_code
    from .jsts import _tokenize, _external_package_path
    from .component_scripts import script_source, component_line
    from .jsx_regions import code_without_jsx
    from .polyglot import (
        LANGUAGES,
        ECOSYSTEMS,
        references,
        without_rust_macros,
        _declarations,
    )

    writer = GraphWriter(graph, EXTRACTOR)
    imports = defaultdict(set)
    for edge in graph["edges"]:
        if (
            edge["type"] == "IMPORTS"
            and writer.entities[edge["to"]]["kind"] == "EXTERNAL_PACKAGE"
        ):
            imports[edge["from"]].add(writer.entities[edge["to"]]["path"])
    processed = Counter()
    skipped = {
        d.get("sourcePath")
        for d in graph["diagnostics"]
        if d["code"].endswith("_ANALYSIS_SKIPPED")
    }
    for source in scan.files:
        language = source.language
        if language == "python" or source.path in skipped:
            continue  # Python already supplies its stronger AST-bound identities.
        if language not in LANGUAGES | {
            "java",
            "javascript",
            "typescript",
            "vue",
            "svelte",
        }:
            continue
        path = source.path
        try:
            text = read_source(root, source, limits.max_file_bytes)
            facts, namespaces, bindings, declared = [], [], {}, []
            allowed = imports[writer.files[path]["id"]]
            if language == "java":
                unit = _parse_unit(path, writer.files[path]["id"], text)
                tokens = tokenize(_mask_non_code(text), "java")
                declared = [t.name for t in unit.types]
                for declaration in unit.types:
                    if declaration.kind == "RECORD":
                        facts.append(
                            writer.fact(path, declaration.line, "AST", "java:record")
                        )
                providers = [
                    (r.name, r.name.rsplit(".", 1)[-1], r.line)
                    for r in unit.imports
                    if not r.name.endswith(".*")
                    and r.name.rsplit(".", 1)[0].replace(".", "/") in allowed
                ]
                for provider, alias, line in providers:
                    bindings[alias] = provider
                    facts.append(writer.fact(path, line, "IMPORT", "java:" + provider))
                if re.search(
                    r"\bstatic\s+void\s+main\s*\(\s*(?:java\.lang\.)?String\b",
                    unit.masked_source,
                ):
                    match = re.search(r"\bstatic\s+void\s+main\b", unit.masked_source)
                    facts.append(
                        writer.fact(
                            path,
                            unit.masked_source.count("\n", 0, match.start()) + 1,
                            "AST",
                            "java:main",
                        )
                    )
            elif language in {"javascript", "typescript", "vue", "svelte"}:
                original_language = language
                if language in {"vue", "svelte"}:
                    source_line = component_line(text, language)
                    text = script_source(text)
                    # The language-specific component file plus real script data
                    # is a source-format fact, not an invented external facility.
                    if source_line is not None:
                        facts.append(
                            writer.fact(
                                path, source_line, "AST", language + ":component"
                            )
                        )
                tokens, jsx_regions = code_without_jsx(_tokenize(text))
                raw_bindings, providers = _js_bindings(tokens)
                providers = [
                    (p, line)
                    for p, line in providers
                    if _external_package_path(p) in allowed
                ]
                provider_names = {p for p, _ in providers}
                bindings = {
                    name: identity
                    for name, identity in raw_bindings.items()
                    if any(
                        identity == p or identity.startswith(p + ".")
                        for p in provider_names
                    )
                }
                for provider, line in providers:
                    facts.append(
                        writer.fact(path, line, "IMPORT", "javascript:" + provider)
                    )
                # JSX is UI syntax, not automatically React (Preact etc. exist).
                if original_language in {
                    "javascript",
                    "typescript",
                } and source.path.endswith((".jsx", ".tsx")):
                    if jsx_regions:
                        facts.append(
                            writer.fact(
                                path, jsx_regions[0][0], "AST", "javascript:jsx"
                            )
                        )
                    # Don't mistake JSX text for executable calls/decorators.
                    bindings = {}
                language = "javascript"
            else:
                tokens = tokenize(text, language)
                if language == "rust":
                    tokens = without_rust_macros(tokens)
                _, declarations = _declarations(tokens, language)
                declared = [name for name, _ in declarations]
                refs = references(tokens, language)
                counts = Counter(ref.alias for ref in refs if ref.alias)
                for ref in refs:
                    name = ref.module.replace("\\", ".").replace(":", "/")
                    if f"{ECOSYSTEMS[language]}/{name}" not in allowed:
                        continue
                    facts.append(
                        writer.fact(
                            path, ref.line, "IMPORT", language + ":" + ref.module
                        )
                    )
                    if (
                        ref.alias
                        and counts[ref.alias] == 1
                        and ref.alias not in {"_", "."}
                    ):
                        bindings[ref.alias] = ref.module
                    if language in {"csharp", "swift", "dart", "ruby", "cpp", "c"}:
                        namespaces.append(ref.module)
                    if language in {"c", "cpp"} and "/" in ref.module:
                        short = ref.module.rsplit("/", 1)[-1]
                        facts.append(
                            writer.fact(
                                path, ref.line, "IMPORT", language + ":" + short
                            )
                        )
                        bindings[short] = short
                if language in {"go", "rust", "kotlin"} and any(
                    name == "main" for name, _ in declarations
                ):
                    if language != "go" or any(
                        t.value == "package"
                        and i + 1 < len(tokens)
                        and tokens[i + 1].value == "main"
                        for i, t in enumerate(tokens)
                    ):
                        line = next(
                            line for name, line in declarations if name == "main"
                        )
                        facts.append(writer.fact(path, line, "AST", language + ":main"))
            if len(bindings) > MAX_BINDINGS:
                raise AnalysisError("framework binding limit")
            if len(namespaces) > 64:
                raise AnalysisError("framework namespace limit")
            facts.extend(
                _usage_facts(
                    writer, path, language, tokens, bindings, namespaces, declared
                )
            )
            writer.claims(path, facts)
            processed[source.language] += 1
        except (OSError, UnicodeError, ValueError, RecursionError):
            writer.diagnostic(
                "FRAMEWORK_ANALYSIS_SKIPPED",
                "Framework binding subset unavailable; structural/import facts retained",
                path,
                "WARNING",
            )
    writer.diagnostic(
        "FRAMEWORK_ANALYZER_COVERAGE",
        "Imported-provider call/annotation/inheritance signatures only; not full framework or dynamic resolution",
        processedByLanguage=dict(sorted(processed.items())),
    )
    return writer.finish()
