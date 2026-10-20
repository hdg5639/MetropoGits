"""Run real source syntax for every bundled polyglot usage profile."""

import copy
import tempfile
import unittest
from pathlib import Path

from metropogits.catalog import load_bundled_catalog
from metropogits.cli import analyze_repository
from scripts.validate_catalog import validate_document
from scripts.validate_ucg import validate_document as validate_ucg

ROOT = Path(__file__).parents[1]


def sample(rule):
    signatures = rule["match"]["codeSignatures"]
    usage = next(s for s in signatures if s["kind"] != "IMPORT")
    imported = next(s for s in signatures if s["kind"] == "IMPORT")
    language, provider = imported["value"].split(":", 1)
    identity = usage["value"].split(":", 1)[1]
    suffix = identity[len(provider) :].lstrip(".")
    kind = usage["kind"]
    if language == "python":
        head = f"import {provider} as Bound\n"
        target = "Bound" + ("." + suffix if suffix else "")
        body = (
            f"class Entry({target}): pass"
            if kind == "INHERITANCE"
            else (
                f"@{target}\nclass Entry: pass"
                if "DATA_MODEL" in rule["produces"]["roles"]
                else f"@{target}\ndef entry(): pass"
            )
            if kind == "ANNOTATION"
            else target + "()"
        )
        return "entry.py", head + body
    if language == "java":
        target = provider.rsplit(".", 1)[-1]
        head = f"import {provider};\n"
        body = (
            f"@{target} class Entry {{}}"
            if kind == "ANNOTATION"
            else f"class Entry extends {target} {{}}"
            if kind == "INHERITANCE"
            else f"class Entry {{void run(){{{target}.{suffix}();}}}}"
        )
        return "Entry.java", head + body
    if language == "kotlin":
        head = f"import {provider} as Bound\n"
        return "Entry.kt", head + (
            "@Bound class Entry" if kind == "ANNOTATION" else "fun entry() { Bound() }"
        )
    if language == "javascript":
        if suffix == "default":
            return "entry.ts", f"import Bound from '{provider}';\nBound();"
        name = suffix.split(".")[0]
        target = "Bound" + ("." + suffix.split(".", 1)[1] if "." in suffix else "")
        head = f"import {{{name} as Bound}} from '{provider}';\n"
        return "entry.ts", head + (
            f"@{target}() class Entry {{}}" if kind == "ANNOTATION" else f"{target}();"
        )
    if language == "go":
        head = f'package main\nimport bound "{provider}"\n'
        value = f"bound.{suffix}{{}}" if kind == "AST" else f"bound.{suffix}()"
        return "main.go", head + f"func main() {{ _ = {value} }}"
    if language == "rust":
        return (
            "main.rs",
            f"use {provider.replace('.', '::')} as Bound;\nfn main(){{ Bound::{suffix}(); }}",
        )
    if language == "csharp":
        head = f"using {provider};\n"
        body = (
            f"class Entry : {suffix} {{}}"
            if kind == "INHERITANCE"
            else f"[{suffix}] class Entry {{}}"
            if kind == "ANNOTATION"
            else f"class Entry {{void Run(){{{suffix}();}}}}"
        )
        return "Entry.cs", head + body
    if language == "php":
        return "Entry.php", "<?php\nuse " + provider.replace(
            ".", "\\"
        ) + " as Bound;\nclass Entry extends Bound {}"
    if language == "ruby":
        return (
            "entry.rb",
            f"require '{provider}'\nclass Entry < {suffix.replace('.', '::')}\nend",
        )
    if language == "swift":
        return "Entry.swift", f"import {provider}\n" + (
            f"struct Entry: {suffix} {{}}"
            if kind == "INHERITANCE"
            else f"let entry = {suffix}()"
        )
    if language == "dart":
        head = f"import '{provider}' as bound;\n"
        return "entry.dart", head + (
            f"class Entry extends bound.{suffix} {{}}"
            if kind == "INHERITANCE"
            else f"void main() {{bound.{suffix}();}}"
        )
    if language in {"cpp", "c"}:
        target = provider.rsplit("/", 1)[-1].split(".")[0]
        body = (
            f"class Entry: public {target} {{}};"
            if kind == "INHERITANCE"
            else f"void run(){{{target}::{suffix}();}}"
            if provider == "QSqlDatabase"
            else f"void run(){{{suffix}();}}"
        )
        return "entry." + language, f"#include <{provider}>\n" + body
    raise AssertionError(language)


