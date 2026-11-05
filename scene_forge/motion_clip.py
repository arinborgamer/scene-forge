"""Provider-neutral compatible-rig motion data. No generation or retargeting."""
import hashlib
import json
import math
import re

from scene_forge.rig_profile import validate_profile, finite_vector


def skeleton_signature(profile):
    validate_profile(profile)
    contract = dict(bones=sorted(profile['bones'], key=lambda b: b['name']), joints=profile['joints'],
                    coordinates={k: profile['coordinates'][k] for k in ('meters_per_unit', 'up_axis', 'forward_axis')})
    return hashlib.sha256(json.dumps(contract, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def continuous_quaternions(track):
    """Equivalent unit-quaternion/hemisphere representation, not a motion repair."""
    result = []
    for value in track:
        if not finite_vector(value, 4):
            raise ValueError('Quaternions must contain four finite numbers in WXYZ order')
        norm = math.sqrt(sum(v*v for v in value))
        if abs(norm-1) > 1e-4:
            raise ValueError('Non-unit quaternion; no silent pose correction')
        q = [v/norm for v in value]
        if result and sum(a*b for a, b in zip(result[-1], q)) < 0:
            q = [-v for v in q]
        result.append(q)
    return result


def validate_clip(clip, profile):
    validate_profile(profile)
    fields = {'schema_version', 'skeleton_signature', 'fps', 'start_frame', 'root_offsets_m', 'joint_rotations', 'source'}
    if not isinstance(clip, dict) or clip.keys() != fields or clip['schema_version'] != 1:
        raise ValueError('Unknown motion-clip fields or version')
    if clip['skeleton_signature'] != skeleton_signature(profile):
        raise ValueError('Motion rest skeleton does not match; explicit retargeting is required')
    fps, start = clip['fps'], clip['start_frame']
    if not isinstance(fps, int) or isinstance(fps, bool) or not 1 <= fps <= 120:
        raise ValueError('Invalid motion FPS')
    if not isinstance(start, int) or isinstance(start, bool) or not 1 <= start <= 100000:
        raise ValueError('Invalid first frame')
    root = clip['root_offsets_m']
    if not isinstance(root, list) or not 2 <= len(root) <= 601 or (len(root)-1)/fps > 20:
        raise ValueError('Motion must contain 2–601 samples and at most 20 seconds')
    if any(not finite_vector(v, 3) or max(abs(x) for x in v) > 100 for v in root):
        raise ValueError('Invalid world root displacement in metres')
    tracks = clip['joint_rotations']
    if not isinstance(tracks, dict) or not tracks.keys() <= profile['joints'].keys():
        raise ValueError('Unknown canonical motion joints')
    for track in tracks.values():
        if not isinstance(track, list) or len(track) != len(root):
            raise ValueError('All tracks require the same sample count')
        continuous_quaternions(track)
    source = clip['source']
    if (not isinstance(source, dict) or source.keys() != {'declared_kind', 'id'}
            or source['declared_kind'] not in ('authored_fixture', 'imported_capture', 'model_output')
            or not isinstance(source['id'], str) or not re.fullmatch(r'[A-Za-z0-9_. -]{1,100}', source['id'])):
        raise ValueError('Explicit declarative source provenance is required')
    return clip
