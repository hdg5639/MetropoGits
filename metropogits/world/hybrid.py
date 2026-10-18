"""Two connected planning regions inside one physical/source-owned district."""

from .geometry import area, partition, shared_boundaries
from .organic import organic_slots
from .planning import slots
from .seed import derive


def hybrid_regions(polygon, seed):
    polygons = partition(
        polygon, [("curved", 0.58), ("planned", 0.42)], derive(seed, "hybrid-regions")
    )
    polygons, _ = shared_boundaries(polygons, polygon)
    return [
        dict(
            id=key,
            polygon=polygons[key],
            planningProfile=profile,
            areaAllocated=area(polygons[key]),
        )
        for key, profile in (("curved", "ORGANIC"), ("planned", "GRID"))
    ]


def hybrid_slots(polygon, seed):
    candidates, lanes = [], []
    angle = 0
    for region in hybrid_regions(polygon, seed):
        planner = organic_slots if region["planningProfile"] == "ORGANIC" else slots
        local, roads, angle = planner(
            region["polygon"], derive(seed, "region", region["id"])
        )
        for slot in local:
            slot.update(
                id=region["id"] + ":" + slot["id"],
                laneId=region["id"] + ":" + slot["laneId"],
                planningRegionId=region["id"],
                blockProfile=region["planningProfile"],
            )
        candidates.extend(local)
        for road in roads:
            lanes.append(dict(road, id=region["id"] + ":" + road["id"]))
        poly = region["polygon"]
        for i, (a, b) in enumerate(zip(poly, poly[1:] + poly[:1])):
            lanes.append(
                dict(
                    id=f"{region['id']}:boundary:{i}",
                    start=a,
                    end=b,
                    width=3.5,
                    access=False,
                )
            )
    return candidates, lanes, angle
