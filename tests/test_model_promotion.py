import copy
import unittest

from modeling_training.promotion import assess


def evaluation(count, exact, valid=None):
    valid = count if valid is None else valid
    return {'complete': True, 'count': count, 'intent_exact': exact, 'schema_valid': valid,
            'records': [{'id': f'case-{i}', 'intent_exact': i < exact, 'schema_valid': i < valid} for i in range(count)]}


class PromotionTests(unittest.TestCase):
    def setUp(self):
        self.trained = evaluation(32, 30)
        self.regression = evaluation(24, 22)
        self.result = {'status': 'completed', 'weights_changed': True, 'successful_optimizer_steps': 64,
                       'training_steps': 64, 'previous_adapter_test': {'complete': True, 'count': 32, 'intent_exact': 19},
                       'trained_test': {k: self.trained[k] for k in ('count', 'intent_exact', 'schema_valid')}}

    def test_passing_gates_do_not_claim_release_or_switch_models(self):
        report = assess(self.result, self.trained, self.regression, True)
        self.assertTrue(report['passed'])
        self.assertEqual(report['decision'], 'eligible_for_blender_review')
        self.assertFalse(report['production_ready'])
        self.assertFalse(report['default_model_changed'])

    def test_forgetting_is_rejected_even_with_better_primary_score(self):
        report = assess(self.result, self.trained, evaluation(24, 21), True)
        self.assertFalse(report['passed'])
        self.assertIn('cgi_regression_at_least_previous_22_of_24', report['failed_checks'])

    def test_missing_partial_and_inconsistent_results_fail_closed(self):
        for broken in ({}, {**self.regression, 'complete': False},
                       {**self.regression, 'intent_exact': 24},
                       {**self.regression, 'records': self.regression['records'][:-1]}):
            with self.subTest(broken=broken):
                self.assertFalse(assess(self.result, self.trained, broken, True)['passed'])

    def test_weight_mismatch_failed_updates_and_bad_schema_rejected(self):
        self.assertFalse(assess(self.result, self.trained, self.regression, False)['passed'])
        result = copy.deepcopy(self.result)
        result['successful_optimizer_steps'] = 63
        self.assertFalse(assess(result, self.trained, self.regression, True)['passed'])
        trained = evaluation(32, 30, 31)
        result = {**self.result, 'trained_test': {k: trained[k] for k in ('count', 'intent_exact', 'schema_valid')}}
        self.assertFalse(assess(result, trained, self.regression, True)['passed'])
        self.assertFalse(assess(self.result, self.trained, evaluation(24, 22, 22), True)['passed'])

    def test_reduced_primary_accuracy_rejected(self):
        trained = evaluation(32, 28)
        result = {**self.result, 'trained_test': {k: trained[k] for k in ('count', 'intent_exact', 'schema_valid')}}
        self.assertFalse(assess(result, trained, self.regression, True)['passed'])
