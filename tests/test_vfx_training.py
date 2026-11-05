import copy,unittest
from modeling_training.vfx_corpus import rows,validate_row
from modeling_training.vfx_ops import validate_operation

class VfxCurriculumTests(unittest.TestCase):
    def test_disjoint_names_and_language(self):
        train=rows('train',224,27101);test=rows('test',24,27103)
        self.assertFalse({r['prompt'] for r in train}&{r['prompt'] for r in test})
        self.assertFalse({r['operation']['target'] for r in train}&{r['operation']['target'] for r in test})
        self.assertEqual(len(test),24)

    def test_wrong_axis_and_units_rejected(self):
        for row in rows('test',24,27103):
            if row['operation']['op'] not in ('transform','deform'): continue
            bad=copy.deepcopy(row);op=bad['operation'];axis='XYZ'.index(row['facts']['axis'])
            op['translation'][(axis+1)%3]=op['translation'][axis];op['translation'][axis]=0
            with self.assertRaises(AssertionError): validate_row(bad)
        row=rows('test',24,27103)[0];row['operation']['watts']/=1000
        with self.assertRaises((AssertionError,ValueError)): validate_row(row)

    def test_unknown_targets_and_unbounded_values_rejected(self):
        op={'op':'camera_lens','target':'Camera','millimeters':50}
        with self.assertRaises(ValueError): validate_operation(op,[])
        op['millimeters']=float('nan')
        with self.assertRaises(ValueError): validate_operation(op,['Camera'])

if __name__=='__main__': unittest.main()
