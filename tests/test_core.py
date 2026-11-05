import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scene_forge.schema import SceneError, apply_revision, demo_scene, validate_scene
from scene_forge.planner import local_endpoint, plan
from scene_forge.jobs import changes, execute_job, new_job


class SchemaTests(unittest.TestCase):
    def test_demo_valid_and_copy_isolated(self):
        scene = demo_scene()
        result = validate_scene(scene)
        result["actors"][0]["start"][0] = 10
        self.assertEqual(scene["actors"][0]["start"][0], -3)

    def test_unsafe_or_unknown_fields_rejected(self):
        for field, value in (("script", "import os"), ("duration_seconds", 999),
                             ("duration_seconds", float("nan")), ("fps", True)):
            with self.subTest(field=field, value=value):
                scene = demo_scene()
                scene[field] = value
                with self.assertRaises(SceneError):
                    validate_scene(scene)

    def test_duplicates_and_path_ids_rejected(self):
        for identifier in ("explorer", "../something", "a\n"):
            scene = demo_scene()
            scene["props"][0]["id"] = identifier
            with self.assertRaises(SceneError):
                validate_scene(scene)

    def test_impossible_motion_rejected(self):
        scene = demo_scene()
        scene["actors"][0]["start"][2] = 3
        with self.assertRaises(SceneError):
            validate_scene(scene)
        scene = demo_scene()
        scene["actors"][0]["action"] = "idle"
        with self.assertRaises(SceneError):
            validate_scene(scene)

    def test_remote_endpoint_rejected(self):
        for url in ("https://example.com", "http://127.0.0.1.example.com", "http://user@localhost:11434", "http://localhost:11434/path"):
            with self.assertRaises(SceneError):
                local_endpoint(url)

    def test_revision_preserves_untouched_properties(self):
        previous = demo_scene()
        revised = apply_revision(previous, {"lighting": "moonlight", "actors": [{"id": "explorer", "color": "#3366ff"}]})
        expected = copy.deepcopy(previous)
        expected["lighting"] = "moonlight"
        expected["actors"][0]["color"] = "#3366ff"
        self.assertEqual(revised, expected)
        self.assertEqual(previous, demo_scene())

    def test_revision_deletes_only_named_entity(self):
        scene = demo_scene()
        revised = apply_revision(scene, {"remove_ids": ["stone"]})
        self.assertEqual(len(revised["props"]), len(scene["props"]) - 1)
        with self.assertRaises(SceneError):
            apply_revision(scene, {"remove_ids": ["unknown"]})

    def test_revision_rejects_incomplete_new_objects(self):
        with self.assertRaises(SceneError):
            apply_revision(demo_scene(), {"props": [{"id": "new_object", "color": "#123456"}]})


class PlannerTests(unittest.TestCase):
    @patch("scene_forge.planner.models", return_value=["test"])
    @patch("scene_forge.planner.request_json")
    def test_validation_failure_gets_one_repair(self, request, _):
        request.side_effect = [{"message": {"content": '{"script": "bad"}'}},
                               {"message": {"content": json.dumps(dict(demo_scene(), unsupported_requests=[]))}}]
        scene, metadata = plan("Make an explorer", model="test")
        self.assertEqual(metadata["attempts"], 2)
        self.assertEqual(scene["title"], "The Amber Discovery")
        self.assertIn("validation error", request.call_args.args[2]["messages"][-1]["content"])

    @patch("scene_forge.planner.models", return_value=["test"])
    @patch("scene_forge.planner.request_json", return_value={"message": {"content": "bad"}})
    def test_invalid_model_output_never_falls_back_to_demo(self, request, _):
        with self.assertRaises(SceneError):
            plan("Make something", model="test")
        self.assertEqual(request.call_count, 2)


class JobTests(unittest.TestCase):
    def test_revision_diff_reports_only_changes(self):
        previous = demo_scene()
        revised = copy.deepcopy(previous)
        revised["lighting"] = "moonlight"
        self.assertEqual(changes(previous, revised), [
            {"path": "scene.lighting", "before": "golden_hour", "after": "moonlight"}])

    def test_jobs_are_unique(self):
        with tempfile.TemporaryDirectory() as root:
            self.assertNotEqual(new_job(root), new_job(root))

    def test_existing_folder_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(FileExistsError):
                execute_job(job_dir=root, provider="demo")

    @patch("scene_forge.jobs.discover_blender", side_effect=SceneError("missing Blender"))
    def test_failure_persists_actionable_status(self, _):
        with tempfile.TemporaryDirectory() as root:
            with self.assertRaises(SceneError):
                execute_job(root, provider="demo")
            status = json.loads(next(Path(root).glob("*/status.json")).read_text())
            self.assertEqual(status["state"], "failed")
            self.assertIn("missing Blender", status["message"])


if __name__ == "__main__":
    unittest.main()
