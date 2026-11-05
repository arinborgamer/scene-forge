"""Independent prompt-specific acceptance checks on saved execution evidence.

These expectations are not sent to the planner. A passed structural build can fail here.
"""
import argparse
import json
import math
from pathlib import Path


def width(state, axis):
    return state['world_max'][axis] - state['world_min'][axis]


def near(a, b, tolerance=1e-5):
    return abs(a-b) <= tolerance


def evaluate(case, result):
    states = {s['id']: s for s in result['states']}
    before = result['before']
    checks = {}
    operations = result['plan']['operations']
    if case == 'bust':
        required = {'head_shell', 'eye_left', 'eye_right', 'neck', 'shoulders', 'badge'}
        checks['required_parts_exist'] = required <= states.keys()
        checks['head_profile_from_Qwen'] = any(op['op'] == 'loft' and op['id'] == 'head_shell' for op in operations)
        checks['badge_explicit_mesh_from_Qwen'] = any(op['op'] == 'mesh' and op['id'] == 'badge' for op in operations)
        if required <= states.keys():
            head = states['head_shell']
            zmin, zmax = head['local_min'][2], head['local_max'][2]
            bottom = [p[0] for p in head['points'] if p[2] <= zmin + (zmax-zmin)*.20]
            upper = [p[0] for p in head['points'] if p[2] >= zmin + (zmax-zmin)*.45]
            checks['tapered_jaw_in_actual_mesh'] = bool(bottom and upper and max(bottom)-min(bottom) < .9*(max(upper)-min(upper)))
            total_height = max(s['world_max'][2] for s in states.values()) - min(s['world_min'][2] for s in states.values())
            checks['requested_scale'] = .5 <= total_height <= .9
            checks['neck_narrower_than_head'] = width(states['neck'], 0) < width(head, 0)
            checks['shoulders_broader_than_head'] = width(states['shoulders'], 0) > width(head, 0)
            left, right = states['eye_left'], states['eye_right']
            checks['eyes_separated_across_x'] = left['world_min'][0] > right['world_max'][0] or right['world_min'][0] > left['world_max'][0]
            checks['eyes_on_front_half'] = all(s['location'][1] < head['location'][1] for s in (left, right))
            checks['cyan_eye_materials'] = all(s['materials'] and s['materials'][0]['color'][0] < .35 and s['materials'][0]['color'][1] > .6 and s['materials'][0]['color'][2] > .6 for s in (left, right))
    elif case == 'revision':
        required = {'head_shell', 'eye_left', 'eye_right', 'neck', 'shoulders', 'badge'}
        checks['no_new_objects'] = not result['trace']['created']
        checks['required_parts_exist'] = required <= states.keys() and required <= before.keys()
        if checks['required_parts_exist']:
            shoulders = states['shoulders']
            old = before['shoulders']
            checks['shoulder_scale_x_20_percent'] = near(shoulders['scale'][0], old['scale'][0]*1.2)
            checks['shoulder_yz_unchanged'] = shoulders['scale'][1:] == old['scale'][1:] and shoulders['mesh_sha256'] == old['mesh_sha256']
            for name in ('eye_left', 'eye_right'):
                s, b = states[name], before[name]
                checks[name+'_forward_2cm'] = near(s['location'][1], b['location'][1]-.02) and near(s['location'][0], b['location'][0]) and near(s['location'][2], b['location'][2])
                checks[name+'_orange'] = bool(s['materials'] and all(near(a, b) for a, b in zip(s['materials'][0]['color'], [1, 136/255, 0, 1])))
                checks[name+'_shape_preserved'] = s['mesh_sha256'] == b['mesh_sha256']
            keys = ('mesh_sha256', 'world_matrix', 'materials', 'modifiers', 'weights_sha256')
            checks['unmentioned_parts_unchanged'] = all(all(states[name][k] == before[name][k] for k in keys) for name in ('head_shell', 'neck', 'badge'))
    elif case == 'humanoid_edit':
        name = 'Humanoid_Trained_Shape'
        checks['no_new_objects'] = not result['trace']['created']
        checks['body_present'] = name in states and name in before
        if checks['body_present']:
            s, b = states[name], before[name]
            changes = [(p, math.dist(p, q)) for p, q in zip(b['points'], s['points'])]
            outside = [d for p, d in changes if abs(p[0]) > .350001 or p[2] < 1.149999 or p[2] > 1.500001]
            checks['actual_local_edit'] = sum(d > 1e-7 for _, d in changes) >= 20
            checks['outside_region_unchanged'] = all(d == 0 for d in outside)
            checks['subtle_under_2cm'] = max(d for _, d in changes) < .02
            checks['only_x_changed'] = all(p[1:] == q[1:] for p, q in zip(b['points'], s['points']))
            checks['topology_preserved'] = b['topology_sha256'] == s['topology_sha256']
            checks['weights_preserved'] = b['weights_sha256'] == s['weights_sha256']
            checks['material_preserved'] = b['materials'] == s['materials']
            checks['object_transform_preserved'] = b['world_matrix'] == s['world_matrix']
            checks['rig_preserved'] = result['trace']['rigs_preserved']
            # The requested broadening should move most changed points outward, not inward.
            checks['broadening_direction'] = all(abs(q[0]) >= abs(p[0])-1e-7 for p, q in zip(b['points'], s['points']))
    else:
        raise ValueError('Unknown evaluation case')
    return {'case': case, 'passed': all(checks.values()), 'checks': checks,
            'visual_quality_approved': False, 'scope': 'Specific numerical request checks, not a general semantic or artistic judge'}


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--case', choices=['bust', 'revision', 'humanoid_edit'], required=True)
    p.add_argument('--job', required=True)
    args = p.parse_args()
    job = Path(args.job)
    report = evaluate(args.case, json.loads((job/'scene/execution.json').read_text()))
    with (job/'acceptance.json').open('x') as file:
        json.dump(report, file, indent=2)
    print(json.dumps(report, indent=2))
