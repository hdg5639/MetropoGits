"""Static dependency declarations from additional ecosystems; never evaluate DSLs."""

import re
import tomllib
import xml.etree.ElementTree as ET
from pathlib import PurePosixPath

from scripts.canonical_json import loads_strict_json

MAX_DEPENDENCIES = 20_000
NAME = r"[A-Za-z0-9][A-Za-z0-9_.-]*"
MODULE = r"[A-Za-z0-9][A-Za-z0-9_./-]*"


def manifest_format(name):
    return {
        "pyproject.toml": "pyproject",
        "requirements.txt": "requirements",
        "Cargo.toml": "cargo",
        "go.mod": "go",
        "composer.json": "composer",
        "Gemfile": "gemfile",
        "pubspec.yaml": "pub",
    }.get(name) or (
        "nuget"
        if PurePosixPath(name).suffix in {".csproj", ".fsproj", ".vbproj"}
        else None
    )


def parse_manifest(kind, content):
    text = content.decode("utf-8-sig")
    dependencies = set()
    namespace = None
    ecosystem = dict(
        pyproject="pypi",
        requirements="pypi",
        cargo="cargo",
        go="go",
        composer="composer",
        gemfile="rubygems",
        pub="pub",
        nuget="nuget",
    )[kind]

    def add(name, pattern=NAME):
        if not isinstance(name, str) or not re.fullmatch(pattern, name) or ".." in name:
            raise ValueError("invalid static dependency name")
        if ecosystem == "pypi":
            name = re.sub(r"[-_.]+", "-", name).lower()
        dependencies.add(name)
        if len(dependencies) > MAX_DEPENDENCIES:
            raise ValueError("dependency count limit")

    def requirement(value):
        if not isinstance(value, str):
            raise ValueError("invalid dependency specifier")
        # Preserve only a validated distribution name, never credentials/URLs.
        match = re.match(
            rf"^\s*({NAME})(?:\[[A-Za-z0-9_, .-]+\])?(?:\s*(?:[<>=!~;@]|$))", value
        )
        if not match:
            raise ValueError("unsupported dependency declaration")
        add(match[1])

    if kind in {"pyproject", "cargo"}:
        data = tomllib.loads(text)
        if kind == "pyproject":
            project = data.get("project", {})
            for value in project.get("dependencies", []):
                requirement(value)
            for values in project.get("optional-dependencies", {}).values():
                for value in values:
                    requirement(value)
            poetry = data.get("tool", {}).get("poetry", {})
            tables = [
                poetry.get("dependencies", {}),
                poetry.get("dev-dependencies", {}),
            ]
            tables += [
                g.get("dependencies", {}) for g in poetry.get("group", {}).values()
            ]
            for table in tables:
                for name in table:
                    if name != "python":
                        add(name)
        else:
            namespace = data.get("package", {}).get("name")
            tables = [
                data.get(k, {})
                for k in ("dependencies", "dev-dependencies", "build-dependencies")
            ]
            tables += [data.get("workspace", {}).get("dependencies", {})]
            for target in data.get("target", {}).values():
                tables += [
                    target.get(k, {})
                    for k in ("dependencies", "dev-dependencies", "build-dependencies")
                ]
            for table in tables:
                for name, value in table.items():
                    add(value.get("package", name) if isinstance(value, dict) else name)
    elif kind == "requirements":
        for line in text.splitlines():
            value = line.split("#", 1)[0].strip()
            if value and not value.startswith("-"):
                requirement(value)
    elif kind == "go":
        text = re.sub(r"/\*.*?\*/", lambda m: "\n" * m[0].count("\n"), text, flags=re.S)
        block = False
        for line in text.splitlines():
            value = line.split("//", 1)[0].strip()
            if value.startswith("module "):
                namespace = value[7:].strip().strip('"')
                if not re.fullmatch(MODULE, namespace):
                    raise ValueError("invalid Go module path")
            elif value == "require (":
                block = True
            elif value == ")":
                block = False
            elif value.startswith("require ") or block:
                pair = value.removeprefix("require ").split()
                if len(pair) >= 2:
                    add(pair[0], MODULE)
    elif kind == "composer":
        data = loads_strict_json(text)
        for key in ("require", "require-dev"):
            for name in data.get(key, {}):
                if "/" in name:
                    add(name, rf"{NAME}/{NAME}")
    elif kind == "nuget":
        if re.search(r"<!\s*(?:DOCTYPE|ENTITY)", text, re.I):
            raise ValueError("XML declarations forbidden")
        tree = ET.fromstring(text)
        for node in tree.iter():
            if node.tag.rsplit("}", 1)[-1] in {"PackageReference", "PackageVersion"}:
                value = node.get("Include") or node.get("Update")
                if value:
                    add(value)
    elif kind == "gemfile":
        # Only complete literal gem statements; no Ruby evaluation/interpolation.
        if any(value in text for value in ("<<", "%q", "%Q")):
            raise ValueError("nonliteral Gemfile subset")
        for line in text.splitlines():
            quote = None
            escaped = False
            for char in line:
                if escaped:
                    escaped = False
                elif char == "\\":
                    escaped = True
                elif quote and char == quote:
                    quote = None
                elif not quote and char == "#":
                    break
                elif not quote and char in "\"'":
                    quote = char
            if quote:
                raise ValueError("multiline Gemfile string")
            match = re.match(rf"^\s*gem\s+[\"']({NAME})[\"'](?:\s*[,#]|\s*$)", line)
            if match:
                add(match[1])
    elif kind == "pub":
        block = False
        for line in text.splitlines():
            if re.match(r"^(?:dev_)?dependencies:\s*(?:#.*)?$", line):
                block = True
            elif line and not line[0].isspace() and not line.startswith("#"):
                block = False
            elif block:
                match = re.match(rf"^  ({NAME}):", line)
                if match:
                    add(match[1])
    if namespace is not None and (
        not isinstance(namespace, str)
        or not re.fullmatch(MODULE, namespace)
        or ".." in namespace
    ):
        raise ValueError("invalid declared module name")
    return ecosystem, tuple(sorted(dependencies)), namespace
