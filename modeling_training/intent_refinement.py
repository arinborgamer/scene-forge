"""Freeze a small corrective curriculum; observed tests stay regression-only."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import random

from modeling_training.intent_corpus import row
from modeling_training.intent_ops import SYSTEM, compile_intent


REFUSALS = {
    'new_geometry': [
        'There are no objects yet. Construct a new textured astronaut mesh.',
        'Sculpt an entirely new animal starting from an empty project.',
        'Model a new statue from nothing, including all of its geometry.',
        'Generate a complete original spaceship mesh in an empty scene.',
        'Build a new topology for a realistic hand; no input asset is available.',
        'Create the geometry for a brand new mountain range.',
        'Produce a new detailed building mesh rather than editing an existing asset.',
        'With no supplied objects, make a new fully modeled robot.',
    ],
    'animation': [
        'Insert keyframes for a character jumping over a fence.',
        'Create a timeline action in which this rig crawls across the floor.',
        'Key the skeleton performing a bow over twenty frames.',
        'Animate the armature doing a cartwheel in a new action.',
        'Add a keyed facial performance that changes over time.',
        'Generate a looping swimming motion for the supplied rig.',
        'Make the camera orbit using newly generated animation keyframes.',
        'Create a sequence of keyed poses for the character to sprint.',
    ],
    'simulation': [
        'Bake a physically simulated waterfall into the scene.',
        'Use fluid dynamics to simulate a river splashing over rocks.',
        'Simulate a cloth cape reacting to wind and collisions.',
        'Calculate a rigid-body collapse for a tower of stones.',
        'Run a smoke simulation with turbulence and a baked cache.',
        'Simulate fire rising from a fuel source using physics.',
        'Generate a physically simulated splash into a pool.',
        'Bake a particle dynamics simulation for falling sand.',
    ],
    'multi_step': [
        'Set lamp BeamA to 420 W and camera OpticA to 47 mm in one request.',
        'First translate object Statue by 2 cm on X, then set its roughness to 30 percent.',
        'Change lens CameraA to 62 mm, then change light LampB to 300 W.',
        'Adjust the power of LampC to 700 W and also the metallic value of BodyC to 20 percent.',
        'Move BaseA 4 mm along Y and move BaseB 3 mm along Z in the same operation.',
        'Set material MeshA roughness to 25 percent and then set CameraB to 54 mm.',
        'Change GlowA strength to 40 percent, followed by a 600 W setting on LampA.',
        'In one command, put LensB at 70 mm and KeyB at 1100 W.',
    ],
    'ambiguous': [
        'Improve whatever needs improving.',
        'Make that thing nicer somehow.',
        'Adjust the object by an unspecified amount.',
        'Move an unspecified target in some direction.',
        'Change its appearance, but I have no particular values in mind.',
        'Do the usual changes to that stuff.',
        'Please fix something in the scene.',
        'Give it a better look without any specific settings.',
    ],
}


def labeled(identifier, prompt, frame, family, split='train'):
    if frame['intent'] == 'unsupported':
        return row(identifier, split, prompt, frame, None,
                   dict(unsupported_feature=frame['feature']), family)
    op = compile_intent(frame, [frame['target']])
    if op['op'] in ('deform', 'transform'):
        facts = dict(axis=frame['axis'], mode='scale' if frame['intent'] == 'local_scale' else 'translate')
        if 'center' in frame:
            facts.update(center=frame['center'], radius=frame['radius'])
        if frame['intent'] == 'local_scale':
            facts['percent'] = frame['percent']
        else:
            facts['distance'] = op['translation']['XYZ'.index(frame['axis'])]
    else:
        facts = {k: v for k, v in op.items() if k not in ('op', 'target')}
    return row(identifier, split, prompt, frame, op, facts, family)


def additions():
    rows = []
    for kind, prompts in REFUSALS.items():
        for i, prompt in enumerate(prompts):
            rows.append(labeled(f'refine-refuse-{kind}-{i}', prompt,
                                dict(intent='unsupported', feature=kind), 'refine-refuse-'+kind))
    for i in range(24):
        name, axis = f'Anatomy_Patch_{i:02d}', 'XYZ'[i % 3]
        percent = (-1 if (i // 3) % 2 else 1) * [6, 9, 11, 14][i // 6]
        center, radius = [.02, -.02, 1.32], [.26, .19, .18]
        direction = 'decrease' if percent < 0 else 'increase'
        prompt = (f'Edit vertices of {name} within ellipsoid center {center} metres, radii {radius} metres. '
                  f'{direction.capitalize()} their distances from that center along {axis} by {abs(percent)} percent. '
                  'Use smooth falloff; preserve the other axes, outside vertices and whole-object position.')
        rows.append(labeled(f'refine-scale-{i}', prompt,
                            dict(intent='local_scale', target=name, axis=axis, percent=percent,
                                 center=center, radius=radius), 'refine-distance-scale'))
    verbs = ['Translate', 'Relocate', 'Reposition', 'Transfer']
    for i in range(24):
        name, axis = f'AssemblyPiece_{i:02d}', 'XYZ'[i % 3]
        unit_index = (i // 3) % 3
        unit, amount = ['mm', 'cm', 'm'][unit_index], [-9, 2, .03][unit_index]
        prompt = (f'{verbs[i % 4]} {name}, the entire object, by {amount:g} {unit} on {axis}. '
                  'Its orientation, size and all mesh-space vertex coordinates must stay fixed.')
        rows.append(labeled(f'refine-name-{i}', prompt,
                            dict(intent='object_translate', target=name, axis=axis, amount=amount, unit=unit),
                            'refine-imperative-name'))
    for i in range(6):
        unit = 'cm' if i % 2 else 'mm'
        amount = [42, 5.8, 68, 8.2, 36, 9.2][i]
        name = f'Optical_Camera_{i:02d}'
        rows.append(labeled(f'refine-lens-{i}',
                            f'Leave the shot framing position untouched. For camera {name}, only the lens changes: {amount:g} {unit}.',
                            dict(intent='camera_lens', target=name, amount=amount, unit=unit), 'refine-camera'))
        name = f'Canopy_Lamp_{i:02d}'
        rows.append(labeled(f'refine-power-{i}', f'The existing light is called {name}. Its output must be {360+i*70} W; leave all other controls as they were.',
                            dict(intent='light_power', target=name, amount=360+i*70, unit='W'), 'refine-power'))
        name = f'Aura_GlareNode_{i:02d}'
        rows.append(labeled(f'refine-glow-{i}', f'In the compositor, use Glare node {name}: threshold 1.1 and strength {20+i*7} percent. Retain its name and remaining settings.',
                            dict(intent='glow', target=name, threshold=1.1, strength=20+i*7, unit='percent'), 'refine-glare'))
        name = f'Shell_Surface_{i:02d}'
        rows.append(labeled(f'refine-surface-{i}', f'Material controls on mesh {name} must read roughness {20+i*8} percent and metallic {i*10} percent. Leave its color alone.',
                            dict(intent='surface', target=name, roughness=20+i*8, metallic=i*10, unit='percent'), 'refine-surface'))
    return rows


def build_training(source, seed=28401):
    rng, selected = random.Random(seed), []
    counts = dict(local_translate=16, object_translate=16, local_scale=12,
                  light_power=8, camera_lens=8, surface=8, glow=8, unsupported=4)
    for kind, count in counts.items():
        candidates = [r for r in source if r['operation']['intent'] == kind]
        if len(candidates) < count:
            raise ValueError('Replay source lacks required slice: '+kind)
        for item in rng.sample(candidates, count):
            selected.append({**item, 'id': 'replay-'+item['id'],
                             'provenance': 'Training-only replay from frozen intent v2 train split.'})
    selected += additions()
    rng.shuffle(selected)
    return selected


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--source', default='output/qwen-intent-corpus-v2')
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    source, output = Path(args.source), Path(args.output)
    manifest = json.loads((source/'manifest.json').read_text())
    for split, info in manifest['files'].items():
        if hashlib.sha256((source/(split+'.jsonl')).read_bytes()).hexdigest() != info['sha256']:
            raise ValueError('Frozen source data changed')
    if manifest['system'] != SYSTEM:
        raise ValueError('Source protocol differs')
    if manifest['compiler_sha256'] != hashlib.sha256(Path(__file__).with_name('intent_ops.py').read_bytes()).hexdigest():
        raise ValueError('Source compiler differs')
    training = build_training([json.loads(line) for line in (source/'train.jsonl').read_text().splitlines()])
    other = [json.loads(line) for split in ('validation', 'test')
             for line in (source/(split+'.jsonl')).read_text().splitlines()]
    if {r['prompt'] for r in training} & {r['prompt'] for r in other}:
        raise ValueError('Training/held-out prompt overlap')
    names = lambda rows: {r['operation']['target'] for r in rows if 'target' in r['operation']}
    if names(training) & names(other) or len({r['prompt'] for r in training}) != len(training):
        raise ValueError('Duplicate prompt or cross-split target')
    output.mkdir(parents=True, exist_ok=False)
    (output/'train.jsonl').write_text(''.join(json.dumps(r)+'\n' for r in training), encoding='utf-8')
    for split in ('validation', 'test'):
        (output/(split+'.jsonl')).write_bytes((source/(split+'.jsonl')).read_bytes())
    manifest.update(seed=28401, source_manifest_sha256=hashlib.sha256((source/'manifest.json').read_bytes()).hexdigest(),
                    source=str(source.resolve()),
                    training_slices=dict(Counter(r['operation']['intent'] for r in training)),
                    scope='Corrective existing-element language experiment. 80 replay plus 112 original authored targets; no geometry or motion learning.',
                    split_limitations='Validation/test are byte-identical v2 development regressions, already observed. No untouched-test claim. Supplemental data uses error categories, not copied failed test prompts.')
    for split in manifest['files']:
        path = output/(split+'.jsonl')
        manifest['files'][split] = dict(count=len(path.read_text().splitlines()), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (output/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    for name in ('intent_refinement.py', 'intent_ops.py', 'intent_corpus.py'):
        (output/(name+'.snapshot')).write_bytes(Path(__file__).with_name(name).read_bytes())
    print(json.dumps(dict(count=len(training), slices=manifest['training_slices'])))


if __name__ == '__main__':
    main()
