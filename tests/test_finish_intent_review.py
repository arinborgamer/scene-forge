import unittest

from modeling_training.finish_intent_review import combined


class FinishIntentReviewTests(unittest.TestCase):
    def test_geometry_success_does_not_override_failed_language_gate(self):
        result = combined({'passed': False}, {'complete': True, 'count': 2, 'passed_count': 2, 'passed': True},
                          {'passed': True}, [{'passed': True}, {'passed': True}])
        self.assertFalse(result['passed'])
        self.assertEqual(result['decision'], 'keep_previous_adapter')

    def test_all_checks_only_qualify_for_human_review(self):
        result = combined({'passed': True}, {'complete': True, 'count': 2, 'passed_count': 2, 'passed': True},
                          {'passed': True}, [{'passed': True}, {'passed': True}])
        self.assertTrue(result['passed'])
        self.assertFalse(result['production_ready'])
        self.assertFalse(result['default_model_changed'])
        self.assertEqual(result['human_visual_review'], 'pending')

    def test_partial_or_missing_checks_never_pass(self):
        self.assertFalse(combined({'passed': True}, {'complete': False, 'passed': True}, {'passed': True}, [])['passed'])

    def test_new_challenge_cannot_be_hidden_by_old_gate_success(self):
        args = ({'passed': True}, {'complete': True, 'count': 2, 'passed_count': 2, 'passed': True},
                {'passed': True}, [{'passed': True}, {'passed': True}])
        challenge = dict(count=20, schema_valid=20, intent_exact=19, groups=dict(unsupported=dict(exact=5)))
        self.assertTrue(combined(*args, challenge)['passed'])
        self.assertFalse(combined(*args, {**challenge, 'intent_exact': 17})['passed'])
        self.assertFalse(combined(*args, {**challenge, 'groups': dict(unsupported=dict(exact=4))})['passed'])

    def test_scene_negative_request_is_an_additional_gate(self):
        args=({'passed':True},{'complete':True,'count':2,'passed_count':2,'passed':True},
              {'passed':True},[{'passed':True},{'passed':True}])
        self.assertFalse(combined(*args,negative={'complete':True,'count':1,'passed_count':0,'passed':False})['passed'])
        self.assertTrue(combined(*args,negative={'complete':True,'count':1,'passed_count':1,'passed':True})['passed'])
