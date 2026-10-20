"""Explicit module syntax across ecosystems; lexical coverage, not full compilers."""

from collections import defaultdict
from dataclasses import dataclass
from pathlib import PurePosixPath
import posixpath
import re

from scripts.stable_ids import make_entity_id
from .common import AnalysisError, GraphWriter, read_source
from .lexical import qualified, tokenize

LANGUAGES = frozenset(
    {
        "go",
        "rust",
        "c",
        "cpp",
        "csharp",
        "kotlin",
        "scala",
        "php",
        "ruby",
        "swift",
        "dart",
        "lua",
    }
)
EXTRACTOR = "polyglot-lexical/0.1"
MAX_REFERENCES = 2048
MAX_WORK = 2_000_000
ECOSYSTEMS = dict(
    go="go",
    rust="cargo",
    c="native",
    cpp="native",
    csharp="nuget",
    kotlin="jvm",
    scala="jvm",
    php="composer",
    ruby="rubygems",
    swift="swift",
    dart="pub",
    lua="lua",
)


@dataclass(frozen=True)
class Reference:
    module: str
    alias: str
    line: int
    syntax: str = "import"


def _rust_use(tokens, start):
    """Expand bounded literal use trees; globs/macros remain unresolved."""
    out = []
    i = start

    def branch(prefix, depth):
        nonlocal i
        if depth > 32 or len(out) > 512:
            raise AnalysisError("Rust use-tree limit")
        names = list(prefix)
        while i < len(tokens):
            value = tokens[i].value
            if value == "{":
                i += 1
                while i < len(tokens) and tokens[i].value != "}":
                    branch(names, depth + 1)
                    if i < len(tokens) and tokens[i].value == ",":
                        i += 1
                if i >= len(tokens):
                    raise AnalysisError("unterminated Rust use tree")
                i += 1
                return
            if value in {",", ";", "}"}:
                break
            if value == "as":
                i += 1
                alias = tokens[i].value if i < len(tokens) else ""
                i += 1
                out.append((".".join(names), alias))
                return
            if tokens[i].kind == "IDENT" or value == "*":
                names.append(value)
            elif value != ":":
                raise AnalysisError("unsupported Rust use expression")
            i += 1
        if names:
            if names[-1] == "self":
                names.pop()
            if names:
                out.append((".".join(names), names[-1]))

    branch([], 0)
    return out


