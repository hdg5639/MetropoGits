"""Commons and fanning walking frontage planned before any source assignment."""

import math
from collections import defaultdict

from .geometry import inside, point, rectangle

VERSION = "campus-plan/0.5"


def bearing(axis, index):
    # Distinct local orders, not independently jittered buildings.
    return axis + math.radians((14, -17, 26)[index])


def ellipse(center, axis, index, a, b):
    yaw = bearing(axis, index)
    c, s = math.cos(yaw), math.sin(yaw)
    return [point([center[0] + c*a*math.cos(t) - s*b*math.sin(t),
                   center[1] + s*a*math.cos(t) + c*b*math.sin(t)])
            for t in (i*math.tau/16 for i in range(16))]


def lawn(center, axis, index):
    return ellipse(center, axis, index, 10.6, 7.6)


def loop(center, axis, index):
    return ellipse(center, axis, index, 12.5, 9.5)


def branches(centers, axis, length, segment, clear, lawns):
    result = []
    for index, center in enumerate(centers):
        ports = loop(center, axis, index)
        for branch, port_index in enumerate((0, 3, 5, 8, 11, 13)):
            start = ports[port_index]
            yaw = math.atan2(start[1]-center[1], start[0]-center[0])
            for scale in (1, .72, .45):
                # Slowly changing tangent; no staircase or disconnected arc.
                points = [start]
                for k in range(1, 7):
                    t = scale*length*k/6
                    bend = (1 if branch % 2 else -1)*.09*t*t/max(length, 1)
                    points.append(point([start[0]+t*math.cos(yaw)-bend*math.sin(yaw),
                                         start[1]+t*math.sin(yaw)+bend*math.cos(yaw)]))
                pieces = [segment(a, b, f"core:{index}:fan:{branch}:{j}")
                          for j, (a, b) in enumerate(zip(points, points[1:]))]
                if all(clear(r['start'], r['end'], lawns) for r in pieces):
                    result.extend(pieces)
                    break
    return result


def frontage(paths, polygon, shapes, collision, terrain):
    from .elevation import suitable
    from .rivers import blocks_ground_connection

    groups = defaultdict(list)
    for r in paths:
        if ':exterior-gate' in r['id']:
            continue
        # Sample whole frontage, not each short curve chord independently.
        key = r['id'].rsplit(':', 1)[0] if ':fan:' in r['id'] else r['id']
        groups[key].append(r)
    lots = []
    for key, pieces in groups.items():
        total = sum(math.dist(r['start'], r['end']) for r in pieces)
        for station in range(max(0, math.floor((total-8)/9.5)+1)):
            remaining = 4+station*9.5
            for r in pieces:
                a, b = r['start'], r['end']
                length = math.dist(a, b)
                if remaining > length:
                    remaining -= length
                    continue
                u = [(b[j]-a[j])/length for j in (0, 1)]
                at = point([a[j]+u[j]*remaining for j in (0, 1)])
                break
            for side in (-1, 1):
                normal = [-u[1]*side, u[0]*side]
                center = point([at[j]+normal[j]*6.3 for j in (0, 1)])
                angle = math.atan2(normal[0], -normal[1])
                poly = rectangle(center, angle, 7.98, 7.98)
                p = dict(id=key+f':lot:{station}:{side}', center=center,
                         angle=angle, polygon=poly,
                         entrance=point([center[j]-normal[j]*3 for j in (0, 1)]),
                         streetPoint=at, laneId=r['id'], blockProfile='CAMPUS')
                if (not all(inside(v, polygon, 1) for v in poly)
                        or collision(poly, shapes+[v['polygon'] for v in lots])
                        or (terrain and 'elevation' in terrain and (
                            not suitable(p, terrain)
                            or blocks_ground_connection(p['entrance'], at, terrain)))):
                    continue
                lots.append(p)
    return lots


def organic_layout(*args):
    import sys
    from .campus_neighborhood import neighborhood_layout
    result = neighborhood_layout(*args, _form=sys.modules[__name__])
    if result is None:
        # Explicit complete-plan fallback; never a tiny campus pocket.
        from .campus_landscape import landscape_layout
        result = landscape_layout(*args)
        args[-1]['organicFallback'] = 'FULL_ORGANIC_CAPACITY_OR_ACCESS'
        return result
    plots, walks, site = result
    site['frontagePolicy'] = 'FANNING_COMMONS'
    site['groupBearings'] = [bearing(site['axis'], i) for i in range(len(site['courts']))]
    return plots, walks, site
