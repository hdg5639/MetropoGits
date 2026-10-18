"""Export a fixed-city shared-road comparison without executing input assets."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from metropogits import __version__
from metropogits.access_routes import derive_access_routes
from metropogits.cli import _artifact_record, _diagnostic_summary
from metropogits.preview import render_preview
from metropogits.road_consolidation import consolidate_routes
from metropogits.showcase import render_showcase
from metropogits.viewer import render_viewer
from scripts.canonical_json import canonical_json_bytes, loads_strict_json
from scripts.parcel_pilot import pavement_intersections
from scripts.parcel_viewer import _bounded_geometry
from scripts.road_metrics import road_metrics
from scripts.validate_city import validate_document


def compare(scene, graph):
    errors = validate_document(scene, graph)
    if errors:
        raise ValueError('; '.join(errors[:8]))
    _bounded_geometry(scene)
    scene = json.loads(canonical_json_bytes(scene))
    baseline = derive_access_routes(scene, graph)
    candidate = consolidate_routes(baseline)
    def identities(routing):
        return {r['id']: (r['source'], r['target'], r['kind'], r['edgeIds'], r['networkIds'])
                for r in routing['routes']}
    expected = {e for n in scene['networks'] for e in n['edgeIds']}
    actual = {e for r in candidate['routes'] for e in r['edgeIds']}
    if identities(baseline) != identities(candidate) or expected != actual:
        raise ValueError('consolidation lost or changed an evidenced relationship')
    if pavement_intersections(candidate, scene['buildings']):
        raise ValueError('consolidated pavement intersects a building')
    before, after = road_metrics(baseline), road_metrics(candidate)
    for key in ('pavementCenterlineLength', 'nearbyParallelPairLength'):
        if after[key] > before[key]+1e-8:
            raise ValueError('global road regression: ' + key)
    return baseline, candidate, dict(version='road-consolidation/0.1', before=before, after=after,
                                    **candidate['consolidation'])


def package(scene, graph, routing, report):
    artifacts = render_viewer(scene, graph, routing=routing)
    artifacts['index.html'] = artifacts['index.html'].replace(b'METROPOGITS / STATIC CITY',
        b'METROPOGITS / SHARED ROAD STUDY').replace(b'METROPOGITS / EXPERIMENTAL PARCEL LAYOUT',
        b'METROPOGITS / SHARED ROAD STUDY')
    artifacts.update({'city.json': canonical_json_bytes(scene), 'graph.ucg.json': canonical_json_bytes(graph),
                      'decision.json': canonical_json_bytes(report),
                      'preview.svg': render_preview(scene, graph, routing=routing),
                      'showcase.svg': render_showcase(scene, graph, routing=routing),
                      'README_SNIPPET.md': b'[![Shared road city](showcase.svg)](index.html)\n'})
    types = {'.html': 'text/html', '.js': 'text/javascript', '.css': 'text/css',
             '.json': 'application/json', '.svg': 'image/svg+xml', '.md': 'text/markdown'}
    summary = _diagnostic_summary(graph['diagnostics'])
    manifest = dict(schemaVersion='manifest/0.1',
                    status='PARTIAL' if summary['errorCount'] or summary['warningCount'] else 'COMPLETE',
                    generator=dict(name='metropogits', version=__version__, catalogVersion=graph['generator']['catalogVersion']),
                    repository=graph['repository'], diagnostics=summary,
                    options=dict(layoutAlgorithm=scene['layoutAlgorithm'], routingVersion=routing['version'],
                                 experimental=True, theme=scene['theme'], width=1200, height=675),
                    privacyWarnings=['Source paths and architecture may be sensitive; publication is not automatic.'],
                    artifacts=[_artifact_record(p, types[Path(p).suffix], b) for p, b in sorted(artifacts.items())])
    artifacts['manifest.json'] = canonical_json_bytes(manifest)
    return artifacts


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('build', type=Path)
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
        before, after, report = compare(scene, graph)
        outputs = {name: package(scene, graph, routing, report)
                   for name, routing in [('before', before), ('after', after)]}
        args.out.mkdir(parents=True, exist_ok=False)
        for name, artifacts in outputs.items():
            for relative, content in artifacts.items():
                path = args.out/name/relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(content)
        print(json.dumps(report, sort_keys=True))
    except (OSError, ValueError) as error:
        parser.exit(2, f'Road consolidation failed: {error}\n')


if __name__ == '__main__':
    main()
