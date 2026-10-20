import unittest
from pathlib import Path

from metropogits.cli import analyze_repository
from metropogits.layout import generate_city
from metropogits.preview import render_preview
from scripts.canonical_json import canonical_json_bytes
from scripts.validate_ucg import validate_document


FIXTURES = Path(__file__).parent / "fixtures" / "repositories"


def files_by_path(graph: dict) -> dict[str, dict]:
    return {
        entity["path"]: entity
        for entity in graph["entities"]
        if entity["kind"] == "FILE"
    }


def claim_values(entity: dict, field: str) -> set[str]:
    return {claim["value"] for claim in entity.get(field, [])}


class PathSemanticsTests(unittest.TestCase):
    def test_exact_paths_create_evidenced_landmarks_and_test_facilities(self):
        graph = analyze_repository(
            FIXTURES / "path-semantics-positive",
            repository_id="fixture/path-positive",
        )
        files = files_by_path(graph)
        page = files["Frontend/portal/app/dashboard/page.tsx"]
        route = files["Frontend/portal/app/api/health/route.ts"]
        jsts_test = files["Frontend/portal/src/__tests__/widget.test.tsx"]
        java_test = files["Backend/src/test/java/example/UserServiceTest.java"]

        self.assertEqual({"UI_PAGE", "UI_COMPONENT"}, claim_values(page, "roles"))
        self.assertEqual({"UI"}, claim_values(page, "capabilities"))
        self.assertEqual({"NEXT_JS", "JSX"}, claim_values(page, "technologies"))
        self.assertEqual({"API_ENDPOINT"}, claim_values(route, "roles"))
        self.assertEqual({"API"}, claim_values(route, "capabilities"))
        self.assertEqual({"NEXT_JS"}, claim_values(route, "technologies"))
        for entity in (jsts_test, java_test):
            extra = {'UI_COMPONENT'} if entity is jsts_test else set()
            self.assertEqual({'TEST'} | extra, claim_values(entity, 'roles'))
            self.assertEqual({'TEST', 'UI'} if extra else {'TEST'}, claim_values(entity, 'capabilities'))

        evidence = {item["evidenceId"]: item for item in graph["evidence"]}
        path_evidence_ids = {
            evidence_id
            for entity in (page, route, jsts_test, java_test)
            for field in ("roles", "capabilities", "technologies")
            for claim in entity.get(field, [])
            for evidence_id in claim["evidenceIds"]
            if evidence[evidence_id]["kind"] == "PATH"
        }
        self.assertEqual(
            {
                "path.nextjs.app-page",
                "path.nextjs.route-handler",
                "path.test-source",
            },
            {evidence[evidence_id]["ruleId"] for evidence_id in path_evidence_ids},
        )
        self.assertTrue(
            all(
                evidence[evidence_id]["kind"] == "PATH"
                for evidence_id in path_evidence_ids
            )
        )
        self.assertEqual([], validate_document(graph))

        scene = generate_city(graph)
        archetypes = {
            building["entityId"]: building["archetype"]
            for building in scene["buildings"]
        }
        self.assertEqual("GATE", archetypes[page["id"]])
        self.assertEqual("API_HUB", archetypes[route["id"]])
        self.assertEqual("LIBRARY", archetypes[jsts_test["id"]])
        self.assertEqual("LIBRARY", archetypes[java_test["id"]])
        preview = render_preview(scene, graph).decode("utf-8")
        self.assertEqual(2, preview.count('data-roof-form="LIBRARY"'))

    def test_near_match_paths_remain_unclassified(self):
        graph = analyze_repository(
            FIXTURES / "path-semantics-negative",
            repository_id="fixture/path-negative",
        )

        for entity in files_by_path(graph).values():
            # Real JSX is UI syntax even outside a framework route directory.
            roles = claim_values(entity, "roles")
            self.assertTrue(roles <= {"UI_COMPONENT"})
            self.assertTrue(claim_values(entity, "capabilities") <= {"UI"})
            self.assertTrue(claim_values(entity, "technologies") <= {"JSX"})
        self.assertFalse(any(item["kind"] == "PATH" for item in graph["evidence"]))

    def test_path_semantics_are_deterministic(self):
        root = FIXTURES / "path-semantics-positive"

        first = analyze_repository(root, repository_id="fixture/path-determinism")
        second = analyze_repository(root, repository_id="fixture/path-determinism")

        self.assertEqual(canonical_json_bytes(first), canonical_json_bytes(second))


if __name__ == "__main__":
    unittest.main()
