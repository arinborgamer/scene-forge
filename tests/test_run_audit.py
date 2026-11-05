import copy
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from modeling_training.run_audit import inspect_budget, audit


class AuditTests(unittest.TestCase):
    def setUp(self):
        self.config=dict(steps=2,accumulate=1,max_skipped_updates=1,step_budget='successful_optimizer_updates')
        self.rows=[dict(operation=dict(intent='local_scale')),dict(operation=dict(intent='object_translate'))]
        self.records=[
            dict(attempt=1,step=0,successful_optimizer_steps=0,skipped_optimizer_steps=1,
                 optimizer_updated=False,batch_indices=[0],loss=.5,gradient_norm=None,gradients_finite=False),
            dict(attempt=2,step=1,successful_optimizer_steps=1,skipped_optimizer_steps=1,
                 optimizer_updated=True,batch_indices=[0],loss=.5,gradient_norm=1.,gradients_finite=True),
            dict(attempt=3,step=2,successful_optimizer_steps=2,skipped_optimizer_steps=1,
                 optimizer_updated=True,batch_indices=[1],loss=.4,gradient_norm=.8,gradients_finite=True),
        ]

    def test_complete_pass_with_same_batch_retry(self):
        result=inspect_budget(self.config,self.rows,self.records)
        self.assertTrue(result['passed'])
        self.assertEqual(result['unique_training_rows'],2)
        self.assertEqual(result['skipped_updates'],1)

    def test_skipped_data_advance_and_false_counters_fail(self):
        records=copy.deepcopy(self.records)
        records[1]['batch_indices']=[1]
        self.assertFalse(inspect_budget(self.config,self.rows,records)['checks']['retries'])
        records=copy.deepcopy(self.records)
        records[1]['step']=2
        self.assertFalse(inspect_budget(self.config,self.rows,records)['checks']['counters'])

    def test_missing_exposure_partial_and_nonfinite_evidence_fail(self):
        records=copy.deepcopy(self.records)
        records[2]['batch_indices']=[0]
        self.assertFalse(inspect_budget(self.config,self.rows,records)['checks']['one_complete_pass'])
        self.assertFalse(inspect_budget(self.config,self.rows,records[:2])['checks']['completed_budget'])
        records[2]['gradient_norm']=float('inf')
        self.assertFalse(inspect_budget(self.config,self.rows,records)['checks']['finite_successes'])

    def test_attempt_budget_or_excess_skips_cannot_pass(self):
        self.assertFalse(inspect_budget({**self.config,'step_budget':'attempts'},self.rows,self.records)['passed'])
        self.assertFalse(inspect_budget({**self.config,'max_skipped_updates':0},self.rows,self.records)['passed'])

    def test_trailing_skip_after_completion_fails_even_if_skip_budget_allows_it(self):
        records=copy.deepcopy(self.records)
        records.append(dict(attempt=4,step=2,successful_optimizer_steps=2,skipped_optimizer_steps=2,
                            optimizer_updated=False,batch_indices=[0],loss=.3,
                            gradient_norm=None,gradients_finite=False))
        result=inspect_budget({**self.config,'max_skipped_updates':2},self.rows,records)
        self.assertFalse(result['passed'])
        self.assertFalse(result['checks']['no_attempts_after_completion'])

    def test_complete_artifact_audit_checks_actual_tensor_changes_and_sources(self):
        import torch
        from safetensors.torch import save_file
        with TemporaryDirectory() as temp:
            root=Path(temp)
            run,data,origin=[root/n for n in ('run','data','origin')]
            for p in (run/'adapter',run/'source_snapshot',data,origin):
                p.mkdir(parents=True,exist_ok=True)
            (data/'train.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in self.rows))
            (run/'source_snapshot/train.py').write_bytes(b'frozen source')
            save_file({'lora_A':torch.tensor([1.])},origin/'adapter_model.safetensors')
            save_file({'lora_A':torch.tensor([2.])},run/'adapter/adapter_model.safetensors')
            sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            config={**self.config,'data':str(data),'initial_adapter':str(origin),
                    'initial_adapter_weights':dict(file='adapter_model.safetensors',sha256=sha(origin/'adapter_model.safetensors')),
                    'source_hashes':{'train.py':sha(run/'source_snapshot/train.py')},
                    'dataset_manifest':dict(files=dict(train=dict(sha256=sha(data/'train.jsonl'))))}
            (run/'config.json').write_text(json.dumps(config))
            (run/'training-log.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in self.records))
            weights=dict(successful_optimizer_steps=2,optimizer_attempts=3,skipped_optimizer_steps=1,
                         adapter_file_sha256=sha(run/'adapter/adapter_model.safetensors'),weights_changed=True,
                         before_sha256='a'*64,after_sha256='b'*64)
            (run/'weight-change.json').write_text(json.dumps(weights))
            result=audit(run)
            self.assertTrue(result['training_evidence_passed'])
            self.assertEqual(result['changed_tensors_vs_warm_start'],1)
            self.assertFalse(result['evaluations_complete'])
            (run/'source_snapshot/train.py').write_bytes(b'modified')
            self.assertFalse(audit(run)['checks']['source_snapshot'])
