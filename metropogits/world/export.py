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
from .geometry import bounds, centroid, point, ribbon
from .seed import derive
from .zoning import planning_document

GROUND = ["#33464b", "#4a4149", "#354b42", "#504835", "#3e4454", "#4e3c42", "#3b4c50"]
ZONE_COLORS = {
    "GENERAL_MIXED": "#414b50",
    "SERVICE_QUARTER": "#3c5260",
    "INDUSTRIAL_LOGISTICS": "#3c574d",
    "CAMPUS_RESEARCH": "#5b5540",
    "GATEWAY_CIVIC": "#5d4555",
    "COMMERCIAL_FRONTEND": "#474b60",
}
COLORS = dict(
    GENERIC_BUILDING="#a2adbb",
    SERVICE_OFFICE="#60a5fa",
    GATE="#f472b6",
    STRUCTURED_WAREHOUSE="#34d399",
    DOCUMENT_DEPOT="#6ee7b7",
    CACHE_TOWER="#fbbf24",
    LIBRARY="#facc15",
    CONTROL_CENTER="#a78bfa",
    PORT="#38bdf8",
    EXCHANGE="#fb923c",
)


def view_data(world, scene, graph):
    root = "visual:world-root:" + derive(world["repositoryNamespace"])

    def envelope(poly):
        x, z, right, bottom = bounds(poly)
        return dict(x=x, z=z, width=right - x, depth=bottom - z)

    districts = [dict(id=root, parentId=None, **envelope(world["envelope"]))]
    territories = []
    neighborhoods = world.get("zoning", world.get("softZoning", {})).get("zones", [])
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
                label=z["label"],
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
    surfaces = [
        dict(
            s,
            points=list(reversed(ribbon(s["start"], s["end"], s["width"]))),
            color="#3e4a54",
        )
        for s in world["streets"]
    ]
    incidence = {}
    for s in world["streets"]:
        for p in (s["start"], s["end"]):
            incidence.setdefault(tuple(p), []).append(s)
    for p, streets in incidence.items():
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
            dict(points=[b, b, a, list(p)], color="#3e4a54")
            for a, b in zip(ring, ring[1:] + ring[:1])
        )
    pavement = dict(
        version="world-pavement/0.1",
        segments={
            s["id"]: [
                dict(
                    points=list(reversed(ribbon(s["start"], s["end"], s["width"]))),
                    width=s["width"],
                )
            ]
            for s in routing["segments"]
        },
    )
    data = dict(
        scene=physical_scene,
        canonicalScene=scene,
        ucg=graph,
        routing=routing,
        roadHierarchy=hierarchy,
        world=dict(
            schemaVersion=world["schemaVersion"],
            seed=world["seed"],
            terrainPreset="flat",
        ),
        majorDistrictIds=[d["id"] for d in world["districts"]],
        streets=dict(
            structural=True,
            surfaces=surfaces,
            orientedEntityIds=sorted(models),
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
    if neighborhoods:
        data["semanticZoning"] = {z["id"]: z for z in neighborhoods}
        if "softZoning" in world:
            data["softZoning"] = dict(
                version=world["softZoning"]["version"], influenceOnly=True
            )
        else:
            data["occupiedGround"]["pads"] = [
                dict(
                    districtId=z["id"],
                    polygons=[list(reversed(z["polygon"]))],
                    color=ZONE_COLORS[z["clusterKey"]],
                )
                for z in neighborhoods
            ]
    return data


def render_svg(world, width=1200, height=750):
    def iso(p, y=0):
        return [(p[0] - p[1]) * 0.866, (p[0] + p[1]) * 0.5 - y]

    points = [iso(p) for p in world["envelope"]]
    points += [
        iso(p, part["y"] + part["height"])
        for b in world["parcels"]
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
    for i, d in enumerate(world["districts"]):
        lines.append(
            polygon(
                [project(p) for p in d["polygon"]],
                GROUND[i % len(GROUND)],
                f'data-directory-id="{escape(d["id"])}" stroke="#62727c" stroke-width=".6"',
            )
        )
    for z in world.get("zoning", {}).get("zones", []):
        lines.append(
            polygon(
                [project(p) for p in z["polygon"]],
                ZONE_COLORS[z["clusterKey"]],
                f'data-zone-id="{escape(z["id"])}"',
            )
        )
    for s in world["streets"]:
        lines.append(
            polygon(
                [project(p) for p in ribbon(s["start"], s["end"], s["width"])],
                "#26333e",
            )
        )
    faces = []
    for b in world["parcels"]:
        color = COLORS.get(b["archetype"], COLORS["GENERIC_BUILDING"])
        for part in b["parts"]:
            poly = part["footprint"]
            low = part["y"] + 0.2
            high = low + part["height"]
            faces.append(
                (
                    sum(sum(p) for p in poly) / 4 + high,
                    [project(p, high) for p in poly],
                    color,
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
                        color,
                        b["entityId"],
                        0.7,
                    )
                )
    for _, vertices, color, identity, shade in sorted(faces, key=lambda f: f[0]):
        if shade < 1:
            color = "#" + "".join(
                f"{int(int(color[i : i + 2], 16) * shade):02x}" for i in (1, 3, 5)
            )
        lines.append(
            polygon(
                vertices,
                color,
                f'data-entity-id="{escape(identity)}" stroke="#10202a" stroke-width=".15"',
            )
        )
    for d in world["districts"]:
        x, y = project(d["anchor"])
        label = d["label"].rsplit("/", 1)[-1] or "."
        lines.append(
            f'<text x="{x:.3f}" y="{y:.3f}" fill="#e2edf5" stroke="#10202a" stroke-width="3" paint-order="stroke" font-family="sans-serif" font-size="13" text-anchor="middle">{escape(label)}</text>'
        )
    lines += [
        f'<text x="28" y="{height - 36}" fill="#b7cbd8" font-family="sans-serif" font-size="12">Structural streets (visual) · Physical layout from world.json · Source facts from UCG</text>',
        f'<text x="28" y="{height - 17}" fill="#8da9b8" font-family="sans-serif" font-size="11">Flat capacity prototype · {len(world["routing"]["routes"])} source-backed trips · No runtime traffic measurement</text>',
        "</svg>",
    ]
    return "\n".join(lines).encode("utf8")


def package_world(world, scene, graph, validation):
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
    svg = render_svg(world)
    artifacts.update(
        {
            "index.html": page,
            "assets/viewer-data.js": _javascript_assignment(
                "METROPOGITS_DATA", view_data(world, scene, graph)
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
