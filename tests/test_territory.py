import unittest

from metropogits.territory import derive_district_territories


class DistrictTerritoryTests(unittest.TestCase):
    def test_sparse_building_groups_form_connected_concave_territory(self):
        scene = {
            "districts": [
                {
                    "depth": 70,
                    "id": "root",
                    "parentId": None,
                    "width": 84,
                    "x": 0,
                    "z": 0,
                }
            ],
            "buildings": [
                {
                    "depth": 6,
                    "districtId": "root",
                    "entityId": "left",
                    "height": 10,
                    "width": 6,
                    "x": 3,
                    "z": 3,
                },
                {
                    "depth": 6,
                    "districtId": "root",
                    "entityId": "right",
                    "height": 10,
                    "width": 6,
                    "x": 73,
                    "z": 59,
                },
            ],
        }

        first = derive_district_territories(scene)
        second = derive_district_territories(scene)
        territory = first["districts"][0]

        self.assertEqual(first, second)
        self.assertGreater(len(territory["rectangles"]), 1)
        self.assertGreater(len(territory["boundary"]), 4)
        territory_area = sum(
            rectangle["width"] * rectangle["depth"]
            for rectangle in territory["rectangles"]
        )
        self.assertLess(territory_area, 84 * 70 * 0.7)
        self.assertGreaterEqual(territory["landmarkPlot"]["width"], 28)
        self.assertGreaterEqual(territory["landmarkPlot"]["depth"], 28)
        for building in scene["buildings"]:
            self.assertTrue(
                any(
                    rectangle["x"] < building["x"] + building["width"]
                    and building["x"] < rectangle["x"] + rectangle["width"]
                    and rectangle["z"] < building["z"] + building["depth"]
                    and building["z"] < rectangle["z"] + rectangle["depth"]
                    for rectangle in territory["rectangles"]
                )
            )

    def test_parent_territory_covers_descendant_buildings(self):
        scene = {
            "districts": [
                {
                    "depth": 56,
                    "id": "root",
                    "parentId": None,
                    "width": 70,
                    "x": 0,
                    "z": 0,
                },
                {
                    "depth": 28,
                    "id": "child",
                    "parentId": "root",
                    "width": 28,
                    "x": 38,
                    "z": 24,
                },
            ],
            "buildings": [
                {
                    "depth": 6,
                    "districtId": "child",
                    "entityId": "nested",
                    "height": 10,
                    "width": 6,
                    "x": 41,
                    "z": 27,
                }
            ],
        }

        territories = {
            item["id"]: item
            for item in derive_district_territories(scene)["districts"]
        }
        building = scene["buildings"][0]
        for district_id in ("root", "child"):
            territory = territories[district_id]
            self.assertTrue(
                any(
                    rectangle["x"] < building["x"] + building["width"]
                    and building["x"] < rectangle["x"] + rectangle["width"]
                    and rectangle["z"] < building["z"] + building["depth"]
                    and building["z"] < rectangle["z"] + rectangle["depth"]
                    for rectangle in territory["rectangles"]
                )
            )
            for rectangle in territory["rectangles"]:
                district = next(
                    item for item in scene["districts"] if item["id"] == district_id
                )
                self.assertGreaterEqual(rectangle["x"], district["x"])
                self.assertGreaterEqual(rectangle["z"], district["z"])
                self.assertLessEqual(
                    rectangle["x"] + rectangle["width"],
                    district["x"] + district["width"],
                )
                self.assertLessEqual(
                    rectangle["z"] + rectangle["depth"],
                    district["z"] + district["depth"],
                )

    def test_empty_district_falls_back_to_canonical_bounds(self):
        scene = {
            "buildings": [],
            "districts": [
                {
                    "depth": 8,
                    "id": "empty",
                    "parentId": None,
                    "width": 8,
                    "x": 10,
                    "z": 20,
                }
            ],
        }

        territory = derive_district_territories(scene)["districts"][0]

        self.assertEqual(
            [{"depth": 8.0, "width": 8.0, "x": 10.0, "z": 20.0}],
            territory["rectangles"],
        )
        self.assertEqual(4, len(territory["boundary"]))


if __name__ == "__main__":
    unittest.main()
