"""Read-only local corpus benchmark; no target builds, hooks or dependencies.

Measurements live outside canonical artifacts. Profiling times are cumulative
within each named stage (not additive); the second build is unprofiled.
"""
from __future__ import annotations

import argparse
from collections import Counter
import cProfile
import hashlib
from html import escape
import json
import platform
import shutil
import subprocess
from pathlib import Path
from time import perf_counter

from metropogits.analyzers.jsts import LANGUAGES as JSTS_LANGUAGES
from metropogits.cli import build_repository
from scripts.canonical_json import canonical_json_bytes, loads_strict_json
from scripts.road_consolidation import package
from scripts.street_grid import compare


STAGES = {
    'scan_repository': 'scan', 'build_structural_ucg': 'structuralGraph',
    'enrich_graph': 'languageAndCatalog', 'generate_city': 'layout',
    'derive_access_routes': 'accessRouting', 'render_preview': 'preview',
    'render_showcase': 'showcase', 'render_viewer': 'viewerPackaging',
}


def summarize(graph, scene):
    """Coverage denominators are scanned FILE entities, not all repository files."""
    files = [e for e in graph['entities'] if e['kind'] == 'FILE']
    skipped = {d.get('sourcePath') for d in graph['diagnostics']
               if d['code'] in {'JAVA_ANALYSIS_SKIPPED', 'JSTS_ANALYSIS_SKIPPED'}}
    languages = []
    for language in sorted({e.get('language', 'unknown') for e in files}):
        members = [e for e in files if e.get('language', 'unknown') == language]
        supported = language == 'java' or language in JSTS_LANGUAGES
        processed = sum(supported and e['path'] not in skipped for e in members)
        languages.append(dict(language=language, files=len(members), adapterProcessed=processed,
                              structuralOnly=len(members)-processed))
    dependencies = [e for e in graph['edges'] if e['type'] not in {'CONTAINS', 'DECLARES'}]
    unresolved = Counter(d['code'] for d in graph['diagnostics'] if 'UNRESOLVED' in d['code'])
    archetypes = Counter(b['archetype'] for b in scene['buildings'])
    processed = sum(item['adapterProcessed'] for item in languages)
    total = len(files)
    districts = scene['districts']
    bounds = None
    if districts:
        width = max(d['x']+d['width'] for d in districts)-min(d['x'] for d in districts)
        depth = max(d['z']+d['depth'] for d in districts)-min(d['z'] for d in districts)
        bounds = dict(width=width, depth=depth, aspectRatio=width/depth if depth else None)
    return dict(files=total, languages=languages, adapterProcessed=processed,
        adapterCoverage=processed/total if total else None,
        structuralOnly=total-processed, districts=len(districts),
        buildings=len(scene['buildings']), networks=len(scene['networks']),
        archetypes=dict(sorted(archetypes.items())),
        nonGenericRatio=1-archetypes['GENERIC_BUILDING']/total if total else None,
        dependencyEdges=len(dependencies),
        dependencyTypes=dict(sorted(Counter(e['type'] for e in dependencies).items())),
        dependencyConfidence=dict(sorted(Counter(e['confidence'] for e in dependencies).items())),
        unresolvedDiagnostics=dict(sorted(unresolved.items())),
        diagnosticCodes=dict(sorted(Counter(d['code'] for d in graph['diagnostics']).items())),
        bounds=bounds,
        limitations=['Adapter processed does not establish complete syntax or relationship coverage.',
            'Unresolved diagnostics are not an estimate of unobserved/missed dependencies.',
            'No language adapter means no claim of extracted internal relationships.',
            'Non-generic ratio is not an accuracy or success score.'])


def artifact_hashes(directory):
    return {p.relative_to(directory).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(directory.rglob('*')) if p.is_file()}


def positions(scene):
    return {b['entityId']: [b[k] for k in ('x', 'z', 'width', 'depth', 'height')]
            for b in scene['buildings']}


def git_identity(repo):
    executable = shutil.which('git')
    if not executable:
        raise ValueError('git must be available on PATH to pin the benchmark revision')
    def run(*args):
        return subprocess.run([executable, '-c', 'core.fsmonitor=false', '-C', str(repo), *args],
            check=True, capture_output=True, text=True, timeout=30).stdout.strip()
    return dict(revision=run('rev-parse', 'HEAD'),
                trackedDirty=bool(run('status', '--porcelain', '--untracked-files=no')),
                untrackedPolicy='Scanner may include eligible untracked files; graph digest pins scanned input.')


