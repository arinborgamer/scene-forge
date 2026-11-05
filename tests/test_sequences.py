import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scene_forge.capabilities import preflight, check_plan_coverage, UnsupportedRequest
from scene_forge.jobs import execute_job
from scene_forge.planner import plan
from scene_forge.schema import SceneError, demo_scene, validate_scene, apply_revision
from scene_forge.sequences import frame_windows


def sequence_scene():
    scene = demo_scene()
    scene.update(schema_version=2, duration_seconds=5, camera='static', props=[], unsupported_requests=[])
    scene['actors'][0].update(start=[-2, 0, 0], end=[0, 0, 0], action='sequence', sequence=[
        {'action': 'walk', 'duration_seconds': 2.5, 'target': [0, 0, 0]},
        {'action': 'hold', 'duration_seconds': 1},
        {'action': 'look_at_camera', 'duration_seconds': 1.5},
    ])
    return scene


class SequenceTests(unittest.TestCase):
    def test_valid_sequence_and_legacy(self):
        self.assertEqual(validate_scene(sequence_scene())['schema_version'], 2)
        self.assertEqual(validate_scene(demo_scene())['schema_version'], 1)

    def test_invalid_timelines_rejected(self):
        mutations = [
            lambda s: s.update(schema_version=1),
            lambda s: s['actors'][0]['sequence'][0].update(duration_seconds=1),
            lambda s: s['actors'][0]['sequence'][0].update(target=[6, 0, 0]),
            lambda s: s['actors'][0]['sequence'][0].update(target=[0, 0, 1]),
            lambda s: s['actors'][0]['sequence'][1].update(target=[0, 0, 0]),
            lambda s: s['actors'][0].update(end=[1, 0, 0]),
            lambda s: s['actors'][0].update(action='idle'),
            lambda s: s.update(style='organic'),
        ]
        for mutation in mutations:
            scene = sequence_scene()
            mutation(scene)
            with self.subTest(scene=scene), self.assertRaises(SceneError):
                validate_scene(scene)

    def test_revision_preserves_sequence(self):
        scene = sequence_scene()
        revised = apply_revision(scene, {'actors': [{'id': 'explorer', 'color': '#0066ff'}]})
        self.assertEqual(revised['actors'][0]['sequence'], scene['actors'][0]['sequence'])
        self.assertNotEqual(revised['actors'][0]['color'], scene['actors'][0]['color'])

    def test_frames_cover_timeline_without_gaps(self):
        scene = sequence_scene()
        windows = list(frame_windows(scene['actors'][0]['sequence'], 5, 120))
        self.assertEqual(windows[0][0], 1)
        self.assertEqual(windows[-1][1], 120)
        self.assertTrue(all(a[1] == b[0] for a, b in zip(windows, windows[1:])))

    def test_revision_can_replace_sequence_with_legacy_action(self):
        scene = sequence_scene()
        revised = apply_revision(scene, {'actors': [{'id': 'explorer', 'action': 'idle', 'end': [-2, 0, 0]}]})
        self.assertNotIn('sequence', revised['actors'][0])

    def test_pause_omission_detected(self):
        self.assertFalse(check_plan_coverage('Walk, pause, and wave', demo_scene())['passed'])

    def test_unseen_chair_task_rejected_before_dependencies(self):
        prompt = 'Create a five-second animation in which a character walks toward a chair, stops, turns their head toward the camera, and sits down.'
        with tempfile.TemporaryDirectory() as root, patch('scene_forge.jobs.discover_blender') as blender, patch('scene_forge.jobs.plan') as model:
            with self.assertRaises(UnsupportedRequest):
                execute_job(root, prompt=prompt, preview='none')
            blender.assert_not_called()
            model.assert_not_called()
            job = next(Path(root).iterdir())
            status = json.loads((job/'status.json').read_text())
            self.assertEqual(status['state'], 'unsupported')
            self.assertEqual(status['unsupported_requests'], ['chair asset', 'sitting'])
            self.assertFalse((job/'scene.blend').exists())

    def test_negation_and_word_boundaries(self):
        self.assertTrue(preflight('Walk and look at the camera. No sitting, no chairs, no jumping.')['passed'])
        self.assertTrue(preflight('Run a five-second animation of a walking character.')['passed'])
        self.assertFalse(preflight('Do not wave, but sit down.')['passed'])
        self.assertTrue(preflight('A classroom with sittingroom colors.')['passed'])

    def test_known_motion_omission_detected(self):
        self.assertFalse(check_plan_coverage('Walk and turn the head toward the camera', demo_scene())['passed'])
        self.assertTrue(check_plan_coverage('Walk and turn the head toward the camera', sequence_scene())['passed'])

    @patch('scene_forge.planner.models', return_value=['test'])
    @patch('scene_forge.planner.request_json')
    def test_model_unmet_requests_do_not_build_or_retry(self, request, _):
        request.return_value = {'message': {'content': json.dumps({'unsupported_requests': [{'feature': 'backflip', 'request_quote': 'backflip'}]})}}
        with self.assertRaises(UnsupportedRequest):
            plan('Make a backflip', model='test')
        self.assertEqual(request.call_count, 1)

    @patch('scene_forge.planner.models', return_value=['test'])
    @patch('scene_forge.planner.request_json')
    def test_unrequested_limit_is_not_accepted_as_a_refusal(self, request, _):
        request.side_effect = [
            {'message': {'content': json.dumps({'unsupported_requests': [{'feature': 'speech', 'request_quote': 'talk to me'}]})}},
            {'message': {'content': json.dumps(sequence_scene())}},
        ]
        scene, metadata = plan('Walk and look at the camera', model='test')
        self.assertEqual(metadata['attempts'], 2)
        self.assertEqual(scene['unsupported_requests'], [])

    @patch('scene_forge.planner.models', return_value=['test'])
    @patch('scene_forge.planner.request_json')
    def test_omission_repaired_through_model_response(self, request, _):
        request.side_effect = [{'message': {'content': json.dumps(dict(demo_scene(), unsupported_requests=[]))}},
                               {'message': {'content': json.dumps(sequence_scene())}}]
        observed = []
        scene, provenance = plan('Walk and look at the camera', model='test', on_response=observed.append)
        self.assertEqual(len(observed), 2)
        self.assertEqual(provenance['attempts'], 2)
        self.assertTrue(provenance['prompt_coverage']['passed'])
        self.assertEqual(scene['actors'][0]['action'], 'sequence')


if __name__ == '__main__':
    unittest.main()
