import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from scripts.index_training_data import build


class TrainingIndexTests(unittest.TestCase):
    def write(self,path,value):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(value),encoding='utf-8')

    def test_wrapper_gate_is_linked_without_promotion_file(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            run=root/'output/run'
            self.write(run/'config.json',dict(dataset_manifest={},steps=3))
            self.write(root/'output/final/gate.json',dict(run=str(run.resolve()),passed=False,decision='keep_previous_adapter'))
            catalog=build(root)
            actual=catalog['runs'][0]
            self.assertFalse(actual['promotion']['passed'])
            self.assertEqual(actual['gate_file'],'output/final/gate.json')
            self.assertFalse(actual['gate_conflict'])

    def test_conflicting_gates_preserved_without_arbitrary_winner(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            run=root/'output/run'
            self.write(run/'config.json',dict(dataset_manifest={},steps=3))
            self.write(run/'promotion.json',dict(passed=True,decision='eligible_for_blender_review'))
            self.write(root/'output/final/gate.json',dict(run=str(run.resolve()),passed=False,decision='keep_previous_adapter'))
            actual=build(root)['runs'][0]
            self.assertTrue(actual['gate_conflict'])
            self.assertEqual(len(actual['gate_records']),2)
            self.assertIsNone(actual['promotion'])
            self.assertIsNone(actual['gate_file'])

    def test_failed_corpus_generation_is_explicit(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            data=root/'output/corpus'
            self.write(data/'manifest.json',dict(files={}))
            self.write(data/'generation-failure.json',dict(complete=False,error='snapshot write failed'))
            actual=build(root)['datasets'][0]
            self.assertFalse(actual['blender_verified'])
            self.assertEqual(actual['generation_failure']['error'],'snapshot write failed')
