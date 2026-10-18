"""Static demand grades, not runtime traffic or new relationship kinds (ADR-019)."""

STYLES = {
    'ACCESS': ('Access', .7, '#33465a'),
    'ALLEY': ('Alley', .9, '#33465a'),
    'STREET': ('Street', 1.5, '#43566a'),
    'AVENUE': ('Avenue', 2.5, '#607c92'),
    'TRUNK': ('Interdistrict trunk demand', 3.5, '#7897ac'),
}


def demand_grade(access, edges, files, cross_edges):
    if access:
        return 'ACCESS'
    if edges >= 64 and files >= 16 and cross_edges >= 16:
        return 'TRUNK'
    if edges >= 24 and files >= 8:
        return 'AVENUE'
    if edges >= 4 and files >= 3:
        return 'STREET'
    return 'ALLEY'


def derive_road_hierarchy(scene, routing):
    # Reuse the exact major structural boundaries drawn by the existing viewer.
    # Local import avoids the preview -> access_routes -> hierarchy import cycle.
    from metropogits.preview import _major_district_ids

    majors = _major_district_ids(scene)
    parents = {d['id']: d['parentId'] for d in scene['districts']}
    owners = {}
    for building in scene['buildings']:
        current, visited = building['districtId'], set()
        while current is not None and current not in majors and current not in visited:
            visited.add(current)
            current = parents.get(current)
        owners[building['entityId']] = current if current in majors else None
    routes = {r['id']: r for r in routing['routes']}
    profiles = {}
    for segment in sorted(routing['segments'], key=lambda s: s['id']):
        edges, cross, sources, targets, districts = set(), set(), set(), set(), set()
        for identity in set(segment['routeIds']):
            route = routes[identity]
            edges.update(route['edgeIds'])
            sources.add(route['source'])
            targets.add(route['target'])
            a, b = owners.get(route['source']), owners.get(route['target'])
            districts.update(d for d in (a, b) if d is not None)
            if a is not None and b is not None and a != b:
                cross.update(route['edgeIds'])
        files = sources | targets
        grade = demand_grade(segment['access'], len(edges), len(files), len(cross))
        label, target, surface = STYLES[grade]
        width = min(segment['width'], target)
        profiles[segment['id']] = dict(
            grade=grade, label=label, edgeCount=len(edges), sourceCount=len(sources),
            targetCount=len(targets), buildingCount=len(files), majorDistrictCount=len(districts),
            crossDistrictEdgeCount=len(cross), unassignedBuildingCount=sum(owners.get(f) is None for f in files),
            routeCount=len(set(segment['routeIds'])), targetWidth=target, width=width,
            clearanceLimited=width < target, surface=surface,
        )
    return dict(version='road-hierarchy/0.1', segments=profiles)
