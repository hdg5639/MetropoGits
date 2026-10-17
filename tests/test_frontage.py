import copy
import unittest

from metropogits.frontage import Affinity, arrange_equal_shapes, assign_frontage, derive_affinity
from metropogits.layout import BUILDING_AXIS, DISTRICT_DEPTH, generate_city
from metropogits.scanner import ScanResult, ScannedFile, build_structural_ucg
from metropogits.streets import derive_street_grid, street_surfaces
from scripts.canonical_json import canonical_json_bytes
from scripts.stable_ids import make_edge_id
from scripts.validate_city import validate_document


def fixture(count=64):
    graph = build_structural_ucg(ScanResult(files=tuple(
        ScannedFile(path=f"src/File{i:03}.java", language="java", size_bytes=1)
        for i in range(count)), diagnostics=()), "fixture/frontage")
    files = [e for e in graph["entities"] if e["kind"] == "FILE"]
    graph["evidence"].append(dict(evidenceId="role-proof", sourcePath=files[0]["path"],
                                  extractor="fixture", kind="ANNOTATION", summary="fixture role"))
    files[0]["roles"] = [dict(value="ENTRYPOINT", confidence="DIRECT", evidenceIds=["role-proof"])]
    files[1]["roles"] = [dict(value="PERSISTENCE_ADAPTER", confidence="DIRECT", evidenceIds=["role-proof"])]
    return graph, files