def references(tokens, language):
    result = []
    shadow_require = language in {"lua", "ruby"} and any(
        t.value in {"require", "require_relative"}
        and i
        and tokens[i - 1].value in {"local", "function", "def"}
        for i, t in enumerate(tokens)
    )
    for i, token in enumerate(tokens):
        value = token.value
        if token.kind != "IDENT":
            continue
        next_token = tokens[i + 1] if i + 1 < len(tokens) else None
        if not next_token:
            continue
        if language == "go" and value == "import":
            if next_token.value == "(":
                j = i + 2
                while j < len(tokens) and tokens[j].value != ")":
                    if tokens[j].kind == "STRING":
                        alias = (
                            tokens[j - 1].value
                            if tokens[j - 1].kind == "IDENT"
                            else tokens[j].value.rsplit("/", 1)[-1]
                        )
                        result.append(Reference(tokens[j].value, alias, tokens[j].line))
                    j += 1
            else:
                j = i + 1
                alias = ""
                if tokens[j].kind == "IDENT":
                    alias = tokens[j].value
                    j += 1
                if j < len(tokens) and tokens[j].kind == "STRING":
                    result.append(
                        Reference(
                            tokens[j].value,
                            alias or tokens[j].value.rsplit("/", 1)[-1],
                            token.line,
                        )
                    )
        elif language == "rust" and value == "use":
            for module, alias in _rust_use(tokens, i + 1):
                result.append(Reference(module, alias, token.line))
        elif (
            language == "rust"
            and value == "mod"
            and next_token.kind == "IDENT"
            and i + 2 < len(tokens)
            and tokens[i + 2].value == ";"
        ):
            result.append(
                Reference(next_token.value, next_token.value, token.line, "mod")
            )
        elif (
            language in {"c", "cpp"}
            and value == "include"
            and i
            and tokens[i - 1].value == "#"
        ):
            if next_token.kind == "STRING":
                result.append(
                    Reference(
                        next_token.value,
                        PurePosixPath(next_token.value).stem,
                        token.line,
                        "include-local",
                    )
                )
            elif next_token.value == "<":
                j = i + 2
                name = []
                while (
                    j < len(tokens)
                    and tokens[j].line == token.line
                    and tokens[j].value != ">"
                ):
                    name.append(tokens[j].value)
                    j += 1
                if j < len(tokens) and tokens[j].value == ">":
                    module = "".join(name)
                    result.append(
                        Reference(
                            module,
                            PurePosixPath(module).stem,
                            token.line,
                            "include-system",
                        )
                    )
        elif language in {"kotlin", "scala", "swift"} and value == "import":
            start = i + 1
            if language == "swift" and next_token.value in {
                "class",
                "struct",
                "func",
                "enum",
                "protocol",
            }:
                start += 1
            module, end = qualified(tokens, start)
            alias = module.rsplit(".", 1)[-1]
            if end + 1 < len(tokens) and tokens[end].value == "as":
                alias = tokens[end + 1].value
            if module:
                result.append(Reference(module, alias, token.line))
        elif language in {"php", "csharp"} and value == (
            "use" if language == "php" else "using"
        ):
            start = i + 1
            alias = ""
            if start + 1 < len(tokens) and tokens[start + 1].value == "=":
                alias = tokens[start].value
                start += 2
            if start < len(tokens) and tokens[start].value in {
                "function",
                "const",
                "static",
                "\\",
            }:
                start += 1
            module, end = qualified(tokens, start, (".", "\\"))
            if end + 1 < len(tokens) and tokens[end].value == "as":
                alias = tokens[end + 1].value
                end += 2
            if module and end < len(tokens) and tokens[end].value == ";":
                result.append(
                    Reference(module, alias or module.rsplit(".", 1)[-1], token.line)
                )
        elif (
            language == "dart"
            and value in {"import", "export"}
            and next_token.kind == "STRING"
        ):
            alias = ""
            if i + 3 < len(tokens) and tokens[i + 2].value == "as":
                alias = tokens[i + 3].value
            result.append(Reference(next_token.value, alias, token.line))
        elif (
            language in {"ruby", "lua"}
            and not shadow_require
            and value in {"require", "require_relative"}
            and (i == 0 or tokens[i - 1].value not in {".", ":", "def", "function"})
        ):
            start = i + 2 if next_token.value == "(" else i + 1
            if start < len(tokens) and tokens[start].kind == "STRING":
                result.append(Reference(tokens[start].value, "", token.line, value))
        if len(result) > MAX_REFERENCES:
            raise AnalysisError("module reference limit")
    return tuple(sorted(set(result), key=lambda r: (r.line, r.module, r.alias)))


def without_rust_macros(tokens):
    result = []
    i = 0
    while i < len(tokens):
        t = tokens[i]
        if t.value == "macro_rules":
            while i < len(tokens) and tokens[i].value not in {"{", "(", "["}:
                i += 1
        elif (
            t.value == "!"
            and i
            and tokens[i - 1].kind == "IDENT"
            and i + 1 < len(tokens)
            and tokens[i + 1].value in {"{", "(", "["}
        ):
            i += 1
        else:
            result.append(t)
            i += 1
            continue
        depth = 0
        while i < len(tokens):
            if tokens[i].value in {"{", "(", "["}:
                depth += 1
                if depth > 128:
                    raise AnalysisError("macro nesting limit")
            elif tokens[i].value in {"}", ")", "]"}:
                depth -= 1
                if depth == 0:
                    i += 1
                    break
            i += 1
        if depth:
            raise AnalysisError("unterminated macro")
    return tuple(result)


def _declarations(tokens, language):
    namespace = ""
    declarations = []
    for i, t in enumerate(tokens[:-1]):
        if t.value in {"namespace", "package"}:
            namespace, _ = qualified(tokens, i + 1, (".", "\\"))
        if (
            t.value
            in {
                "class",
                "interface",
                "struct",
                "enum",
                "trait",
                "object",
                "protocol",
                "type",
                "fn",
                "func",
                "fun",
                "function",
            }
            and tokens[i + 1].kind == "IDENT"
        ):
            declarations.append((tokens[i + 1].value, t.line))
    return namespace, declarations


def _relative(path, value):
    if value.startswith("/") or "\\" in value or ":" in value:
        return None
    result = posixpath.normpath(str(PurePosixPath(path).parent / value))
    return None if result.startswith("../") or result == ".." else result


