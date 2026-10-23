"""One-command procedural city: analysis, structural build, then the world pipeline.

Wraps the same stages as ``scripts.procedural_world`` with its recommended
urban preset. Source code is never executed; output is a static artifact.
"""

import json
import tempfile
from pathlib import Path

RECOMMENDED = dict(
    planning="varied",
    outline="varied",
    zoning="neighborhoods",
    pattern_scale="adaptive",
    street_policy="porous",
    street_hierarchy=True,
    campus=True,
    campus_style="precinct",
    capacity_replan=True,
)
TERRAINS = (
    "watershed-landscape",
    "mountain-landscape",
    "varied-landscape",
    "river-landscape",
    "river-corridor",
    "flat",
)


def build_world_city(repo, output, *, repository_id=None, theme="minimal", revision=None,
                     source_url=None, limits=None, seed=None, terrain="watershed-landscape"):
    from metropogits.cli import CliError, build_repository
    from metropogits.world.export import package_world
    from metropogits.world.generator import generate_world
    from metropogits.world.validation import validate_world
    from scripts.canonical_json import loads_strict_json

    output = Path(output)
    if output.exists() and any(output.iterdir()):
        raise CliError("city output directory must be new or empty")
    with tempfile.TemporaryDirectory(prefix="metropogits-structure-") as directory:
        structure = Path(directory) / "build"
        build_repository(repo, structure, repository_id, theme, revision, source_url, limits=limits)
        read = lambda name: loads_strict_json((structure / name).read_text(encoding="utf8"))
        scene, graph = read("city.json"), read("graph.ucg.json")
    attempts = [terrain] + (["flat"] if terrain != "flat" else [])
    world, used = None, None
    for preset in attempts:
        try:
            world = generate_world(scene, graph, seed=seed, terrain=preset, **RECOMMENDED)
            used = preset
            break
        except ValueError:
            # Very small repositories cannot host certified water crossings.
            if preset == attempts[-1]:
                raise
    validation = validate_world(world, scene, graph)
    artifacts = package_world(world, scene, graph, validation, building_style="urban")
    output.mkdir(parents=True, exist_ok=True)
    for name, content in artifacts.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
    return dict(output=str(output), seed=world["seed"], terrain=used, validation=validation,
                buildings=len(world["parcels"]), districts=len(world["districts"]))


def summary_line(result):
    return (f"Built procedural city ({result['buildings']} buildings, {result['districts']} districts, "
            f"terrain {result['terrain']}): {result['output']}")


__all__ = ["build_world_city", "summary_line", "TERRAINS", "json"]
