"""Tight visual ground supports, distinct from allocated directory ownership."""

from collections import defaultdict

from metropogits.frontage_parcels import area, corners
from metropogits.block_orientation import clip
from metropogits.street_diagonals import hull, bounds

MAX_MERGE_CHECKS = 500_000
MAX_CLIP_CHECKS = 500_000


def occupied_ground(scene, parcels):
    groups = defaultdict(list)
    districts = {d["id"]: d for d in scene["districts"]}
    for b in sorted(scene["buildings"], key=lambda b: b["entityId"]):
        poly = parcels.get(b["entityId"], {}).get("footprint", corners(b))
        support = hull(
            [
                [x + dx, z + dz]
                for x, z in poly
                for dx in (-1.25, 1.25)
                for dz in (-1.25, 1.25)
            ]
        )
        groups[b["districtId"]].append(
            dict(
                points=support,
                members=[b["entityId"]],
                buildingArea=b["width"] * b["depth"],
            )
        )
    pads, checks, clip_checks = [], 0, 0
    for key, clusters in sorted(groups.items()):
        # Deterministic local merges: no hull spanning a large vacant reservation.
        result = []
        for cluster in clusters:
            for existing in result:
                checks += 1
                if checks > MAX_MERGE_CHECKS:
                    raise ValueError("occupied ground merge limit")
                a, b = bounds(existing["points"]), bounds(cluster["points"])
                if max(a[0] - b[2], b[0] - a[2], a[1] - b[3], b[1] - a[3]) > 7:
                    continue
                combined = hull(existing["points"] + cluster["points"])
                if area(combined) <= 2.8 * (
                    existing["buildingArea"] + cluster["buildingArea"]
                ):
                    existing["points"] = combined
                    existing["members"] += cluster["members"]
                    existing["buildingArea"] += cluster["buildingArea"]
                    break
            else:
                result.append(cluster)
        for index, pad in enumerate(result):
            pieces = []
            for rect in districts[key].get("footprint", [districts[key]]):
                clip_checks += 1
                if clip_checks > MAX_CLIP_CHECKS:
                    raise ValueError("occupied ground clipping limit")
                # Clip against the full convex owner rectangle, preserving holes
                # in polygon-union districts by never spanning between rectangles.
                p = clip(pad["points"], corners(rect))
                if area(p) > 1e-8:
                    pieces.append(p)
            pads.append(
                dict(
                    id=f"{key}:occupied:{index}",
                    districtId=key,
                    memberEntityIds=sorted(pad["members"]),
                    polygons=pieces,
                )
            )
    root_area = sum(
        r["width"] * r["depth"]
        for d in scene["districts"]
        if d["parentId"] is None
        for r in d.get("footprint", [d])
    )
    return dict(
        version="occupied-ground/0.1",
        semantic=False,
        pads=pads,
        allocatedRootArea=root_area,
        padAreaUpperBound=sum(area(p) for pad in pads for p in pad["polygons"]),
        buildingArea=sum(b["width"] * b["depth"] for b in scene["buildings"]),
        basis="physical building supports; allocated directory bounds remain in Structure overlay",
    )
