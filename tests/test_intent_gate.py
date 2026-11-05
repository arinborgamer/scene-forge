import copy
import json
import unittest

from modeling_training.intent_corpus import build
from modeling_training.intent_eval import score
from modeling_training.intent_gate import inspect, assess,evaluation_bound


class IntentGateTests(unittest.TestCase):
    def setUp(self):
        self.rows = build('test', 28203)
        records = [dict(id=r['id'], prompt=r['prompt'], raw=json.dumps(r['operation']),
                        **score(json.dumps(r['operation']), r)) for r in self.rows]
        self.evaluation = dict(complete=True, count=56, schema_valid=56, intent_exact=56, records=records)
        self.candidate = inspect(self.evaluation, self.rows)
        self.regression = dict(count=56, schema_valid=56, intent_exact=54, groups={}, modeling_exact=31, cgi_exact=23)
        self.result = dict(status='completed', weights_changed=True, training_steps=128,
                           successful_optimizer_steps=128, baseline_test=dict(complete=True, intent_exact=10))

    def test_correct_candidate_qualifies_for_review_only(self):
        report = assess(self.result, self.candidate, self.regression, True, True)
        self.assertTrue(report['passed'])
        self.assertFalse(report['production_ready'])
        self.assertFalse(report['default_model_changed'])

    def test_high_aggregate_does_not_hide_scope_or_refusal_errors(self):
        for kind, exact in [('local_translate', 15), ('unsupported', 5)]:
            candidate = copy.deepcopy(self.candidate)
            candidate['groups'][kind]['exact'] = exact
            self.assertFalse(assess(self.result, candidate, self.regression, True, True)['passed'])

    def test_raw_output_tampering_and_incomplete_evaluation_rejected(self):
        evaluation = copy.deepcopy(self.evaluation)
        evaluation['records'][0]['raw'] = '{}'
        self.assertIsNone(inspect(evaluation, self.rows))
        evaluation = copy.deepcopy(self.evaluation)
        evaluation['records'][0]['prompt'] = 'different prompt'
        self.assertIsNone(inspect(evaluation, self.rows))
        self.assertIsNone(inspect({**self.evaluation, 'complete': False}, self.rows))

    def test_checksum_or_old_suite_failure_rejects_candidate(self):
        self.assertFalse(assess(self.result, self.candidate, self.regression, False, True)['passed'])
        self.assertFalse(assess(self.result, self.candidate, self.regression, True, False)['passed'])
        self.assertFalse(assess(self.result, self.candidate, {**self.regression, 'cgi_exact': 21}, True, True)['passed'])

    def test_another_adapter_or_profile_cannot_supply_regression_evidence(self):
        config=dict(profile='scene_intent',base='output/base')
        proof=dict(profile='scene_intent',base='output/base',candidate_weights=dict(sha256='candidate'))
        self.assertTrue(evaluation_bound(proof,config,'candidate'))
        self.assertFalse(evaluation_bound({**proof,'profile':'intent'},config,'candidate'))
        self.assertFalse(evaluation_bound(proof,config,'another'))
        self.assertFalse(assess(self.result,self.candidate,self.regression,True,True,False)['passed'])
