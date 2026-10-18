"""Bounded cartographic paint inside existing roads; never a source relationship."""
import math


def dash_segments(start, end, trims=(0, 0)):
    dx, dz = end[0]-start[0], end[1]-start[1]
    length = math.hypot(dx, dz)
    if not math.isfinite(length) or length <= sum(trims)+1e-8 or (dx and dz):
        return []
    a = [start[0]+dx*trims[0]/length, start[1]+dz*trims[0]/length]
    b = [end[0]-dx*trims[1]/length, end[1]-dz*trims[1]/length]
    axis = 0 if dz == 0 else 1
    lo, hi = sorted((a[axis], b[axis]))
    first, last = math.floor(lo/4), math.floor(hi/4)
    if last-first > 512:
        return []
    pieces = []
    for i in range(first, last+1):
        low, high = max(lo, i*4), min(hi, i*4+1.6)
        if high-low < 1e-8:
            continue
        left, right = list(a), list(a)
        left[axis], right[axis] = low, high
        pieces.append(dict(start=left, end=right))
    return pieces


def junction_trims(routing, visible, widths):
    """Same visible-junction mouths as the interactive viewer, without WebGL."""
    segments = {s['id']: s for s in visible}
    trims = {}
    for junction in routing.get('junctions', ()):
        groups = {}
        for identity in junction['segmentIds']:
            if identity in segments:
                segment = segments[identity]
                groups.setdefault(segment['kind'], []).append(segment)
        for incident in groups.values():
            if len(incident) < 3:
                continue
            sizes = [widths[s['id']] for s in incident]
            reach = max(sizes)/2+min(sizes)*.12
            for segment in incident:
                side = 0 if segment['start'] == junction['point'] else 1 if segment['end'] == junction['point'] else -1
                if side < 0:
                    continue
                extent = min(math.dist(segment['start'], segment['end']), reach)
                trim = trims.setdefault(segment['id'], [0, 0])
                trim[side] = max(trim[side], extent)
    return trims
