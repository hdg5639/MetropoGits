"""Bounded, evidence-selected courtyard morphology; never a new source role."""

import math
from collections import defaultdict

from metropogits.street_diagonals import overlap
from .geometry import bounds, centroid, inside, nearest, point, q, rectangle, ribbon
from .seed import derive, draw

VERSION = "campus-plan/0.1"
MAX_CENTERS = 384
MAX_CHECKS = 200_000
MAX_WALKS = 256
WALK_WIDTH = 1.2


def eligibility(zone, pairs, seed):
    ids = set(zone["memberEntityIds"])
    supported = {}
    for item in zone.get("memberClaims", []):
        evidence = sorted(
            {
                ev
                for role in item["roles"]
                if role["value"] == "TEST"
                and role["confidence"] in ("DIRECT", "RESOLVED")
                for ev in role["evidenceIds"]
            }
        )
        if item["entityId"] in ids and evidence:
            supported[item["entityId"]] = evidence
    internal = sum(1 for a, b in pairs if a in ids and b in ids)
    external = sum(1 for a, b in pairs if (a in ids) != (b in ids))
    outside = external / max(1, internal + external)
    evidence_ok = len(supported) >= max(4, math.ceil(len(ids) * 0.06))
    cohesive = internal >= len(ids) and outside <= 0.25
    eligible = len(ids) >= 12 and (evidence_ok or cohesive)
    probability = (
        min(
            0.85,
            0.35
            + 0.4 * min(1, len(supported) / max(4, len(ids) * 0.35))
            + (0.15 if cohesive else 0),
        )
        if eligible
        else 0
    )
    roll = draw(derive(seed, zone["id"], VERSION, "choice"))
    return dict(
        eligible=eligible,
        status="RETAINED",
        reason="NOT_ELIGIBLE"
        if not eligible
        else "SEEDED_OTHER_GRAMMAR"
        if roll >= probability
        else "AWAITING_CAPACITY",
        probability=q(probability),
        draw=q(roll),
        internalPairCount=internal,
        externalPairCount=external,
        supportingEntityIds=sorted(supported),
        evidenceIds=sorted({e for v in supported.values() for e in v}),
    )


def _quad(center, axis, a, b, exit_side, seed):
    c, s = math.cos(axis), math.sin(axis)

    def place(p):
        return point([center[0] + c * p[0] - s * p[1], center[1] + s * p[0] + c * p[1]])

    identity = "world:campus-court:" + derive(seed, str(center), str([a, b]))
    choices = []

    def lot(local, angle, front, at, key):
        center = place(local)
        choices.append(
            dict(
                id=identity + ":lot:" + key,
                center=center,
                angle=axis + angle,
                polygon=rectangle(center, axis + angle, 7.98, 7.98),
                entrance=place([local[j] + front[j] * 3 for j in (0, 1)]),
                streetPoint=place(at),
                laneId=identity,
                blockProfile="CAMPUS",
            )
        )

    for side in (-1, 1):
        for i in range(-math.floor((a - 7) / 8), math.floor((a - 7) / 8) + 1):
            if i == 0 and exit_side == ("N" if side == 1 else "S"):
                continue
            lot(
                [i * 8, side * (b + 5)],
                math.pi if side == 1 else 0,
                [0, -side],
                [i * 8, side * b],
                f"z:{side}:{i}",
            )
        for i in range(-math.floor((b - 7) / 8), math.floor((b - 7) / 8) + 1):
            if i == 0 and exit_side == ("E" if side == 1 else "W"):
                continue
            lot(
                [side * (a + 5), i * 8],
                side * math.pi / 2,
                [-side, 0],
                [side * a, i * 8],
                f"x:{side}:{i}",
            )
    for x in (-1, 1):
        for z in (-1, 1):
            front = [-x / math.sqrt(2), -z / math.sqrt(2)]
            lot(
                [x * (a + 5 / math.sqrt(2)), z * (b + 5 / math.sqrt(2))],
                math.atan2(-front[0], front[1]),
                front,
                [x * a, z * b],
                f"corner:{x}:{z}",
            )
    corners = [place(p) for p in ((-a, -b), (a, -b), (a, b), (-a, b))]
    walks = [
        dict(
            id=identity + ":walk:" + str(i),
            start=p,
            end=r,
            width=WALK_WIDTH,
            access=False,
            structural=True,
        )
        for i, (p, r) in enumerate(zip(corners, corners[1:] + corners[:1]))
    ]
    edge, outer = {
        "N": ([0, b], [0, b + 12]),
        "S": ([0, -b], [0, -b - 12]),
        "E": ([a, 0], [a + 12, 0]),
        "W": ([-a, 0], [-a - 12, 0]),
    }[exit_side]
    walks.append(
        dict(
            id=identity + ":exit",
            start=place(edge),
            end=place(outer),
            width=WALK_WIDTH,
            access=False,
            structural=True,
        )
    )
    court = dict(
        id=identity,
        center=point(center),
        polygon=rectangle(center, axis, 2 * (a - 1.25), 2 * (b - 1.25)),
    )
    return choices, walks, court, rectangle(center, axis, 2 * (a + 9.5), 2 * (b + 9.5))


