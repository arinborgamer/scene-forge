"""Timed motion programs, shared by validation and the Blender executor."""
import math


def frame_windows(steps, duration, last_frame):
    elapsed = 0.0
    start = 1
    for step in steps:
        elapsed += step['duration_seconds']
        end = 1 + round(elapsed / duration * (last_frame - 1))
        yield start, end, step
        start = end


def validate_sequence(actor, scene):
    steps = actor.get('sequence')
    if actor['action'] != 'sequence':
        if steps is not None:
            raise ValueError('Only action=sequence may contain sequence steps')
        return
    if scene['schema_version'] != 2 or scene['style'] == 'organic':
        raise ValueError('Sequences require schema_version=2 and blocky or low_poly style')
    if not steps:
        raise ValueError('Sequence actors require a nonempty sequence')
    if not math.isclose(sum(s['duration_seconds'] for s in steps), scene['duration_seconds'], abs_tol=1e-6):
        raise ValueError('Sequence durations must sum to scene duration_seconds')
    position = actor['start']
    last_frame = round(scene['duration_seconds'] * scene['fps'])
    for start, end, step in frame_windows(steps, scene['duration_seconds'], last_frame):
        if step['action'] == 'walk':
            target = step.get('target')
            if target is None or target[2] != 0:
                raise ValueError('Every walk step needs a target on ground Z=0')
            distance = math.dist(position, target)
            if distance < 0.01:
                raise ValueError('Walk steps need different start and target positions')
            # Smoothstep has a peak derivative of 1.5. Bound peak, not just average speed.
            seconds = (end-start) / scene['fps']
            if 1.5 * distance > seconds * 2:
                raise ValueError('Sequence walk peak speed exceeds 2 m/s')
            position = target
        elif 'target' in step:
            raise ValueError('Only walk steps accept target; look_at_camera targets the scene camera')
    if math.dist(position, actor['end']) > 0.001:
        raise ValueError('Actor end must match the final walk target, or start if there is no walk')
