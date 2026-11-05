import copy
import json
import unittest

from modeling_training import intent_ops
from modeling_training.scene_intent_ops import compile_intent,prompt,from_legacy,validate_scene
from modeling_training.scene_intent_eval import score


class SceneIntentTests(unittest.TestCase):
    def setUp(self):
        self.scene=[dict(name=n,type='MESH') for n in ('FigureA','FigureB','FigureC')]
        self.frame=dict(intent='local_scale',target='FigureB',axis='Y',direction='decrease',percent=12,
                        center=[0,0,1.2],radius=[.3,.2,.1])

    def test_direction_literal_not_repaired_from_request(self):
        original=copy.deepcopy(self.frame)
        self.assertEqual(compile_intent(self.frame,self.scene)['scale'],[1,.88,1])
        self.assertEqual(self.frame,original)
        row=dict(operation=self.frame,scene=self.scene)
        wrong={**self.frame,'direction':'increase'}
        result=score(json.dumps(wrong),row)
        self.assertTrue(result['schema_valid'])
        self.assertFalse(result['intent_exact'])
        self.assertEqual(result['compiled_operation']['scale'],[1,1.12,1])

    def test_another_valid_target_is_wrong_not_coerced(self):
        result=score(json.dumps({**self.frame,'target':'FigureA'}),dict(operation=self.frame,scene=self.scene))
        self.assertTrue(result['schema_valid'])
        self.assertFalse(result['intent_exact'])
        self.assertEqual(result['compiled_operation']['target'],'FigureA')

    def test_wrong_types_signed_magnitudes_and_old_frames_rejected(self):
        for frame in ({**self.frame,'percent':-12},{k:v for k,v in self.frame.items() if k!='direction'},
                      {**self.frame,'target':'NoSuchMesh'},{**self.frame,'percent':0}):
            with self.assertRaises(ValueError):
                compile_intent(frame,self.scene)
        with self.assertRaises(ValueError):
            compile_intent(self.frame,[dict(name='FigureB',type='LIGHT')])

    def test_old_protocol_unchanged_and_conversion_exact(self):
        legacy={k:v for k,v in self.frame.items() if k!='direction'}
        legacy['percent']=-12
        self.assertEqual(from_legacy(legacy),self.frame)
        self.assertEqual(intent_ops.compile_intent(legacy,['FigureB']),compile_intent(self.frame,self.scene))
        with self.assertRaises(ValueError):
            intent_ops.validate_intent(self.frame,['FigureB'])

    def test_model_input_contains_only_request_and_actual_catalog(self):
        payload=json.loads(prompt('Reduce the Y patch on FigureB by 12 percent.',self.scene))
        self.assertEqual(set(payload),{'request','scene'})
        self.assertNotIn('operation',payload)
        self.assertEqual(len(payload['scene']),3)
        with self.assertRaises(ValueError):
            validate_scene(self.scene+[self.scene[0]])