class FrameworkBindingsTests(unittest.TestCase):
    def test_every_polyglot_usage_rule_is_exercised_from_real_source(self):
        rules = [
            r
            for r in load_bundled_catalog()["rules"]
            if any(s["kind"] == "IMPORT" for s in r["match"]["codeSignatures"])
            and any(":" in s["value"] for s in r["match"]["codeSignatures"])
        ]
        self.assertGreaterEqual(len(rules), 140)
        for rule in rules:
            with self.subTest(rule=rule["id"]), tempfile.TemporaryDirectory() as d:
                name, source = sample(rule)
                root = Path(d)
                (root / name).write_text(source, encoding="utf8")
                graph = analyze_repository(root, "fixture/framework")
                entity = next(e for e in graph["entities"] if e["kind"] == "FILE")
                roles = {r["value"] for r in entity["roles"]}
                self.assertTrue(
                    set(rule["produces"]["roles"]) <= roles,
                    (rule["id"], roles, graph["diagnostics"]),
                )
                self.assertEqual(validate_ucg(graph), [])
                evidence = {e["evidenceId"]: e for e in graph["evidence"]}
                for claim in entity["roles"]:
                    proofs = [evidence[e] for e in claim["evidenceIds"]]
                    if claim["value"] != "CLI_ENTRYPOINT":
                        self.assertTrue(any(e["kind"] == "IMPORT" for e in proofs))

    def test_catalog_schema_and_positive_negative_facts_are_valid_and_immutable(self):
        self.assertEqual(
            validate_document(load_bundled_catalog(), ROOT / "catalog/0.5.0/fixtures"),
            [],
        )
        bad = copy.deepcopy(load_bundled_catalog())
        bad["schemaVersion"] = "catalog/99.0"
        self.assertTrue(validate_document(bad))

    def test_unused_imports_and_name_lookalikes_do_not_create_facilities(self):
        examples = {
            "entry.py": "from fastapi import FastAPI\nclass PaymentService: pass\n",
            "entry.ts": "import { Controller } from '@nestjs/common';\nclass PaymentService {}",
            "Entry.java": "import jakarta.ws.rs.Path;\nclass PaymentService {}",
            "main.go": 'package main\nimport "github.com/gin-gonic/gin"\nfunc helper() {}',
            "entry.rs": "use axum::Router;\nfn helper() {}",
        }
        for name, text in examples.items():
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                (root / name).write_text(text, encoding="utf8")
                graph = analyze_repository(root, "fixture/unused")
                self.assertFalse(
                    next(e for e in graph["entities"] if e["kind"] == "FILE")["roles"]
                )

    def test_alias_shadows_comments_strings_local_modules_and_type_parameters(self):
        examples = [
            {"entry.py": "from fastapi import FastAPI\nFastAPI=object\nFastAPI()"},
            {
                "entry.py": "from fastapi import FastAPI\nFastAPI()",
                "fastapi.py": "class FastAPI: pass",
            },
            {
                "entry.ts": "import {Controller as Gate} from '@nestjs/common';\nfunction f(Gate) {Gate();}"
            },
            {
                "entry.ts": "import {Controller} from '@nestjs/common';\nconst s='@Controller()'; // @Controller()"
            },
            {
                "Entry.java": "import jakarta.ws.rs.Path;\n@interface Path {}\n@Path class Entry {}"
            },
            {
                "Entry.cs": "using Microsoft.EntityFrameworkCore;\nclass Entry<DbContext> {}"
            },
            {
                "Entry.cs": "using Microsoft.EntityFrameworkCore;\nclass DbContext {}\nclass Entry:DbContext{}"
            },
            {
                "main.go": 'package main\nimport gin "github.com/gin-gonic/gin"\nfunc f(gin Fake){gin.Default()}'
            },
        ]
        for files in examples:
            with self.subTest(files=files), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                for name, text in files.items():
                    (root / name).write_text(text, encoding="utf8")
                graph = analyze_repository(root, "fixture/negative")
                roles = {
                    r["value"]
                    for e in graph["entities"]
                    if e["kind"] == "FILE"
                    for r in e["roles"]
                }
                self.assertFalse(roles, roles)

    def test_plain_entrypoints_and_source_components_are_evidenced(self):
        examples = [
            ("entry.py", 'if __name__ == "__main__":\n    pass', "CLI_ENTRYPOINT"),
            (
                "Entry.java",
                "class Entry {public static void main(String[] args) {}}",
                "CLI_ENTRYPOINT",
            ),
            ("main.go", "package main\nfunc main() {}", "CLI_ENTRYPOINT"),
            ("main.rs", "fn main() {}", "CLI_ENTRYPOINT"),
            ("main.kt", "fun main() {}", "CLI_ENTRYPOINT"),
            (
                "View.vue",
                "<script setup>const x=1;</script><template><p>View</p></template>",
                "UI_COMPONENT",
            ),
            ("View.svelte", "<script>const x=1;</script><p>View</p>", "UI_COMPONENT"),
            ("View.svelte", "<h1>Pure markup</h1>", "UI_COMPONENT"),
            ("Value.java", "record Value(String name) {}", "DATA_MODEL"),
            (
                "value.py",
                "from dataclasses import dataclass\n@dataclass\nclass Value:\n    name: str",
                "DATA_MODEL",
            ),
        ]
        for name, text, role in examples:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                (root / name).write_text(text, encoding="utf8")
                graph = analyze_repository(root, "fixture/source")
                self.assertIn(
                    role,
                    {
                        r["value"]
                        for e in graph["entities"]
                        if e["kind"] == "FILE"
                        for r in e["roles"]
                    },
                )

    def test_jsx_text_is_not_code_and_type_parameters_are_not_ui(self):
        examples = [
            (
                "View.tsx",
                "export const view = <div className='plain'>import './fake'; @Controller()</div>;",
                {"UI_COMPONENT"},
            ),
            ("value.tsx", "export const identity = <T,>(value: T): T => value;", set()),
        ]
        for name, source, expected in examples:
            with self.subTest(name=name), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                (root / name).write_text(source, encoding="utf8")
                graph = analyze_repository(root, "fixture/jsx")
                self.assertEqual(
                    {
                        r["value"]
                        for e in graph["entities"]
                        if e["kind"] == "FILE"
                        for r in e["roles"]
                    },
                    expected,
                )
                self.assertFalse(
                    any("fake" in e.get("path", "") for e in graph["entities"])
                )
