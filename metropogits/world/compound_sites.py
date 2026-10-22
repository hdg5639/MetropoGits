"""Reserve complete source-cohort sites before individual file subdivision.

Planning units are private geometric requests, never synthetic source entities.
Their real members keep their full requested envelopes, distinct IDs/roles and
doors; an exterior shared promenade connects every door to the parent street.
"""

import math
from collections import defaultdict

from .geometry import point, rectangle
from .seed import derive

VERSION = 'cohort-sites/0.1'
MAX_MEMBERS = 4
EDGE = 4
GAP = .6


def units(members):
    grouped = defaultdict(list)
    for b in members:
        grouped[b.get('cohortId', b['entityId'])].append(b)
    result = []
    for cohort, population in sorted(grouped.items()):
        population = sorted(population, key=lambda b: (-b['width'] * b['depth'], b['entityId']))
        for batch in range(0, len(population), MAX_MEMBERS):
            selected = population[batch:batch + MAX_MEMBERS]
            if len(selected) == 1:
                result.append({k: v for k, v in selected[0].items() if k != 'cohortId'})
                continue
            rows = [[] for _ in range(2 if len(selected) > 2 else 1)]
            widths = [0 for _ in rows]
            for b in selected:
                row = min(range(len(rows)), key=lambda i: (widths[i], i))
                rows[row].append(b)
                widths[row] += b['width'] + 2 + GAP
            widths = [w - GAP for w in widths]
            heights = [max(b['depth'] + 2 for b in row) for row in rows]
            inner_width, inner_depth = max(widths), sum(heights) + GAP * (len(rows) - 1)
            children = []
            for number, row in enumerate(rows):
                x = -widths[number] / 2
                facing = 1 if number == 0 else -1
                z = inner_depth / 2 - heights[number] / 2 if facing == 1 else -inner_depth / 2 + heights[number] / 2
                for b in row:
                    children.append(dict(source=b, x=x + (b['width'] + 2) / 2, z=z, facing=facing))
                    x += b['width'] + 2 + GAP
            result.append(dict(entityId='world:architectural-site:' + derive(cohort, *(b['entityId'] for b in selected), VERSION),
                               width=inner_width + EDGE * 2, depth=inner_depth + EDGE * 2,
                               **({'blockProfile': selected[0]['blockProfile']} if 'blockProfile' in selected[0] else {}),
                               _site=dict(version=VERSION, cohortId=cohort, width=inner_width, depth=inner_depth, children=children)))
    return result


def subdivision(unit, slot, seed):
    """Real variable envelopes, two outward-facing rows, no internal public road."""
    site = unit['_site']
    angle = slot['angle']
    c, s = math.cos(angle), math.sin(angle)
    def at(x, z):
        return point([slot['center'][0] + c * x - s * z, slot['center'][1] + s * x + c * z])
    hw, hd = site['width'] / 2 + 2, site['depth'] / 2 + 2
    ring = [at(x, z) for x, z in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd))]
    walks = [dict(id=unit['entityId'] + f':promenade:{i}', start=a, end=b, width=1.2, access=False, structural=True)
             for i, (a, b) in enumerate(zip(ring, ring[1:] + ring[:1]))]
    walks.append(dict(id=unit['entityId'] + ':approach', start=at(0, hd), end=slot['streetPoint'],
                      width=1.2, access=False, structural=True))
    choices = []
    for child in site['children']:
        b = child['source']
        x, z, facing = child['x'], child['z'], child['facing']
        center = at(x, z)
        yaw = angle if facing == 1 else angle + math.pi
        choice = dict(slot, id='program:' + derive(seed, b['entityId']), entityId=b['entityId'],
                      center=center, angle=yaw, polygon=rectangle(center, yaw, b['width'] + 2, b['depth'] + 2),
                      entrance=at(x, z + facing * b['depth'] / 2), streetPoint=at(x, facing * hd),
                      laneId=unit['entityId'] + (':front' if facing == 1 else ':rear'),
                      architecturalSiteId=unit['entityId'])
        if 'blockProfile' in b and ('planningRegionId' not in slot or b['blockProfile'] == 'CAMPUS'):
            choice['blockProfile'] = b['blockProfile']
        choices.append(choice)
    return choices, walks


def suitable(unit, slot, field):
    from .elevation import MAX_ACCESS_GRADE, MAX_LOT_RELIEF
    choices, walks = subdivision(unit, slot, 'suitability')
    for choice, child in zip(choices, unit['_site']['children']):
        b = child['source']
        low, high = field.range(rectangle(choice['center'], choice['angle'], b['width'], b['depth']))
        length = math.dist(choice['entrance'], choice['streetPoint'])
        if high - low > MAX_LOT_RELIEF or abs(high + .04 - field.height(choice['streetPoint'])) / length > MAX_ACCESS_GRADE - .001:
            return False
    for road in walks:
        profile = field.profile(road['start'], road['end'])
        if any(abs(b[2] - a[2]) / math.dist(a[:2], b[:2]) > .1598 for a, b in zip(profile, profile[1:])):
            return False
    return True


def allocate(members, polygon, plan, external, terrain, seed, **options):
    from .capacity import fit_programs
    requests = units(members)
    admitted, lanes, axis, regions = fit_programs(requests, polygon, plan, external, terrain, seed,
                                                _planning_units=True, **options)
    by_id = {u['entityId']: u for u in requests}
    choices, additions = [], []
    for slot in admitted:
        unit = by_id[slot['entityId']]
        if '_site' not in unit:
            choices.append(slot)
            continue
        children, paths = subdivision(unit, slot, seed)
        choices.extend(children)
        additions.extend(paths)
    return sorted(choices, key=lambda c: c['id']), lanes + additions, axis, regions
