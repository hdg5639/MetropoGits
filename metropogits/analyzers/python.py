"""Python AST imports/declarations/explicit bindings, without importing the target."""

from __future__ import annotations

import ast
from collections import Counter, defaultdict
from pathlib import PurePosixPath

from .common import AnalysisError, GraphWriter, read_source

EXTRACTOR = "python-ast/0.1"
MAX_NODES = 150_000


def module_index(paths):
    result = defaultdict(set)
    packages = {
        str(PurePosixPath(p).parent) for p in paths if p.endswith("/__init__.py")
    }
    for path in sorted(paths):
        parts = list(PurePosixPath(path).with_suffix("").parts)
        if parts[-1] == "__init__":
            parts.pop()
        if parts:
            result[".".join(parts)].add(path)
        if parts and parts[0] == "src":
            result[".".join(parts[1:])].add(path)
        parent = str(PurePosixPath(path).parent)
        if parent in packages:
            base = PurePosixPath(parent)
            while str(base.parent) in packages:
                base = base.parent
            rel = PurePosixPath(path).relative_to(base.parent).with_suffix("")
            names = list(rel.parts)
            if names[-1] == "__init__":
                names.pop()
            result[".".join(names)].add(path)
    return result


def dotted(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        prefix = dotted(node.value)
        return f"{prefix}.{node.attr}" if prefix else None
    return None


def relative_module(path, module, level):
    if not level:
        return module or ""
    parts = list(PurePosixPath(path).parent.parts)
    if level > len(parts):
        return None
    return ".".join(
        parts[: len(parts) - level + 1] + ((module or "").split(".") if module else [])
    )


def enrich_python_graph(root, scan, graph, limits):
    writer = GraphWriter(graph, EXTRACTOR)
    sources = [s for s in scan.files if s.language == "python"]
    index = module_index([s.path for s in sources])
    local_roots = {name.split(".")[0] for name in index}
    units = {}
    for source in sources:
        try:
            tree = ast.parse(
                read_source(root, source, limits.max_file_bytes), filename=source.path
            )
            for count, _ in enumerate(ast.walk(tree), 1):
                if count > MAX_NODES:
                    raise AnalysisError("AST node limit")
            units[source.path] = tree
        except (OSError, UnicodeError, SyntaxError, RecursionError, AnalysisError):
            writer.diagnostic(
                "PYTHON_ANALYSIS_SKIPPED",
                "Python syntax, encoding or AST resource limit; structural file retained",
                source.path,
                "WARNING",
            )

    for path, tree in sorted(units.items()):
        source_id = writer.files[path]["id"]
        nodes = list(ast.walk(tree))
        top_imports = {
            id(n) for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom))
        }
        bindings = {}
        import_counts = Counter()
        writes = Counter(
            n.id
            for n in nodes
            if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
        )
        writes.update(n.arg for n in nodes if isinstance(n, ast.arg))
        writes.update(
            n.name
            for n in nodes
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
        )
        writes.update(
            n.name for n in nodes if isinstance(n, ast.ExceptHandler) and n.name
        )
        facts = []

        for n in nodes:
            if not isinstance(n, (ast.Import, ast.ImportFrom)):
                continue
            for alias in n.names:
                module = (
                    alias.name
                    if isinstance(n, ast.Import)
                    else relative_module(path, n.module, n.level)
                )
                if module is None:
                    writer.diagnostic(
                        "PYTHON_IMPORT_UNRESOLVED",
                        "Relative import exceeds package root",
                        path,
                    )
                    continue
                full = (
                    module
                    if isinstance(n, ast.Import)
                    else ".".join(filter(None, [module, alias.name]))
                )
                candidates = index.get(full, set()) or index.get(module, set())
                proof = writer.proof(path, n.lineno, "IMPORT", "python:" + full)
                local = False
                target = None
                if len(candidates) == 1:
                    candidate = next(iter(candidates))
                    target = writer.files[candidate]["id"]
                    local = True
                elif len(candidates) > 1:
                    writer.diagnostic(
                        "PYTHON_IMPORT_AMBIGUOUS",
                        "Multiple source modules match; no target chosen",
                        path,
                        "WARNING",
                    )
                elif (isinstance(n, ast.ImportFrom) and n.level) or full.split(".")[
                    0
                ] in local_roots:
                    writer.diagnostic(
                        "PYTHON_IMPORT_UNRESOLVED",
                        "Local module not found in scanned package roots",
                        path,
                    )
                else:
                    target = writer.external(
                        "python", module.split(".")[0] or alias.name
                    )
                    facts.append(
                        writer.fact(path, n.lineno, "IMPORT", "python:" + full)
                    )
                    for end in range(1, len(full.split("."))):
                        facts.append(
                            writer.fact(
                                path,
                                n.lineno,
                                "IMPORT",
                                "python:" + ".".join(full.split(".")[:end]),
                            )
                        )
                if target:
                    writer.edge(
                        source_id,
                        target,
                        "IMPORTS",
                        proof,
                        full,
                        "RESOLVED" if local else "DIRECT",
                    )
                if alias.name == "*":
                    writer.diagnostic(
                        "PYTHON_WILDCARD_UNRESOLVED",
                        "Wildcard exports are not symbol-resolved",
                        path,
                    )
                    continue
                name = alias.asname or (
                    alias.name.split(".")[0]
                    if isinstance(n, ast.Import)
                    else alias.name
                )
                import_counts[name] += 1
                if id(n) in top_imports and target:
                    identity = (
                        full
                        if alias.asname or isinstance(n, ast.ImportFrom)
                        else alias.name.split(".")[0]
                    )
                    bindings[name] = (identity, target, not local)

        bindings = {
            k: v for k, v in bindings.items() if not writes[k] and import_counts[k] == 1
        }

        def binding(node):
            name = dotted(node)
            if not name:
                return None
            base, _, tail = name.partition(".")
            if base not in bindings:
                return None
            identity, target, external = bindings[base]
            return (identity + ("." + tail if tail else ""), target, external)

        # Track one explicit, unreassigned constructor binding (e.g. app=FastAPI()).
        # Arbitrary returned objects and dynamic attributes are not resolved.
        for n in tree.body:
            if (
                isinstance(n, ast.Assign)
                and len(n.targets) == 1
                and isinstance(n.targets[0], ast.Name)
                and isinstance(n.value, ast.Call)
            ):
                name = n.targets[0].id
                found = binding(n.value.func)
                if (
                    found
                    and found[2]
                    and writes[name] == 1
                    and name not in import_counts
                ):
                    bindings[name] = found

        for n in tree.body:
            if isinstance(n, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
                writer.symbol(path, n.name, n.lineno, n.end_lineno)
            if isinstance(n, ast.If) and isinstance(n.test, ast.Compare):
                compare = n.test
                if (
                    isinstance(compare.left, ast.Name)
                    and compare.left.id == "__name__"
                    and len(compare.ops) == 1
                    and isinstance(compare.ops[0], ast.Eq)
                    and len(compare.comparators) == 1
                    and isinstance(compare.comparators[0], ast.Constant)
                    and compare.comparators[0].value == "__main__"
                ):
                    facts.append(writer.fact(path, n.lineno, "AST", "python:__main__"))

        for n in nodes:
            if isinstance(n, ast.Call):
                found = binding(n.func)
                if found:
                    identity, target, external = found
                    if external:
                        facts.append(
                            writer.fact(path, n.lineno, "CALL", "python:" + identity)
                        )
                    else:
                        proof = writer.proof(
                            path, n.lineno, "CALL", "python:" + identity
                        )
                        writer.edge(source_id, target, "REFERENCES", proof, identity)
            if isinstance(n, ast.ClassDef):
                for base in n.bases:
                    found = binding(base)
                    if found:
                        identity, target, external = found
                        if external:
                            facts.append(
                                writer.fact(
                                    path, n.lineno, "INHERITANCE", "python:" + identity
                                )
                            )
                        else:
                            proof = writer.proof(
                                path, n.lineno, "INHERITANCE", "python:" + identity
                            )
                            writer.edge(source_id, target, "EXTENDS", proof, identity)
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                for decorator in n.decorator_list:
                    found = binding(
                        decorator.func if isinstance(decorator, ast.Call) else decorator
                    )
                    if found and found[2]:
                        facts.append(
                            writer.fact(
                                path,
                                decorator.lineno,
                                "ANNOTATION",
                                "python:" + found[0],
                            )
                        )
        writer.claims(path, facts)

    writer.diagnostic(
        "PYTHON_ANALYZER_COVERAGE",
        "Python stdlib AST: imports,declarations,explicitBindings,inheritance; no execution, dynamic dispatch or star-export resolution",
        parsedFiles=len(units),
        skippedFiles=len(sources) - len(units),
        languages=["python"],
    )
    return writer.finish()
