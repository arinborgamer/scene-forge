import copy
import json
import unittest
from modeling_lab.operations import validate_plan, deform_points, loft_geometry


def plan(*steps):
    return {'title': 'generic operations', 'operations': list(steps), 'unsupported_requests': []}


class OperationTests(unittest.TestCase):
    def test_model_receives_exact_schema_and_request(self):
        from modeling_lab.operate import planner_messages
        from modeling_lab.operations import SCHEMA
        scene = {'objects': [{'id': 'existing'}], 'rigs': {}}
        messages = planner_messages('Preserve existing geometry.', scene)
        self.assertEqual(json.loads(messages[0]['content'].split('Required JSON schema:\n')[1]), SCHEMA)
        self.assertEqual(json.loads(messages[1]['content']), {'request': 'Preserve existing geometry.', 'existing_scene': scene})

    def test_arbitrary_mesh_indices_and_zero_area_checked(self):
        p = plan({'op': 'mesh', 'id': 'asset', 'vertices': [[0, 0, 0], [1, 0, 0], [0, 1, 0]], 'faces': [[0, 1, 2]]})
        validate_plan(p)
        for bad in ([0, 1, 3], [0, 1, 1]):
            q = copy.deepcopy(p)
            q['operations'][0]['faces'] = [bad]
            with self.assertRaises(ValueError):
                validate_plan(q)
        p['operations'][0]['vertices'][2] = [2, 0, 0]
        with self.assertRaisesRegex(ValueError, 'Degenerate'):
            validate_plan(p)

    def test_forward_references_code_and_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            validate_plan(plan({'op': 'duplicate', 'source': 'absent', 'id': 'new', 'translation': [0, 0, 0]}))
        with self.assertRaises(ValueError):
            validate_plan(plan({'op': 'python', 'code': 'print(1)'}))
        with self.assertRaises(ValueError):
            validate_plan(plan({'op': 'duplicate', 'source': 'a', 'id': 'a', 'translation': [0, 0, 0]}), ['a'])

    def test_local_edit_is_exactly_local_and_has_smooth_falloff(self):
        step = dict(center=[0, 0, 0], radius=[1, 1, 1], translation=[.1, 0, 0], scale=[1, 1, 1])
        points = [[0, 0, 0], [.5, 0, 0], [1, 0, 0], [1.5, 0, 0]]
        result, count = deform_points(points, step)
        self.assertEqual(count, 2)
        self.assertEqual(result[2:], points[2:])
        self.assertAlmostEqual(result[0][0], .1)
        self.assertLess(result[1][0] - points[1][0], .1)

    def test_loft_is_closed_and_changes_with_profile(self):
        rings = [dict(z=0, radius_x=.1, radius_y=.1, center_y=0),
                 dict(z=1, radius_x=.3, radius_y=.2, center_y=.1)]
        vertices, faces = loft_geometry(rings, segments=8)
        edges = {}
        for face in faces:
            for a, b in zip(face, (*face[1:], face[0])):
                key = tuple(sorted((a, b)))
                edges[key] = edges.get(key, 0) + 1
        self.assertTrue(all(n == 2 for n in edges.values()))
        self.assertEqual(len(vertices), 16)
        self.assertEqual(vertices[0][0], .1)
        self.assertEqual(vertices[8][0], .3)
        with self.assertRaises(ValueError):
            validate_plan(plan(dict(op='loft', id='x', location=[0, 0, 0], rings=list(reversed(rings)))))

    def test_nonfinite_and_modifier_budget_rejected(self):
        step = dict(op='modifier', target='x', kind='subdivide', value=3)
        with self.assertRaises(ValueError):
            validate_plan(plan(step), ['x'])
        step['value'] = float('nan')
        with self.assertRaises(ValueError):
            validate_plan(plan(step), ['x'])
        step['value'] = 1
        with self.assertRaises(ValueError):
            validate_plan(plan(step, step), ['x'])

    def test_explicit_unsupported_is_not_a_success(self):
        p = plan()
        p['unsupported_requests'] = ['learned skin texture']
        with self.assertRaisesRegex(ValueError, 'Unsupported'):
            validate_plan(p)

    def test_no_op_edits_rejected_before_blender(self):
        for step in (
            dict(op='deform', target='x', center=[0, 0, 1], radius=[.3, .3, .2],
                 translation=[0, 0, 0], scale=[1, 1, 1]),
            dict(op='transform', target='x', translation=[0, 0, 0], scale=[1, 1, 1],
                 rotation_degrees=[0, 0, 0]),
        ):
            with self.assertRaisesRegex(ValueError, 'No-op'):
                validate_plan(plan(step), ['x'])
            step['scale'][0] = 1.05
            validate_plan(plan(step), ['x'])


if __name__ == '__main__':
    unittest.main()
