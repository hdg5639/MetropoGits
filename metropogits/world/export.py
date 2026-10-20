"""One physical world feeding the existing browser and CPU isometric export."""

import copy
import html
import math
from importlib.resources import files
from pathlib import Path

from metropogits import __version__
from metropogits.road_hierarchy import derive_road_hierarchy
from metropogits.viewer import _javascript_assignment
from metropogits.cli import _artifact_record, _diagnostic_summary
from scripts.canonical_json import canonical_json_bytes
from .geometry import bounds, centroid, point, q, ribbon
from .seed import derive
from .zoning import planning_document
from .materials import ROLE_COLORS as COLORS, part_material, policy as material_policy
from .landscape import generate_landscape
from .rivers import bridge_faces, height_at
from .street_hierarchy import COLORS as STREET_COLORS, marking_surfaces
from .elevation import surface as terrain_surface, pavement as graded_pavement, lifted_faces, foundation_faces
from .street_mesh import street_mesh, VERSION as STREET_MESH_VERSION
from .compounds import derive_compounds

GROUND = ["#33464b", "#4a4149", "#354b42", "#504835", "#3e4454", "#4e3c42", "#3b4c50"]
ZONE_COLORS = {
    "GENERAL_MIXED": "#414b50",
    "SERVICE_QUARTER": "#3c5260",
    "INDUSTRIAL_LOGISTICS": "#3c574d",
    "CAMPUS_RESEARCH": "#5b5540",
    "GATEWAY_CIVIC": "#5d4555",
    "COMMERCIAL_FRONTEND": "#474b60",
}


def _landscape(world, value):
    if value is None:
        value = generate_landscape(world) if world.get("patternScale") == "adaptive" else False
    if value and world.get('campusPlan',{}).get('sites') and not value.get('campusReserved'):
        value=copy.deepcopy(value)
        value['campusReserved']=True
        for site in world['campusPlan']['sites']:
            for court in site['courts']:
                value['patches'].append(dict(id=court['id'],districtId=site['parentId'],polygon=court['polygon'],
                                            color='#55755c',reservedCampus=True))
    if value and "surface" in world and not value.get("elevated"):
        value=copy.deepcopy(value)
        value.update(elevated=True,terrainPreset=world["terrainPreset"])
        s=terrain_surface(world["terrain"])
        for p in value["patches"]:
            p["faces"]=[dict(points=[[q[0],s.height(q)+.02,q[1]] for q in reversed(poly)],color=p["color"])
                        for poly in s.pieces(p["polygon"])]
        for tree in value["trees"]:
            tree["faces"]=lifted_faces(tree["faces"],world["terrain"],rigid=True)
    return value


