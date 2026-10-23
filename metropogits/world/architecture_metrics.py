"""Material-blind measurements of compiled geometry, not catalog labels.

Normalized occupancy samples the actual solid sections of the shared renderer
meshes. World translation, yaw, mirrors, facade colors and tiny entrance props
cannot manufacture extra morphological families. This is a finite-resolution
diagnostic, not a perceptual quality score or proof of visual differentiation.
"""

import math
from collections import Counter

from metropogits.street_diagonals import hull
from .geometry import inside, q

VERSION = 'rendered-morphology/0.1'
GRID = (10, 10, 16)


def _sections(part, y):
    if not part['y'] < y < part['y'] + part['height']:
        return []
    faces = part.get('meshFaces')
    if not faces:
        return [part['footprint']]
    # A sawtooth mesh is three adjoining convex roof bays, not their convex
    # union (which would incorrectly fill the gaps between their roof teeth).
    groups = [faces[i:i + 7] for i in range(0, len(faces), 7)] if part.get('primitive') == 'SAWTOOTH' else [faces]
    sections = []
    for group in groups:
        cuts = []
        for face in group:
            vertices = face['points']
            for a, b in zip(vertices, vertices[1:] + vertices[:1]):
                if min(a[1], b[1]) <= y <= max(a[1], b[1]) and abs(a[1] - b[1]) > 1e-9:
                    t = (y - a[1]) / (b[1] - a[1])
                    cuts.append([a[i] + t * (b[i] - a[i]) for i in (0, 2)])
        if len(cuts) >= 3:
            section = hull(cuts)
            # inside() expects the same winding as rectangular footprints.
            area = sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(section, section[1:] + section[:1]))
            sections.append(section[::-1] if area < 0 else section)
    return sections


def occupancy(model):
    nx, nz, ny = GRID
    parts = [p for p in model['parts'] if p.get('materialKind') not in (12, 13, 14)
             and p['width'] * p['depth'] * p['height'] >= model['width'] * model['depth'] * model['height'] * .003]
    top = max(p['y'] + p['height'] for p in parts)
    c, s = math.cos(model['angle']), math.sin(model['angle'])
    def local(p):
        x, z = p[0] - model['center'][0], p[1] - model['center'][1]
        return [.5 + (c * x + s * z) / model['width'], .5 + (-s * x + c * z) / model['depth']]
    mask = mirror = 0
    for iy in range(ny):
        height = top * (iy + .5) / ny
        polygons = [[local(p) for p in poly] for part in parts for poly in _sections(part, height)]
        for iz in range(nz):
            for ix in range(nx):
                if any(inside([(ix + .5) / nx, (iz + .5) / nz], poly, -.00001) for poly in polygons):
                    mask |= 1 << ((iy * nz + iz) * nx + ix)
                    mirror |= 1 << ((iy * nz + iz) * nx + nx - ix - 1)
    return min(mask, mirror)


def distribution(values):
    values = sorted(values)
    if not values:
        return dict(count=0)
    return dict(count=len(values), min=q(values[0]), p10=q(values[round((len(values) - 1) * .1)]),
                median=q(values[round((len(values) - 1) * .5)]), p90=q(values[round((len(values) - 1) * .9)]),
                max=q(values[-1]))


def geometry_metrics(styled, profiles):
    models = styled['parcels']
    if not models or len(models) > 10000:
        raise ValueError('geometry metrics source limit')
    masks = {p['entityId']: occupancy(p) for p in models}
    normalized = Counter(masks.values())
    # Greedy material-blind near-repeat groups, weighted by real source count.
    # Most frequent exemplar first; deterministic tie-breaking on its bit mask.
    clusters = []
    for mask, count in sorted(normalized.items(), key=lambda kv: (-kv[1], kv[0])):
        match = next((c for c in clusters if (c['mask'] & mask).bit_count() / max(1, (c['mask'] | mask).bit_count()) >= .90), None)
        if match:
            match['count'] += count
        else:
            clusters.append(dict(mask=mask, count=count))
    scale_aware = {(masks[p['entityId']], q(p['width']), q(p['depth']), round(max(part['y'] + part['height'] for part in p['parts']) * 2) / 2)
                   for p in models}
    return dict(version=VERSION, sampledModels=len(models), voxelGrid=list(GRID),
                normalizedShapeCount=len(normalized), scaleAwareShapeCount=len(scale_aware),
                nearRepeatThreshold=.90, nearRepeatClusterCount=len(clusters),
                largestExactRepeat=max(normalized.values()), largestNearRepeat=max(c['count'] for c in clusters),
                largestNearRepeatFraction=q(max(c['count'] for c in clusters) / len(models)),
                footprintArea=distribution([p['width'] * p['depth'] for p in models]),
                actualRenderedHeight=distribution([max(part['y'] + part['height'] for part in p['parts']) for p in models]),
                footprintSizes=dict(sorted(Counter(f"{p['width']}x{p['depth']}" for p in models).items())),
                catalogFamilies=dict(sorted(Counter(p['family'] for p in profiles.values()).items())),
                actualCompositions=dict(sorted(Counter(p.get('massingLayout', 'CATALOG') for p in profiles.values()).items())),
                neutralRoleSources=sum(p['verifiedRole'] is None and not p.get('composite') for p in profiles.values()),
                compositeModels=sum(bool(p.get('composite')) for p in profiles.values()),
                limitation='Finite-resolution solid geometry similarity; inspect matched grayscale renders as well.')
