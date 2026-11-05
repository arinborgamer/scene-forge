import copy
import json
from pathlib import Path
import tempfile
import unittest

from scene_forge.schema import SceneError, apply_revision, demo_scene, organic_scene, validate_scene
from scene_forge.dataset import collect_examples, export_dataset, scene_digest


class OrganicSchemaTests(unittest.TestCase):
    def test_valid_original_and_organic_styles(self):
        for scene in (demo_scene(), organic_scene()):
            self.assertEqual(validate_scene(scene), scene)

    def test_unsupported_organic_movement_rejected(self):
        for key, value in (('action', 'walk'), ('action', 'walk_and_wave')):
            scene = organic_scene()
            scene['actors'][0][key] = value
            with self.assertRaises(SceneError):
                validate_scene(scene)

    def test_wave_requires_full_body_stationary_shot(self):
        scene = organic_scene()
        scene['actors'][0]['action'] = 'wave'
        with self.assertRaises(SceneError):
            validate_scene(scene)
        scene['camera'] = 'full_body'
        self.assertEqual(validate_scene(scene), scene)
        scene['actors'][0]['end'][0] = 1
        with self.assertRaises(SceneError):
            validate_scene(scene)

    def test_anatomical_weights_normalized_and_limbs_independent(self):
        from scene_forge.organic_motion import skin_weights
        for x in (-0.65, -0.4, -0.2, 0, 0.2, 0.4, 0.65):
            for i in range(361):
                weights = skin_weights(x, i/100)
                self.assertAlmostEqual(sum(weights.values()), 1)
                self.assertTrue(all(0 < weight <= 1 for weight in weights.values()))
        self.assertEqual(skin_weights(0.59, 1.0), {'hand_r': 1})
        self.assertEqual(skin_weights(0.52, 0.78), {'hand_r': 1})
        self.assertEqual(skin_weights(0.42, 1.05), {'hand_r': 1})
        self.assertEqual(skin_weights(-0.2, 0.1), {'foot_l': 1})
        self.assertEqual(skin_weights(0, 2.9), {'head': 1})
        self.assertAlmostEqual(skin_weights(0.35, 1.5).get('arm_r', 0)+skin_weights(0.35, 1.5).get('forearm_r', 0), 1)
        self.assertFalse(any('arm' in name or 'hand' in name for name in skin_weights(0.32, 0.8)))

    def test_organic_camera_and_actor_count_bounded(self):
        scene = organic_scene()
        scene['actors'].append(copy.deepcopy(scene['actors'][0]))
        scene['actors'][1]['id'] = 'second'
        with self.assertRaises(SceneError):
            validate_scene(scene)
        scene = demo_scene()
        scene['camera'] = 'portrait'
        with self.assertRaises(SceneError):
            validate_scene(scene)

    def test_sculpt_controls_are_bounded_and_revisable(self):
        scene = organic_scene()
        controls = copy.deepcopy(scene['actors'][0]['morphology'])
        controls['ear_length'] = 1.2
        result = apply_revision(scene, {'actors': [{'id': 'keeper', 'morphology': controls}]})
        self.assertEqual(result['actors'][0]['morphology']['ear_length'], 1.2)
        self.assertEqual(result['actors'][0]['color'], scene['actors'][0]['color'])
        controls['ear_length'] = 9
        with self.assertRaises(SceneError):
            apply_revision(scene, {'actors': [{'id': 'keeper', 'morphology': controls}]})

    def test_partial_sculpt_revision_preserves_other_anatomy(self):
        original = organic_scene()
        revised = apply_revision(original, {'actors': [{'id': 'keeper', 'morphology': {'head_width': 0.9}}]})
        expected = copy.deepcopy(original)
        expected['actors'][0]['morphology']['head_width'] = 0.9
        self.assertEqual(revised, expected)
        self.assertEqual(original, organic_scene())

    def test_sculpt_revision_resolves_implicit_default_anatomy(self):
        original = organic_scene()
        del original['actors'][0]['morphology']
        revised = apply_revision(original, {'actors': [{'id': 'keeper', 'morphology': {'ear_length': 1.2}}]})
        expected = dict(organic_scene()['actors'][0]['morphology'], ear_length=1.2)
        self.assertEqual(revised['actors'][0]['morphology'], expected)


class DatasetTests(unittest.TestCase):
    def fixture(self, root):
        folder = Path(root) / 'example'
        folder.mkdir()
        scene = organic_scene()
        files = {'scene.json': scene, 'status.json': {'state': 'complete'},
                 'validation.json': {'passed': True},
                 'provenance.json': {'provider': 'ollama', 'model': 'test', 'training_context': {
                     'revision': False, 'messages': [{'role': 'system', 'content': 'schema'},
                                                    {'role': 'user', 'content': 'request'}]}},
                 'review.json': {'approved': True, 'scene_sha256': scene_digest(scene),
                                 'reviewer': 'test fixture', 'rights_note': 'synthetic test',
                                 'quality_notes': 'test fixture, not an actual artist review'}}
        for name, value in files.items():
            (folder / name).write_text(json.dumps(value), encoding='utf-8')
        return folder, files

    def test_only_reviewed_successful_captured_generations_export(self):
        with tempfile.TemporaryDirectory() as root:
            folder, files = self.fixture(root)
            rows, skipped = collect_examples(root)
            self.assertEqual(len(rows), 1)
            self.assertEqual(skipped, [])
            self.assertEqual(rows[0]['messages'][-1]['role'], 'assistant')
            for name, change in [('review.json', {'approved': False}),
                                 ('review.json', {'scene_sha256': 'stale'}),
                                 ('status.json', {'state': 'failed'}),
                                 ('provenance.json', {'provider': 'demo'}),
                                 ('provenance.json', {'training_context': {'revision': True}})]:
                with self.subTest(name=name, change=change):
                    value = dict(files[name], **change)
                    (folder / name).write_text(json.dumps(value), encoding='utf-8')
                    self.assertEqual(len(collect_examples(root)[0]), 0)
                    (folder / name).write_text(json.dumps(files[name]), encoding='utf-8')

    def test_export_never_overwrites_curated_file(self):
        with tempfile.TemporaryDirectory() as root:
            self.fixture(root)
            output = Path(root) / 'curated.jsonl'
            report = export_dataset(root, output)
            self.assertEqual(report['accepted_examples'], 1)
            with self.assertRaises(FileExistsError):
                export_dataset(root, output)
