"""Measure derived road geometry, not runtime traffic or semantic accuracy."""
from __future__ import annotations

import argparse
import json
import math
from collections import defaultdict
from pathlib import Path


def road_metrics(routing):
    def distance(a, b):
        return math.dist(a, b)

    turns, travel = 0, 0.0
    for route in routing["routes"]:
        vectors = [(b[0]-a[0], b[1]-a[1]) for a, b in zip(route["path"], route["path"][1:]) if a != b]
        travel += sum(math.hypot(*v) for v in vectors)
        turns += sum(a[0]*b[1] != a[1]*b[0] or a[0]*b[0]+a[1]*b[1] < 0
                     for a, b in zip(vectors, vectors[1:]))
    length, shared = 0.0, 0.0
    lines = defaultdict(lambda: defaultdict(list))
    for segment in routing["segments"]:
        a, b = segment["start"], segment["end"]
        size = distance(a, b)
        length += size
        if len(segment["routeIds"]) > 1:
            shared += size
        if segment["access"]:
            continue
        axis = 0 if a[1] == b[1] else 1
        lines[(segment["kind"], axis)][a[1-axis]].append(tuple(sorted((a[axis], b[axis]))))
    parallel = 0.0
    for offsets in lines.values():
        keys = sorted(offsets)
        for i, first in enumerate(keys):
            left = sorted(offsets[first])
            for second in keys[i+1:]:
                if second-first > 7:
                    break
                right = sorted(offsets[second])
                x = y = 0
                while x < len(left) and y < len(right):
                    a, b = left[x], right[y]
                    parallel += max(0, min(a[1], b[1])-max(a[0], b[0]))
                    if a[1] <= b[1]:
                        x += 1
                    else:
                        y += 1
    return dict(routes=len(routing["routes"]), segments=len(routing["segments"]),
                junctions=len(routing["junctions"]), turns=turns,
                routeLength=round(travel, 3), pavementCenterlineLength=round(length, 3),
                sharedCenterlineLength=round(shared, 3),
                nearbyParallelPairLength=round(parallel, 3),
                unresolvedEdges=len(routing["unresolvedEdgeIds"]),
                searchExpansions=routing.get("searchExpansions", 0))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path, nargs="+")
    args = parser.parse_args()
    for directory in args.build:
        raw = (directory / "assets/viewer-data.js").read_text(encoding="utf-8")
        prefix = "globalThis.METROPOGITS_DATA="
        if not raw.startswith(prefix):
            parser.error("expected a JSON-only viewer data artifact")
        data = json.loads(raw[len(prefix):].strip().removesuffix(";"))
        print(json.dumps(dict(build=str(directory), **road_metrics(data["routing"])), sort_keys=True))


if __name__ == "__main__":
    main()