def enrich_polyglot_graph(root, scan, graph, limits):
    writer = GraphWriter(graph, EXTRACTOR)
    units = {}
    for source in scan.files:
        if source.language not in LANGUAGES:
            continue
        try:
            text = read_source(root, source, limits.max_file_bytes)
            if source.language in {"php", "ruby"} and (
                "<<<" in text or re.search(r"<<[-~]?\s*['\"]?[A-Z]", text)
            ):
                raise AnalysisError("heredoc syntax is outside lexical subset")
            tokens = tokenize(text, source.language)
            if source.language == "rust":
                tokens = without_rust_macros(tokens)
            refs = references(tokens, source.language)
            namespace, declared = _declarations(tokens, source.language)
            units[source.path] = (source.language, tokens, refs, namespace, declared)
        except (OSError, UnicodeError, AnalysisError):
            writer.diagnostic(
                "POLYGLOT_ANALYSIS_SKIPPED",
                "Unsupported literal/syntax or lexical resource limit; structural file retained",
                source.path,
                "WARNING",
            )

    qualified_files = defaultdict(set)
    unit_paths = set(units)
    work = 0
    go_packages = defaultdict(set)
    for path, (language, _, _, namespace, declarations) in units.items():
        if language == "go" and not path.endswith("_test.go"):
            go_packages[str(PurePosixPath(path).parent)].add(path)
        for name, _ in declarations:
            qualified_files[
                (language, (namespace + "." if namespace else "") + name)
            ].add(path)

    for path, (language, tokens, refs, namespace, declarations) in sorted(
        units.items()
    ):
        source_id = writer.files[path]["id"]
        facts = []
        uses = defaultdict(list)
        go_shadowed = set()
        aliases = {ref.alias for ref in refs}
        for i, token in enumerate(tokens[:-2]):
            if token.kind == "IDENT" and tokens[i + 1].value == ".":
                uses[token.value].append((tokens[i + 2].value, token.line))
            elif (
                language == "go"
                and token.kind == "IDENT"
                and token.value in aliases
                and tokens[i + 1].kind != "STRING"
            ):
                go_shadowed.add(token.value)
        for name, line in declarations:
            writer.symbol(
                path, (namespace + "." if namespace else "") + name, line, line
            )
        for ref in refs:
            if (
                not re.fullmatch(r"[A-Za-z0-9_@+./:*\\-]+", ref.module)
                or len(ref.module) > 240
            ):
                writer.diagnostic(
                    "POLYGLOT_IMPORT_UNRESOLVED",
                    "Nonliteral or unsupported module identity",
                    path,
                )
                continue
            targets = set()
            local = False
            if "*" in ref.module:
                writer.diagnostic(
                    "POLYGLOT_IMPORT_UNRESOLVED",
                    "Wildcard module imports are not symbol-resolved",
                    path,
                )
                continue
            if language == "go":
                manifests = [
                    m
                    for m in scan.manifests
                    if m.format == "go"
                    and getattr(m, "namespace", None)
                    and (
                        str(PurePosixPath(m.path).parent) == "."
                        or path.startswith(str(PurePosixPath(m.path).parent) + "/")
                    )
                ]
                if manifests:
                    manifest = max(manifests, key=lambda m: len(m.path))
                    if ref.module == manifest.namespace or ref.module.startswith(
                        manifest.namespace + "/"
                    ):
                        local = True
                        suffix = ref.module[len(manifest.namespace) :].lstrip("/")
                        directory = str(PurePosixPath(manifest.path).parent / suffix)
                        targets = go_packages.get(directory, set())
            elif language == "rust":
                parts = ref.module.split(".")
                local = ref.syntax == "mod" or parts[0] in {"crate", "self", "super"}
                if local:
                    parent = PurePosixPath(path).parent
                    if ref.syntax != "mod" and PurePosixPath(path).stem not in {
                        "main",
                        "lib",
                        "mod",
                    }:
                        parent = parent / PurePosixPath(path).stem
                    if ref.syntax != "mod" and parts[0] == "crate":
                        cargo = [
                            m
                            for m in scan.manifests
                            if m.format == "cargo"
                            and (
                                str(PurePosixPath(m.path).parent) == "."
                                or path.startswith(
                                    str(PurePosixPath(m.path).parent) + "/"
                                )
                            )
                        ]
                        parent = (
                            PurePosixPath(
                                max(cargo, key=lambda m: len(m.path)).path
                            ).parent
                            / "src"
                            if cargo
                            else PurePosixPath("src")
                        )
                        parts.pop(0)
                    elif ref.syntax != "mod":
                        first = parts.pop(0)
                        if first == "super":
                            parent = parent.parent
                    elif PurePosixPath(path).stem not in {"main", "lib", "mod"}:
                        parent = parent / PurePosixPath(path).stem
                    for end in range(len(parts), 0, -1):
                        base = parent.joinpath(*parts[:end])
                        candidates = {str(base) + ".rs", str(base / "mod.rs")}
                        found = candidates & unit_paths
                        if end < len(parts):
                            found = {
                                p
                                for p in found
                                if any(name == parts[end] for name, _ in units[p][4])
                            }
                        if found:
                            targets = found
                            break
            elif language in {"c", "cpp"} and ref.syntax == "include-local":
                local = True
                candidate = _relative(path, ref.module)
                targets = {candidate} if candidate in units else set()
            elif language == "dart" and not ref.module.startswith(
                ("package:", "dart:")
            ):
                local = True
                candidate = _relative(path, ref.module)
                targets = {candidate} if candidate in units else set()
            elif language == "ruby" and ref.syntax == "require_relative":
                local = True
                candidate = _relative(path, ref.module)
                targets = {
                    p
                    for p in (candidate, (candidate + ".rb") if candidate else None)
                    if p in units
                }
            elif language == "lua":
                candidates = {
                    ref.module.replace(".", "/") + ".lua",
                    ref.module.replace(".", "/") + "/init.lua",
                }
                targets = candidates & unit_paths
                local = bool(targets)
            elif language in {"php", "csharp", "kotlin", "scala"}:
                targets = qualified_files.get((language, ref.module), set())
                local = bool(targets)
            proof = writer.proof(path, ref.line, "IMPORT", language + ":" + ref.module)
            if local:
                if len(targets) == 1:
                    writer.edge(
                        source_id,
                        writer.files[next(iter(targets))]["id"],
                        "IMPORTS",
                        proof,
                        ref.module,
                    )
                elif language == "go" and targets:
                    directory = str(PurePosixPath(sorted(targets)[0]).parent)
                    module_id = make_entity_id(
                        writer.repo,
                        "MODULE",
                        directory if directory != "." else "go.mod",
                    )
                    writer.entities.setdefault(
                        module_id,
                        dict(
                            id=module_id,
                            kind="MODULE",
                            path=directory if directory != "." else "go.mod",
                        ),
                    )
                    writer.edge(source_id, module_id, "IMPORTS", proof, ref.module)
                    # An imported Go package is NOT a dependency on every file.
                    for name, line in (
                        [] if ref.alias in go_shadowed else uses[ref.alias]
                    ):
                        work += sum(len(units[p][4]) for p in targets)
                        if work > MAX_WORK:
                            raise AnalysisError("polyglot reference work limit")
                        owners = {
                            p for p in targets if any(n == name for n, _ in units[p][4])
                        }
                        if len(owners) == 1:
                            evidence = writer.proof(
                                path,
                                line,
                                "AST",
                                language + ":" + ref.module + "." + name,
                            )
                            writer.edge(
                                source_id,
                                writer.files[next(iter(owners))]["id"],
                                "REFERENCES",
                                evidence,
                                ref.module + "." + name,
                            )
                else:
                    writer.diagnostic(
                        "POLYGLOT_IMPORT_UNRESOLVED",
                        "Local module missing or ambiguous; no guessed target",
                        path,
                    )
            else:
                name = ref.module.replace("\\", ".").replace(":", "/")
                target = writer.external(ECOSYSTEMS[language], name)
                writer.edge(source_id, target, "IMPORTS", proof, ref.module, "DIRECT")
                facts.append(
                    writer.fact(path, ref.line, "IMPORT", language + ":" + ref.module)
                )
        writer.claims(path, facts)

    for language in sorted(LANGUAGES):
        total = sum(s.language == language for s in scan.files)
        if total:
            parsed = sum(u[0] == language for u in units.values())
            writer.diagnostic(
                "POLYGLOT_ANALYZER_COVERAGE",
                "Lexical module/declaration analysis; no compiler binding, macro/preprocessor evaluation or dynamic dispatch",
                languages=[language],
                parsedFiles=parsed,
                skippedFiles=total - parsed,
            )
    return writer.finish()