def view_data(world, scene, graph, *, landscape=None, building_style="semantic", role_compounds=True):
    if building_style not in ("semantic", "architectural", "purposeful"):
        raise ValueError("unknown building presentation style")
    programs = None
    if building_style == 'purposeful':
        from .architecture import purpose_world
        world, programs = purpose_world(world, graph)
    landscape = _landscape(world, landscape)
    compounds, compound_policy = (derive_compounds(world, graph) if role_compounds else
                                  ([],dict(disabled=True,structural=False)))
    root = "visual:world-root:" + derive(world["repositoryNamespace"])

    def envelope(poly):
        x, z, right, bottom = bounds(poly)
        return dict(x=x, z=z, width=right - x, depth=bottom - z)

    districts = [dict(id=root, parentId=None, **envelope(world["envelope"]))]
    territories = []
    neighborhoods = world.get("zoning", world.get("softZoning", {})).get("zones", [])
    precincts = {s['zoneId']:s['sourceProgram'] for s in world.get('campusPlan',{}).get('sites',[]) if 'sourceProgram' in s}
    physical_polygons = {d["id"]: d["polygon"] for d in world["districts"]}
    physical_polygons.update({z["id"]: z["polygon"] for z in neighborhoods})
    for d in world["districts"]:
        districts.append(dict(id=d["id"], parentId=root, **envelope(d["polygon"])))
        if neighborhoods:
            districts[-1]["label"] = d["label"]
    for z in neighborhoods:
        districts.append(
            dict(
                id=z["id"],
                label=z['label'] + (' · '+precincts[z['id']]['label'] if z['id'] in precincts else ''),
                parentId=z["parentId"],
                **envelope(z["polygon"]),
            )
        )
    for d in districts:
        polygon = world["envelope"] if d["id"] == root else physical_polygons[d["id"]]
        x, z, right, bottom = bounds(polygon)
        territories.append(
            dict(
                id=d["id"],
                rectangles=[],
                boundary=[[a, b] for a, b in zip(polygon, polygon[1:] + polygon[:1])],
                labelAnchor=point(centroid(polygon)),
                bounds=dict(minX=x, minZ=z, maxX=right, maxZ=bottom),
            )
        )
    if "surface" in world:
        s=terrain_surface(world["terrain"])
        for territory in territories:
            territory["boundary"]=[[a[:2],b[:2]] for start,end in territory["boundary"]
                                   for path in [s.profile(start,end)] for a,b in zip(path,path[1:])]
    buildings = []
    models = {}
    for p in world["parcels"]:
        b = {
            k: p[k]
            for k in (
                "entityId",
                "districtId",
                "width",
                "depth",
                "height",
                "archetype",
                "evidenceIds",
                "styleVariant",
            )
        }
        b.update(x=p["center"][0] - p["width"] / 2, z=p["center"][1] - p["depth"] / 2)
        if "baseElevation" in p:
            b["baseElevation"]=p["baseElevation"]
        if "zoneId" in p:
            b["districtId"] = p["zoneId"]
        buildings.append(b)
        models[p["entityId"]] = dict(
            p,
            frontageEdge=[p["footprint"][2], p["footprint"][3]],
            facing=[-math.sin(p["angle"]), math.cos(p["angle"])],
            pivot=p["center"],
            shift=[0, 0],
            frontagePoint=p["entrance"],
            frontageGap=1,
            displacement=0,
            pinnedDoors=[p["entrance"]],
        )
        if "surface" in world:
            models[p["entityId"]]["parts"]=[dict(part,y=part["y"]+p["baseElevation"]) for part in p["parts"]]
            models[p["entityId"]]["foundationFaces"]=foundation_faces(p,world["terrain"])
    physical_scene = dict(
        schemaVersion="world-view/0.1",
        layoutAlgorithm=world["generatorVersion"],
        ucgDigest=world["ucgDigest"],
        theme=scene["theme"],
        districts=districts,
        buildings=buildings,
        networks=world["networks"],
        decorations=[],
    )
    routing = copy.deepcopy(world["routing"])
    routing["parcelPlan"] = dict(buildings=models, changedFootprintIds=sorted(models))
    hierarchy = derive_road_hierarchy(physical_scene, routing)
    pavement_color = (
        "#26333e" if world.get("zoningPolicy") == "neighborhoods" else "#3e4a54"
    )
    surfaces = [
        dict(
            s,
            points=list(reversed(ribbon(s["start"], s["end"], s["width"]))),
            color=pavement_color,
        )
        for s in world["streets"]
    ]
    for surface in surfaces:
        if "heights" in surface:
            surface["pointHeights"] = [height_at(surface,p) for p in surface["points"]]
    if "surface" in world and "streetPlan" not in world:
        surfaces=[p for s in world["streets"] for p in graded_pavement(s,world["terrain"],pavement_color)]
    if "streetPlan" in world:
        profiles = world["streetPlan"]["segments"]
        if "surface" in world:
            surfaces = [dict(p, physicalId=s["id"], streetClass=profiles[s["id"]]["streetClass"])
                        for s in world["streets"] for p in graded_pavement(s,world["terrain"],pavement_color)]
        else:
            surfaces = [dict(p, physicalId=p["id"], streetClass=profiles[p["id"]]["streetClass"]) for p in surfaces]
        for s in routing["segments"]:
            s.update(streetClass=profiles[s["physicalId"]]["streetClass"],
                     streetReasons=profiles[s["physicalId"]]["reasons"])
    incidence = {}
    for s in world["streets"]:
        for p in (s["start"], s["end"]):
            incidence.setdefault(tuple(p), []).append(s)
    for p, streets in incidence.items():
        if "surface" in world:
            continue
        if len(streets) < 3:
            continue
        radius = max(s["width"] for s in streets) / 2
        ring = [
            [
                p[0] + math.cos(i * math.pi / 4) * radius,
                p[1] + math.sin(i * math.pi / 4) * radius,
            ]
            for i in range(8)
        ]
        surfaces.extend(
            dict(points=[b, b, a, list(p)], color=pavement_color)
            for a, b in zip(ring, ring[1:] + ring[:1])
        )
    if 'streetPlan' in world:
        surfaces=street_mesh(world)
    pavement = dict(
        version="world-pavement/0.1",
        segments={
            s["id"]: [
                dict(
                    points=list(reversed(ribbon(s["start"], s["end"], s["width"]))),
                    width=s["width"],
                    **(dict(pointHeights=[height_at(s,p)+.03 for p in reversed(ribbon(s["start"],s["end"],s["width"]))])
                       if "heights" in s else {}),
                )
            ]
            for s in routing["segments"]
        },
    )
    from metropogits.facilities import FACILITY_MODELS
    data = dict(
        facilityModels=FACILITY_MODELS,
        scene=physical_scene,
        canonicalScene=scene,
        ucg=graph,
        routing=routing,
        roadHierarchy=hierarchy,
        world=dict(
            schemaVersion=world["schemaVersion"],
            seed=world["seed"],
            terrainPreset=world["terrainPreset"],
        ),
        majorDistrictIds=[d["id"] for d in world["districts"]],
        streets=dict(
            structural=True,
            surfaces=surfaces,
            **(dict(meshVersion=STREET_MESH_VERSION) if 'streetPlan' in world else {}),
            orientedEntityIds=sorted(models),
            roleCompounds=compounds,
            roleCompoundPolicy=compound_policy,
            rectangles=[],
        ),
        streetDemand=pavement,
        streetCurves=dict(
            version="world-lines/0.1",
            segments={s["id"]: [s["start"], s["end"]] for s in routing["segments"]},
            paintSegments={
                s["id"]: [dict(start=s["start"], end=s["end"])]
                for s in routing["segments"]
            },
        ),
        occupiedGround=dict(
            pads=[
                dict(districtId=d["id"], polygons=[list(reversed(d["polygon"]))])
                for d in world["districts"]
            ]
        ),
        cityContext=dict(
            version="city-context/0.1", ground="#35434b", majorColors=GROUND
        ),
        territories=dict(districts=territories),
    )
    if "streetPlan" in world:
        data["physicalStreetPlan"] = dict(version=world["streetPlan"]["version"], colors=STREET_COLORS,
                                          summary=world["streetPlan"]["summary"], markings=marking_surfaces(world))
    if "terrain" in world:
        data["terrain"] = world["terrain"]
        if "surface" in world:
            data["terrain"]=copy.deepcopy(world["terrain"])
            for f in data["terrain"]["features"]:
                f["faces"]=lifted_faces(f["faces"],world["terrain"])
        if world["terrain"].get("crossings"):
            data["infrastructure"] = dict(structural=True, faces=bridge_faces(world["terrain"]))
        if world["terrain"].get("version") in ("terrain/0.4","terrain/0.5","terrain/0.6"):
            from .river_landscape import natural_faces
            data["terrain"]["features"]=natural_faces(world)
    if "surface" in world:
        data["surface"]=world["surface"]
        data["streetDemand"]["segments"]={s["id"]:graded_pavement(s,world["terrain"],pavement_color,.11) for s in routing["segments"]}
        data["streetCurves"]["segments"]={s["id"]:[p[:2] for p in s["heightProfile"]] for s in routing["segments"]}
        data["streetCurves"]["paintSegments"]={s["id"]:[dict(start=a[:2],end=b[:2]) for a,b in zip(s["heightProfile"],s["heightProfile"][1:])] for s in routing["segments"]}
    if neighborhoods:
        data["semanticZoning"] = {z["id"]: z for z in neighborhoods}
        if world.get("zoningPolicy") == "neighborhoods":
            data["neighborhoodPlan"] = dict(
                version=world["zoning"]["version"],
                blocks={b["id"]: b for b in world["zoning"]["blocks"]},
                mainRoadCount=len(world["zoning"]["mainRoads"]),
            )
            if world.get("patternScale") in ("district", "adaptive"):
                data["neighborhoodPlan"].update(
                    patternScale=world["patternScale"],
                    districtPatterns=world["zoning"]["districtPatterns"],
                )
        if "softZoning" in world:
            data["softZoning"] = dict(
                version=world["softZoning"]["version"], influenceOnly=True
            )
        else:
            data["occupiedGround"]["pads"] = [
                dict(
                    districtId=z["id"],
                    polygons=[list(reversed(z["polygon"]))],
                    color=ZONE_COLORS.get(
                        z["clusterKey"], ZONE_COLORS["GENERAL_MIXED"]
                    ),
                )
                for z in neighborhoods
            ]
    if landscape:
        # Local administrative cells live in one continuous parent material.
        # Keep the actual cells in territories/inspectors, not separate plates.
        data["occupiedGround"]["pads"] = [
            dict(districtId=d["id"], polygons=[list(reversed(d["polygon"]))],
                 color=GROUND[i % len(GROUND)])
            for i, d in enumerate(world["districts"])
        ]
        data["landscape"] = landscape
    if programs is not None:
        data['buildingPrograms'] = programs
    if building_style in ("architectural", "purposeful"):
        data["buildingMaterials"] = material_policy()
    return data


