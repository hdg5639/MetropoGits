"""Opt-in ADR-020 comparison; canonical City/UCG remain unchanged."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from metropogits.access_routes import derive_access_routes
from metropogits.structural_streets import assign_streets
from scripts.canonical_json import canonical_json_bytes, loads_strict_json
from scripts.parcel_pilot import pavement_intersections
from scripts.parcel_viewer import _bounded_geometry
from scripts.road_consolidation import package
from scripts.road_metrics import road_metrics
from scripts.validate_city import validate_document


def compare(scene, graph, *, aligned=False, curves=False, diagonals=False):
    if diagonals and (not aligned or curves):
        raise ValueError('diagonal streets require aligned blocks and cannot combine with corner curves')
    errors = validate_document(scene, graph)
    if errors:
        raise ValueError('; '.join(errors[:8]))
    _bounded_geometry(scene)
    scene = json.loads(canonical_json_bytes(scene))
    before = derive_access_routes(scene, graph)
    after = assign_streets(scene, before, aligned=aligned)
    if curves:
        from metropogits.street_curves import plan_curves
        after['curvePlan'] = plan_curves(scene, after)
    if diagonals:
        from metropogits.street_diagonals import plan_diagonals
        after['diagonalPlan'] = plan_diagonals(scene, after)
    def identity(routing):
        return {p['id']: [p[k] for k in ('source', 'target', 'kind', 'edgeIds', 'networkIds')]
                for p in routing['routes']}
    if identity(before) != identity(after):
        raise ValueError('street assignment changed relationship identities')
    if pavement_intersections(after, scene['buildings']) or pavement_intersections(after['streetGrid'], scene['buildings']):
        raise ValueError('street pavement intersects buildings')
    report = dict(version='street-study/0.1', baseline='original visual-access/0.2',
        before=road_metrics(before), after=road_metrics(after),
        streetStatus=after['streetGrid']['status'],
        structuralSegments=len(after['streetGrid']['segments']),
        structuralEntrances=len(after['streetGrid']['entrances']),
        assignment=after['streetGrid']['assignment'],
        disclaimer='Structural streets are visual infrastructure. Dependency demand is static, not measured traffic.')
    if curves:
        report['curves'] = after['curvePlan']
    if diagonals:
        report['diagonals'] = after['diagonalPlan']
    return before, after, report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    parser.add_argument('--street-grid', required=True, action='store_true', help='explicitly enable experimental structural streets')
    parser.add_argument('--aligned-blocks', action='store_true', help='align block streets to parcel boundaries and join geometric neighbors')
    parser.add_argument('--curved-streets', action='store_true', help='round clearance-certified non-branching bends; requires aligned blocks')
    parser.add_argument('--diagonal-streets', action='store_true', help='replace eligible branch-free street detours with collision-checked diagonal chords; requires aligned blocks')
    parser.add_argument('--out', required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.out.exists():
            raise ValueError('output directory must not already exist')
        def read(name):
            path = args.build/name
            if path.stat().st_size > 64*1024*1024:
                raise ValueError('input exceeds 64 MiB')
            return loads_strict_json(path.read_text(encoding='utf-8'))
        scene, graph = read('city.json'), read('graph.ucg.json')
        if args.curved_streets and not args.aligned_blocks:
            raise ValueError('--curved-streets requires --aligned-blocks')
        before, after, report = compare(scene, graph, aligned=args.aligned_blocks, curves=args.curved_streets,
                                       diagonals=args.diagonal_streets)
        outputs = {name: package(scene, graph, routing, report)
                   for name, routing in [('before', before), ('after', after)]}
        args.out.mkdir(parents=True, exist_ok=False)
        for name, artifacts in outputs.items():
            for relative, content in artifacts.items():
                path = args.out/name/relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
        print(json.dumps(dict(output=str(args.out), structuralSegments=report['structuralSegments'],
            assigned=len(report['assignment']['assignedRouteIds']), fallback=len(report['assignment']['fallbackRouteIds']))))
    except (OSError, ValueError) as error:
        parser.exit(2, f'Structural street experiment failed: {error}\n')


if __name__ == '__main__':
    main()
