import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from modeling_training.finish_intent_review import verify_scene_transfer


class TransferBindingTests(unittest.TestCase):
    def prepare(self,root,one_choice=False,wrong_adapter=False):
        folder=root/'transfer'
        job=folder/'case'
        job.mkdir(parents=True)
        cases=[dict(id='case',prompt='Shrink Body on Y.')]
        case_file=root/'negative-transfer.json'
        case_file.write_text(json.dumps(cases))
        sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
        (folder/'provenance.json').write_text(json.dumps(dict(cases=str(case_file),profile='scene_intent',case_sha256=sha(case_file))))
        (folder/'result.json').write_text(json.dumps(dict(passed=True,records=[dict(id='case',passed=True)])))
        observed=[dict(id=n) for n in ('Body','Iris','Pupil')]
        (job/'source-inventory.json').write_text(json.dumps(dict(objects=observed)))
        scene=[dict(name=n,type='MESH') for n in (('Body',) if one_choice else ('Iris','Body','Pupil'))]
        (job/'model-input.json').write_text(json.dumps(dict(request=cases[0]['prompt'],scene=scene)))
        request=dict(profile='scene_intent',adapter_sha256='other' if wrong_adapter else 'candidate',
                     model_input_sha256=sha(job/'model-input.json'),observed_inventory_sha256=sha(job/'source-inventory.json'))
        (job/'request.json').write_text(json.dumps(request))
        (job/'scene').mkdir()
        (job/'scene/execution.json').write_text('{}')
        (job/'reopen.json').write_text('{}')
        return folder,cases

    def test_expected_target_only_catalog_is_rejected(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            folder,cases=self.prepare(root,one_choice=True)
            with patch('modeling_training.scene_intent_data.verify_artifact',return_value=cases):
                with self.assertRaisesRegex(ValueError,'independent observed scene choices'):
                    verify_scene_transfer(folder,root,dict(dataset_manifest={}),'candidate','negative-transfer.json')

    def test_observed_reordered_catalog_passes_only_with_recomputed_execution(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            folder,cases=self.prepare(root)
            with patch('modeling_training.scene_intent_data.verify_artifact',return_value=cases),patch(
                    'modeling_training.transfer_review.assess',return_value=dict(passed=False)):
                result=verify_scene_transfer(folder,root,dict(dataset_manifest={}),'candidate','negative-transfer.json')
            self.assertFalse(result['passed'])

    def test_other_adapter_cannot_supply_transfer_evidence(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            folder,cases=self.prepare(root,wrong_adapter=True)
            with patch('modeling_training.scene_intent_data.verify_artifact',return_value=cases):
                with self.assertRaisesRegex(ValueError,'different candidate'):
                    verify_scene_transfer(folder,root,dict(dataset_manifest={}),'candidate','negative-transfer.json')
