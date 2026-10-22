"""Land admission -> physical envelopes -> shared offline architecture."""

from metropogits.street_diagonals import overlap
from .architecture_catalog import catalog_world
from .urban_land import admit_land, validate_land
from .compounds import derive_compounds
from .geometry import rectangle


def urban_world(world, graph):
    if 'capacityPlan' in world:
        # A physical program has already shaped district boundaries, roads and
        # parcels. Do not run the obsolete vacancy-only admission a second time.
        from .capacity import VERSION
        from .geometry import q
        decisions = {}
        for p in world['parcels']:
            program = world['capacityPlan']['programs'][p['entityId']]
            envelope = {k: p[k] for k in ('center', 'angle', 'width', 'depth', 'footprint')}
            decisions[p['entityId']] = dict(status='ALLOCATED', request=program,
                sourceEnvelope=dict(envelope, **program['sourceEnvelope']), allocatedEnvelope=envelope,
                allocatedArea=q(p['width'] * p['depth']))
        physical = world
        plan = dict(version=VERSION, derived=True, structural=False, decisions=decisions,
                    counts=world['capacityPlan']['counts'], districts=world['capacityPlan']['districts'],
                    basis='DEMAND_FIRST_PHYSICAL_REPLAN_NOT_SOURCE_FACTS', limitations=[])
    else:
        compounds = derive_compounds(world, graph, campus_landmarks=True)[0]
        physical, plan = admit_land(world, graph, compounds)
        validate_land(world, physical, graph, compounds, plan)
    styled, profiles = catalog_world(physical, graph, massing="modern")
    for identity, profile in profiles.items():
        decision = plan["decisions"][identity]
        profile["landAllocation"] = dict(version=plan["version"], status=decision["status"],
                                         sourceEnvelope=decision["sourceEnvelope"],
                                         allocatedEnvelope=decision["allocatedEnvelope"], request=decision["request"])
        if 'capacityPlan' in world:
            profile['landAllocation']['replanned'] = True
    return styled, profiles, plan


def clear_physical_trees(landscape, world):
    if not landscape:
        return landscape
    from .urban_land import ClearanceIndex
    index = ClearanceIndex()
    for p in world["parcels"]:
        index.add(("building", p["entityId"]), p["footprint"])
    trees = []
    for t in landscape["trees"]:
        poly = rectangle(t["center"], 0, t["radius"] * 2, t["radius"] * 2)
        nearby = {k for cell in index.cells_for(poly) for k in index.cells[cell]}
        if not any(overlap(poly, index.shapes[k]) for k in nearby):
            trees.append(t)
    return dict(landscape, trees=trees)
