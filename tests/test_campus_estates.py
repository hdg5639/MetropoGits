import copy
import json
import unittest
from pathlib import Path

from jsonschema import Draft202012Validator

from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.world.campus_estates import estate_layout, requirements
from metropogits.world.compounds import derive_compounds
from metropogits.world.export import package_world
from metropogits.world.generator import generate_world, _estate_fallback
from metropogits.world.geometry import inside, rectangle
from metropogits.world.validation import validate_world

OPTIONS = dict(
    seed="purpose-4",
    zoning="neighborhoods",
    pattern_scale="adaptive",
    planning="varied",
    outline="varied",
    street_policy="porous",
    street_hierarchy=True,
    campus=True,
    campus_style="estate",
)


class CampusEstateTests(unittest.TestCase):
    def test_optional_fit_failure_retains_a_working_city_but_never_hides_invalid_input(
        self,
    ):
        calls = []

        def implementation(scene, graph, **options):
            calls.append(options["campus_style"])
            if options["campus_style"] == "estate":
                raise ValueError("world infrastructure disconnected at actual/source")
            return dict(diagnostics=[])

        result = _estate_fallback(implementation)({}, {}, campus_style="estate")
        self.assertEqual(calls, ["estate", "programmed"])
        self.assertEqual(result["diagnostics"][0]["actualCampusStyle"], "programmed")

        def no_fit(scene, graph, **options):
            return dict(
                diagnostics=[],
                campusPlan=dict(
                    style=options["campus_style"],
                    sites=[],
                    decisions={"zone": dict(eligible=True, reason="NO_SPACE")},
                ),
            )

        result = _estate_fallback(no_fit)({}, {}, campus_style="estate")
        self.assertEqual(result["campusPlan"]["style"], "programmed")
        self.assertIn("no dedicated facility site", result["diagnostics"][0]["limitOrFailure"])
        # No request/default mode must not trigger a second planner invocation.
        self.assertEqual(
            _estate_fallback(no_fit)({}, {}, campus_style="programmed"),
            no_fit({}, {}, campus_style="programmed"),
        )

        def invalid(scene, graph, **options):
            raise ValueError("invalid world input: missing source evidence")

        with self.assertRaisesRegex(ValueError, "missing source evidence"):
            _estate_fallback(invalid)({}, {}, campus_style="estate")

    def test_requirements_precede_sites_and_never_group_unrelated_entities(self):
        zone = dict(id="zone", memberEntityIds=[str(i) for i in range(17)])
        pairs = {(str(i), str(i + 1)): 2 for i in range(14)}
        planned = requirements(zone, pairs)
        self.assertEqual(
            sorted(k for p in planned for k in p["memberEntityIds"]),
            sorted(zone["memberEntityIds"]),
        )
        self.assertTrue(all(len(p["memberEntityIds"]) <= 8 for p in planned))
        self.assertGreater(len({p["width"] * p["depth"] for p in planned}), 1)
        self.assertTrue(all(p["rows"] <= 2 or p["columns"] <= 2 for p in planned))
        neutral = requirements(zone, {})
        self.assertTrue(all(len(p["memberEntityIds"]) == 1 for p in neutral))
        extended = requirements(
            dict(zone, memberEntityIds=zone["memberEntityIds"] + ["unrelated"]), pairs
        )
        self.assertEqual(
            planned, [p for p in extended if p["memberEntityIds"] != ["unrelated"]]
        )

    def test_infeasible_campus_is_an_explicit_fallback_not_dropped_sources(self):
        zone = dict(
            id="narrow",
            parentId="p",
            memberEntityIds=[str(i) for i in range(20)],
            memberClaims=[],
        )
        stats = {}
        result = estate_layout(
            zone, rectangle([0, 0], 0, 12, 20), 0, "seed", [], None, {}, stats
        )
        self.assertIsNone(result)
        self.assertEqual(stats["estateFallback"], "DEDICATED_SITE_CAPACITY_OR_ACCESS")

    def test_real_source_pipeline_reserves_large_sites_and_preserves_inspectable_members(
        self,
    ):
        graph = analyze_repository(
            Path("tests/fixtures/repositories/purpose-campus"),
            repository_id="fixture/purpose-campus",
        )
        scene = generate_city(graph)
        saved = copy.deepcopy((scene, graph))
        world = generate_world(scene, graph, **OPTIONS)
        self.assertEqual(world, generate_world(scene, graph, **OPTIONS))
        self.assertEqual((scene, graph), saved)
        self.assertEqual(world["campusPlan"]["version"], "campus-plan/0.8")
        self.assertEqual(len(world["campusPlan"]["sites"]), 1)
        site = world["campusPlan"]["sites"][0]
        facilities = site["architecturalSites"]
        self.assertTrue(any(p["width"] * p["depth"] >= 256 for p in facilities))
        self.assertGreater(len({p["width"] * p["depth"] for p in facilities}), 1)
        parcels = {p["entityId"]: p for p in world["parcels"]}
        for facility in facilities:
            for key in facility["memberEntityIds"]:
                self.assertIn(parcels[key]["slotId"], facility["slotIds"])
                self.assertTrue(
                    all(
                        inside(v, facility["polygon"], -0.001)
                        for v in parcels[key]["parcel"]
                    )
                )
        validation = validate_world(world, scene, graph)
        self.assertEqual(validation["accessibleBuildings"], len(scene["buildings"]))
        complexes, _ = derive_compounds(world, graph, campus_landmarks=True)
        complexes = [c for c in complexes if c.get("campusProgram")]
        self.assertGreaterEqual(len(complexes), 3)
        self.assertGreaterEqual(sum(len(c["memberEntityIds"]) for c in complexes), 20)
        for c in complexes:
            self.assertTrue(
                any(
                    set(c["memberEntityIds"]).issubset(p["memberEntityIds"])
                    for p in facilities
                )
            )
            self.assertTrue(c["sourceEdgeIds"])
        package = package_world(
            world,
            scene,
            graph,
            validation,
            campus_landmarks=True,
            building_style="catalog",
        )
        self.assertEqual(
            package,
            package_world(
                world,
                scene,
                graph,
                validation,
                campus_landmarks=True,
                building_style="catalog",
            ),
        )
        for name, payload in (
            ("world", world),
            ("planning", json.loads(package["planning.json"])),
        ):
            schema = json.loads(
                Path(
                    "schemas/"
                    + (
                        "world-0.1.schema.json"
                        if name == "world"
                        else "planning-0.5.schema.json"
                    )
                ).read_text(encoding="utf8")
            )
            Draft202012Validator(schema).validate(payload)
        forged = copy.deepcopy(world)
        forged["campusPlan"]["sites"][0]["architecturalSites"][0]["width"] += 8
        with self.assertRaises(ValueError):
            validate_world(forged, scene, graph)


if __name__ == "__main__":
    unittest.main()
