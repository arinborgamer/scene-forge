"""Versioned skeleton metadata, independent of Blender and animation generation."""
import math

MPFB_JOINTS = {
    'root': 'root', 'spine': 'spine03', 'chest': 'spine01', 'neck': 'neck01', 'head': 'head', 'jaw': 'jaw',
    'left_shoulder': 'upperarm01.L', 'left_elbow': 'lowerarm01.L', 'left_wrist': 'wrist.L',
    'right_shoulder': 'upperarm01.R', 'right_elbow': 'lowerarm01.R', 'right_wrist': 'wrist.R',
    'left_hip': 'upperleg01.L', 'left_knee': 'lowerleg01.L', 'left_ankle': 'foot.L',
    'right_hip': 'upperleg01.R', 'right_knee': 'lowerleg01.R', 'right_ankle': 'foot.R',
    'left_index': 'finger2-1.L', 'right_index': 'finger2-1.R',
}
REQUIRED_JOINTS = frozenset(MPFB_JOINTS)


def finite_vector(value, length):
    return (isinstance(value, list) and len(value) == length
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in value))


def validate_profile(profile):
    if profile.get('schema_version') != 1:
        raise ValueError('Unsupported skeleton profile version')
    units = profile.get('coordinates', {})
    scale = units.get('meters_per_unit')
    if (not isinstance(scale, (int, float)) or isinstance(scale, bool)
            or not math.isfinite(scale) or scale <= 0 or units.get('up_axis') != 'Z'
            or units.get('forward_axis') not in ('Y', '-Y')):
        raise ValueError('Explicit finite metre scale and supported axis conventions required')
    fps = profile.get('fps')
    if not isinstance(fps, (int, float)) or isinstance(fps, bool) or not math.isfinite(fps) or not 1 <= fps <= 240:
        raise ValueError('Invalid profile FPS')
    bones = profile.get('bones', [])
    if not bones or any(not isinstance(b.get('name'), str) or not b['name'] for b in bones):
        raise ValueError('Named bones are required')
    by_name = {b['name']: b for b in bones}
    if len(by_name) != len(bones):
        raise ValueError('Duplicate bone names')
    for bone in bones:
        if not finite_vector(bone.get('head'), 3) or not finite_vector(bone.get('tail'), 3):
            raise ValueError('Invalid bone endpoints')
        if math.dist(bone['head'], bone['tail']) < 1e-6:
            raise ValueError('Zero-length bone')
        matrix = bone.get('rest_matrix', [])
        if not isinstance(matrix, list) or len(matrix) != 4 or not all(finite_vector(r, 4) for r in matrix):
            raise ValueError('Invalid rest transform')
        parent = bone.get('parent')
        if parent is not None and parent not in by_name:
            raise ValueError('Unknown bone parent')
        seen = {bone['name']}
        while parent is not None:
            if parent not in by_name:
                raise ValueError('Unknown bone ancestor')
            if parent in seen:
                raise ValueError('Cyclic skeleton hierarchy')
            seen.add(parent); parent = by_name[parent].get('parent')
    joints = profile.get('joints', {})
    if not REQUIRED_JOINTS <= joints.keys():
        raise ValueError('Missing canonical joints: '+str(sorted(REQUIRED_JOINTS-joints.keys())))
    if any(name not in by_name for name in joints.values()):
        raise ValueError('Mapping references a missing bone')
    if len(set(joints.values())) != len(joints):
        raise ValueError('Canonical joints require distinct bone assignments')
    return profile


def joint_bone(profile, joint):
    validate_profile(profile)
    if joint not in profile['joints']:
        raise ValueError('Unmapped canonical joint: '+joint)
    return profile['joints'][joint]
