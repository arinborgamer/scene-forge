"""Original language families for typed intents; no failed test text used as training."""
import argparse
import hashlib
import itertools
import json
from pathlib import Path
import random

from modeling_training.corpus import validate_example
from modeling_training.intent_ops import SYSTEM, compile_intent, validate_intent, UnsupportedIntent
from modeling_training.transfer_review import equivalent


def row(identifier, split, prompt, frame, expected, facts, family):
    existing = [frame['target']] if 'target' in frame else []
    validate_intent(frame, existing)
    if expected is None:
        try:
            compile_intent(frame, existing)
        except UnsupportedIntent:
            pass
        else:
            raise AssertionError('Refusal unexpectedly compiled')
    else:
        assert equivalent(compile_intent(frame, existing), expected)
        if expected['op'] in ('deform', 'transform'):
            validate_example(dict(operation=expected, facts=facts))
        else:
            assert {k: v for k, v in expected.items() if k not in ('op', 'target')} == facts
    return dict(id=identifier, split=split, prompt=prompt, operation=frame,
                expected_operation=expected, facts=facts, language_family=family,
                provenance='Original authored synthetic intent; compiler and final action both checked. No external teacher outputs.')


def movement(split, rng):
    result = []
    variants = range(8) if split == 'train' else range(2 if split == 'test' else 1)
    combos = list(itertools.product(range(3), range(3), variants))
    if split == 'validation':
        combos = [(i % 3, (i // 3 + i) % 3, 0) for i in range(6)]
    for i, (axis, unit_index, variant) in enumerate(combos):
        name = f'{split}_mesh_{i:03d}'
        sign = -1 if (axis + unit_index + variant) % 2 else 1
        centimeters = sign*rng.choice([.5, 1, 1.25, 2, 2.5, 3, 4] if split == 'train' else [.75, 1.5, 2.25, 3.5])
        unit = ['m', 'cm', 'mm'][unit_index]
        amount = centimeters / 100 if unit == 'm' else centimeters if unit == 'cm' else centimeters*10
        amount_text = f'{amount:g} '+{'m': 'metres', 'cm': 'centimetres', 'mm': 'millimetres'}[unit]
        center = [rng.choice([-.03, .01, .05]), -.01, rng.choice([1.08, 1.24, 1.36])]
        radius = [.27, .21, .17]
        region = f'ellipsoid centered at {center} metres, radii {radius} metres'
        letter = 'XYZ'[axis]
        delta = [0, 0, 0]; delta[axis] = centimeters/100
        for local in [True, False]:
            if local:
                frame = dict(intent='local_translate', target=name, axis=letter, amount=amount, unit=unit, center=center, radius=radius)
                expected = dict(op='deform', target=name, center=center, radius=radius, translation=delta, scale=[1, 1, 1])
                facts = dict(axis=letter, distance=centimeters/100, mode='translate', center=center, radius=radius)
                train = [
                    f'The placement of object {name} is locked. Shift its vertices inside the {region} {amount_text} along {letter}; smooth falloff, no scaling or outside edits.',
                    f'Object {name} keeps its transform. Apply {amount_text} on {letter} to only the vertex patch in the {region}, with smooth falloff. All other vertices stay unchanged.',
                    f'Translate the selected vertices of mesh {name}: {region}, {letter} displacement {amount_text}. Keep the whole-object placement fixed and scale unchanged.',
                    f'For {name}, do a local vertex edit inside the {region}. Offset {amount_text} on {letter} with smooth falloff, preserving object position and everything outside.',
                    f'Keep {name} as an object stationary. Only its vertices in the {region} receive a {amount_text} {letter} movement. Preserve outside coordinates and do not scale.',
                    f'Geometry change on {name}, not a placement change: vertices in the {region} move {amount_text} along {letter} with smooth falloff; no scaling.',
                    f'Preserve the object coordinates of {name}. Within the {region}, deform the mesh by a {letter} translation of {amount_text}. No rotation, scale or outside changes.',
                    f'Move a patch of {name}, leaving the object itself where it is: {region}, {amount_text} on {letter}, smooth falloff. Keep all scaling at one.',
                ]
                test = [
                    f'Please leave {name} where it is in the scene. In its mesh, offset just the vertices bounded by the {region} {amount_text} along {letter}, fading smoothly to zero at the boundary. Keep scaling and every outside vertex intact.',
                    f'We are adjusting the shape of {name}, not its placement. Add {amount_text} to the {letter} coordinates of the vertex patch in the {region} with smooth falloff; leave object position, scale and all other vertices alone.',
                ]
                validation = f'Keep the object transform of {name}. Give mesh vertices in the {region} a smooth displacement of {amount_text} on {letter}. Other vertices and scale are untouched.'
            else:
                frame = dict(intent='object_translate', target=name, axis=letter, amount=amount, unit=unit)
                expected = dict(op='transform', target=name, translation=delta, scale=[1, 1, 1], rotation_degrees=[0, 0, 0])
                facts = dict(axis=letter, distance=centimeters/100)
                train = [
                    f'The vertex coordinates inside mesh {name} must remain fixed. Shift the entire object {amount_text} along {letter}, preserving rotation and scale.',
                    f'Preserve all local vertices of {name} and relocate the whole object {amount_text} on {letter}. No resizing or turning.',
                    f'Change only the object position of {name}, by {amount_text} on {letter}; keep its mesh, orientation and scale untouched.',
                    f'For {name}, do a whole-object translation of {amount_text} along {letter}. Its vertex coordinates remain exactly the same in local space.',
                    f'Move {name} as a rigid object {amount_text} on {letter}, without modifying any individual vertex or changing the scale or orientation.',
                    f'Placement change on {name}, not a geometry change: move the entire object {amount_text} along {letter}. Keep its mesh and rotation unchanged.',
                    f'Keep the geometry of {name} intact. Set a {letter} object displacement of {amount_text}; no mesh editing, rotation or resizing.',
                    f'Relocate the complete mesh object {name} {amount_text} on {letter}. All vertices retain their local positions, and scale and rotation stay unchanged.',
                ]
                test = [
                    f'Please leave the vertex data of {name} alone. Reposition the complete scene object {amount_text} along {letter}, retaining its dimensions, orientation and all other location coordinates.',
                    f'We are adjusting the placement of {name}, not its shape. Add an offset of {amount_text} in {letter} to the whole object; its local vertices, rotation and scale must remain intact.',
                ]
                validation = f'Keep local geometry unchanged on {name}, but move its whole object {amount_text} on {letter}. Preserve scale and orientation.'
            prompt = train[variant] if split == 'train' else test[variant] if split == 'test' else validation
            result.append(row(f'{split}-intent-move-{i:03d}-{"local" if local else "whole"}', split, prompt, frame, expected, facts,
                              f'{split}-movement-form-{variant}'))
    return result


def scaling(split, rng):
    result = []
    count = 36 if split == 'train' else 6
    for i in range(count):
        axis = i % 3; letter = 'XYZ'[axis]; name = f'{split}_shape_{i:03d}'
        percent = rng.choice([-15, -10, -5, 5, 8, 10, 15, 20]) if split == 'train' else (7 if i < 3 else -12)
        center = [.01, -.01, rng.choice([1.1, 1.25, 1.4])]; radius = [.28, .22, .16]
        region = f'center {center} metres and ellipsoid radii {radius} metres'
        frame = dict(intent='local_scale', target=name, axis=letter, percent=percent, center=center, radius=radius)
        scale = [1, 1, 1]; scale[axis] = round(1+percent/100, 4)
        expected = dict(op='deform', target=name, center=center, radius=radius, translation=[0, 0, 0], scale=scale)
        facts = dict(axis=letter, center=center, radius=radius, mode='scale', percent=percent)
        verb = 'Increase' if percent > 0 else 'Reduce'
        templates = [
            f'{verb} the local {letter} extent of {name} by {abs(percent)} percent, using {region}. Keep object placement and all outside vertices unchanged.',
            f'Object {name} stays fixed. In the region with {region}, change the {letter} extent of the mesh vertices by {percent:+g} percent with smooth falloff. No translation.',
            f'Apply {percent:+g} percent scaling on {letter} to vertices of {name} within {region}; leave other axes, outside vertices and object transforms fixed.',
            f'Keep {name} in position and alter only local geometry: {verb.lower()} its {letter} size by {abs(percent)} percent inside {region}. Smooth falloff; no translation.',
        ]
        prompt = templates[(i//3) % len(templates)]
        if split != 'train':
            prompt = f'The object {name} does not move. Within {region}, {verb.lower()} distances from the center on {letter} by {abs(percent)} percent with smooth falloff. Preserve other coordinates and vertices beyond the region.'
        result.append(row(f'{split}-intent-scale-{i:03d}', split, prompt, frame, expected, facts, f'{split}-scale'))
    return result


def controls(split, rng):
    result = []
    per = {'train': 16, 'validation': 1, 'test': 2}[split]
    for family in ['light_power', 'camera_lens', 'surface', 'glow']:
        for i in range(per):
            name = f'{split}_{family}_{i:03d}'
            variant = (i//2) % 3
            if family == 'light_power':
                watts = rng.choice([125, 250, 375, 500, 625, 750, 1250, 1500])
                unit = 'kW' if i % 2 else 'W'; value = watts/1000 if unit == 'kW' else watts
                frame = dict(intent=family, target=name, amount=value, unit=unit)
                expected = dict(op=family, target=name, watts=watts)
                texts = [f'Use {value:g} {unit} on area light {name}.', f'Area-light power for {name}: {value:g} {unit}. Keep its position and color.', f'Change only the output power of light {name} to {value:g} {unit}.']
                test = f'Leave the illumination color alone and set the existing area lamp called {name} to an output of {value:g} {unit}.'
            elif family == 'camera_lens':
                mm = rng.choice([28, 32, 40, 45, 55, 65, 75, 85, 95])
                unit = 'cm' if i % 2 else 'mm'; value = mm/10 if unit == 'cm' else mm
                frame = dict(intent=family, target=name, amount=value, unit=unit)
                expected = dict(op=family, target=name, millimeters=mm)
                texts = [f'Set existing camera {name} to a focal length of {value:g} {unit}.', f'Keep camera {name} still; its lens should be {value:g} {unit}.', f'Change only focal length on {name}, the camera, to {value:g} {unit}.']
                test = f'The named camera is {name}. Without moving it, use a focal length specified as {value:g} {unit}.'
            else:
                unit = 'percent' if i % 2 else 'fraction'
                factor = 100 if unit == 'percent' else 1
                if family == 'surface':
                    rough, metal = rng.choice([.15, .25, .35, .45, .55, .65, .75, .85]), rng.choice([0, .2, .4, .6, .8, 1])
                    frame = dict(intent=family, target=name, roughness=round(rough*factor, 4), metallic=round(metal*factor, 4), unit=unit)
                    expected = dict(op=family, target=name, roughness=rough, metallic=metal)
                    text = f'roughness {rough*factor:g} and metallic {metal*factor:g}, both expressed as {unit} values'
                    texts = [f'Set the existing material of {name} to {text}.', f'On mesh {name}, use {text}; keep its color.', f'Mesh surface {name}: {text}, preserving its other material settings.']
                    test = f'For the material already assigned to {name}, retain the color and use {text}.'
                else:
                    strength, threshold = rng.choice([.15, .25, .35, .45, .55, .65, .75, .85]), rng.choice([.4, .6, .8, 1.2, 1.4, 1.6])
                    frame = dict(intent=family, target=name, threshold=threshold, strength=round(strength*factor, 4), unit=unit)
                    expected = dict(op=family, target=name, threshold=threshold, strength=strength)
                    text = f'threshold {threshold:g} and strength {strength*factor:g} as a {unit} value'
                    texts = [f'Existing compositor glare node {name}: {text}.', f'Adjust the glow node called {name} to {text}.', f'For compositor glare {name}, use {text}, changing nothing else.']
                    test = f'The existing Glare effect is named {name}; retain its other controls but apply {text}.'
            facts = {k: v for k, v in expected.items() if k not in ('op', 'target')}
            result.append(row(f'{split}-intent-{family}-{i:03d}', split,
                              texts[variant] if split == 'train' else test, frame, expected, facts, f'{split}-control-{variant}'))
    return result


REFUSALS = {
    'train': [
        ('new_geometry', 'Generate a new detailed human mesh from scratch.'),
        ('new_geometry', 'Create a new sculpted dragon with complete topology.'),
        ('new_geometry', 'Build a new car model; there is no supplied mesh.'),
        ('animation', 'Animate the supplied character walking for five seconds.'),
        ('animation', 'Generate a dancing performance with keyframes.'),
        ('animation', 'Add a new waving animation to this rig.'),
        ('simulation', 'Run a physically simulated ocean wave.'),
        ('simulation', 'Simulate smoke moving around the character.'),
        ('simulation', 'Create a fluid simulation that pours into a cup.'),
        ('multi_step', 'Set camera MainLens to 50 mm, then set light MainKey to 500 W.'),
        ('ambiguous', 'Make it look much better.'),
        ('ambiguous', 'Move the thing a little.'),
    ],
    'validation': [('new_geometry', 'Make an entirely new creature asset.'), ('animation', 'Add a new running action.'),
                   ('simulation', 'Bake a cloth simulation.'), ('ambiguous', 'Fix this.')],
    'test': [('new_geometry', 'Invent a fresh, fully modeled realistic head without a supplied asset.'),
             ('animation', 'Keyframe a character sitting and looking around.'),
             ('simulation', 'Calculate an explosion using fluid dynamics.'),
             ('multi_step', 'Change LampA to 600 watts and also change LensA to 60 mm in the same operation.'),
             ('ambiguous', 'Change that until it seems right.'),
             ('ambiguous', 'Shift something over there.')],
}


def build(split, seed):
    rng = random.Random(seed)
    items = movement(split, rng)+scaling(split, rng)+controls(split, rng)
    for i, (feature, prompt) in enumerate(REFUSALS[split]):
        items.append(row(f'{split}-intent-refuse-{i:03d}', split, prompt,
                         dict(intent='unsupported', feature=feature), None,
                         dict(unsupported_feature=feature), split+'-refusal'))
    rng.shuffle(items)
    return items


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True)
    parser.add_argument('--seed', type=int, default=28201)
    args = parser.parse_args()
    values = {s: build(s, args.seed+i) for i, s in enumerate(['train', 'validation', 'test'])}
    prompts = [r['prompt'] for rows in values.values() for r in rows]
    assert len(prompts) == len(set(prompts))
    names = [{r['operation']['target'] for r in rows if 'target' in r['operation']} for rows in values.values()]
    assert all(not names[i] & names[j] for i in range(3) for j in range(i+1, 3))
    out = Path(args.output); out.mkdir(parents=True, exist_ok=False)
    compiler = Path(__file__).with_name('intent_ops.py')
    manifest = dict(profile='intent', seed=args.seed, system=SYSTEM, compiler_sha256=hashlib.sha256(compiler.read_bytes()).hexdigest(), files={},
                    scope='Typed existing-element intent, deterministic units, local/whole scope and explicit refusals. No learned geometry or motion.',
                    split_limitations='Separate sentence families, names and numerical tuples, but synthetic operation families and source generator are shared. Earlier observed suites are regression cases.',
                    license_note='Original synthetic authored data, no movie imagery, teacher model outputs or downloaded asset data.')
    for split, rows in values.items():
        p = out/(split+'.jsonl'); p.write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf-8')
        manifest['files'][split] = dict(count=len(rows), sha256=hashlib.sha256(p.read_bytes()).hexdigest())
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest['files']))


if __name__ == '__main__':
    main()
