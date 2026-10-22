"""Actual module syntax across languages, exact targets and lexical limitations."""

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from metropogits.cli import analyze_repository
from metropogits.analyzers.lexical import tokenize
from metropogits.analyzers.polyglot import references
from scripts.canonical_json import canonical_json_bytes
from scripts.validate_ucg import validate_document


def write(root, files):
    for name, text in files.items():
        path = root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf8")


def links(graph):
    paths = {e["id"]: e.get("path") for e in graph["entities"]}
    return {
        (e["type"], paths[e["from"]], paths[e["to"]])
        for e in graph["edges"]
        if e["type"] not in {"CONTAINS", "DECLARES"}
    }


class PolyglotAnalyzerTests(unittest.TestCase):
    def test_explicit_local_imports_across_nine_language_shapes(self):
        cases = [
            (
                {
                    "main.cpp": '#include "store.hpp"\n#include <vector>',
                    "store.hpp": "class Store {};",
                },
                "main.cpp",
                "store.hpp",
            ),
            (
                {"main.c": '#include "store.h"', "store.h": "struct Store {};"},
                "main.c",
                "store.h",
            ),
            (
                {
                    "main.cs": "using Repo = App.Store;\nclass Main {}",
                    "store.cs": "namespace App; class Store {}",
                },
                "main.cs",
                "store.cs",
            ),
            (
                {
                    "main.kt": "import app.Store\nfun main() {}",
                    "store.kt": "package app\nclass Store",
                },
                "main.kt",
                "store.kt",
            ),
            (
                {
                    "main.scala": "import app.Store\nobject Main {}",
                    "store.scala": "package app\nclass Store {}",
                },
                "main.scala",
                "store.scala",
            ),
            (
                {
                    "main.php": "<?php use App\\Store;",
                    "store.php": "<?php namespace App; class Store {}",
                },
                "main.php",
                "store.php",
            ),
            (
                {
                    "main.rb": "require_relative './store'",
                    "store.rb": "class Store\nend",
                },
                "main.rb",
                "store.rb",
            ),
            (
                {"main.dart": "import 'store.dart';", "store.dart": "class Store {}"},
                "main.dart",
                "store.dart",
            ),
            (
                {"main.lua": "local util = require('util')", "util.lua": "return {}"},
                "main.lua",
                "util.lua",
            ),
        ]
        for files, source, target in cases:
            with self.subTest(source=source), tempfile.TemporaryDirectory() as d:
                root = Path(d)
                write(root, files)
                graph = analyze_repository(root, "fixture/polyglot")
                self.assertIn(("IMPORTS", source, target), links(graph))
                self.assertEqual(validate_document(graph), [])
                self.assertEqual(
                    canonical_json_bytes(graph),
                    canonical_json_bytes(analyze_repository(root, "fixture/polyglot")),
                )

    def test_go_package_import_and_exported_symbol_do_not_connect_every_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(
                root,
                {
                    "go.mod": "module example.org/app\n",
                    "main.go": 'package main\nimport s "example.org/app/store"\nfunc main(){ _ = s.Store{} }',
                    "store/store.go": "package store\ntype Store struct {}",
                    "store/unrelated.go": "package store\ntype Other struct {}",
                },
            )
            graph = analyze_repository(root, "fixture/go")
            self.assertIn(("IMPORTS", "main.go", "store"), links(graph))
            self.assertIn(("REFERENCES", "main.go", "store/store.go"), links(graph))
            self.assertNotIn(
                ("REFERENCES", "main.go", "store/unrelated.go"), links(graph)
            )

    def test_rust_use_tree_mod_alias_and_unknown_member(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(
                root,
                {
                    "Cargo.toml": '[package]\nname="demo"\n',
                    "src/lib.rs": "mod store;\nuse crate::store::{Store as S};\nuse serde::{Serialize, de::DeserializeOwned};",
                    "src/store.rs": "pub struct Store;",
                },
            )
            graph = analyze_repository(root, "fixture/rust")
            self.assertIn(("IMPORTS", "src/lib.rs", "src/store.rs"), links(graph))
            self.assertTrue(
                any(e.get("path") == "cargo/serde.Serialize" for e in graph["entities"])
            )
            write(root, {"src/lib.rs": "use crate::store::Missing;"})
            graph = analyze_repository(root, "fixture/rust")
            self.assertFalse(
                any(e[0] == "IMPORTS" and e[2] == "src/store.rs" for e in links(graph))
            )
            self.assertTrue(
                any(
                    d["code"] == "POLYGLOT_IMPORT_UNRESOLVED"
                    for d in graph["diagnostics"]
                )
            )

    def test_swift_import_is_explicit_external_not_invented_source_file(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(root, {"View.swift": "import SwiftUI\nstruct Page: View {}"})
            graph = analyze_repository(root, "fixture/swift")
            self.assertIn(("IMPORTS", "View.swift", "swift/SwiftUI"), links(graph))

    def test_comments_strings_raw_literals_and_macros_never_create_dependencies(self):
        cases = {
            "go": '// import "evil"\nvar s = `import "evil"`',
            "rust": '/* use evil::Bad; */ const S:&str = r###"use evil::Bad;"###;\nmacro_rules! m { () => {use evil::Bad;} }',
            "cpp": '// ignored\\\n#include "evil.h"\nconst char* p=R"raw(#include <evil>)raw";',
            "lua": '--[[\nrequire "evil"\n]]\nlocal s = [=[require "evil"]=]',
            "ruby": '=begin\nrequire "evil"\n=end\nx = "require \'evil\'"',
        }
        from metropogits.analyzers.polyglot import without_rust_macros

        for language, text in cases.items():
            with self.subTest(language=language):
                tokens = tokenize(text, language)
                if language == "rust":
                    tokens = without_rust_macros(tokens)
                self.assertEqual(references(tokens, language), ())

    def test_escaping_includes_missing_rust_and_resource_failures_stay_unresolved(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            write(
                root,
                {"main.cpp": '#include "../outside.hpp"', "main.rs": "mod missing;"},
            )
            graph = analyze_repository(root, "fixture/negative")
            self.assertFalse(any(e["type"] == "IMPORTS" for e in graph["edges"]))
            with patch("metropogits.analyzers.lexical.MAX_TOKENS", 1):
                graph = analyze_repository(root, "fixture/negative")
            self.assertEqual(sum(e["kind"] == "FILE" for e in graph["entities"]), 2)
            self.assertTrue(
                any(
                    e["code"] == "POLYGLOT_ANALYSIS_SKIPPED"
                    for e in graph["diagnostics"]
                )
            )

    def test_shadowed_lua_require_is_not_a_module_import(self):
        self.assertEqual(
            references(
                tokenize('local function require(x) end\nrequire("fake")', "lua"), "lua"
            ),
            (),
        )


if __name__ == "__main__":
    unittest.main()
