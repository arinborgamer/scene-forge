"""Bounded organic skinning and authored performance. No learned motion model."""
import math


def smoothstep(low, high, value):
    t = max(0.0, min(1.0, (value-low)/(high-low)))
    return t*t*(3-2*t)


def skin_weights(x, z):
    """Continuous, normalized anatomical region weights in character rest space."""
    if z < 1.1:
        weights = {'root': 1.0}
    elif z < 1.65:
        t = smoothstep(1.1, 1.65, z)
        weights = {'root': 1-t, 'spine': t}
    elif z < 2.15:
        t = smoothstep(1.95, 2.15, z)
        weights = {'spine': 1-t, 'neck': t}
    elif z < 2.55:
        t = smoothstep(2.15, 2.55, z)
        weights = {'neck': 1-t, 'head': t}
    else:
        weights = {'head': 1.0}
    side = 'l' if x < 0 else 'r'
    # Below the shoulder the inner arm must follow the limb fully. A fixed wide
    # blend leaves inner upper-arm vertices on the torso, forming a web when raised.
    inner = 0.275+0.075*(1-smoothstep(1.15, 1.5, z))+0.075*smoothstep(1.65, 2.05, z)
    arm = smoothstep(inner, inner+0.065, abs(x)) * (1-smoothstep(1.94, 2.15, z))
    if arm:
        upper = smoothstep(1.36, 1.60, z)
        hand = 1-smoothstep(1.06, 1.20, z)
        limb = {'arm_'+side: upper, 'forearm_'+side: (1-upper)*(1-hand),
                'hand_'+side: (1-upper)*hand}
        weights = {k: v*(1-arm) for k, v in weights.items()}
        weights.update({k: v*arm for k, v in limb.items()})
    leg = (1-smoothstep(0.85, 1.17, z))*(1-arm)
    if leg:
        thigh = smoothstep(0.46, 0.68, z)
        foot = 1-smoothstep(0.14, 0.25, z)
        limb = {'leg_'+side: thigh, 'shin_'+side: (1-thigh)*(1-foot),
                'foot_'+side: (1-thigh)*foot}
        weights = {k: v*(1-leg) for k, v in weights.items()}
        weights.update({k: v*leg for k, v in limb.items()})
    return {k: v for k, v in weights.items() if v > 0}


def animate(rig, scene, action):
    from mathutils import Quaternion
    rig['forge_motion'] = 'authored stationary greeting' if action == 'wave' else 'authored idle'
    frames = sorted(set(range(1, scene.frame_end+1, 2)) | {scene.frame_end})
    for frame in frames:
        t = (frame-1)/scene.render.fps
        u = (frame-1)/max(1, scene.frame_end-1)
        envelope = smoothstep(0.04, 0.30, u)*(1-smoothstep(0.76, 1.0, u)) if action == 'wave' else 0
        for side in ('l', 'r'):
            sign = -1 if side == 'l' else 1
            raised = envelope if side == 'r' else 0
            for name, angle in (
                ('arm_', -sign*(0.035*math.sin(t*1.5)+1.03*raised)),
                ('forearm_', -sign*(0.08+1.55*raised)),
                ('hand_', -sign*0.28*math.sin(t*8)*raised),
            ):
                bone = rig.pose.bones[name+side]
                rest = bone.bone.matrix_local.to_quaternion()
                bone.rotation_mode = 'QUATERNION'
                bone.rotation_quaternion = rest.inverted() @ Quaternion((0, 1, 0), angle) @ rest
                bone.keyframe_insert('rotation_quaternion', frame=frame)
        head = rig.pose.bones['head']
        head.rotation_mode = 'XYZ'
        head.rotation_euler = (0.018*math.sin(t), 0.025*math.sin(t*0.7), 0.075*math.sin(t*0.75))
        head.keyframe_insert('rotation_euler', frame=frame)
        chest = rig.pose.bones['spine']
        chest.scale = (1+0.006*math.sin(t*1.8), 1+0.008*math.sin(t*1.8), 1+0.004*math.sin(t*1.8))
        chest.keyframe_insert('scale', frame=frame)
        chest.rotation_mode = 'XYZ'
        chest.rotation_euler = (0, 0.018*math.sin(t), -0.025*envelope)
        chest.keyframe_insert('rotation_euler', frame=frame)
    rig['foot_contact_note'] = 'Stationary legs and feet. No locomotion, IK or learned performance.'


def wind_leaf(obj, start, end, scene, phase=0, strength=0.07):
    """Bend a leaf about its attached base, leaving the attachment stationary."""
    from mathutils import Vector
    start, end = Vector(start), Vector(end)
    axis = end-start
    obj.shape_key_add(name='Basis')
    wind = obj.shape_key_add(name='Wind')
    wind.slider_min = -1
    for vertex, target in zip(obj.data.vertices, wind.data):
        t = max(0, min(1, (vertex.co-start).dot(axis)/axis.length_squared))
        target.co += Vector((strength*t*t, -strength*0.6*t*t, strength*0.3*t*t))
    for frame in sorted(set(range(1, scene.frame_end+1, 4)) | {scene.frame_end}):
        wind.value = math.sin((frame-1)/scene.render.fps*1.7+phase)
        wind.keyframe_insert('value', frame=frame)
    obj['forge_role'] = 'wind_foliage'