def courtyard_layout(
    zone,
    polygon,
    axis,
    seed,
    roads,
    terrain,
    pairs,
    diagnostics=None,
    max_courts=3,
    variant="ACADEMIC_QUAD",
):
    """Reserve courts, then plots/walks. Return None, never grow global land."""
    n = len(zone["memberEntityIds"])
    if n > 116 or not roads:
        return None
    checks = 0
    stats = diagnostics if diagnostics is not None else {}
    stats.update(
        outside=0, blockedCourt=0, blockedWalk=0, disconnected=0, maxCapacity=0
    )
    natural = [f["noBuildPolygon"] for f in (terrain or {}).get("features", [])]
    road_shapes = [ribbon(r["start"], r["end"], r["width"] + 0.4) for r in roads]
    boxes = [(bounds(p), p) for p in road_shapes + natural]

    def collides(poly, obstacles):
        nonlocal checks
        x0, z0, x1, z1 = bounds(poly)
        for box, other in obstacles:
            if x1 < box[0] or box[2] < x0 or z1 < box[1] or box[3] < z0:
                continue
            checks += 1
            if checks > MAX_CHECKS:
                raise ValueError("campus clearance work limit")
            if overlap(poly, other):
                return True
        return False

    c, s = math.cos(axis), math.sin(axis)
    local = [[c * p[0] + s * p[1], -s * p[0] + c * p[1]] for p in polygon]
    x0, z0, x1, z1 = bounds(local)
    nx, nz = (
        min(16, max(1, math.floor((x1 - x0) / 10))),
        min(16, max(1, math.floor((z1 - z0) / 10))),
    )
    centers = [
        point([c * x - s * z, s * x + c * z])
        for x in (x0 + (i + 0.5) * (x1 - x0) / nx for i in range(nx))
        for z in (z0 + (j + 0.5) * (z1 - z0) / nz for j in range(nz))
    ]
    if len(centers) > MAX_CENTERS:
        raise ValueError("campus candidate limit")
    middle = centroid(polygon)
    centers.sort(key=lambda p: (math.dist(p, middle), derive(seed, str(p))))

    def walk_clear(walk, obstacles):
        a, b = walk["start"], walk["end"]
        if math.dist(a, b) < 0.001 or not all(
            inside(p, polygon, -0.001) for p in (a, b)
        ):
            return False
        if collides(ribbon(a, b, WALK_WIDTH + 0.15), obstacles):
            return False
        if terrain and "elevation" in terrain:
            from .elevation import surface
            from .rivers import blocks_ground_connection

            if blocks_ground_connection(a, b, terrain):
                return False
            profile = surface(terrain).profile(a, b)
            if any(
                abs(y[2] - x[2]) / math.dist(x[:2], y[:2]) > 0.1598
                for x, y in zip(profile, profile[1:])
            ):
                return False
        return True

    # A court is shared space surrounded by actual files, not a large vacant
    # landscape patch with every building on one side. Bound lawn per member.
    configs = (
        ((17, 13),)
        if variant == "TECH_PARK"
        else ((17, 13), (25, 17), (33, 21), (41, 25), (49, 29))
    )
    for a, b in configs:
        required = (
            9
            if variant == "TECH_PARK"
            else max(9, math.ceil(4 * (a - 1.25) * (b - 1.25) / 120) + 1)
        )
        if required > min(32, max(8, n // 3)) + 1:
            continue
        chosen, footprints, plots, walks, courts = [], [], [], [], []
        for center in centers:
            shell = rectangle(center, axis, 2 * (a + 9.5), 2 * (b + 9.5))
            if not all(inside(p, polygon, 2) for p in shell) or collides(
                shell, [(bounds(p), p) for p in footprints]
            ):
                stats["outside"] += 1
                continue
            lawn = rectangle(center, axis, 2 * (a - 1.25), 2 * (b - 1.25))
            if (variant == "ACADEMIC_QUAD" and collides(lawn, boxes)) or collides(
                shell, [(bounds(p), p) for p in natural]
            ):
                stats["blockedCourt"] += 1
                continue
            for side in sorted(
                ("N", "E", "S", "W"), key=lambda k: derive(seed, str(center), k)
            ):
                if variant == "TECH_PARK":
                    from .campus_forms import tech_park

                    candidates, ring, new_courts, shell = tech_park(
                        center, axis, a, b, side, seed
                    )
                    if any(collides(c["polygon"], boxes) for c in new_courts):
                        stats["blockedCourt"] += 1
                        continue
                else:
                    candidates, ring, court, shell = _quad(
                        center, axis, a, b, side, seed
                    )
                    new_courts = [court]
                candidates = [
                    p
                    for p in candidates
                    if not collides(p["polygon"], boxes)
                    and not collides(
                        p["polygon"],
                        [
                            (
                                bounds(ribbon(w["start"], w["end"], WALK_WIDTH + 0.15)),
                                ribbon(w["start"], w["end"], WALK_WIDTH + 0.15),
                            )
                            for w in walks
                        ],
                    )
                ]
                if terrain:
                    from .elevation import suitable

                    if "elevation" in terrain:
                        candidates = [p for p in candidates if suitable(p, terrain)]
                sides = {
                    p["id"].split(":lot:")[1].rsplit(":", 1)[0]
                    for p in candidates
                    if ":lot:corner:" not in p["id"]
                }
                if len(candidates) < required or len(sides) < 3:
                    continue
                obstacles = [
                    (bounds(p["polygon"]), p["polygon"]) for p in plots + candidates
                ]
                obstacles += [
                    (bounds(p["polygon"]), p["polygon"]) for p in courts + new_courts
                ]
                obstacles += [(bounds(p), p) for p in natural]
                if not all(walk_clear(w, obstacles) for w in ring):
                    stats["blockedWalk"] += 1
                    continue
                at = ring[-1]["end"]
                targets = sorted(
                    {tuple(point(nearest(at, r["start"], r["end"]))) for r in roads},
                    key=lambda p: (math.dist(at, p), p),
                )[:8]
                connection = None
                for target in targets:
                    options = [
                        [at, list(target)],
                        [at, [at[0], target[1]], list(target)],
                        [at, [target[0], at[1]], list(target)],
                    ]
                    for path in options:
                        segments = [
                            dict(
                                id=new_courts[0]["id"] + ":join:" + str(i),
                                start=x,
                                end=y,
                                width=WALK_WIDTH,
                                access=False,
                                structural=True,
                            )
                            for i, (x, y) in enumerate(zip(path, path[1:]))
                            if math.dist(x, y) >= 0.001
                        ]
                        if segments and all(walk_clear(w, obstacles) for w in segments):
                            connection = segments
                            break
                    if connection:
                        break
                if connection is None:
                    stats["disconnected"] += 1
                    continue
                chosen.append(center)
                footprints.append(shell)
                plots.extend(candidates)
                walks.extend(ring + connection)
                courts.extend(new_courts)
                stats["maxCapacity"] = max(stats["maxCapacity"], len(plots))
                break
            if len(plots) >= min(32, max(8, n // 3)) + 1 or len(chosen) == max_courts:
                break
        # The pilot is a source-mixed enclave, not a compulsory whole-zone sort.
        if len(plots) >= 9:
            if len(walks) > MAX_WALKS:
                raise ValueError("campus walkway limit")
            degree = defaultdict(float)
            for (x, y), weight in pairs.items():
                if x in zone["memberEntityIds"] and y in zone["memberEntityIds"]:
                    degree[x] += weight
                    degree[y] += weight
            anchors = sorted(zone["memberEntityIds"], key=lambda k: (-degree[k], k))[
                : len(courts)
            ]
            return (
                plots,
                walks,
                dict(
                    zoneId=zone["id"],
                    parentId=zone["parentId"],
                    variant=variant,
                    memberEntityIds=zone["memberEntityIds"],
                    anchorEntityIds=anchors,
                    courts=courts,
                    walkways=walks,
                    axis=axis,
                    capacity=len(plots),
                    envelopes=footprints,
                ),
            )
    return None


def _mixed_pocket(plan, layout, zone, pairs, roads, diagnostics=None):
    """Replace vacant local addresses, keeping only actually connected supply."""
    from .infrastructure import atomic_streets
    from .terrain import outside

    plots, walks, site = layout
    stats = diagnostics if diagnostics is not None else {}
    original, lanes, axis, regions = plan
    shells = site["envelopes"]
    kept = []
    for lane in lanes:
        pieces = [(lane["start"], lane["end"])]
        for shell in shells:
            pieces = [s for a, b in pieces for s in outside(a, b, shell)]
        kept.extend(
            dict(lane, start=a, end=b, id=lane["id"] + ":campus-cut:" + str(i))
            for i, (a, b) in enumerate(pieces)
        )
    path_shapes = [ribbon(w["start"], w["end"], w["width"] + 0.2) for w in walks]
    choices = [
        p
        for p in original
        if not any(
            overlap(p["polygon"], s) or inside(p["streetPoint"], s) for s in shells
        )
        and not any(
            overlap(p["polygon"], s)
            or overlap(ribbon(p["entrance"], p["streetPoint"], 0.9), s)
            for s in path_shapes
        )
    ]
    stats.update(
        originalCapacity=len(original),
        retainedCapacityBeforeAccess=len(choices),
        campusCapacity=len(plots),
    )
    graph = atomic_streets(kept + walks + roads)
    adjacency = defaultdict(set)
    for r in graph:
        a, b = tuple(r["start"]), tuple(r["end"])
        adjacency[a].add(b)
        adjacency[b].add(a)
    reached = {
        tuple(p) for r in roads for p in (r["start"], r["end"]) if tuple(p) in adjacency
    }
    queue = list(sorted(reached))
    while queue:
        at = queue.pop()
        for other in sorted(adjacency[at] - reached):
            reached.add(other)
            queue.append(other)
    connected = [r for r in graph if tuple(r["start"]) in reached]
    index = defaultdict(list)
    entries = 0
    for r in connected:
        lo, zo, hi, zh = bounds([r["start"], r["end"]])
        for x in range(
            math.floor((lo - 0.002) / 32), math.floor((hi + 0.002) / 32) + 1
        ):
            for z in range(
                math.floor((zo - 0.002) / 32), math.floor((zh + 0.002) / 32) + 1
            ):
                index[x, z].append(r)
                entries += 1
                if entries > 200_000:
                    raise ValueError("campus access index limit")
    checks = 0

    def attached(at):
        nonlocal checks
        near = index[math.floor(at[0] / 32), math.floor(at[1] / 32)]
        checks += len(near)
        if checks > MAX_CHECKS:
            raise ValueError("campus access work limit")
        return any(
            math.dist(at, nearest(at, r["start"], r["end"])) < 0.002 for r in near
        )

    choices = [p for p in choices if attached(p["streetPoint"])]
    kept = [
        r for r in kept if attached([(r["start"][j] + r["end"][j]) / 2 for j in (0, 1)])
    ]
    if not all(attached(p["streetPoint"]) for p in plots):
        stats["rejected"] = "DISCONNECTED_CAMPUS"
        return None
    quota = min(len(plots) - 1, 32, max(8, len(zone["memberEntityIds"]) // 3))
    degree = defaultdict(float)
    neighbors = defaultdict(set)
    ids = set(zone["memberEntityIds"])
    for (a, b), w in pairs.items():
        if a in ids and b in ids:
            degree[a] += w
            degree[b] += w
            neighbors[a].add(b)
            neighbors[b].add(a)
    proven = set(eligibility(zone, pairs, "membership")["supportingEntityIds"])
    chosen = sorted(proven, key=lambda k: (-degree[k], k))[: max(4, quota // 2)]
    if not chosen:
        chosen = sorted(ids, key=lambda k: (-degree[k], k))[:1]
    while len(chosen) < quota:
        candidates = (set().union(*(neighbors[k] for k in chosen)) | proven) - set(
            chosen
        )
        if not candidates:
            break
        chosen.append(
            min(
                candidates,
                key=lambda k: (
                    k in proven,
                    -len(neighbors[k] & set(chosen)),
                    -degree[k],
                    k,
                ),
            )
        )
    if len(chosen) < 8 or len(choices) < len(ids) - len(chosen) + 2:
        stats.update(
            rejected="CAPACITY",
            provenMembers=len(chosen),
            retainedCapacity=len(choices),
            requiredRetained=len(ids) - len(chosen) + 2,
        )
        return None
    site.update(
        memberEntityIds=sorted(chosen),
        anchorEntityIds=sorted(chosen, key=lambda k: (-degree[k], k))[
            : len(site["courts"])
        ],
        retainedMemberEntityIds=sorted(ids - set(chosen)),
    )
    return choices, kept, plots, site


def apply_campuses(
    plans, selections, zones, polygons, seed, roads, terrain, pairs, style="quad"
):
    """At most one actual campus per parent; retained plans stay byte-identical."""
    decisions = {z["id"]: eligibility(z, pairs, seed) for z in zones}
    sites = {}
    for z in sorted(zones, key=lambda z: (decisions[z["id"]]["draw"], z["id"])):
        decision = decisions[z["id"]]
        if not decision["eligible"] or decision["draw"] >= decision["probability"]:
            continue
        if sites:
            decision["reason"] = "PARENT_DIVERSITY_LIMIT"
            continue
        if style in ("neighborhood","landscape"):
            from .campus_neighborhood import neighborhood_layout
            if style=='landscape':
                from .campus_landscape import landscape_layout as neighborhood_layout

            fit = {}
            try:
                layout = neighborhood_layout(z, polygons[z['id']], selections[z['id']]['axis'],
                                             derive(seed,z['id'],VERSION),roads,terrain,pairs,fit)
            except ValueError as error:
                if not str(error).startswith('campus neighborhood ') or 'limit' not in str(error):
                    raise
                decision.update(reason='RESOURCE_LIMIT_FALLBACK',fit={'limit':str(error)})
                continue
            decision['fit'] = fit
            if layout is None:
                decision['reason'] = 'FULL_NEIGHBORHOOD_FIT_FALLBACK'
                continue
            plots, walks, site = layout
            plans[z['id']] = (plots,walks,site['axis'],None)
            sites[z['id']] = site
            decision.update(status='SELECTED',reason='WHOLE_NEIGHBORHOOD_PLANNED')
            continue
        mixed = None
        variants = ["ACADEMIC_QUAD"]
        if style == "varied":
            from .campus_forms import VERSION as FORM_VERSION

            variants = ["TECH_PARK", "ACADEMIC_QUAD"]
            if draw(derive(seed, z["id"], FORM_VERSION, "form")) >= 0.75:
                variants.reverse()
        attempts = [
            (v, count)
            for v in variants
            for count in ((1,) if v == "TECH_PARK" else (1, 2, 3))
        ]
        for variant, count in attempts:
            try:
                layout = courtyard_layout(
                    z,
                    polygons[z["id"]],
                    selections[z["id"]]["axis"],
                    derive(seed, z["id"], VERSION),
                    roads,
                    terrain,
                    pairs,
                    max_courts=count,
                    variant=variant,
                )
                if layout is None:
                    decision["reason"] = "CAPACITY_OR_ACCESS_FALLBACK"
                    continue
                fit = {}
                mixed = _mixed_pocket(plans[z["id"]], layout, z, pairs, roads, fit)
            except ValueError as error:
                if not str(error).startswith("campus ") or "limit" not in str(error):
                    raise
                decision.update(
                    reason="RESOURCE_LIMIT_FALLBACK", fit={"limit": str(error)}
                )
                break
            decision["fit"] = fit
            if mixed is not None:
                break
        if mixed is None:
            if decision["reason"] != "RESOURCE_LIMIT_FALLBACK":
                decision["reason"] = "RETAINED_CAPACITY_OR_CONNECTIVITY_FALLBACK"
            continue
        original, lanes, plots, site = mixed
        plans[z["id"]] = (
            original + plots,
            lanes + site["walkways"],
            site["axis"],
            plans[z["id"]][3],
        )
        sites[z["id"]] = site
        decision.update(status="SELECTED", reason="EVIDENCE_WEIGHT_AND_PHYSICAL_FIT")
    return decisions, sites


def collect_plan(blocks, style="quad"):
    result = dict(
        version=VERSION,
        structural=True,
        decisions={
            b["zoneId"]: b["campusDecision"]
            for b in sorted(blocks, key=lambda b: b["zoneId"])
        },
        sites=[
            b["campusSite"]
            for b in sorted(blocks, key=lambda b: b["zoneId"])
            if "campusSite" in b
        ],
    )
    if style == "varied":
        from .campus_forms import VERSION as FORM_VERSION

        result.update(version=FORM_VERSION, style=style)
    if style == "neighborhood":
        from .campus_neighborhood import VERSION as NEIGHBORHOOD_VERSION

        result.update(version=NEIGHBORHOOD_VERSION,style=style)
    if style == 'landscape':
        from .campus_landscape import VERSION as LANDSCAPE_VERSION
        result.update(version=LANDSCAPE_VERSION,style=style)
    return result


def validate_campuses(world):
    """Reconstruction is checked upstream; independently check occupied courts."""
    style = world["campusPlan"].get("style", "quad")
    if style not in ("quad", "varied", "neighborhood", "landscape") or world["campusPlan"] != collect_plan(
        world["zoning"]["blocks"], style
    ):
        raise ValueError("campus plan differs from verified block records")
    sites = world["campusPlan"]["sites"]
    if len(sites) > 64 or len({s["parentId"] for s in sites}) != len(sites):
        raise ValueError("campus parent or output limit")
    obstacles = []
    index = defaultdict(set)
    entries = checks = 0
    for poly in [p["parcel"] for p in world["parcels"]] + [
        ribbon(r["start"], r["end"], r["width"]) for r in world["streets"]
    ]:
        x0, z0, x1, z1 = bounds(poly)
        for x in range(math.floor(x0 / 32), math.floor(x1 / 32) + 1):
            for z in range(math.floor(z0 / 32), math.floor(z1 / 32) + 1):
                index[x, z].add(len(obstacles))
                entries += 1
                if entries > 500_000:
                    raise ValueError("campus court index limit")
        obstacles.append(poly)
    for site in sites:
        if not set(site["anchorEntityIds"]).issubset(site["memberEntityIds"]):
            raise ValueError("campus anchor is not an original member")
        if style in ('neighborhood','landscape'):
            zone=next(z for z in world['zoning']['zones'] if z['id']==site['zoneId'])
            if site['memberEntityIds']!=sorted(zone['memberEntityIds']) or site['retainedMemberEntityIds']:
                raise ValueError('campus precinct must include the entire source neighborhood')
            parcels={p['entityId']:p for p in world['parcels']}
            if not all(parcels[k]['slotId']==slot for k,slot in site['anchorSlots'].items()):
                raise ValueError('campus activity anchor left its planned group')
            for group in site['activityCenters']:
                if not any(parcels[k]['slotId'] in group['slotIds'] for k in site['memberEntityIds']):
                    raise ValueError('campus activity group has no original source members')
        for court in site["courts"]:
            x0, z0, x1, z1 = bounds(court["polygon"])
            near = {
                i
                for x in range(math.floor(x0 / 32), math.floor(x1 / 32) + 1)
                for z in range(math.floor(z0 / 32), math.floor(z1 / 32) + 1)
                for i in index[x, z]
            }
            checks += len(near)
            if checks > MAX_CHECKS:
                raise ValueError("campus court clearance limit")
            if any(overlap(court["polygon"], obstacles[i]) for i in near):
                raise ValueError(
                    "campus shared court overlaps a street or source parcel"
                )
