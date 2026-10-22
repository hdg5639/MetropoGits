import copy
import unittest
from pathlib import Path

from metropogits.cli import analyze_repository
from metropogits.world.urban_character import CharacterEngine, character_document
from test_reference_skyline import fixture


class UrbanCharacterTests(unittest.TestCase):
    def test_unique_local_pairs_components_and_evidence_are_reconstructable(self):
        w, g, ids = fixture()
        g["repository"] = dict(id="fixture")
        saved = copy.deepcopy((w, g))
        doc = character_document(w, g)
        f = doc["profiles"][0]["facts"]
        self.assertEqual(f["localDirectedPairs"], 9)
        self.assertEqual(f["weakComponentSizes"], [10])
        self.assertEqual(f["incomingCentralization"], 1)
        self.assertEqual(f["roleCounts"], {})
        self.assertEqual(doc["profiles"][0]["planning"]["preferredTypology"], "CONVENTIONAL_MIXED_USE")
        # A star of imports is NOT a business center or headquarters.
        self.assertLess(doc["profiles"][0]["planning"]["verticalPotential"], 0.2)
        self.assertEqual((w, g), saved)
        duplicate = copy.deepcopy(g)
        duplicate["edges"] += copy.deepcopy(g["edges"])
        self.assertEqual(CharacterEngine(g).profile("x", ids),
                         CharacterEngine(duplicate).profile("x", reversed(ids)))
        p = CharacterEngine(g).profile("part", ids[:4], kind="zone")
        self.assertEqual(p["facts"]["localDirectedPairs"], 3)
        self.assertEqual(p["facts"]["boundaryDirectedPairs"], 6)
        self.assertEqual(p["facts"]["relationEdgeIds"], sorted(e["id"] for e in g["edges"]))

    def test_unknown_manifest_inferred_and_missing_proofs_do_not_create_usage(self):
        w, g, ids = fixture()
        for confidence, proof in (("INFERRED", ["ev:1"]), ("UNKNOWN", ["ev:1"]), ("DIRECT", ["absent"])):
            bad = copy.deepcopy(g)
            for e in bad["edges"]:
                e.update(confidence=confidence, evidenceIds=proof)
            p = CharacterEngine(bad).profile("x", ids)
            self.assertEqual(p["facts"]["localDirectedPairs"], 0)
            self.assertEqual(p["facts"]["weakComponentSizes"], [1] * 10)
        g["entities"][0]["roles"] = [dict(value="SERVICE", confidence="DIRECT", evidenceIds=["absent"])]
        self.assertEqual(CharacterEngine(g).profile("x", ids)["facts"]["roleCounts"], {})
        with self.assertRaises(ValueError):
            CharacterEngine(g).profile("x", [ids[0], ids[0]])
        with self.assertRaises(ValueError):
            CharacterEngine(g).profile("x", ["absent"])

    def test_real_program_and_unknown_scopes_are_repeatable_without_geometry(self):
        for name in ("purpose-campus", "architecture-unknown"):
            graph = analyze_repository(Path("tests/fixtures/repositories") / name,
                                       repository_id="fixture/" + name)
            engine = CharacterEngine(graph)
            saved = copy.deepcopy(graph)
            p = engine.profile("repo", engine.files)
            self.assertEqual(p, engine.profile("repo", reversed(list(engine.files))))
            self.assertEqual(saved, graph)
            if name == "purpose-campus":
                self.assertGreater(p["facts"]["classifiedSourceCount"], 0)
                self.assertGreater(p["planning"]["campusPotential"], 0)
                self.assertGreater(p["spatialDemand"]["perSourceUnits"], 1)
                self.assertTrue(p["facts"]["semanticEvidenceIds"])
            else:
                self.assertEqual(p["facts"]["sourceCount"], 3)
                self.assertEqual(p["facts"]["roleCounts"], {})
                self.assertEqual(p["facts"]["localDirectedPairs"], 0)
                self.assertEqual(p["planning"]["preferredTypology"], "CONVENTIONAL_MIXED_USE")
            self.assertEqual(p["spatialDemand"]["status"], "RELATIVE_UNALLOCATED")

    def test_order_external_declarations_and_symbols_are_not_counted_as_local_files(self):
        _, g, ids = fixture()
        g["entities"] += [dict(id="symbol", kind="SYMBOL", path="src/1.py"),
                          dict(id="pkg", kind="EXTERNAL_PACKAGE")]
        g["edges"] += [dict(id="external", type="IMPORTS", confidence="DIRECT",
                            **{"from": "symbol", "to": "pkg", "evidenceIds": ["ev:1"]}),
                       dict(id="declared", type="DEPENDS_ON", confidence="DIRECT",
                            **{"from": ids[0], "to": "pkg", "evidenceIds": ["ev:1"]})]
        p = CharacterEngine(g).profile("x", ids)
        self.assertEqual(p["facts"]["externalUsagePairs"], 1)
        self.assertEqual(p["facts"]["declaredExternalPairs"], 1)
        for field in ("entities", "edges", "evidence"):
            g[field].reverse()
        self.assertEqual(p, CharacterEngine(g).profile("x", ids))


if __name__ == "__main__":
    unittest.main()
