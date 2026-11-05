import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from modeling_training.progress import summarize


class ProgressTests(unittest.TestCase):
    def test_overflow_and_partial_results_are_not_completed(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            (root/'training-log.jsonl').write_text('\n'.join(json.dumps(r) for r in [
                dict(optimizer_updated=False, gradient_norm=None),
                dict(optimizer_updated=True, gradient_norm=1.),
            ])+'\n{"incomplete":',encoding='utf-8')
            report=summarize(root,dict(steps=2))
            self.assertEqual(report['recorded_successful_updates'],1)
            self.assertEqual(report['recorded_skips'],1)
            self.assertEqual(report['malformed_log_lines'],1)
            self.assertEqual(report['last_recorded_stage'],'training')
            self.assertFalse(report['liveness_verified'])
            (root/'weight-change.json').write_text(json.dumps(dict(successful_optimizer_steps=1)))
            (root/'trained-test.json').write_text(json.dumps(dict(complete=False,records=[
                dict(intent_exact=True,schema_valid=True)])))
            report=summarize(root,dict(steps=2))
            self.assertEqual(report['last_recorded_stage'],'candidate_evaluation')
            self.assertFalse(report['evaluation']['trained-test']['complete'])
            self.assertTrue(report['saved_count_matches_log'])
            (root/'weight-change.json').write_text(json.dumps(dict(successful_optimizer_steps=2)))
            self.assertFalse(summarize(root,dict(steps=2))['saved_count_matches_log'])

    def test_legacy_infinity_is_flagged_and_file_preserved(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            raw='{"optimizer_updated":false,"gradient_norm":Infinity}\n'
            (root/'training-log.jsonl').write_text(raw)
            report=summarize(root,dict(steps=1))
            self.assertTrue(report['legacy_nonstandard_json'])
            self.assertEqual(report['recorded_skips'],1)
            self.assertEqual((root/'training-log.jsonl').read_text(),raw)

    def test_empty_failure_and_completion_stages(self):
        with TemporaryDirectory() as temp:
            root=Path(temp)
            self.assertEqual(summarize(root,{})['last_recorded_stage'],'prepared')
            (root/'baseline-test.json').write_text(json.dumps(dict(complete=True,records=[])))
            self.assertEqual(summarize(root,{})['last_recorded_stage'],'base_evaluation')
            (root/'result.json').write_text(json.dumps(dict(status='completed')))
            self.assertEqual(summarize(root,{})['last_recorded_stage'],'completed')
            (root/'failure.json').write_text(json.dumps(dict(error='explicit failure')))
            self.assertEqual(summarize(root,{})['last_recorded_stage'],'failed')
