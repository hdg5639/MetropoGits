"""Bounded, clearance-preserving presentation of structural street widths.

Only narrows existing pavement. No path, entrance or semantic record changes.
"""
from collections import defaultdict
import heapq
import math

MAX_SAMPLES = 500_000
SAMPLE_LENGTH = 3.5
WIDTH_SLOPE = .25  # full-width change per world unit, not traffic demand


def _remove_short_bulges(limits, adjacency):
    """Opening on each straight lattice run; no isolated diamond-shaped widenings.

    A width increase needs a fourteen-unit neighborhood. Truncated neighborhoods
    at a road end are allowed; the operation can only reduce clearance bounds.
    """
    lines = defaultdict(set)
    for p, neighbors in adjacency.items():
        for q in neighbors:
            axis = 0 if p[1] == q[1] else 1
            lines[axis,p[1-axis]].update((p,q))
    result = dict(limits)
    for (axis,_), nodes in sorted(lines.items()):
        runs = []
        for p in sorted(nodes, key=lambda p:p[axis]):
            if not runs or p not in adjacency[runs[-1][-1]]:
                runs.append([])
            runs[-1].append(p)
        for run in runs:
            # Non-entrance structural segments are on the fixed 3.5-unit lattice.
            neighborhoods = [run[max(0,i-2):i+3] for i in range(len(run))]
            eroded = {p:min(limits[q] for q in neighbors) for p,neighbors in zip(run,neighborhoods)}
            for p,neighbors in zip(run,neighborhoods):
                result[p] = min(result[p],max(eroded[q] for q in neighbors))
    return result


def tapered_surfaces(segments):
    chains, adjacency, limits = [], defaultdict(dict), {}
    samples = 0
    for segment in sorted(segments, key=lambda s: s['id']):
        a, b = segment['start'], segment['end']
        length = abs(b[0]-a[0])+abs(b[1]-a[1])
        count = max(1, math.ceil(length/SAMPLE_LENGTH))
        samples += count+1
        if samples > MAX_SAMPLES:
            raise ValueError('structural surface sample limit')
        points = [tuple(round(a[j]+(b[j]-a[j])*i/count, 6) for j in (0, 1))
                  for i in range(count+1)]
        chains.append((segment, points))
        # Door stubs must not squeeze the street they join down to doorway width.
        if segment.get('entrance'):
            continue
        for point in points:
            limits[point] = min(limits.get(point, math.inf), segment['width'])
        for p, q in zip(points, points[1:]):
            distance = abs(q[0]-p[0])+abs(q[1]-p[1])
            adjacency[p][q] = adjacency[q][p] = distance
    # Multi-source shortest envelope: width never exceeds a cleared segment's
    # bound and can grow only gradually away from a narrow junction/corridor.
    widths = _remove_short_bulges(limits, adjacency)
    queue = [(w, p) for p, w in widths.items()]
    heapq.heapify(queue)
    while queue:
        width, point = heapq.heappop(queue)
        if width != widths[point]:
            continue
        for neighbor, distance in sorted(adjacency[point].items()):
            candidate = width+WIDTH_SLOPE*distance
            if candidate < widths[neighbor]-1e-9:
                widths[neighbor] = candidate
                heapq.heappush(queue, (candidate, neighbor))
    result = []
    for segment, points in chains:
        profile = [segment['width'] if segment.get('entrance') else widths[p] for p in points]
        # Coalesce equal-slope pieces: no per-cell mesh cost on uniform streets.
        keep = [0]
        for i in range(1, len(points)-1):
            if abs((profile[i]-profile[i-1])-(profile[i+1]-profile[i])) > 1e-8:
                keep.append(i)
        keep.append(len(points)-1)
        for index, (i, j) in enumerate(zip(keep, keep[1:])):
            a, b = points[i], points[j]
            horizontal = a[1] == b[1]
            dx, dz = (0, 1) if horizontal else (1, 0)
            ra, rb = profile[i]/2, profile[j]/2
            polygon = [[a[0]-dx*ra, a[1]-dz*ra], [b[0]-dx*rb, b[1]-dz*rb],
                       [b[0]+dx*rb, b[1]+dz*rb], [a[0]+dx*ra, a[1]+dz*ra]]
            if sum(p[0]*q[1]-q[0]*p[1] for p,q in zip(polygon, polygon[1:]+polygon[:1])) > 0:
                polygon.reverse()  # upward-facing winding in X/Y/Z
            x, z = min(p[0] for p in polygon), min(p[1] for p in polygon)
            result.append(dict(id=f'{segment["id"]}:surface:{index}', segmentId=segment['id'],
                x=x, z=z, width=max(p[0] for p in polygon)-x,
                depth=max(p[1] for p in polygon)-z, points=polygon,
                color='#43515d', elevation=.10, semantic=False))
    return result
