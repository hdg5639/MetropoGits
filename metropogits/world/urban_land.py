"""Bounded physical land admission, before architecture, with pinned front doors.

The original World remains the strict source-address/collision baseline. This
opt-in derived plan reassigns vacant reserves, never protected terrain or roads.
An unfulfilled request is deferred, not secretly shrunk to a nominal tiny lot.
"""

import math
from collections import Counter, defaultdict

from metropogits.street_diagonals import overlap, hull
from .geometry import bounds, inside, point, q, rectangle, ribbon
from .seed import derive
from .urban_character import CharacterEngine, verified_claims, DEMAND_VERSION

VERSION = "urban-land/0.1"
MAX_CHECKS = 1_000_000
MAX_INDEX = 500_000


class ClearanceIndex:
    def __init__(self):
        self.cells, self.shapes = defaultdict(set), {}
        self.checks = self.entries = 0

    def cells_for(self, poly):
        a, b, c, d = bounds(poly)
        x0, z0, x1, z1 = math.floor(a / 32), math.floor(b / 32), math.floor(c / 32), math.floor(d / 32)
        if (x1 - x0 + 1) * (z1 - z0 + 1) > MAX_INDEX:
            raise ValueError("urban land index limit")
        return [(x, z) for x in range(x0, x1 + 1) for z in range(z0, z1 + 1)]

    def add(self, key, polygon):
        self.shapes[key] = polygon
        for cell in self.cells_for(polygon):
            self.cells[cell].add(key)
            self.entries += 1
            if self.entries > MAX_INDEX:
                raise ValueError("urban land index limit")

    def clear(self, polygon, ignored):
        for key in sorted({k for cell in self.cells_for(polygon) for k in self.cells[cell]} - ignored):
            self.checks += 1
            if self.checks > MAX_CHECKS:
                raise ValueError("urban land clearance limit")
            if overlap(polygon, self.shapes[key]):
                return False
        return True


def request(source, entity, evidence, district_demand):
    claims = verified_claims(entity, "roles", evidence)
    roles = {c["value"] for c in claims}
    if roles & {"PERSISTENCE_ADAPTER", "OBJECT_STORAGE_ADAPTER", "DATA_PROCESSOR", "ML_COMPONENT"}:
        kind, width, depth = "HORIZONTAL_WORKS", 16, 12
    elif roles & {"SERVICE", "ENTRYPOINT", "API_ENDPOINT", "UI_PAGE", "UI_COMPONENT"}:
        kind, width, depth = "MIXED_OFFICE", 12, 10
    elif roles & {"TEST", "DATA_MODEL", "GENERAL_COMPONENT"}:
        kind, width, depth = "SUPPORT_BLOCK", 10, 8
    else:
        kind, width, depth = "NEUTRAL_BLOCK", 8, 8
    # Request land from the evidenced district program, not source fan-in.
    if district_demand["perSourceUnits"] >= 1.8:
        depth += 2
    width, depth = max(source["width"], width), max(source["depth"], depth)
    return dict(kind=kind, width=width, depth=depth, area=q(width * depth),
                evidenceIds=sorted({k for c in claims for k in c["evidenceIds"]}),
                demandVersion=DEMAND_VERSION, derived=True)


def _baseline(world, compounds):
    index = ClearanceIndex()
    sources = {p["entityId"]: p for p in world["parcels"]}
    doors = defaultdict(set)
    for p in sources.values():
        index.add(("source", p["entityId"]), rectangle(p["center"], p["angle"], p["width"] + .4, p["depth"] + .4))
        doors[tuple(p["entrance"])].add(("source", p["entityId"]))
    own_access = defaultdict(set)
    junctions = defaultdict(list)
    for r in world["streets"]:
        key = ("road", r["id"])
        index.add(key, ribbon(r["start"], r["end"], r["width"]))
        if r["access"]:
            for at in (r["start"], r["end"]):
                for source in doors.get(tuple(at), ()):
                    own_access[source[1]].add(key)
        else:
            for at, other in ((r["start"], r["end"]), (r["end"], r["start"])):
                length = math.dist(at, other)
                normal = [-(other[1] - at[1]) / length, (other[0] - at[0]) / length]
                junctions[tuple(at)].extend(point([at[j] + side * normal[j] * r["width"] / 2 for j in (0, 1)]) for side in (-1, 1))
    # Protect the bevel/crossing surface too, not just individual road ribbons.
    for number, (_, tips) in enumerate(sorted(junctions.items())):
        if len(tips) >= 4:
            polygon = hull(tips)
            if len(polygon) >= 3:
                index.add(("junction", str(number)), polygon)
    for f in world.get("terrain", {}).get("features", []):
        index.add(("terrain", f["id"]), f["noBuildPolygon"])
    protected = set()
    for f in compounds:
        protected.update(f["memberEntityIds"])
        index.add(("complex", f["id"]), f["physicalModel"]["footprint"])
    for site in world.get("campusPlan", {}).get("sites", []):
        protected.update(site["memberEntityIds"])
        for court in site["courts"]:
            index.add(("court", court["id"]), court["polygon"])
    return index, own_access, protected


