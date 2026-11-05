import json
import unittest

from modeling_training.intent_corpus import build
from modeling_training.scene_intent_corpus import convert,new_challenge
from modeling_training.scene_intent_eval import score


class SceneCorpusTests(unittest.TestCase):
    def test_conversion_preserves_actions_but_exposes_no_label_in_input(self):
        rows=convert(build('test',28303),28501)
        positions=set()
        for row in rows:
            payload=json.loads(row['prompt'])
            self.assertEqual(set(payload),{'request','scene'})
            self.assertEqual(len(row['scene']),3)
            self.assertTrue(score(json.dumps(row['operation']),row)['intent_exact'],row['id'])
            self.assertIn('facts',row)
            if 'target' in row['operation']:
                positions.add([e['name'] for e in row['scene']].index(row['operation']['target']))
        self.assertEqual(positions,{0,1,2})

    def test_twenty_fresh_cases_have_all_declared_categories_and_correct_targets(self):
        rows=convert(new_challenge(),29001)
        self.assertEqual(len(rows),20)
        self.assertEqual(len({r['request'] for r in rows}),20)
        self.assertEqual(sum(r['operation']['intent']=='unsupported' for r in rows),5)
        for row in rows:
            self.assertTrue(score(json.dumps(row['operation']),row)['intent_exact'],row['id'])

    def test_older_cases_without_fixture_facts_are_normalized(self):
        rows=[dict(id='older',prompt='Reduce Patch Y by 7 percent.',
                   operation=dict(intent='local_scale',target='Patch',axis='Y',percent=-7,
                                  center=[0,0,1],radius=[.3,.2,.1]))]
        row=convert(rows,42)[0]
        self.assertEqual(row['facts']['mode'],'scale')
        self.assertEqual(row['facts']['percent'],-7)
