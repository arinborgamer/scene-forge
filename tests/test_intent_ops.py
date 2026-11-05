import copy
import unittest

from modeling_training.intent_ops import compile_intent, canonical_intent, UnsupportedIntent


class IntentCompilerTests(unittest.TestCase):
    def local(self, **values):
        return dict(intent='local_translate', target='Body', axis='Z', amount=12.5, unit='mm',
                    center=[0, 0, 1.2], radius=[.3, .25, .2], **values)

    def test_explicit_units_and_preserved_properties(self):
        for amount, unit, expected in [(12.5, 'mm', .0125), (-2.75, 'cm', -.0275), (.008, 'm', .008)]:
            frame = self.local(); frame.update(amount=amount, unit=unit)
            prior = copy.deepcopy(frame)
            op = compile_intent(frame, ['Body'])
            self.assertEqual(op['op'], 'deform')
            self.assertEqual(op['translation'], [0, 0, expected])
            self.assertEqual(op['scale'], [1, 1, 1])
            self.assertEqual(prior, frame)
        lens = compile_intent(dict(intent='camera_lens', target='Cam', amount=6.5, unit='cm'), ['Cam'])
        self.assertEqual(lens['millimeters'], 65)
        light = compile_intent(dict(intent='light_power', target='Key', amount=.75, unit='kW'), ['Key'])
        self.assertEqual(light['watts'], 750)

    def test_scope_is_never_silently_repaired(self):
        local = compile_intent(self.local(), ['Body'])
        frame = dict(intent='object_translate', target='Body', axis='Z', amount=12.5, unit='mm')
        whole = compile_intent(frame, ['Body'])
        self.assertEqual(local['op'], 'deform')
        self.assertEqual(whole['op'], 'transform')
        self.assertEqual(whole['rotation_degrees'], [0, 0, 0])
        frame['center'] = [0, 0, 1.2]
        with self.assertRaises(ValueError): compile_intent(frame, ['Body'])

    def test_unknown_targets_units_nonfinite_and_noops_rejected(self):
        with self.assertRaises(ValueError): compile_intent(self.local(), [])
        for change in [{'unit': 'inches'}, {'amount': float('nan')}, {'amount': True}, {'amount': 0}, {'amount': 5000}]:
            frame = self.local(); frame.update(change)
            with self.subTest(change=change), self.assertRaises(ValueError): compile_intent(frame, ['Body'])
        with self.assertRaises(ValueError):
            compile_intent(dict(intent='camera_lens', target='Cam', amount=.2, unit='cm'), ['Cam'])

    def test_percentages_and_canonical_roundtrip(self):
        frame = dict(intent='local_scale', target='Body', axis='Y', percent=6,
                     center=[0, 0, 1.3], radius=[.3, .22, .18])
        op = compile_intent(frame, ['Body'])
        self.assertEqual(op['scale'], [1, 1.06, 1])
        self.assertEqual(compile_intent(canonical_intent(op), ['Body']), op)
        frame = dict(intent='surface', target='Body', roughness=25, metallic=80, unit='percent')
        op = compile_intent(frame, ['Body'])
        self.assertEqual((op['roughness'], op['metallic']), (.25, .8))
        self.assertEqual(compile_intent(canonical_intent(op), ['Body']), op)

    def test_unsupported_stops_before_execution(self):
        with self.assertRaises(UnsupportedIntent):
            compile_intent({'intent': 'unsupported', 'feature': 'simulation'}, [])