def admit_land(world, graph, compounds):
    engine = CharacterEngine(graph)
    members = defaultdict(list)
    for p in world["parcels"]:
        members[p["districtId"]].append(p["entityId"])
    demands = {k: engine.profile(k, v, kind="district")["spatialDemand"] for k, v in sorted(members.items())}
    index, access, protected = _baseline(world, compounds)
    zones = {z["id"]: z["polygon"] for z in world.get("zoning", {}).get("zones", [])}
    zones.update({d["id"]: d["polygon"] for d in world["districts"]})
    from .elevation import surface
    field = surface(world["terrain"]) if "surface" in world else None
    requests = {p["entityId"]: request(p, engine.files[p["entityId"]], engine.evidence, demands[p["districtId"]]) for p in world["parcels"]}
    parcels, decisions = {}, {}
    # Path/seed order is stable, not a global importance percentile ranking.
    for p in sorted(world["parcels"], key=lambda p: derive(world["seed"], VERSION, p["entityId"])):
        identity = p["entityId"]
        wanted = requests[identity]
        decision = dict(request=wanted, status="PRESERVED_COMPLEX" if identity in protected else "DEFERRED_REPLAN",
                        sourceEnvelope={k: p[k] for k in ("center", "angle", "width", "depth", "footprint")})
        model = dict(p)
        if identity not in protected:
            w, d = wanted["width"], wanted["depth"]
            # Equal-area alternatives, not reduced-capacity variants. Frontage
            # and the original access point remain fixed, even on diagonal roads.
            candidates = [(w, d), (q(w * 1.25), q(d / 1.25)), (q(w / 1.25), q(d * 1.25))]
            for width, depth in candidates:
                if width < p["width"] or depth < p["depth"]:
                    continue
                facing = [-math.sin(p["angle"]), math.cos(p["angle"])]
                center = point([p["center"][i] - facing[i] * (depth - p["depth"]) / 2 for i in (0, 1)])
                poly = rectangle(center, p["angle"], width, depth)
                if not all(inside(v, zones[p.get("zoneId", p["districtId"])], .3) for v in poly):
                    continue
                if not index.clear(poly, {("source", identity)} | access[identity]):
                    continue
                low, high = field.range(poly) if field else (0, 0)
                if high - low > 1.5:
                    continue
                model.update(center=center, width=width, depth=depth, footprint=poly, parcel=poly)
                if field:
                    model.update(baseElevation=q(high), foundationLow=q(low))
                decision.update(status="ADMITTED", allocatedArea=q(width * depth))
                index.add(("source", identity), rectangle(center, p["angle"], width + .4, depth + .4))
                break
        decision["allocatedEnvelope"] = {k: model[k] for k in ("center", "angle", "width", "depth", "footprint")}
        decisions[identity] = decision
        parcels[identity] = model
    plan = dict(version=VERSION, structural=False, derived=True,
                basis="PHYSICAL_LAND_ADMISSION_NOT_NEW_SOURCE_FACTS", decisions=dict(sorted(decisions.items())),
                districtDemands=demands, counts=dict(sorted(Counter(d["status"] for d in decisions.values()).items())),
                checks=index.checks, indexEntries=index.entries,
                limitations=["Insufficient land requires later local replanning; requests are not silently shrunk.",
                             "Original World remains a source-address baseline; admitted physical envelopes are explicit."])
    return dict(world, parcels=[parcels[p["entityId"]] for p in world["parcels"]]), plan


def validate_land(world, physical, graph, compounds, plan):
    """Reconstruct admission; independently check final physical exclusion."""
    expected, record = admit_land(world, graph, compounds)
    if plan != record or physical != expected:
        raise ValueError("urban land allocation mismatch")
    index, access, protected = _baseline(world, compounds)
    originals = {p["entityId"]: p for p in world["parcels"]}
    for p in physical["parcels"]:
        identity = p["entityId"]
        original = originals[identity]
        if any(p[k] != original[k] for k in ("entityId", "districtId", "entrance", "streetPoint", "angle", "height", "archetype", "evidenceIds")):
            raise ValueError("urban land changed source ownership or access")
        if identity in protected or plan["decisions"][identity]["status"] != "ADMITTED":
            if p != original:
                raise ValueError("urban land changed retained source")
            continue
        if not index.clear(p["footprint"], {("source", identity)} | access[identity]):
            raise ValueError("urban land physical overlap")
        if not all(inside(v, p["footprint"], -.001) for v in original["footprint"]):
            raise ValueError("urban land lost original address envelope")
        index.add(("source", identity), p["footprint"])
