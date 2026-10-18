"""Fit evidenced road paint inside the same physical street envelope (ADR-020)."""
from bisect import bisect_left
from collections import defaultdict
import math

from metropogits.structural_streets import street_rectangles

MAX_PIECES = 500_000


def _quad(axis, fixed, lo, hi, first, last):
    points = [[lo,fixed-first/2],[hi,fixed-last/2],
              [hi,fixed+last/2],[lo,fixed+first/2]]
    if axis:
        points = [[z,x] for x,z in points]
    else:
        points.reverse()
    return points


def demand_pavement(routing, hierarchy, surfaces=None):
    """Renderer-only polygons: no modifications to stored route geometry/IDs.

    Collinear overlaps follow the structural taper. A crossing alone is NOT an
    overlap. Door connectors and legacy-only intervals retain certified widths.
    """
    if routing.get('streetGrid', {}).get('version') != 'structural-streets/0.2':
        return None
    surfaces = surfaces if surfaces is not None else street_rectangles(routing)
    originals = {s['id']:s for s in routing['streetGrid']['segments']}
    lines = defaultdict(list)
    for surface in surfaces:
        original = originals[surface['segmentId']]
        if original.get('entrance'):
            continue
        a,b = original['start'],original['end']
        axis = 0 if a[1]==b[1] else 1
        fixed = a[1-axis]
        points = surface['points']
        lo,hi = min(p[axis] for p in points),max(p[axis] for p in points)
        first = max(abs(p[1-axis]-fixed)*2 for p in points if p[axis]==lo)
        last = max(abs(p[1-axis]-fixed)*2 for p in points if p[axis]==hi)
        lines[axis,fixed].append((lo,hi,first,last))
    for intervals in lines.values():
        intervals.sort()
    ends = {key:[p[1] for p in values] for key,values in lines.items()}
    result, total = {}, 0
    for segment in sorted(routing['segments'],key=lambda s:s['id']):
        if segment['kind'] != 'DEPENDENCY_ROAD':
            continue  # HTTP/messaging retain their established category geometry.
        a,b = segment['start'],segment['end']
        axis = 0 if a[1]==b[1] else 1
        fixed = a[1-axis]
        lo,hi = sorted((a[axis],b[axis]))
        if hi<=lo:
            continue
        profile = (hierarchy or {}).get('segments',{}).get(segment['id'],{})
        width = min(segment['width'],profile.get('width',.7+math.log2(len(segment['routeIds'])+1)*.5))
        intervals = lines.get((axis,fixed),[])
        index = bisect_left(ends.get((axis,fixed),[]),lo)
        pieces, cursor = [], lo
        def add(left,right,w0,w1,covered):
            if right-left<=1e-9:
                return
            pieces.append(dict(points=_quad(axis,fixed,left,right,w0,w1),
                start=[left,fixed] if not axis else [fixed,left],
                end=[right,fixed] if not axis else [fixed,right],
                width=min(w0,w1), maxWidth=max(w0,w1), structural=covered))
        for n in range(index,len(intervals)):
            start,end,w0,w1 = intervals[n]
            if start>=hi:
                break
            left,right = max(cursor,start),min(hi,end)
            if right<=left:
                continue
            add(cursor,left,width,width,False)
            def at(value):
                return w0+(w1-w0)*(value-start)/(end-start)
            cuts=[left,right]
            if w0!=w1:
                crossing=start+(width-w0)*(end-start)/(w1-w0)
                if left<crossing<right:
                    cuts.insert(1,crossing)
            for x,y in zip(cuts,cuts[1:]):
                add(x,y,min(width,at(x)),min(width,at(y)),True)
            cursor=right
        add(cursor,hi,width,width,False)
        total += len(pieces)
        if total>MAX_PIECES:
            raise ValueError('street demand surface limit')
        result[segment['id']]=pieces
    return dict(version='street-demand-surfaces/0.1',segments=result)


def clip_paint(paint, pieces):
    if pieces is None:
        return [paint]
    axis = 0 if paint['start'][1]==paint['end'][1] else 1
    lo,hi = sorted((paint['start'][axis],paint['end'][axis]))
    result=[]
    for piece in pieces:
        if piece['width']<1.25:
            continue
        left=max(lo,min(piece['start'][axis],piece['end'][axis]))
        right=min(hi,max(piece['start'][axis],piece['end'][axis]))
        if right-left>1e-8:
            a,b=list(paint['start']),list(paint['end'])
            a[axis],b[axis]=left,right
            result.append(dict(start=a,end=b))
    return result
