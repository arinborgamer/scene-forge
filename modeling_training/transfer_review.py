"""Check a declared local edit against actual saved vertex/rig evidence."""
import hashlib
import math
from pathlib import Path


def equivalent(actual, expected):
    if isinstance(expected, dict):
        return isinstance(actual, dict) and actual.keys() == expected.keys() and all(equivalent(actual[k], v) for k, v in expected.items())
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(equivalent(a, b) for a, b in zip(actual, expected))
    if isinstance(expected, (int, float)):
        return isinstance(actual, (int, float)) and not isinstance(actual, bool) and math.isclose(actual, expected, rel_tol=0, abs_tol=1e-6)
    return actual == expected


def assess(case, execution, reopened, request):
    name = case['editable']
    wanted = case['expected_operation']
    before = execution['before'][name]
    after = next(state for state in execution['states'] if state['id'] == name)
    prior, actual = before['points'], after['points']
    center, radius = wanted['center'], wanted['radius']
    predicted = []
    outside = []
    for point in prior:
        d2 = sum(((point[i]-center[i])/radius[i])**2 for i in range(3))
        weight = (1-d2)**2 if d2 < 1 else 0
        predicted.append([point[i] + weight*((point[i]-center[i])*(wanted['scale'][i]-1)
                                             + wanted['translation'][i]) for i in range(3)])
        outside.append(weight == 0)
    checks = {
        'declared_source_and_prompt': Path(request['input']).resolve() == Path(case['input']).resolve()
            and request['prompt'] == case['prompt'],
        'declared_operation_exact': equivalent(execution['plan']['operations'], [wanted]),
        'all_expected_vertices_match': len(actual) == len(predicted)
            and all(math.dist(p, q) <= 1e-6 for p, q in zip(actual, predicted)),
        'outside_region_unchanged': len(actual) == len(prior)
            and all(p == q for p, q, is_outside in zip(prior, actual, outside) if is_outside),
        'nonzero_edit': len(actual) == len(prior) and any(math.dist(p, q) > 1e-7 for p, q in zip(prior, actual)),
        'topology_preserved': before['topology_sha256'] == after['topology_sha256'],
        'skin_weights_preserved': before['weights_sha256'] == after['weights_sha256'],
        'material_names_and_colors_preserved': before['materials'] == after['materials'],
        'modifier_names_and_types_preserved': before.get('modifiers') == after.get('modifiers'),
        'object_transform_preserved': before['world_matrix'] == after['world_matrix'],
        'rig_preserved': execution['trace']['rigs_preserved'] is True,
        'no_new_objects': not execution['trace']['created'],
        'fresh_blender_reopen': reopened.get('passed') is True,
        'original_file_unchanged': hashlib.sha256(Path(request['input']).read_bytes()).hexdigest() == request['input_sha256'],
    }
    return {'passed': all(checks.values()), 'checks': checks,
            'moved_vertices': sum(math.dist(p, q) > 1e-7 for p, q in zip(prior, actual)),
            'maximum_displacement_mm': max(math.dist(p, q) for p, q in zip(prior, actual))*1000,
            'visual_quality_approved': False,
            'scope': 'A numerical edit on supplied topology and skeleton. The host adds review camera/lights to the copy; checks cover target mesh and rig, not arbitrary whole-scene preservation. No learned anatomy, rig generation or motion claim.'}
