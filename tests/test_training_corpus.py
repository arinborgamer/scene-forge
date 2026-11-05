import copy
import unittest
from modeling_training.corpus import build_rows, validate_example


class TrainingCorpusTests(unittest.TestCase):
    def test_splits_disjoint_and_reproducible(self):
        a = build_rows('train', 24, 7)
        b = build_rows('test', 24, 8)
        self.assertEqual(a, build_rows('train', 24, 7))
        names = lambda rows: {r['operation'].get('target', r['operation'].get('id')) for r in rows}
        self.assertFalse(names(a) & names(b))
        self.assertTrue(all(validate_example(r) for r in a+b))

    def test_wrong_axis_and_identity_cannot_be_training_targets(self):
        row = build_rows('train', 1, 7)[0]
        wrong = copy.deepcopy(row)
        wrong['operation']['scale'] = list(reversed(wrong['operation']['scale']))
        with self.assertRaises(AssertionError):
            validate_example(wrong)
        wrong['operation']['scale'] = [1, 1, 1]
        with self.assertRaises(ValueError):
            validate_example(wrong)
