"""Exercise composed actions in Blender; assert evaluated motion, then detect corruption."""
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent/'tests'))

import bpy
from test_sequences import sequence_scene
from scene_forge.schema import validate_scene
from scene_forge.blender_scene import build, inspect_scene
from scene_forge.sequence_motion import inspect_sequence
from scene_forge.sequences import frame_windows

for variant in ('walk_hold_look', 'wave_walk_look_walk', 'two_actors'):
    spec = sequence_scene()
    if variant == 'wave_walk_look_walk':
        spec.update(duration_seconds=8, camera='orbit')
        spec['actors'][0].update(end=[0, 1, 0], sequence=[
            {'action': 'wave', 'duration_seconds': 1.5},
            {'action': 'walk', 'duration_seconds': 3, 'target': [0, 0, 0]},
            {'action': 'look_at_camera', 'duration_seconds': 1.5},
            {'action': 'walk', 'duration_seconds': 2, 'target': [0, 1, 0]},
        ])
    if variant == 'two_actors':
        import copy
        second = copy.deepcopy(spec['actors'][0])
        second.update(id='friend', start=[-2, 1.5, 0], end=[0, 1.5, 0])
        second['sequence'][0]['target'] = [0, 1.5, 0]
        spec['actors'].append(second)
    validate_scene(spec)
    scene, rigs = build(spec)
    report = inspect_scene(spec, scene, rigs)
    assert report['passed'], report
    rig = rigs[0]
    item = spec['actors'][0]
    for start, end, step in frame_windows(item['sequence'], spec['duration_seconds'], scene.frame_end):
        if step['action'] == 'walk':
            scene.frame_set(start+max(1, (end-start)//5))
            assert abs(rig.pose.bones['leg_l'].rotation_quaternion.angle) > .01
        if step['action'] == 'wave':
            scene.frame_set((start+end)//2)
            assert abs(rig.pose.bones['arm_r'].rotation_quaternion.angle) > 1
    assert any(m.name.endswith('look_at_camera') for m in scene.timeline_markers)
    # Deleting head animation must make endpoint aim validation fail.
    action = rig.animation_data.action
    for layer in action.layers:
        for strip in layer.strips:
            for bag in strip.channelbags:
                for curve in list(bag.fcurves):
                    if 'pose.bones["head"]' in curve.data_path:
                        bag.fcurves.remove(curve)
    rig.pose.bones['head'].rotation_quaternion.identity()
    checks = inspect_sequence(rig, item, spec, scene)
    assert any(not check['passed'] for check in checks if 'look_at_camera' in check['name']), checks
    print('SEQUENCE_PASS', variant, len(report['checks']))
print('SEQUENCES_BLENDER_PASS')