def render_svg(world, width=1200, height=750, *, landscape=None, building_style="semantic", compounds=None, graph=None):
    if building_style not in ("semantic", "architectural", "purposeful"):
        raise ValueError("unknown building presentation style")
    if building_style == 'purposeful':
        if graph is None:
            raise ValueError('purposeful architecture requires its source graph')
        from .architecture import purpose_world
        world, _ = purpose_world(world, graph)
    landscape = _landscape(world, landscape)
    graded="surface" in world
    field=terrain_surface(world["terrain"]) if graded else None
    compound_by_id={f['id']:f for f in compounds or []}
    grouped={k for f in compounds or [] for k in f['memberEntityIds']}
    display_buildings=[b for b in world['parcels'] if b['entityId'] not in grouped]
    for f in compounds or []:
        model=f['physicalModel']
        display_buildings.append(dict(model,entityId=f['id'],height=f['height'],
            archetype=f['archetypeCounts'][0]['archetype'],
            parts=[dict(p,y=q(p['y']-model['baseElevation'])) for p in model['parts']]))
    def iso(p, y=0):
        return [(p[0] - p[1]) * 0.866, (p[0] + p[1]) * 0.5 - y]

    points = [iso(p) for p in world["envelope"]]
    points += [
        iso(p, part["y"] + part["height"]+b.get("baseElevation",0))
        for b in display_buildings
        for part in b["parts"]
        for p in part["footprint"]
    ]
    x0, y0, x1, y1 = bounds(points)
    scale = min((width - 80) / max(1, x1 - x0), (height - 155) / max(1, y1 - y0))
    ox = 40 + (width - 80 - (x1 - x0) * scale) / 2 - x0 * scale
    oy = 75 + (height - 155 - (y1 - y0) * scale) / 2 - y0 * scale

    def project(p, y=0):
        x, z = iso(p, y)
        return [ox + x * scale, oy + z * scale]

    def encoded(points):
        return " ".join(f"{x:.3f},{y:.3f}" for x, y in points)

    def polygon(points, fill, extra=""):
        return f'<polygon points="{encoded(points)}" fill="{fill}" {extra}/>'

    def escape(text):
        return html.escape(str(text), quote=True)

    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Procedural source city — flat world</title>',
        f'<desc id="desc">{len(world["parcels"])} source files, {len(world["districts"])} structural districts. Streets are visual infrastructure; semantic trips retain exact edge IDs.</desc>',
        '<rect width="100%" height="100%" fill="#101923"/>',
        f'<text x="28" y="30" fill="#e2edf5" font-family="sans-serif" font-size="20">{escape(world["repositoryNamespace"])}</text>',
        f'<text x="28" y="51" fill="#8da9b8" font-family="sans-serif" font-size="11">{len(world["parcels"])} files · {len(world["districts"])} districts · seed {world["seed"]}</text>',
    ]
    for i, d in enumerate([] if graded else world["districts"]):
        lines.append(
            polygon(
                [project(p) for p in d["polygon"]],
                GROUND[i % len(GROUND)],
                f'data-directory-id="{escape(d["id"])}" stroke="#62727c" stroke-width=".6"',
            )
        )
    if graded:
        for face in world["surface"]["faces"]:
            lines.append(polygon([project([x,z],y) for x,y,z in face["points"]],face["color"]))
    for z in ([] if landscape or graded else world.get("zoning", {}).get("zones", [])):
        lines.append(
            polygon(
                [project(p) for p in z["polygon"]],
                ZONE_COLORS.get(z["clusterKey"], ZONE_COLORS["GENERAL_MIXED"]),
                f'data-zone-id="{escape(z["id"])}"',
            )
        )
    if landscape:
        for patch in landscape["patches"]:
            if graded:
                for face in patch["faces"]:
                    lines.append(polygon([project([x,z],y) for x,y,z in face["points"]],face["color"]))
                continue
            lines.append(polygon([project(p, .01) for p in patch["polygon"]],
                                 patch["color"], 'data-decorative="green-pocket"'))
    for s in ([] if 'streetPlan' in world else world["streets"]):
        road_color = (STREET_COLORS[world["streetPlan"]["segments"][s["id"]]["streetClass"]]["overview"]
                      if "streetPlan" in world else "#26333e")
        if graded:
            for p in graded_pavement(s,world["terrain"],road_color):
                lines.append(polygon([project(v,y) for v,y in zip(p["points"],p["pointHeights"])],p["color"]))
            continue
        lines.append(
            polygon(
                [project(p) for p in ribbon(s["start"], s["end"], s["width"])],
                road_color,
            )
        )
    if 'streetPlan' in world:
        for p in street_mesh(world):
            color=STREET_COLORS[p['streetClass']]['overview']
            heights=p.get('pointHeights',[.08]*len(p['points']))
            lines.append(polygon([project(v,y) for v,y in zip(p['points'],heights)],color,
                                 'data-structural="street-mesh"'))
    for p in marking_surfaces(world):
        if p["streetClass"] != "ARTERIAL":
            continue
        lines.append(polygon([project(v,p.get("pointHeights",[p.get("elevation",.12)]*len(p["points"]))[i])
                              for i,v in enumerate(p["points"])],p["color"], 'data-structural="street-marking"'))
    faces = []
    open_river=world.get("terrain",{}).get("version") in ("terrain/0.4","terrain/0.5","terrain/0.6")
    if open_river:
        from .river_landscape import natural_faces
    for feature in (natural_faces(world) if open_river else world.get("terrain", {}).get("features", [])):
        for face in (lifted_faces(feature["faces"],world["terrain"]) if graded and not open_river else feature["faces"]):
            p = face["points"]
            faces.append((sum(v[0]+v[1]+v[2] for v in p)/len(p),
                          [project([x,z], y) for x,y,z in p], face["color"], None, 1,
                          'data-environmental="natural-terrain"'))
    for face in bridge_faces(world.get("terrain",{})):
        p = face["points"]
        faces.append((sum(x+y+z for x,y,z in p)/len(p),[project([x,z],y) for x,y,z in p],
                      face["color"],None,1,'data-structural="shared-bridge"'))
    if landscape:
        for tree in landscape["trees"]:
            for face in tree["faces"]:
                vertices = face["points"]
                depth = sum(x + z + y for x, y, z in vertices) / len(vertices)
                faces.append((depth, [project([x, z], y) for x, y, z in vertices],
                              face["color"], None, 1))
    for b in display_buildings:
        color = COLORS.get(b["archetype"], COLORS["GENERIC_BUILDING"])
        top = max(p["y"] + p["height"] for p in b["parts"])
        if graded:
            for face in foundation_faces(b,world["terrain"]):
                p=face["points"]
                faces.append((sum(x+y+z for x,y,z in p)/len(p),[project([x,z],y) for x,y,z in p],face["color"],b["entityId"],1))
        for part in b["parts"]:
            material = part_material(b, part, top) if building_style in ("architectural", "purposeful") else None
            poly = part["footprint"]
            low = part["y"] + 0.2+b.get("baseElevation",0)
            high = low + part["height"]
            faces.append(
                (
                    sum(sum(p) for p in poly) / 4 + high,
                    [project(p, high) for p in poly],
                    material["roof"] if material else color,
                    b["entityId"],
                    1,
                )
            )
            for a, c in zip(poly, poly[1:] + poly[:1]):
                if (c[1] - a[1]) - (c[0] - a[0]) <= 0:
                    continue
                vertices = [
                    project(a, low),
                    project(c, low),
                    project(c, high),
                    project(a, high),
                ]
                faces.append(
                    (
                        (sum(a) + sum(c)) / 2 + (high + low) / 2,
                        vertices,
                        material["wall"] if material else color,
                        b["entityId"],
                        0.7,
                    )
                )
    for face in sorted(faces, key=lambda f: f[0]):
        _, vertices, color, identity, shade = face[:5]
        if shade < 1:
            color = "#" + "".join(
                f"{int(int(color[i : i + 2], 16) * shade):02x}" for i in (1, 3, 5)
            )
        lines.append(
            polygon(
                vertices,
                color,
                face[5] if len(face) > 5 else (f'data-aggregate-id="{escape(identity)}" data-member-entity-ids="{escape(" ".join(compound_by_id[identity]["memberEntityIds"]))}" stroke="#10202a" stroke-width=".15"'
                 if identity in compound_by_id else f'data-entity-id="{escape(identity)}" stroke="#10202a" stroke-width=".15"'
                 if identity else 'data-decorative="tree"'),
            )
        )
    for d in world["districts"]:
        x, y = project(d["anchor"],field.height(d["anchor"]) if graded else 0)
        label = d["label"].rsplit("/", 1)[-1] or "."
        lines.append(
            f'<text x="{x:.3f}" y="{y:.3f}" fill="#e2edf5" stroke="#10202a" stroke-width="3" paint-order="stroke" font-family="sans-serif" font-size="13" text-anchor="middle">{escape(label)}</text>'
        )
    for site in world.get('campusPlan',{}).get('sites',[]):
        if 'sourceProgram' in site:
            x,y=project(site['courts'][0]['center'], .25)
            lines.append(f'<text x="{x:.3f}" y="{y:.3f}" fill="#d8eadb" stroke="#15221c" stroke-width="3" paint-order="stroke" font-family="sans-serif" font-size="11" text-anchor="middle">{escape(site["sourceProgram"]["label"])}</text>')
    lines += [
        f'<text x="28" y="{height - 36}" fill="#b7cbd8" font-family="sans-serif" font-size="12">Structural streets (visual) · Physical layout from world.json · Source facts from UCG</text>',
        f'<text x="28" y="{height - 17}" fill="#8da9b8" font-family="sans-serif" font-size="11">Flat capacity prototype · {len(world["routing"]["routes"])} source-backed trips · No runtime traffic measurement</text>',
        "</svg>",
    ]
    if landscape:
        lines[-2] = lines[-2].replace("Flat capacity prototype", "Flat landscaping (decorative)")
    if "terrain" in world:
        lines[-2] = lines[-2].replace("Flat landscaping (decorative)", "Terrain-first lakes and hills (procedural)").replace(
            "Flat capacity prototype", "Terrain-first lakes and hills (procedural)")
        if world["terrain"].get("crossings"):
            lines[-2] = lines[-2].replace("Terrain-first lakes and hills (procedural)",
                                         "Connected waterway and shared bridges (procedural)")
        if graded:
            lines[-2]=lines[-2].replace("Connected waterway and shared bridges (procedural)","Graded valley and level foundations (procedural)")
    if building_style in ("architectural", "purposeful"):
        lines[-3] = lines[-3].replace("Structural streets (visual)", "Procedural walls / role roof accents · Structural streets (visual)")
    return "\n".join(lines).encode("utf8")


