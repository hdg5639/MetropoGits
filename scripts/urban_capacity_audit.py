"""Independently audit a generated capacity World and its rendered morphology.

Usage: python -m scripts.urban_capacity_audit PACKAGE --baseline OLD --out NEW.json
No target code, build scripts, dependencies or browser are executed.
"""

import argparse
import json
from pathlib import Path
from time import perf_counter

from scripts.canonical_json import loads_strict_json, canonical_json_bytes, sha256_digest
from metropogits.block_orientation import clip
from metropogits.world.architecture_catalog import catalog_compounds
from metropogits.world.architecture_metrics import geometry_metrics
from metropogits.world.compounds import derive_compounds
from metropogits.world.geometry import area
from metropogits.world.street_mesh import street_mesh
from metropogits.world.urban_architecture import urban_world
from metropogits.world.urban_land import ClearanceIndex
from metropogits.world.validation import validate_world


def read(path):
    if path.stat().st_size > 64 * 1024 * 1024:
        raise ValueError('audit input exceeds 64 MiB')
    return json.loads(canonical_json_bytes(loads_strict_json(path.read_text(encoding='utf8'))))


def rendered_models(styled, profiles, compounds):
    hidden = {key for f in compounds for key in f['memberEntityIds']}
    models = [p for p in styled['parcels'] if p['entityId'] not in hidden]
    actual_profiles = {p['entityId']: profiles[p['entityId']] for p in models}
    for f in compounds:
        model = f['physicalModel']
        base = model.get('baseElevation', 0)
        parts = [dict(p, y=p['y'] - base,
                      **(dict(meshFaces=[dict(face, points=[[x, y - base, z] for x, y, z in face['points']])
                                         for face in p['meshFaces']]) if 'meshFaces' in p else {})) for p in model['parts']]
        models.append(dict(model, entityId=f['id'], parts=parts, height=max(p['y'] + p['height'] for p in parts)))
        actual_profiles[f['id']] = dict(family='CERTIFIED_SOURCE_COMPLEX', verifiedRole=None,
                                       massingLayout=f.get('architecture', {}).get('archetypeId', 'SOURCE_COMPLEX'))
    return dict(styled, parcels=models), actual_profiles


def assess(package):
    scene, graph, world = [read(package / name) for name in ('city.json', 'graph.ucg.json', 'world.json')]
    at = perf_counter()
    valid = validate_world(world, scene, graph)
    styled, profiles, land = urban_world(world, graph)
    compounds = catalog_compounds(derive_compounds(world, graph, campus_landmarks=True)[0])
    index = ClearanceIndex()
    for p in world['parcels']:
        index.add(('source', p['entityId']), p['footprint'])
    intersections, surface_count = [], 0
    for surface in street_mesh(world):
        poly = surface['points']
        surface_count += 1
        near = {key for cell in index.cells_for(poly) for key in index.cells[cell]}
        for key in sorted(near):
            if area(clip(poly, index.shapes[key])) > .001:
                intersections.append(dict(source=key[1], surface=surface.get('id')))
                if len(intersections) >= 100:
                    raise ValueError('rendered pavement/building overlap limit')
    if intersections:
        raise ValueError('rendered pavement intersects source envelopes: ' + str(intersections[:5]))
    visible, visible_profiles = rendered_models(styled, profiles, compounds)
    result = dict(repositoryId=graph['repository']['id'], validation=valid,
                  sourceCityDigest=sha256_digest(scene), sourceGraphDigest=sha256_digest(graph),
                  capacity=world.get('capacityPlan'), landCounts=land['counts'],
                  sourceGeometry=geometry_metrics(styled, profiles),
                  visibleGeometry=geometry_metrics(visible, visible_profiles),
                  visibleComplexes=len(compounds), complexSourceMembers=sum(len(f['memberEntityIds']) for f in compounds),
                  campusSites=len(world.get('campusPlan', {}).get('sites', [])),
                  renderedPavementSurfaces=surface_count, renderedPavementBuildingIntersections=0,
                  auditSeconds=perf_counter() - at)
    if result['capacity']:
        result['capacity'] = {k: v for k, v in result['capacity'].items() if k != 'programs'}
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('package', type=Path)
    p.add_argument('--baseline', type=Path)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise ValueError('audit output must not exist')
    report = dict(after=assess(a.package))
    if a.baseline:
        report['before'] = assess(a.baseline)
        for key in ('sourceCityDigest', 'sourceGraphDigest'):
            if report['before'][key] != report['after'][key]:
                raise ValueError('baseline source facts changed: ' + key)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_bytes(canonical_json_bytes(report))
    print(json.dumps(dict(output=str(a.out), sourceEntities=report['after']['validation']['buildings'],
                          normalizedShapes=report['after']['visibleGeometry']['normalizedShapeCount'],
                          largestNearRepeat=report['after']['visibleGeometry']['largestNearRepeatFraction'])))


if __name__ == '__main__':
    main()
