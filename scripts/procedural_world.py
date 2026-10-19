"""Generate an explicit experimental world from a validated local build."""

import argparse
import json
from pathlib import Path
from time import perf_counter

from metropogits.world.generator import generate_world
from metropogits.world.validation import validate_world
from metropogits.world.export import package_world
from scripts.canonical_json import loads_strict_json


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed")
    parser.add_argument(
        "--zoning",
        choices=("none", "semantic", "soft", "neighborhoods"),
        default="none",
        help="opt-in evidence-backed neighborhoods; leaves canonical City/UCG intact",
    )
    parser.add_argument(
        "--outline",
        choices=("ellipse", "varied"),
        default="ellipse",
        help="seeded convex silhouette; ellipse preserves existing geography",
    )
    parser.add_argument(
        "--planning",
        choices=(
            "grid",
            "mixed",
            "radial",
            "organic",
            "industrial",
            "hybrid",
            "varied",
        ),
        default="grid",
        help="visual planning grammar; grid retains the original default",
    )
    parser.add_argument(
        "--namespace", help="portable world identity; does not rewrite existing UCG IDs"
    )
    parser.add_argument("--previous-world", type=Path)
    parser.add_argument(
        "--pattern-scale",
        choices=("block", "district"),
        default="block",
        help="inherit a shared district street field across physical neighborhoods",
    )
    args = parser.parse_args()

    def read(path):
        if path.stat().st_size > 64 * 1024 * 1024:
            raise ValueError("world input exceeds 64 MiB")
        return loads_strict_json(path.read_text(encoding="utf8"))

    try:
        if args.out.exists():
            raise ValueError("world output must not already exist")
        if (
            args.out.resolve() == args.build.resolve()
            or args.out.resolve() in args.build.resolve().parents
        ):
            raise ValueError("world output must not replace its input")
        scene, graph = (
            read(args.build / "city.json"),
            read(args.build / "graph.ucg.json"),
        )
        start = perf_counter()
        world = generate_world(
            scene,
            graph,
            seed=args.seed,
            namespace=args.namespace,
            previous=read(args.previous_world) if args.previous_world else None,
            planning=args.planning,
            outline=args.outline,
            zoning=args.zoning,
            pattern_scale=args.pattern_scale,
        )
        generated = perf_counter()
        validation = validate_world(world, scene, graph)
        validated = perf_counter()
        artifacts = package_world(world, scene, graph, validation)
        packaged = perf_counter()
        args.out.mkdir(parents=True, exist_ok=False)
        for name, content in artifacts.items():
            p = args.out / name
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content)
        print(
            json.dumps(
                dict(
                    output=str(args.out),
                    seed=world["seed"],
                    validation=validation,
                    timingSeconds=dict(
                        generate=generated - start,
                        validate=validated - generated,
                        package=packaged - validated,
                    ),
                )
            )
        )
    except (ValueError, OSError, KeyError) as error:
        parser.exit(2, f"Procedural world failed: {error}\n")


if __name__ == "__main__":
    main()
