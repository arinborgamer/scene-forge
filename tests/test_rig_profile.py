import copy
import unittest

from scene_forge.rig_profile import MPFB_JOINTS, joint_bone, validate_profile


def profile(prefix=''):
    names = list(MPFB_JOINTS.values())
    matrix = [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]]
    return dict(schema_version=1, coordinates=dict(meters_per_unit=1, up_axis='Z', forward_axis='-Y'), fps=24,
                joints={k: prefix+v for k, v in MPFB_JOINTS.items()},
                bones=[dict(name=prefix+n, parent=prefix+names[i-1] if i else None,
                            head=[0, 0, i*.1], tail=[0, 0, i*.1+.1], rest_matrix=matrix) for i, n in enumerate(names)])


class RigProfileTests(unittest.TestCase):
    def test_explicit_mapping_accepts_renamed_bones(self):
        self.assertEqual(joint_bone(profile(), 'left_elbow'), 'lowerarm01.L')
        self.assertEqual(joint_bone(profile('Other_'), 'left_elbow'), 'Other_lowerarm01.L')

    def test_missing_joint_bone_duplicate_and_cycle_rejected(self):
        for edit in ['missing_joint', 'unknown_bone', 'duplicate', 'cycle']:
            p = profile()
            if edit == 'missing_joint': del p['joints']['jaw']
            elif edit == 'unknown_bone': p['joints']['jaw'] = 'missing'
            elif edit == 'duplicate': p['bones'].append(copy.deepcopy(p['bones'][0]))
            else: p['bones'][0]['parent'] = p['bones'][-1]['name']
            with self.subTest(edit=edit), self.assertRaises(ValueError): validate_profile(p)

    def test_invalid_units_rest_pose_and_endpoints_rejected(self):
        for edit in ['scale', 'matrix', 'endpoint', 'fps']:
            p = profile()
            if edit == 'scale': p['coordinates']['meters_per_unit'] = 0
            elif edit == 'matrix': p['bones'][0]['rest_matrix'][0][0] = float('nan')
            elif edit == 'endpoint': p['bones'][0]['tail'] = p['bones'][0]['head'].copy()
            else: p['fps'] = True
            with self.subTest(edit=edit), self.assertRaises(ValueError): validate_profile(p)
