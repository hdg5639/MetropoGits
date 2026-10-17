"""Bounded config-only aliases; no compiler, plugins, inheritance or filesystem IO."""
from dataclasses import dataclass
from pathlib import PurePosixPath

from scripts.canonical_json import loads_strict_json


@dataclass(frozen=True)
class ModulePaths:
    path: str
    base: str = "."
    mappings: tuple[tuple[str, tuple[str, ...]], ...] = ()
    supported: bool = True


def safe_relative(value: str) -> bool:
    return bool(value) and not value.startswith("/") and not any(
        character in value for character in ("\\", ":", "\0", "?", "#")
    )


def parse_module_paths(path: str, content: bytes) -> ModulePaths:
    data = loads_strict_json(content.decode("utf-8-sig"))
    if not isinstance(data, dict) or "extends" in data:
        raise ValueError("config inheritance is not supported")
    options = data.get("compilerOptions", {})
    if not isinstance(options, dict):
        raise ValueError("compilerOptions must be an object")
    base = options.get("baseUrl", ".")
    paths = options.get("paths", {})
    if not isinstance(base, str) or not safe_relative(base) or "*" in base:
        raise ValueError("baseUrl must be a relative path")
    if not isinstance(paths, dict) or len(paths) > 128:
        raise ValueError("paths must be a bounded object")
    mappings = []
    for pattern, targets in paths.items():
        if not safe_relative(pattern) or pattern.count("*") > 1:
            raise ValueError("unsupported paths pattern")
        if not isinstance(targets, list) or not 1 <= len(targets) <= 16:
            raise ValueError("paths targets must be a bounded nonempty list")
        if any(not isinstance(target, str) or not safe_relative(target)
               or target.count("*") > pattern.count("*") for target in targets):
            raise ValueError("unsupported paths substitution")
        mappings.append((pattern, tuple(targets)))
    return ModulePaths(path, base, tuple(mappings))


def config_for_file(path: str, configurations: tuple[ModulePaths, ...]) -> ModulePaths | None:
    ancestors = set(PurePosixPath(path).parents)
    matches = [config for config in configurations if PurePosixPath(config.path).parent in ancestors]
    # Nearest configuration wins; an unsupported nested config blocks ancestors.
    return min(matches, key=lambda config: (-len(PurePosixPath(config.path).parts),
                                           PurePosixPath(config.path).name != "tsconfig.json",
                                           config.path), default=None)


def alias_targets(config: ModulePaths, specifier: str) -> tuple[str, tuple[str, ...]] | None:
    """Exact match, otherwise longest prefix; target fallbacks retain declared order."""
    matches = []
    for pattern, targets in config.mappings:
        if "*" not in pattern:
            if pattern == specifier:
                return pattern, targets
            continue
        prefix, suffix = pattern.split("*")
        if specifier.startswith(prefix) and specifier.endswith(suffix) and len(specifier) >= len(prefix) + len(suffix):
            value = specifier[len(prefix):len(specifier) - len(suffix) if suffix else None]
            matches.append((len(prefix), pattern, tuple(target.replace("*", value) for target in targets)))
    if not matches:
        return None
    _, pattern, targets = max(matches, key=lambda match: match[0])
    return pattern, targets
