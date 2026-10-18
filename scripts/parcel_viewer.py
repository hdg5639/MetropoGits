"""Explicit experimental City/3D export from a validated baseline build (ADR-017)."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

from jsonschema import Draft202012Validator

from metropogits.access_routes import derive_access_routes
from metropogits.cli import _artifact_record, _diagnostic_summary
from metropogits.layout import _network_walkable_cells, _route_network
from metropogits.preview import render_preview
from metropogits.showcase import render_showcase
from metropogits.viewer import render_viewer
from scripts.canonical_json import canonical_json_bytes, loads_strict_json
from scripts.parcel_pilot import experiment, pavement_intersections
from scripts.road_metrics import road_metrics
from scripts.validate_city import validate_document as validate_city
from scripts.validate_city import SCHEMA_PATHS
from scripts.validate_ucg import validate_document as validate_ucg

LAYOUT = 'hierarchical-parcel/0.1-experimental'
BASELINE = 'hierarchical-paged/1.14'


def _bounded_geometry(scene):
    districts = scene['districts']
    if len(scene['buildings']) > 5000 or len(districts) > 10000:
        raise ValueError('experimental exporter item limit exceeded')
    if districts:
        spans = [max(d[a]+d[size] for d in districts)-min(d[a] for d in districts)
                 for a, size in [('x', 'width'), ('z', 'depth')]]
        if (math.ceil(spans[0]/7)+8)*(math.ceil(spans[1]/7)+8) > 100000:
            raise ValueError('experimental exporter geometry budget exceeded')


def _apply_hint(scene, previous):
    # Old evidence/digest may differ. Check shape here, ownership below and all
    # transferred geometry against the current graph after applying coordinates.
    schema = json.loads(SCHEMA_PATHS['city/0.2'].read_text(encoding='utf-8'))
    valid = Draft202012Validator(schema).is_valid(previous)
    if not valid or previous.get('layoutAlgorithm') != LAYOUT:
        raise ValueError('incompatible experimental hint: expected valid ' + LAYOUT)
    if sorted(scene['districts'], key=lambda d: d['id']) != sorted(previous['districts'], key=lambda d: d['id']):
        raise ValueError('incompatible experimental hint: directory geometry changed; omit hint for cold layout')
    def identity(b):
        return tuple(b[k] for k in ('entityId', 'districtId', 'width', 'depth'))
    if sorted(map(identity, scene['buildings'])) != sorted(map(identity, previous['buildings'])):
        raise ValueError('incompatible experimental hint: file membership/ownership changed; omit hint for cold layout')
    positions = {b['entityId']: b for b in previous['buildings']}
    for building in scene['buildings']:
        old = positions[building['entityId']]
        building.update(x=old['x'], z=old['z'])


def export_scene(baseline, graph, previous=None):
    """Return validated scene, whole-city routing and a non-semantic decision report."""
    errors = validate_ucg(graph) + validate_city(baseline, graph)
    if errors:
        raise ValueError('invalid input: ' + '; '.join(errors[:8]))
    if baseline.get('layoutAlgorithm') != BASELINE or baseline['schemaVersion'] != 'city/0.2':
        raise ValueError('expected a city/0.2 baseline with layout ' + BASELINE)
    _bounded_geometry(baseline)
    scene = json.loads(canonical_json_bytes(baseline))
    # Sort input-order-independent outputs; no graph facts or original IDs change.
    for key, identity in [('buildings', 'entityId'), ('districts', 'id'), ('networks', 'id')]:
        scene[key].sort(key=lambda item: item[identity])
    if previous is not None:
        _apply_hint(scene, json.loads(canonical_json_bytes(previous)))
        decision = dict(selection='HINT_APPLIED', hintPolicy='same-structure-only')
    else:
        report = experiment(scene, graph)
        if report['status'] != 'NOT_APPLICABLE' and not report['safeCandidate']:
            raise ValueError('parcel experiment failed safety checks')
        changes = {b['entityId']: b for b in report['overrides']}
        for building in scene['buildings']:
            if building['entityId'] in changes:
                building.update(x=changes[building['entityId']]['x'], z=changes[building['entityId']]['z'])
        decision = {k: v for k, v in report.items() if k not in ('variants', 'overrides')}
        decision.setdefault('selection', 'BASELINE_RETAINED')
    scene['layoutAlgorithm'] = LAYOUT
    if scene['networks']:
        buildings = {b['entityId']: b for b in scene['buildings']}
        edges = {e['id']: e for e in graph['edges']}
        walkable = _network_walkable_cells(scene['districts'], scene['buildings'])
        for network in scene['networks']:
            members = [edges[e] for e in network['edgeIds']]
            if any(e['from'] not in buildings or e['to'] not in buildings for e in members):
                raise ValueError('experimental network endpoint is not a file building')
            network['path'] = _route_network(walkable,
                                           {e['from']: buildings[e['from']] for e in members},
                                           {e['to']: buildings[e['to']] for e in members})
    errors = validate_city(scene, graph)
    if errors:
        raise ValueError('invalid experimental scene: ' + '; '.join(errors[:8]))
    routing = derive_access_routes(scene, graph)
    expected = {e for n in scene['networks'] for e in n['edgeIds']}
    actual = {e for r in routing['routes'] for e in r['edgeIds']}
    intersections = pavement_intersections(routing, scene['buildings'])
    if routing['status'] != 'COMPLETE' or actual != expected or intersections:
        raise ValueError('full-city access routing failed coverage/intersection checks; no output exported')
    decision.update(layoutAlgorithm=LAYOUT, experimental=True,
                    fullCityRouting=dict(road_metrics(routing), edgeCount=len(actual), pavementBuildingIntersections=intersections))
    return scene, routing, decision


def package(scene, graph, routing, decision):
    """Fresh bundled assets only. All renderers share identical geometry/routing."""
    artifacts = render_viewer(scene, graph, routing=routing)
    artifacts.update({
        'city.json': canonical_json_bytes(scene),
        'graph.ucg.json': canonical_json_bytes(graph),
        'decision.json': canonical_json_bytes(decision),
        'preview.svg': render_preview(scene, graph, routing=routing),
        'showcase.svg': render_showcase(scene, graph, routing=routing),
        'README_SNIPPET.md': b'[![Experimental parcel city](showcase.svg)](index.html)\n',
    })
    summary = _diagnostic_summary(graph['diagnostics'])
    media_types = {'.json': 'application/json', '.js': 'text/javascript', '.css': 'text/css',
                   '.html': 'text/html', '.svg': 'image/svg+xml', '.md': 'text/markdown'}
    manifest = dict(schemaVersion='manifest/0.1',
                    status='PARTIAL' if summary['warningCount'] or summary['errorCount'] else 'COMPLETE',
                    generator=graph['generator'], repository=graph['repository'],
                    options=dict(layoutAlgorithm=LAYOUT, experimental=True, hintPolicy='same-structure-only',
                                 width=1200, height=675, theme=scene['theme']),
                    privacyWarnings=['Private source paths and architecture may be exposed. Publication is not automatic.'],
                    diagnostics=summary,
                    artifacts=[_artifact_record(path, media_types[Path(path).suffix], content)
                               for path, content in sorted(artifacts.items())])
    artifacts['manifest.json'] = canonical_json_bytes(manifest)
    return artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
    parser.add_argument('--out', required=True, type=Path)
    parser.add_argument('--previous-scene', type=Path)
    args = parser.parse_args()
    try:
        if args.out.exists():
            raise ValueError('output directory must not already exist')
        def load(path):
            if path.stat().st_size > 64*1024*1024:
                raise ValueError('experimental input exceeds 64 MiB')
            return loads_strict_json(path.read_text(encoding='utf-8'))
        graph, baseline = load(args.build/'graph.ucg.json'), load(args.build/'city.json')
        previous = load(args.previous_scene) if args.previous_scene else None
        scene, routing, decision = export_scene(baseline, graph, previous)
        artifacts = package(scene, graph, routing, decision)
        args.out.mkdir(parents=True, exist_ok=False)
        for name, content in sorted(artifacts.items()):
            path = args.out/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        print(f"EXPERIMENTAL {decision['selection']}: {len(scene['buildings'])} buildings, {len(routing['routes'])} routes -> {args.out}")
    except (OSError, ValueError) as error:
        parser.exit(2, f'Experimental parcel export failed: {error}\n')


if __name__ == '__main__':
    main()
