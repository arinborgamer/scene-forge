import collections
import copy
import unittest

from modeling_training.balanced_corpus import build, displacement_rows
from modeling_training.vfx_corpus import validate_row


class BalancedCorpusTests(unittest.TestCase):
    def test_axes_units_and_wording_are_independently_crossed(self):
        rows = displacement_rows('train', 28101)
        coverage = collections.Counter((r['facts']['axis'], r['unit_family'],
                                        r['wording_family'], r['operation']['op']) for r in rows)
        self.assertEqual(len(coverage), 3*3*4*2)
        self.assertEqual(set(coverage.values()), {1})
        pairs = collections.defaultdict(list)
        for row in rows:
            pairs[row['operation']['target']].append(row)
        for local, whole in pairs.values():
            self.assertEqual(local['operation']['translation'], whole['operation']['translation'])
            self.assertEqual(local['operation']['op'], 'deform')
            self.assertEqual(whole['operation']['op'], 'transform')

    def test_split_is_disjoint_and_replay_retains_capabilities(self):
        train, val, test = [build(s, seed) for s, seed in
                            [('train', 28101), ('validation', 28102), ('test', 28103)]]
        self.assertEqual([len(train), len(val), len(test)], [128, 16, 32])
        self.assertEqual(train, build('train', 28101))
        for a, b in [(train, val), (train, test), (val, test)]:
            self.assertFalse({r['operation']['target'] for r in a} & {r['operation']['target'] for r in b})
            self.assertFalse({r['prompt'] for r in a} & {r['prompt'] for r in b})
        self.assertEqual(sum(r['facts'].get('mode') == 'scale' for r in train), 24)
        self.assertEqual(sum(r['operation']['op'] in ('light_power', 'camera_lens', 'surface', 'glow') for r in train), 32)

    def test_unrequested_scale_and_wrong_unit_are_rejected(self):
        row = next(r for r in displacement_rows('train', 7) if r['operation']['op'] == 'transform')
        wrong = copy.deepcopy(row)
        wrong['operation']['scale'][0] = .99
        with self.assertRaises(AssertionError):
            validate_row(wrong)
        wrong = copy.deepcopy(row)
        axis = 'XYZ'.index(row['facts']['axis'])
        wrong['operation']['translation'][axis] *= 100
        with self.assertRaises(AssertionError):
            validate_row(wrong)
