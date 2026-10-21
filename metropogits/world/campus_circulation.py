"""Deletion-only, purpose-aware cleanup of built campus walking circulation."""

import heapq
import math
from collections import defaultdict

from .geometry import bounds, nearest
from .seed import derive

VERSION = "campus-circulation/0.1"
MAX_STREETS = 50_000
MAX_RESERVES = 30_000
MAX_INDEX = 500_000
MAX_CHECKS = 2_000_000


def prune_campus_tails(streets, sites, reserved, parcels, routing):
    """Peel only non-purposeful walking leaves from an already atomic graph.

    A lack of dependency traffic is NOT a lack of purpose. Keep courts,
    promenades, exterior gates, every occupied frontage (including generic
    sources), vehicle corridors, crossings and source-backed trip pavement.
    Removing a graph leaf cannot increase any remaining pair's travel distance.
    Raw campus walkways remain planning reservations; streets are built pavement.
    """
    note = dict(reason="campus walking tails beyond actual access removed",
                version=VERSION, removedStreetIds=[], removedStreets=[], removedLength=0.0,
                candidateChecks=0, indexEntries=0)
    try:
        return _prune(streets, sites, reserved, parcels, routing, note), note
    except ValueError as error:
        # No partially pruned output when a resource bound is reached.
        if not str(error).startswith("campus circulation "):
            raise
        note.update(reason="campus circulation retained certified streets",
                    removedStreetIds=[], removedStreets=[], removedLength=0.0, fallback=str(error))
        return streets, note


def _prune(streets, sites, reserved, parcels, routing, note):
    walks = [r for site in sites if site.get("scope") == "NEIGHBORHOOD"
             for r in site["walkways"]]
    if not walks:
        return streets
    if len(streets) > MAX_STREETS or len(walks) + len(reserved) > MAX_RESERVES:
        raise ValueError("campus circulation input limit")
    # All non-campus reserves remain protected, even if exceptionally narrow.
    records = [(r, True) for r in reserved
               if not r.get("id", "").startswith("world:campus-court:")]
    records += [(r, any(k in r["id"] for k in (":loop:", ":promenade:", ":exterior-gate:")))
                for r in walks]
    index = defaultdict(set)

    def cells(r):
        x0, z0, x1, z1 = bounds([r["start"], r["end"]])
        a, b = math.floor((x0 - .003) / 32), math.floor((x1 + .003) / 32)
        c, d = math.floor((z0 - .003) / 32), math.floor((z1 + .003) / 32)
        if (b - a + 1) * (d - c + 1) > MAX_INDEX:
            raise ValueError("campus circulation index limit")
        return [(x, z) for x in range(a, b + 1) for z in range(c, d + 1)]

    for i, (r, _) in enumerate(records):
        keys = cells(r)
        note["indexEntries"] += len(keys)
        if note["indexEntries"] > MAX_INDEX:
            raise ValueError("campus circulation index limit")
        for key in keys:
            index[key].add(i)
    protected = {s["physicalId"] for s in routing.get("segments", [])}
    stops = {tuple(p[k]) for p in parcels for k in ("entrance", "streetPoint")}
    adjacent = defaultdict(set)
    candidates = set()
    by_id = {s["id"]: s for s in streets}
    for s in streets:
        for p in (s["start"], s["end"]):
            adjacent[tuple(p)].add(s["id"])
        if (s["id"] in protected or s["access"] or s["width"] > 1.202
                or s.get("bridgeId") or s.get("tunnelId")):
            continue
        walking = False
        for i in sorted({i for key in cells(s) for i in index[key]}):
            note["candidateChecks"] += 1
            if note["candidateChecks"] > MAX_CHECKS:
                raise ValueError("campus circulation geometry limit")
            r, keep = records[i]
            if all(math.dist(p, nearest(p, r["start"], r["end"])) < .002
                   for p in (s["start"], s["end"])):
                if keep:
                    walking = False
                    break
                walking = True
        if walking:
            candidates.add(s["id"])
    # Deterministic leaf peeling stops at access/junction/public circulation.
    queue = sorted(p for p, ids in adjacent.items() if len(ids) == 1 and p not in stops)
    heapq.heapify(queue)
    removed = set()
    while queue:
        at = heapq.heappop(queue)
        if at in stops or len(adjacent[at]) != 1:
            continue
        identity = next(iter(adjacent[at]))
        if identity not in candidates:
            continue
        s = by_id[identity]
        removed.add(identity)
        for p in (tuple(s["start"]), tuple(s["end"])):
            adjacent[p].remove(identity)
            if len(adjacent[p]) == 1 and p not in stops:
                heapq.heappush(queue, p)
    note.update(removedStreetIds=sorted(removed),
                removedStreets=[{f: by_id[k][f] for f in ("id", "start", "end", "width", "access")}
                                for k in sorted(removed)],
                removedLength=round(sum(math.dist(by_id[k]["start"], by_id[k]["end"])
                                        for k in sorted(removed)), 4))
    return [s for s in streets if s["id"] not in removed]


def verified_omissions(world, reserved):
    """Restore omitted atomic pieces and independently prove they are safe tails.

    Do not trust a diagnostic as permission to erase a protected main road.
    Legacy worlds without this optional policy record retain full coverage checks.
    """
    notes = [n for n in world["diagnostics"] if n.get("version") == VERSION]
    if not notes:
        return []
    if len(notes) != 1 or world.get("campusPlan", {}).get("style") not in ("neighborhood","landscape","organic","fabric","programmed","estate"):
        raise ValueError("invalid campus circulation policy record")
    note = notes[0]
    sites = [b["campusSite"] for b in world["zoning"]["blocks"] if "campusSite" in b]
    if not note.get("removedStreetIds"):
        if note.get("removedStreets") != [] or note.get("removedLength") != 0:
            raise ValueError("invalid empty campus circulation omission record")
        return []
    omitted = note.get("removedStreets")
    if (not isinstance(omitted, list) or len(world["streets"]) + len(omitted) > MAX_STREETS):
        raise ValueError("campus circulation reconstruction limit")
    for s in omitted:
        if (not isinstance(s, dict) or set(s) != {"id", "start", "end", "width", "access"}
                or s["width"] != 1.2 or s["access"] is not False
                or any(not isinstance(p, list) or len(p) != 2
                       or any(not isinstance(v, (int, float)) or isinstance(v, bool)
                              or not math.isfinite(v) or abs(v) > 100000 for v in p)
                       for p in (s["start"], s["end"]))
                or not tuple(s["start"]) < tuple(s["end"])
                or s["id"] != "world:street:" + derive(str(tuple(s["start"])), str(tuple(s["end"])))):
            raise ValueError("invalid campus circulation omitted geometry")
    # Raw reservations can cross repaired/quantized seams differently from the
    # built atomic graph. Restore exact omitted pieces, not a new atomization
    # that invents additional intersection nodes and changes an old street ID.
    restored = world["streets"] + omitted
    _, expected = prune_campus_tails(restored, sites, reserved, world["parcels"], world["routing"])
    if (set(note["removedStreetIds"]) & {s["id"] for s in world["streets"]}
            or note["removedStreetIds"] != expected["removedStreetIds"]
            or omitted != expected["removedStreets"]
            or note.get("removedLength") != expected["removedLength"]):
        raise ValueError("campus circulation omitted purposeful or unverified pavement")
    return omitted
