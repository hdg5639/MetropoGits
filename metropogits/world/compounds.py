"""Certified presentation-only role compounds for actual rotated World parcels."""

import math
from collections import defaultdict

from metropogits.street_diagonals import overlap
from .geometry import area, bounds, inside, point, q, rectangle, ribbon
from .seed import derive

VERSION = "world-role-compounds/0.1"
MAX_CHECKS = 300_000
MAX_INDEX = 500_000
MAX_CANDIDATES = 50_000


def role_key(parcel, evidence):
    rules = {evidence.get(k, {}).get("ruleId", "") for k in parcel["evidenceIds"]}
    if parcel["archetype"] == "LIBRARY" and "path.test-source" in rules:
        return "TEST"
    if parcel["archetype"] != "GATE":
        return None
    if "path.nextjs.app-page" in rules:
        return "PAGE"
    if "path.nextjs.route-handler" in rules:
        return "API"
    spring = sorted(k for k in rules if k.startswith("spring.controller"))
    return "GATE:" + ",".join(spring) if spring else None


def derive_compounds(world, graph, *, campus_landmarks=False):
    note = dict(version=VERSION, structural=False, checks=0, indexEntries=0)
    try:
        return _derive(world, graph, note, campus_landmarks=campus_landmarks), note
    except ValueError as error:
        if not str(error).startswith("role compound "):
            raise
        note["fallback"] = str(error)
        return [], note