def write_report(output, report):
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    cards = []
    for case in report['cases']:
        name = escape(case['name'], quote=True)
        if 'error' in case:
            cards.append(f'<section><h2>{name}</h2><pre>{escape(case["error"])}</pre></section>')
            continue
        s = case['summary']
        destination = 'streets' if case.get('streets') else 'first'
        cards.append(f'<section><h2>{name}</h2><p>{s["buildings"]} buildings · '
            f'{s["adapterProcessed"]}/{s["files"]} adapter-processed · '
            f'{s["dependencyEdges"]} non-structural edges · {case["status"]}</p>'
            f'<a href="{name}/{destination}/index.html">Open viewer</a> · '
            f'<a href="{name}/first/preview.svg">Structural preview</a>'
            f'<img alt="{name} generated showcase" src="{name}/{destination}/showcase.svg"></section>')
    (output/'index.html').write_text('<!doctype html><meta charset="utf-8">'
        '<title>Cross-repository benchmark</title><style>body{background:#101820;color:#ddd;'
        'font:16px system-ui;margin:2rem}a{color:#75cfff}section{margin:2rem 0}img{display:block;'
        'width:min(100%,1200px);background:#080d14}pre{white-space:pre-wrap}</style>'
        '<h1>Cross-repository benchmark</h1><p>Local static analysis only. Structural streets '
        'are visual infrastructure, not inferred dependencies. Generic output is not a failure. '
        'Fitted previews have different world scales; use the browser audit for common-scale comparison.</p>'
        + ''.join(cards), encoding='utf-8')


def benchmark_case(repo, output, *, streets=False):
    identity = git_identity(repo)
    times, hashes, scenes = [], [], []
    profile = cProfile.Profile()
    for index, label in enumerate(('first', 'repeat')):
        start = perf_counter()
        if index == 0:
            profile.enable()
        try:
            manifest = build_repository(repo, output/label, repository_id=f'benchmark/{repo.name}',
                                        revision=identity['revision'])
        finally:
            profile.disable()
        times.append(perf_counter()-start)
        hashes.append(artifact_hashes(output/label))
        scenes.append(loads_strict_json((output/label/'city.json').read_text(encoding='utf-8')))
    if identity != git_identity(repo):
        raise ValueError('repository revision/tracked state changed during benchmark')
    graph = loads_strict_json((output/'first/graph.ucg.json').read_text(encoding='utf-8'))
    mismatches = sorted(k for k in hashes[0].keys() | hashes[1].keys() if hashes[0].get(k) != hashes[1].get(k))
    stage_times = Counter()
    for entry in profile.getstats():
        code = entry.code
        if not isinstance(code, str) and code.co_name in STAGES and 'metropogits' in code.co_filename:
            stage_times[STAGES[code.co_name]] += entry.totaltime
    result = dict(name=repo.name, input=identity, status=manifest['status'],
        summary=summarize(graph, scenes[0]), buildSeconds=times,
        profiledStageSeconds=dict(stage_times), artifactHashes=hashes[0],
        determinism=dict(identicalArtifacts=not mismatches, mismatches=mismatches,
                         identicalBuildingPositions=positions(scenes[0]) == positions(scenes[1])),
        viewerPerformance=None)
    if mismatches:
        raise ValueError('repeat artifact mismatch: '+', '.join(mismatches))
    if streets:
        start = perf_counter()
        _, routing, study = compare(scenes[0], graph, aligned=True, curves=True)
        result['streetDerivationSeconds'] = perf_counter()-start
        start = perf_counter()
        artifacts = package(scenes[0], graph, routing, study)
        result['streetPackagingSeconds'] = perf_counter()-start
        # Re-derive from the second canonical build, not a reused routing cache.
        _, repeated, repeated_study = compare(scenes[1], graph, aligned=True, curves=True)
        repeat_artifacts = package(scenes[1], graph, repeated, repeated_study)
        if artifacts != repeat_artifacts:
            raise ValueError('repeat experimental street artifacts differ')
        result['determinism']['identicalStreetArtifacts'] = True
        for relative, content in artifacts.items():
            path = output/'streets'/relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        result['streets'] = dict(structuralSegments=study['structuralSegments'],
            curves=len(study['curves']['corners']), status=study['streetStatus'],
            assignedRoutes=len(study['assignment']['assignedRouteIds']),
            fallbackRoutes=len(study['assignment']['fallbackRouteIds']),
            routingDigest=hashlib.sha256(canonical_json_bytes(routing)).hexdigest())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, action='append', required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--streets', action='store_true', help='also package aligned curved structural streets')
    args = parser.parse_args()
    repos, output = [p.resolve(strict=True) for p in args.repo], args.out.resolve()
    if output.exists() or len({p.name.casefold() for p in repos}) != len(repos):
        parser.error('use a new output directory and unique repository directory names')
    if any(output == p or output in p.parents or p in output.parents for p in repos):
        parser.error('benchmark output must be outside every input repository')
    output.mkdir(parents=True)
    report = dict(version='repository-benchmark/0.1', python=platform.python_version(),
        platform=platform.system(), machine=platform.machine(), cases=[],
        timingPolicy='First build uses cProfile; stage totals are cumulative, not additive. '
            'Second build is unprofiled. Timings are observational, not canonical or a cross-machine SLA.',
        viewerPolicy='Not measured here. Run scripts/viewer_audit.mjs; CPU submission timing is not GPU FPS.')
    failed = False
    for repo in repos:
        print(f'Benchmarking {repo.name}', flush=True)
        try:
            case = benchmark_case(repo, output/repo.name, streets=args.streets)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            case = dict(name=repo.name, error=str(error), status='FAILED')
            failed = True
        report['cases'].append(case)
        write_report(output, report)
        print(json.dumps({k: case[k] for k in ('name', 'status')}), flush=True)
    return int(failed)


if __name__ == '__main__':
    raise SystemExit(main())
