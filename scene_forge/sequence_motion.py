"""Bake supported timed actions into editable Blender curves; no learned motion."""
import json
import math

from .sequences import frame_windows


def smooth(t):
    return t*t*(3-2*t)


def camera_head_rotation(rig, scene):
    head = rig.pose.bones['head']
    scene.view_layers[0].update()
    origin = rig.matrix_world @ head.head
    direction = scene.camera.matrix_world.translation - origin
    if direction.length < 0.001:
        raise ValueError('Camera overlaps the head; a look direction cannot be determined')
    world_aim = direction.to_track_quat('X', 'Z')
    rest = head.bone.matrix_local.to_quaternion()
    return rest.inverted() @ rig.matrix_world.to_quaternion().inverted() @ world_aim @ rest


def animate_sequence(rig, item, spec, scene):
    from mathutils import Quaternion, Vector
    position = Vector(item['start'])
    heading = 0.0
    head_rotation = Quaternion()
    head = rig.pose.bones['head']
    head.rotation_mode = 'QUATERNION'
    rig.rotation_mode = 'XYZ'
    for index, (start, end, step) in enumerate(frame_windows(item['sequence'], spec['duration_seconds'], scene.frame_end)):
        action = step['action']
        scene.timeline_markers.new(f"{item['id']} / {index+1}: {action}", frame=start)
        target = Vector(step['target']) if action == 'walk' else position.copy()
        delta = target-position
        destination_heading = math.atan2(delta.y, delta.x) if action == 'walk' else heading
        turn = (destination_heading-heading+math.pi) % math.tau-math.pi
        head_start = head_rotation.copy()
        for frame in range(start, end+1):
            scene.frame_set(frame)
            u = (frame-start)/max(1, end-start)
            travel = smooth(u)
            rig.location = position.lerp(target, travel)
            rig.rotation_euler.z = heading+turn*smooth(min(1, u*4))
            phase = travel*max(1, round(delta.length/0.9))*math.tau
            amplitude = math.sin(math.pi*min(1, u*8)/2)*math.sin(math.pi*min(1, (1-u)*8)/2) if action == 'walk' else 0
            rig.location.z = 0.045*abs(math.sin(phase))*amplitude
            rig.keyframe_insert('location', frame=frame)
            rig.keyframe_insert('rotation_euler', frame=frame)
            angles = {'leg_l': .38*math.sin(phase)*amplitude, 'leg_r': -.38*math.sin(phase)*amplitude,
                      'arm_l': -.3*math.sin(phase)*amplitude, 'arm_r': .3*math.sin(phase)*amplitude}
            for name, angle in angles.items():
                bone = rig.pose.bones[name]
                rest = bone.bone.matrix_local.to_quaternion()
                rotation = Quaternion((0, 1, 0), angle)
                if name == 'arm_r' and action == 'wave':
                    envelope = smooth(min(1, u*4))*smooth(min(1, (1-u)*4))
                    rotation = Quaternion((1, 0, 0), (-2.3+.22*math.sin(u*step['duration_seconds']*8))*envelope)
                bone.rotation_mode = 'QUATERNION'
                bone.rotation_quaternion = rest.inverted() @ rotation @ rest
                bone.keyframe_insert('rotation_quaternion', frame=frame)
            if action == 'look_at_camera':
                head_rotation = head_start.slerp(camera_head_rotation(rig, scene), travel)
            head.rotation_quaternion = head_rotation
            head.keyframe_insert('rotation_quaternion', frame=frame)
        position = target
        heading += turn
    rig['forge_motion'] = 'procedural timed action sequence'
    rig['forge_sequence'] = json.dumps(item['sequence'])
    rig['forge_motion_limits'] = 'No contact IK, anatomical head limits, sitting or learned performance.'


def inspect_sequence(rig, item, spec, scene):
    """Measure baked scene behavior, independently of model-written descriptions."""
    from mathutils import Vector
    checks = []
    position = Vector(item['start'])
    for index, (start, end, step) in enumerate(frame_windows(item['sequence'], spec['duration_seconds'], scene.frame_end)):
        scene.frame_set(start)
        actual_start = rig.location.copy()
        initial_heading = rig.rotation_euler.copy()
        scene.frame_set(end)
        actual_end = rig.location.copy()
        target = Vector(step['target']) if step['action'] == 'walk' else position
        passed = (actual_start-position).length < .01 and (actual_end-target).length < .01
        detail = 'Start/end positions match this action'
        if step['action'] != 'walk':
            drift = 0.0
            rotation_drift = 0.0
            for frame in range(start, end+1):
                scene.frame_set(frame)
                drift = max(drift, (rig.location-position).length)
                rotation_drift = max(rotation_drift, max(abs(a-b) for a, b in zip(rig.rotation_euler, initial_heading)))
            passed = passed and drift < .01 and rotation_drift < .01
            detail += f'; stationary drift={drift:.6f}m'
        if step['action'] == 'walk':
            scene.frame_set((start+end)//2)
            progressed = (rig.location-position).length > .001 and (rig.location-target).length > .001
            passed = passed and progressed
            detail += '; sampled intermediate movement'
        if step['action'] in ('walk', 'wave'):
            name = 'leg_l' if step['action'] == 'walk' else 'arm_r'
            motion = 0.0
            for frame in range(start, end+1):
                scene.frame_set(frame)
                motion = max(motion, abs(rig.pose.bones[name].rotation_quaternion.angle))
            passed = passed and motion > (.01 if step['action'] == 'walk' else .5)
            detail += f'; {name} peak rotation={motion:.3f} radians'
        if step['action'] == 'look_at_camera':
            scene.frame_set(end)
            scene.view_layers[0].update()
            head = rig.pose.bones['head']
            transform = rig.matrix_world @ head.matrix @ head.bone.matrix_local.inverted()
            forward = (transform.to_3x3() @ Vector((1, 0, 0))).normalized()
            desired = (scene.camera.matrix_world.translation-rig.matrix_world @ head.head).normalized()
            error = math.degrees(forward.angle(desired))
            passed = passed and error < 2
            detail += f'; head/camera angular error={error:.3f} degrees'
        checks.append({'name': f'sequence:{rig.name}:{index+1}:{step["action"]}', 'passed': bool(passed), 'detail': detail})
        position = target.copy()
    return checks
