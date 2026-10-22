"""Reserve source-program land before structural streets subdivide it.

Only the explicit precinct experiment uses this policy. Original source facts,
district boundaries, terrain and all other campus styles retain their meaning.
"""

import math

from metropogits.street_diagonals import overlap
from .campus import eligibility
from .campus_estates import requirements
from .geometry import area, inside, point, ribbon
from .radial import _clipped
from .seed import derive

VERSION = "campus-reservation/0.1"


def program_demand(zone, pairs):
    """Physical site/circulation allowance, not source size or runtime demand."""
    requests = requirements(zone, pairs)
    sites = sum((r["width"] + 4) * (r["depth"] + 5) for r in requests)
    # Two shared commons plus independent frontage/perimeter circulation.
    return dict(siteArea=sites, commonsArea=1536, total=math.ceil(sites * 1.35 + 1536))


def reserve_precinct(zones, polygons, seed, main, pattern, terrain, pairs):
    """At most one feasible precinct; never grow/move unrelated geography.

    Preserve every outside segment and connect its boundary port to one shared
    perimeter. No dependency is added/deleted: these are structural streets
    before any source-to-address assignment or trip routing exists.
    """
    if len(zones) > 448 or len(main) > 20_000:
        raise ValueError("campus reservation input resource limit")
    choices = []
    for zone in zones:
        if not 12 <= len(zone["memberEntityIds"]) <= 256:
            continue
        decision = eligibility(zone, pairs, seed)
        demand = program_demand(zone, pairs)
        if (decision["eligible"] and decision["draw"] < decision["probability"]
                and demand["total"] <= area(polygons[zone["id"]])):
            choices.append((decision["draw"], zone["id"], demand))
    work = 0
    for _, identity, demand in sorted(choices):
        poly = polygons[identity]
        width = max((r["width"] for r in main), default=4)
        edges = [(a, b) for a, b in zip(poly, poly[1:] + poly[:1]) if math.dist(a, b) > .01]
        # Terrain comes first. A protected waterfront/mountain cannot be turned
        # into a perimeter road just to make an optional composition fit.
        natural = [f["noBuildPolygon"] for f in (terrain or {}).get("features", [])]
        work += len(edges) * (len(natural) + len(main))
        if work > 2_000_000:
            raise ValueError("campus reservation work limit")
        if any(overlap(ribbon(a, b, width + .3), p) for a, b in edges for p in natural):
            continue
        from .rivers import blocks_ground_connection
        if terrain and any(blocks_ground_connection(a, b, terrain) for a, b in edges):
            continue
        retained, removed = [], []
        for road in main:
            a, b = road["start"], road["end"]
            clipped = _clipped(a, b, poly)
            if not clipped or math.dist(*clipped) < .01:
                retained.append(road)
                continue
            middle = [(clipped[0][i] + clipped[1][i]) / 2 for i in (0, 1)]
            if not inside(middle, poly, .01):
                retained.append(road)  # Already on the boundary.
                continue
            removed.append(road["id"])
            for index, (p, q) in enumerate(((a, clipped[0]), (clipped[1], b))):
                if math.dist(p, q) > .001:
                    retained.append(dict(road, id=road["id"] + f":precinct-outside:{index}", start=point(p), end=point(q)))
        if not removed:
            continue
        ring = [dict(
            id="world:campus-perimeter:" + derive(identity, str(i), VERSION),
            start=point(a), end=point(b), width=width, access=False,
            structural=True, patternId=pattern["id"],
        ) for i, (a, b) in enumerate(edges)]
        result = retained + ring
        record = dict(version=VERSION, zoneId=identity, polygon=poly,
                      physicalProgram=demand, reservedArea=area(poly),
                      reroutedStreetIds=sorted(removed), perimeterStreetIds=[r["id"] for r in ring],
                      structural=True, relationship=False)
        updated = dict(pattern, campusReservation=record,
                       protectedStreetIds=sorted(r["id"] for r in result), roadCount=len(result))
        return result, updated
    return main, pattern