class FrontageTests(unittest.TestCase):
    def test_relation_tiebreak_never_sacrifices_local_compactness(self):
        offsets = {"a": (0, 0), "b": (100, 0), "c": (7, 0), "different": (0, 7)}
        shapes = {key: {(0, 0)} for key in offsets}
        shapes["different"] = {(0, 0), (1, 0)}
        sizes = {key: (7, 7) for key in offsets}
        sizes["different"] = (14, 7)
        affinity = Affinity(neighbors={"a": {"b": 3}, "b": {"a": 3}})
        placed = arrange_equal_shapes(offsets, shapes, sizes, ["b", "c", "different"], affinity)
        self.assertEqual((7, 0), placed["b"])
        self.assertEqual(offsets["a"], placed["a"])
        self.assertEqual(offsets["different"], placed["different"])
        self.assertEqual(set(offsets.values()), set(placed.values()))
        self.assertEqual(offsets, arrange_equal_shapes(offsets, shapes, sizes, [], affinity))

    def test_external_references_bias_frontage_but_local_references_do_not(self):
        graph, files = fixture(4)
        for item in files:
            item["roles"] = []
        owners = {item["id"]: "service" for item in files}
        graph["edges"].append(dict(id="ref", type="REFERENCES", confidence="RESOLVED",
                                  evidenceIds=["role-proof"],
                                  **{"from": files[0]["id"], "to": files[1]["id"]}))
        local = derive_affinity(graph, owners, {"service": "root"})
        self.assertEqual(0, local.exposure[files[1]["id"]])
        owners[files[0]["id"]] = "api"
        external = derive_affinity(graph, owners, {"service": "root", "api": "root"})
        self.assertEqual(0.75, external.exposure[files[1]["id"]])
        self.assertGreater(external.neighbors["service"]["api"], 0)

    def test_surface_layers_stay_inside_street_reservation(self):
        for width, depth in ((7, 7), (7, 70), (70, 7), (14, 42)):
            rectangle = dict(x=-14, z=21, width=width, depth=depth)
            parts = street_surfaces(rectangle)
            self.assertGreaterEqual(len(parts), 2)
            self.assertEqual("#253141", parts[1]["color"])
            for part in parts:
                self.assertGreater(part["width"], 0)
                self.assertGreater(part["depth"], 0)
                self.assertGreaterEqual(part["x"], rectangle["x"])
                self.assertGreaterEqual(part["z"], rectangle["z"])
                self.assertLessEqual(part["x"] + part["width"], rectangle["x"] + width)
                self.assertLessEqual(part["z"] + part["depth"], rectangle["z"] + depth)

    def test_frontage_and_interior_are_different_when_sites_allow_it(self):
        slots = {f"f{i}": row * 8 + column for i, (row, column) in enumerate(
            (r, c) for r in range(3) for c in range(3))}
        affinity = Affinity(exposure={"f0": 3, "f1": -2})
        placed = assign_frontage(slots, affinity, {}, list(BUILDING_AXIS), DISTRICT_DEPTH)
        self.assertEqual(9, placed["f1"])
        self.assertIn(placed["f0"], [0, 1, 2, 8, 10, 16, 17, 18])
        self.assertEqual(set(slots.values()), set(placed.values()))

    def test_relation_attraction_and_locked_sites(self):
        sites = {"a": 0, "b": 7, "c": 63, "d": 56}
        affinity = Affinity(neighbors={"b": {"a": 3}})
        placed = assign_frontage(sites, affinity, {"a": 0}, list(BUILDING_AXIS), DISTRICT_DEPTH)
        self.assertEqual(7, placed["b"])
        self.assertEqual(0, placed["a"])
        self.assertEqual(sites, assign_frontage(sites, Affinity(), {}, list(BUILDING_AXIS), DISTRICT_DEPTH))

    def test_names_unknown_edges_and_missing_evidence_do_not_create_frontage(self):
        graph, files = fixture(4)
        owners = {f["id"]: "src" for f in files}
        files[0]["roles"][0]["confidence"] = "INFERRED"
        files[1]["roles"][0]["evidenceIds"] = []
        files[2]["path"] = "ControllerServiceDAO.java"
        graph["edges"].append(dict(id="unknown", type="REFERENCES", confidence="UNKNOWN",
                                   evidenceIds=["role-proof"], **{"from": files[0]["id"], "to": files[2]["id"]}))
        affinity = derive_affinity(graph, owners, {})
        self.assertFalse(any(affinity.exposure.values()))
        self.assertFalse(affinity.neighbors)

    def test_duplicate_observations_do_not_strengthen_a_pair(self):
        graph, files = fixture(4)
        owners = {f["id"]: "src" for f in files}
        edge = dict(id="ref", type="REFERENCES", confidence="DIRECT", evidenceIds=["role-proof"],
                    **{"from": files[0]["id"], "to": files[1]["id"]})
        graph["edges"].append(edge)
        first = derive_affinity(graph, owners, {})
        graph["edges"].append({**edge, "id": "duplicate"})
        self.assertEqual(first, derive_affinity(graph, owners, {}))
        for source in files[2:]:
            graph["edges"].append({**edge, "from": source["id"]})
        popular = derive_affinity(graph, owners, {})
        self.assertLess(popular.neighbors[files[0]["id"]][files[1]["id"]],
                        first.neighbors[files[0]["id"]][files[1]["id"]])

    def test_real_scene_has_internal_streets_without_invented_networks(self):
        graph, _ = fixture()
        original = copy.deepcopy(graph)
        scene = generate_city(graph)
        self.assertEqual([], validate_document(scene, graph))
        self.assertEqual([], scene["networks"])
        self.assertEqual(original, graph)
        streets = derive_street_grid(scene)
        self.assertFalse(streets["semantic"])
        self.assertGreater(len(streets["rectangles"]), 0)
        for road in streets["rectangles"]:
            for building in scene["buildings"]:
                self.assertFalse(road["x"] < building["x"] + building["width"]
                                 and road["x"] + road["width"] > building["x"]
                                 and road["z"] < building["z"] + building["depth"]
                                 and road["z"] + road["depth"] > building["z"])
        self.assertEqual(canonical_json_bytes(scene), canonical_json_bytes(generate_city(graph)))
        shuffled = copy.deepcopy(graph)
        shuffled["entities"].reverse()
        shuffled["edges"].reverse()
        owners = {e["id"]: "src" for e in graph["entities"] if e["kind"] == "FILE"}
        self.assertEqual(derive_affinity(graph, owners, {}), derive_affinity(shuffled, owners, {}))

    def test_new_reference_does_not_relocate_compatible_hinted_buildings(self):
        graph, files = fixture()
        baseline = generate_city(graph)
        source, target = files[0]["id"], files[-1]["id"]
        graph["edges"].append(dict(id=make_edge_id(source, "REFERENCES", target),
                                  type="REFERENCES", confidence="DIRECT", evidenceIds=["role-proof"],
                                  **{"from": source, "to": target}))
        graph["edges"].sort(key=lambda edge: edge["id"])
        changed = generate_city(graph, previous_scene=baseline)
        self.assertEqual(baseline["buildings"], changed["buildings"])
        self.assertEqual(baseline["districts"], changed["districts"])