def _derive(world, graph, note, *, campus_landmarks=False):
    from .elevation import surface, foundation_faces

    parcels = sorted(world["parcels"], key=lambda p: p["entityId"])
    if len(parcels) > 10_000 or len(world["streets"]) > 50_000:
        raise ValueError("role compound input limit")
    evidence = {e["evidenceId"]: e for e in graph["evidence"]}
    entities = {e["id"]: e for e in graph["entities"]}
    modules = sorted(
        (e for e in graph["entities"] if e["kind"] == "MODULE"),
        key=lambda e: (-len(e["path"]), e["id"]),
    )
    zones = {z["id"]: z["polygon"] for z in world.get("zoning", {}).get("zones", [])}
    zones.update({d["id"]: d["polygon"] for d in world["districts"]})
    groups = defaultdict(list)
    campus_zones = {z["id"]: z for z in world.get("zoning", {}).get("zones", [])}
    campus_members = (
        {
            s["zoneId"]: set(s["memberEntityIds"])
            for s in world.get("campusPlan", {}).get("sites", [])
        }
        if campus_landmarks
        else {}
    )
    planned_sites = {
        identity: set(site["memberEntityIds"])
        for campus_site in world.get("campusPlan", {}).get("sites", [])
        for site in campus_site.get("architecturalSites", [])
        for identity in site["memberEntityIds"]
    } if campus_landmarks else {}
    links = defaultdict(dict)
    if campus_members:
        from .campus_landmarks import campus_affinity

        pairs = campus_affinity(
            graph,
            {
                p["entityId"]: p.get("zoneId", p["districtId"])
                for p in parcels
                if p["entityId"]
                in campus_members.get(p.get("zoneId", p["districtId"]), set())
            },
        )
        for (a, b), weight in pairs.items():
            links[a][b] = links[b][a] = weight
        note["campusLandmarks"] = dict(
            version="campus-landmarks/0.1", selected=0, rejected=0
        )
    for p in parcels:
        role = role_key(p, evidence)
        zone = p.get("zoneId", p["districtId"])
        eligible_campus = (
            p["entityId"] in campus_members.get(zone, set()) and links[p["entityId"]]
        )
        if role is None and not eligible_campus:
            continue
        path = entities[p["entityId"]]["path"]
        owner = next((m["id"] for m in modules if path.startswith(m["path"] + "/")), "")
        if eligible_campus:
            groups[zone, owner, "CAMPUS"].append(p)
        if role is not None:
            groups[zone, owner, role].append(p)
    obstacles = []
    index = defaultdict(set)

    def cells(poly):
        x, z, X, Z = bounds(poly)
        if (math.floor(X / 32) - math.floor(x / 32) + 1) * (
            math.floor(Z / 32) - math.floor(z / 32) + 1
        ) > MAX_INDEX:
            raise ValueError("role compound index limit")
        return [
            (i, j)
            for i in range(math.floor(x / 32), math.floor(X / 32) + 1)
            for j in range(math.floor(z / 32), math.floor(Z / 32) + 1)
        ]

    def add(poly, kind, item):
        keys = cells(poly)
        note["indexEntries"] += len(keys)
        if note["indexEntries"] > MAX_INDEX:
            raise ValueError("role compound index limit")
        n = len(obstacles)
        obstacles.append((poly, kind, item))
        for k in keys:
            index[k].add(n)

    for p in parcels:
        add(p["parcel"], "parcel", p)
    for r in world["streets"]:
        add(ribbon(r["start"], r["end"], r["width"]), "street", r)
    for f in world.get("terrain", {}).get("features", []):
        add(f["noBuildPolygon"], "nature", f)
    for site in world.get("campusPlan", {}).get("sites", []):
        for court in site["courts"]:
            add(court["polygon"], "court", court)
    field = surface(world["terrain"]) if "surface" in world else None

    def envelope(members, campus=False):
        angle = members[0]["angle"]
        c, s = math.cos(angle), math.sin(angle)
        vertices = [p for b in members for p in b["parcel" if campus else "footprint"]]
        lo, zo, hi, zh = bounds(
            [[c * p[0] + s * p[1], -s * p[0] + c * p[1]] for p in vertices]
        )
        width, depth = hi - lo, zh - zo
        if max(width, depth) > 56 or sum(
            area(b["parcel" if campus else "footprint"]) for b in members
        ) / (width * depth) < (0.55 if campus else 0.43):
            return None
        center = point(
            [
                c * (lo + hi) / 2 - s * (zo + zh) / 2,
                s * (lo + hi) / 2 + c * (zo + zh) / 2,
            ]
        )
        poly = rectangle(center, angle, width, depth)
        return dict(
            center=center, angle=angle, width=q(width), depth=q(depth), footprint=poly
        )

    def proposal(members, zone, eligible, campus=False):
        members = members[:]
        # Absorb every equally evidenced occupant of a growing envelope, rather
        # than drawing over an omitted file or refusing every two-row complex.
        for _ in range(16):
            model = envelope(members, campus)
            if model is None:
                return None
            poly = model["footprint"]
            if not all(inside(p, zones[zone], 0.1) for p in poly):
                return None
            ids = {b["entityId"] for b in members}
            extra = []
            for i in sorted({i for k in cells(poly) for i in index[k]}):
                shape, kind, item = obstacles[i]
                if kind != "parcel" or item["entityId"] in ids:
                    continue
                note["checks"] += 1
                if note["checks"] > MAX_CHECKS:
                    raise ValueError("role compound clearance limit")
                if overlap(poly, shape):
                    if item["entityId"] not in eligible or (
                        campus and not any(links[item["entityId"]].get(k) for k in ids)
                    ):
                        return None
                    extra.append(item)
            if not extra:
                break
            if len(members) + len(extra) > 16:
                return None
            members += extra
        else:
            return None
        ids = {b["entityId"] for b in members}
        doors = {tuple(b["entrance"]) for b in members}
        for i in sorted({i for k in cells(poly) for i in index[k]}):
            shape, kind, item = obstacles[i]
            if kind == "parcel" and item["entityId"] in ids:
                continue
            if (
                kind == "street"
                and item["access"]
                and any(tuple(item[k]) in doors for k in ("start", "end"))
            ):
                continue
            note["checks"] += 1
            if note["checks"] > MAX_CHECKS:
                raise ValueError("role compound clearance limit")
            if overlap(poly, shape):
                return None
        low, high = field.range(poly) if field else (0, 0)
        if high - low > 1.5:
            return None
        model.update(baseElevation=q(high), foundationLow=q(low))
        return model, members

    result = []
    candidate_checks = 0
    reserved = set()
    site_counts = defaultdict(int)
    for (zone, owner, role), members in sorted(groups.items()):
        campus = role == "CAMPUS"
        available = {p["entityId"] for p in members} - reserved
        ordered = (
            sorted(
                members,
                key=lambda p: (-sum(links[p["entityId"]].values()), p["entityId"]),
            )
            if campus
            else members
        )
        limit = 1 + min(3, len(campus_members.get(zone, ())) // 48)
        if campus and (world.get("campusPlan", {}).get("style") == "estate" or (
            world.get("campusPlan", {}).get("style") == "precinct"
            and any(b['entityId'] in planned_sites for b in members)
        )):
            limit = 4
        for seed in ordered:
            if campus and site_counts[zone] >= limit:
                break
            if seed["entityId"] not in available:
                continue
            chosen = [seed]
            model = None
            for b in sorted(
                (b for b in members if b["entityId"] in available and b != seed),
                key=lambda b: (math.dist(b["center"], seed["center"]), b["entityId"]),
            ):
                if campus and seed["entityId"] in planned_sites and b["entityId"] not in planned_sites[seed["entityId"]]:
                    continue
                candidate_checks += 1
                if candidate_checks > MAX_CANDIDATES:
                    raise ValueError("role compound candidate limit")
                if len(chosen) >= 16:
                    break
                if min(math.dist(b["center"], p["center"]) for p in chosen) > (
                    22 if campus else 16
                ):
                    continue
                if campus and not any(
                    links[b["entityId"]].get(p["entityId"]) for p in chosen
                ):
                    continue
                if b in chosen:
                    continue
                candidate = proposal(chosen + [b], zone, available, campus)
                if candidate:
                    model, chosen = candidate
            if len(chosen) < (2 if campus else 4) or (
                campus and model and model["width"] * model["depth"] < 90
            ):
                if campus:
                    note["campusLandmarks"]["rejected"] += 1
                continue
            ids = sorted(p["entityId"] for p in chosen)
            available.difference_update(ids)
            reserved.update(ids)
            identity = "visual:world-role:" + derive(VERSION, *ids)
            height = min(30, 12 + math.log2(len(chosen)) * 3)
            # A shared hall/concourse with a bounded roof/anchor, not N gates.
            specs = (
                [
                    (0, 0, 0, 1, 0.28, 1),
                    (0.06, 0.28, 0.14, 0.88, 0.48, 0.72),
                    (0.72, 0.76, 0.34, 0.18, 0.24, 0.3),
                ]
                if role == "TEST"
                else [
                    (0.03, 0, 0.2, 0.94, 0.4, 0.76),
                    (0.02, 0.4, 0.17, 0.96, 0.14, 0.8),
                    (0.12, 0, 0, 0.76, 0.3, 0.24),
                    (0.73, 0.54, 0.4, 0.18, 0.46, 0.3),
                ]
            )
            parts = []
            c, s = math.cos(model["angle"]), math.sin(model["angle"])
            for x, y, z, w, h, d in specs:
                u = (x + w / 2 - 0.5) * model["width"]
                v = (z + d / 2 - 0.5) * model["depth"]
                at = [
                    model["center"][0] + c * u - s * v,
                    model["center"][1] + s * u + c * v,
                ]
                parts.append(
                    dict(
                        footprint=rectangle(
                            at, model["angle"], w * model["width"], d * model["depth"]
                        ),
                        y=q(model["baseElevation"] + y * height),
                        height=q(h * height),
                    )
                )
            model["parts"] = parts
            model["foundationFaces"] = (
                foundation_faces(model, world["terrain"]) if field else []
            )
            x, z, X, Z = bounds(model["footprint"])
            tier = "campus" if len(chosen) >= 12 else "center"
            title = (
                "Test " + tier
                if role == "TEST"
                else (
                    "Page"
                    if role == "PAGE"
                    else "API"
                    if role == "API" or ".rest" in role
                    else "Entry"
                )
                + " "
                + ("terminal" if tier == "campus" else "hall")
            )
            result.append(
                dict(
                    id=identity,
                    role=role,
                    tier=tier,
                    title=title,
                    x=x,
                    z=z,
                    width=X - x,
                    depth=Z - z,
                    height=height,
                    labelX=model["center"][0],
                    labelZ=model["center"][1],
                    districtId=zone,
                    majorDistrictId=seed["districtId"],
                    memberEntityIds=ids,
                    memberDistrictIds=sorted({p["districtId"] for p in chosen}),
                    evidenceIds=sorted({e for p in chosen for e in p["evidenceIds"]}),
                    archetypeCounts=[
                        dict(archetype=seed["archetype"], count=len(chosen))
                    ],
                    plots=[dict(x=x, z=z, width=X - x, depth=Z - z)],
                    physicalModel=model,
                )
            )
            if campus:
                from .campus_landmarks import decorate

                result[-1].update(
                    decorate(
                        model,
                        chosen,
                        campus_zones[zone],
                        graph,
                        links,
                        field,
                        world.get("terrain"),
                    )
                )
                site_counts[zone] += 1
                note["campusLandmarks"]["selected"] += 1
            # Empty interstitial space may belong to a previous compound's
            # checked envelope even when no original parcel occupies it.
            add(model["footprint"], "compound", result[-1])
    return sorted(result, key=lambda f: f["id"])
