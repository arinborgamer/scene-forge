import json
import unittest
from collections import Counter
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from modeling_training.intent_corpus import build
from modeling_training.intent_eval import score
from modeling_training.intent_refinement import additions, build_training, main
from modeling_training.intent_challenge import build as challenge


class RefinementTests(unittest.TestCase):
    def test_counts_replay_and_new_examples_are_deterministic(self):
        original = build('train', 28301)
        rows = build_training(original)
        self.assertEqual(rows, build_training(original))
        self.assertEqual(len(rows), 192)
        self.assertEqual(sum(r['id'].startswith('replay-') for r in rows), 80)
        self.assertEqual(len({r['id'] for r in rows}), 192)
        self.assertEqual(len({r['prompt'] for r in rows}), 192)
        self.assertEqual(Counter(r['operation']['intent'] for r in additions())['unsupported'], 40)

    def test_new_labels_compile_and_score_without_repair(self):
        for row in additions():
            result = score(json.dumps(row['operation']), row)
            self.assertTrue(result['intent_exact'], row['id'])
            self.assertTrue(result['schema_valid'], row['id'])
        scales = [r for r in additions() if r['operation']['intent'] == 'local_scale']
        for axis in 'XYZ':
            values = [r['operation']['percent'] for r in scales if r['operation']['axis'] == axis]
            self.assertTrue(any(v < 0 for v in values))
            self.assertTrue(any(v > 0 for v in values))

    def test_known_test_prompts_never_enter_training(self):
        source = Path('output/qwen-intent-corpus-v2')
        if not source.exists():
            self.skipTest('Local frozen corpus is not packaged with source')
        training = build_training([json.loads(x) for x in (source/'train.jsonl').read_text().splitlines()])
        test = [json.loads(x) for x in (source/'test.jsonl').read_text().splitlines()]
        self.assertFalse({r['prompt'] for r in training} & {r['prompt'] for r in test})
        self.assertEqual({r['operation']['feature'] for r in additions() if r['operation']['intent']=='unsupported'},
                         {'new_geometry', 'animation', 'simulation', 'multi_step', 'ambiguous'})

    def test_freeze_writes_snapshots_and_preserves_regressions(self):
        source = Path('output/qwen-intent-corpus-v2')
        if not source.exists():
            self.skipTest('Local frozen corpus is not packaged with source')
        with TemporaryDirectory() as temp:
            dest = Path(temp)/'frozen'
            with patch('sys.argv', ['intent_refinement', '--source', str(source), '--output', str(dest)]):
                main()
            for split in ('test', 'validation'):
                self.assertEqual((dest/(split+'.jsonl')).read_bytes(), (source/(split+'.jsonl')).read_bytes())
            for name in ('intent_refinement.py', 'intent_ops.py', 'intent_corpus.py'):
                self.assertTrue((dest/(name+'.snapshot')).is_file())
            manifest = json.loads((dest/'manifest.json').read_text())
            self.assertIn('No untouched-test claim', manifest['split_limitations'])

    def test_new_challenge_disjoint_from_corrective_training(self):
        rows = challenge()
        training = build_training(build('train', 28301))
        self.assertEqual(len(rows), 20)
        self.assertFalse({r['prompt'] for r in rows} & {r['prompt'] for r in training})
        for row in rows:
            self.assertTrue(score(json.dumps(row['operation']), row)['intent_exact'])


if __name__ == '__main__':
    unittest.main()