def package_world(world, scene, graph, validation, *, landscaping=True, building_style="semantic", role_compounds=True):
    if building_style not in ("semantic", "architectural", "purposeful"):
        raise ValueError("unknown building presentation style")
    landscape = _landscape(world, None if landscaping else False)
    resources = files("metropogits.viewer_assets")
    artifacts = {
        f"assets/{name}": resources.joinpath(name).read_bytes()
        for name in (
            "viewer.css",
            "viewer-filters.js",
            "viewer-activity.js",
            "viewer-3d.js",
            "viewer.js",
        )
    }
    page = (
        resources.joinpath("index.html")
        .read_bytes()
        .replace(b"METROPOGITS / STATIC CITY", b"METROPOGITS / PROCEDURAL FLAT WORLD")
    )
    page = page.replace(
        b"Civic block (visual)", b"World district (structural)"
    ).replace(b"Route corridor (derived)", b"Structural street (visual)")
    if "zoning" in world or "softZoning" in world:
        page = page.replace(
            b"World district (structural)", b"Planning neighborhood (derived)"
        )
    page = page.replace(
        b'<span id="renderer-mode"',
        b'<button type="button" data-action="toggle-structure" aria-pressed="false">Structure overlay</button><span id="renderer-mode"',
    )
    if landscape:
        page = page.replace(
            b'<span><i class="line messaging"></i>Messaging path</span>',
            b'<span><i class="line messaging"></i>Messaging path</span>'
            b'<span title="Procedural flat greenery; not source architecture. Hidden by Structure overlay."><i class="swatch landscape"></i>Landscape (decorative)</span>',
        )
    if "terrain" in world:
        page = page.replace(b"PROCEDURAL FLAT WORLD", b"TERRAIN-FIRST WORLD")
        page = page.replace(b'<span id="renderer-mode"',
                            b'<span title="Procedural terrain constrains building and street placement; not source architecture.">Natural terrain (procedural)</span><span id="renderer-mode"')
    if "streetPlan" in world:
        page = page.replace(b'<span><i class="block street"></i>Structural street (visual)</span>',
                            b'<span title="Physical street hierarchy: arterial / collector / local / access. Structural functions, not source relations or runtime traffic."><i class="block street"></i>Street hierarchy (structural)</span>')
        page = page.replace(b'Dependency road &#183; width / paint = static demand',
                            b'Dependency demand (select / All routes)')
        page = page.replace('Dependency road · width / paint = static demand'.encode('utf8'),
                            b'Dependency demand (select / All routes)')
    if world.get('campusPlan',{}).get('sites'):
        page = page.replace(b'Landscape (decorative)',b'Landscape / campus courts (visual)')
    if building_style in ("architectural", "purposeful"):
        page = page.replace(b'<span id="renderer-mode"',
                            b'<button type="button" data-action="toggle-role-colors" aria-pressed="false" title="Restore full role tint; wall materials are procedural styling, not source facts">Role colours</button><span id="renderer-mode"')
        page = page.replace(b'<span><i class="swatch generic"></i>Generic</span>',
                            b'<span title="Walls are procedural tones; role colours appear on upper roofs. Filters or Role colours restore full tint.">Walls: procedural / Roof accents: roles</span><span><i class="swatch generic"></i>Generic</span>')
    svg = render_svg(world, landscape=landscape, building_style=building_style,
                     compounds=derive_compounds(world,graph)[0] if role_compounds else [], graph=graph)
    artifacts.update(
        {
            "index.html": page,
            "assets/viewer-data.js": _javascript_assignment(
                "METROPOGITS_DATA", view_data(world, scene, graph, landscape=landscape, building_style=building_style,role_compounds=role_compounds)
            ),
            "world.json": canonical_json_bytes(world),
            "city.json": canonical_json_bytes(scene),
            "graph.ucg.json": canonical_json_bytes(graph),
            "validation.json": canonical_json_bytes(validation),
            "preview.svg": svg,
            "showcase.svg": svg,
            "README_SNIPPET.md": b"[![Procedural source city](showcase.svg)](index.html)\n",
        }
    )
    if landscape:
        artifacts["landscape.json"] = canonical_json_bytes(landscape)
    if "zoning" in world or "softZoning" in world:
        artifacts["planning.json"] = canonical_json_bytes(planning_document(world))
    types = {
        ".html": "text/html",
        ".js": "text/javascript",
        ".css": "text/css",
        ".json": "application/json",
        ".svg": "image/svg+xml",
        ".md": "text/markdown",
    }
    diagnostic_summary = _diagnostic_summary(graph["diagnostics"])
    presentation = dict(buildingStyle=building_style, buildingMaterialsVersion=material_policy()["version"]) if building_style in ("architectural", "purposeful") else {}
    artifacts["manifest.json"] = canonical_json_bytes(
        dict(
            schemaVersion="manifest/0.1",
            generator=dict(
                name="metropogits",
                version=__version__,
                catalogVersion=graph["generator"]["catalogVersion"],
            ),
            repository=graph["repository"],
            status="PARTIAL"
            if diagnostic_summary["errorCount"] or diagnostic_summary["warningCount"]
            else "COMPLETE",
            diagnostics=diagnostic_summary,
            options=dict(
                experimental=True,
                worldVersion=world["schemaVersion"],
                worldSeed=world["seed"],
                sourceLayout=scene["layoutAlgorithm"],
                **presentation,
            ),
            privacyWarnings=[
                "Source paths and architecture may be sensitive; publication is not automatic."
            ],
            artifacts=[
                _artifact_record(p, types[Path(p).suffix], b)
                for p, b in sorted(artifacts.items())
            ],
        )
    )
    return artifacts
