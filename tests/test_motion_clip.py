import copy
import unittest

from scene_forge.motion_clip import skeleton_signature, validate_clip, continuous_quaternions
from tests.test_rig_profile import profile


def clip(p):
    return dict(schema_version=1, skeleton_signature=skeleton_signature(p), fps=24, start_frame=1,
                root_offsets_m=[[0, 0, 0], [.1, 0, 0]], joint_rotations={'left_elbow': [[1, 0, 0, 0], [-1, 0, 0, 0]]},
                source=dict(declared_kind='authored_fixture', id='test-only'))


class MotionClipTests(unittest.TestCase):
    def test_quaternion_hemisphere_is_equivalent_and_nonmutating(self):
        track = [[1, 0, 0, 0], [-1, 0, 0, 0]]
        result = continuous_quaternions(track)
        self.assertEqual(result, [[1, 0, 0, 0], [1, 0, 0, 0]])
        self.assertEqual(track[-1], [-1, 0, 0, 0])
        p = profile(); self.assertEqual(validate_clip(clip(p), p)['fps'], 24)

    def test_other_rest_skeleton_requires_explicit_retargeting(self):
        p = profile(); c = clip(p); p['bones'][0]['tail'][0] += .01
        with self.assertRaises(ValueError): validate_clip(c, p)

    def test_wrong_tracks_nonfinite_unnormalized_and_injected_fields_fail(self):
        p = profile()
        for change in ['length', 'nan', 'norm', 'joint', 'code', 'source']:
            c = clip(p)
            if change == 'length': c['joint_rotations']['left_elbow'].pop()
            elif change == 'nan': c['root_offsets_m'][0][0] = float('nan')
            elif change == 'norm': c['joint_rotations']['left_elbow'][0] = [2, 0, 0, 0]
            elif change == 'joint': c['joint_rotations']['invented'] = [[1, 0, 0, 0]]*2
            elif change == 'code': c['python'] = 'unsupported'
            else: c['source'] = {}
            with self.subTest(change=change), self.assertRaises(ValueError): validate_clip(c, p)
