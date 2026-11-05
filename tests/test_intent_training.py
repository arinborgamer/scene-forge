import json
import unittest

from modeling_training.intent_corpus import build
from modeling_training.intent_eval import score


class IntentTrainingTests(unittest.TestCase):
    def test_scene_profile_and_legacy_profile_do_not_mix(self):
        from modeling_training import finetune
        from modeling_training.scene_intent_corpus import convert
        old_profile=finetune.PROFILE
        try:
            row=convert(build('test',28303),42)[0]
            finetune.configure_profile('scene_intent')
            self.assertTrue(finetune.score(json.dumps(row['operation']),row)['intent_exact'])
            self.assertIn('direction',finetune.SYSTEM)
            finetune.configure_profile('intent')
            legacy=build('test',28303)[0]
            self.assertTrue(finetune.score(json.dumps(legacy['operation']),legacy)['intent_exact'])
        finally:
            finetune.configure_profile(old_profile)

    def test_split_counts_disjoint_names_and_language(self):
        train, val, test = [build(s, seed) for s, seed in [('train', 28201), ('validation', 28202), ('test', 28203)]]
        self.assertEqual([len(train), len(val), len(test)], [256, 26, 56])
        self.assertEqual(train, build('train', 28201))
        for a, b in [(train, val), (train, test), (val, test)]:
            self.assertFalse({r['prompt'] for r in a} & {r['prompt'] for r in b})
            self.assertFalse({r['operation'].get('target') for r in a if 'target' in r['operation']}
                             & {r['operation'].get('target') for r in b if 'target' in r['operation']})
            self.assertFalse({r['language_family'] for r in a} & {r['language_family'] for r in b})

    def test_both_scope_classes_contain_object_and_vertex_language(self):
        rows = build('train', 28201)
        for kind in ['local_translate', 'object_translate']:
            selected = [r for r in rows if r['operation']['intent'] == kind]
            self.assertEqual(len(selected), 72)
            coverage = {(r['operation']['axis'], r['operation']['unit'], r['language_family']) for r in selected}
            self.assertEqual(len(coverage), 3*3*8)
            self.assertTrue(any(r['prompt'].startswith('Object ') for r in selected) if kind == 'local_translate' else True)
            self.assertTrue(any('vertex' in r['prompt'] or 'vertices' in r['prompt'] for r in selected))

    def test_expected_intents_and_refusals_score_correctly(self):
        for row in build('test', 28203):
            result = score(json.dumps(row['operation']), row)
            self.assertTrue(result['schema_valid'], row['id'])
            self.assertTrue(result['intent_exact'], row['id'])

    def test_wrong_scope_valid_refusal_and_wrong_units_are_not_repairs(self):
        row = next(r for r in build('test', 28203) if r['operation']['intent'] == 'local_translate')
        wrong = {k: v for k, v in row['operation'].items() if k not in ('center', 'radius')}
        wrong['intent'] = 'object_translate'
        result = score(json.dumps(wrong), row)
        self.assertTrue(result['schema_valid'])
        self.assertFalse(result['intent_exact'])
        self.assertEqual(result['compiled_operation']['op'], 'transform')
        self.assertFalse(score(json.dumps({'intent':'unsupported','feature':'ambiguous'}), row)['intent_exact'])
        wrong = {**row['operation'], 'unit': 'cm' if row['operation']['unit'] != 'cm' else 'mm'}
        self.assertFalse(score(json.dumps(wrong), row)['intent_exact'])

    def test_unknown_model_target_and_invented_fields_rejected(self):
        row = next(r for r in build('test', 28203) if r['operation']['intent'] == 'object_translate')
        wrong = {**row['operation'], 'target': 'OtherMesh'}
        self.assertFalse(score(json.dumps(wrong), row)['schema_valid'])
        wrong = {**row['operation'], 'scale': [1, 1, 1]}
        self.assertFalse(score(json.dumps(wrong), row)['schema_valid'])
