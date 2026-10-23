"""Continuous district height fields, not a per-file importance ranking.

This migration consumer composes the existing physical geography. It does NOT
pretend to be the pending land-first downtown/campus master planners. A field
center is an aesthetic coordinate, never a newly discovered source entity.
"""

import math
from collections import defaultdict

from .geometry import point, q
from .urban_character import CharacterEngine, VERSION as CHARACTER_VERSION

VERSION = "district-skyline/0.1"
ALLOCATION_VERSION = "height-allocation/0.1"
MAX_CENTERS = 3


def district_skyline(world, graph):
    engine = CharacterEngine(graph)
    groups = defaultdict(list)
    for p in world["parcels"]:
        groups[p["districtId"]].append(p)
    districts, allocations = {}, {}
    for identity, sources in sorted(groups.items()):
        sources.sort(key=lambda p: p["entityId"])
        profile = engine.profile(identity, [p["entityId"] for p in sources], kind="district")
        # Functional neighborhood membership already exists. Preserve it; a
        # field blends across its border rather than making another hard zone.
        regions = defaultdict(list)
        for p in sources:
            regions[p.get("zoneId", identity)].append(p)
        candidates = []
        for region, members in sorted(regions.items()):
            center = [sum(p["center"][j] for p in members) / len(members) for j in (0, 1)]
            xx = sum((p["center"][0] - center[0]) ** 2 for p in members) / len(members)
            zz = sum((p["center"][1] - center[1]) ** 2 for p in members) / len(members)
            xz = sum((p["center"][0] - center[0]) * (p["center"][1] - center[1]) for p in members) / len(members)
            angle = 0.5 * math.atan2(2 * xz, xx - zz)
            radius = math.hypot(xx - zz, 2 * xz)
            axes = [max(12, math.sqrt(max(0, (xx + zz + sign * radius) / 2)) * 1.4)
                    for sign in (1, -1)]
            candidates.append(dict(regionId=region, center=point(center),
                                   axes=[q(v) for v in axes], angle=q(angle),
                                   sourceCount=len(members)))
        candidates.sort(key=lambda c: (-c["sourceCount"], c["regionId"]))
        centers = []
        for candidate in candidates:
            if centers and (candidate["sourceCount"] < max(12, candidates[0]["sourceCount"] * 0.35)
                            or any(math.dist(candidate["center"], c["center"]) < 32 for c in centers)):
                continue
            centers.append(dict(candidate, relativeStrength=q(1 if not centers else 0.8)))
            if len(centers) == MAX_CENTERS:
                break
        planning = profile["planning"]
        coverage = profile["facts"]["classifiedSourceCount"] / len(sources)
        # Pure structural fallback cannot become a CBD from a utility's fan-in.
        # With verified programs, aggregate district potential can influence
        # amplitude, never an individual entity's incoming reference count.
        amplitude = q(0.62 + 0.38 * min(1, coverage * planning["verticalPotential"] * 4))
        for p in sources:
            influence = 0
            for c in centers:
                dx, dz = [p["center"][i] - c["center"][i] for i in (0, 1)]
                co, si = math.cos(c["angle"]), math.sin(c["angle"])
                u, v = (co * dx + si * dz) / c["axes"][0], (-si * dx + co * dz) / c["axes"][1]
                influence = max(influence, c["relativeStrength"] * math.exp(-0.5 * (u * u + v * v)))
            allocations[p["entityId"]] = dict(
                version=ALLOCATION_VERSION, districtId=identity,
                fieldIntensity=q(amplitude * influence),
                basis="CONTINUOUS_DISTRICT_FIELD_NOT_FILE_REFERENCE_COUNT", derived=True)
        zone_characters = {}
        for region, members in sorted(regions.items()):
            if region == identity:
                continue
            zone = engine.profile(region, [p["entityId"] for p in members], kind="zone")["planning"]
            zone_characters[region] = dict(
                preferredTypology=zone["preferredTypology"], campusPotential=zone["campusPotential"],
                industrialPotential=zone["industrialPotential"], interfacePotential=zone["interfacePotential"])
        districts[identity] = dict(
            zones=zone_characters,
            characterVersion=CHARACTER_VERSION,
            sourceCount=len(sources), preferredTypology=planning["preferredTypology"],
            verticalPotential=planning["verticalPotential"], semanticCoverage=q(coverage),
            campusPotential=planning["campusPotential"], industrialPotential=planning["industrialPotential"],
            amplitude=amplitude, centers=centers,
            spatialDemand=profile["spatialDemand"])
    return dict(version=VERSION, presentationOnly=True, districts=districts,
                allocations=allocations,
                limitations=["Existing land is retained; this is not a constructed downtown master plan.",
                             "Height-field centers are aesthetic coordinates, not source facilities.",
                             "Certified campus complexes keep their site-scale massing."])


def allocated_height(capacity, form, allocation):
    """Use capacity, do not fill it indiscriminately. No universal height cap."""
    intensity = allocation["fieldIntensity"]
    if not math.isfinite(intensity) or not 0 <= intensity <= 1:
        raise ValueError("invalid district height field")
    if form in ("tower", "twin", "mast"):
        # Convex curve: quiet fringes, a few dramatic peaks at district cores.
        fraction = 0.24 + 0.76 * intensity ** 1.6
    elif form in ("bar", "terrace"):
        fraction = 0.5 + 0.5 * intensity
    elif form in ("court", "atrium", "gate", "pods", "archive"):
        fraction = 0.7 + 0.3 * intensity
    else:
        fraction = 0.88 + 0.12 * intensity
    return q(capacity * fraction)
