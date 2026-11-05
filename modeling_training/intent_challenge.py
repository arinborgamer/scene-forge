"""New authored language suite, frozen before refinement training begins."""
import argparse
import hashlib
import json
from pathlib import Path

from modeling_training.intent_ops import SYSTEM
from modeling_training.intent_refinement import labeled


def build():
    rows = []
    center, radius = [.02, 0, 1.21], [.24, .18, .13]
    region = f'ellipsoid centered at {center} metres with radii {radius} metres'
    for i, (axis, amount, unit) in enumerate([('X', 1.75, 'cm'), ('Y', -6, 'mm'), ('Z', .0125, 'm')]):
        name = f'CopperFigure{i}'
        rows.append(labeled(f'challenge-local-{i}',
                    f'For {name}, translate just the patch of vertices in the {region}. The displacement is {amount:g} {unit} on {axis}. Use smooth falloff and leave object placement fixed.',
                    dict(intent='local_translate', target=name, axis=axis, amount=amount, unit=unit,
                         center=center, radius=radius), 'challenge-patch', 'test'))
        name = f'GalleryPiece{i}'
        rows.append(labeled(f'challenge-whole-{i}',
                    f'At object level, offset {name} along {axis} by {amount:g} {unit}. Keep its mesh-space coordinates, size and orientation unchanged.',
                    dict(intent='object_translate', target=name, axis=axis, amount=amount, unit=unit),
                    'challenge-placement', 'test'))
    for i, (axis, percent) in enumerate([('X', -4), ('Y', -13), ('Z', 17)]):
        name = f'CeramicBody{i}'
        verb = 'Contract' if percent < 0 else 'Expand'
        rows.append(labeled(f'challenge-scale-{i}',
                    f'{verb} the {axis} extent of the vertex patch on {name} by {abs(percent)} percent, measured from the center of the {region}. Smooth falloff; no object movement or changes outside that region.',
                    dict(intent='local_scale', target=name, axis=axis, percent=percent,
                         center=center, radius=radius), 'challenge-extent', 'test'))
    controls = [
        ('Use 4.6 cm as the lens focal length of camera PortraitOptic. Retain its position.',
         dict(intent='camera_lens', target='PortraitOptic', amount=4.6, unit='cm')),
        ('Camera VistaOptic needs an 87 mm focal length; leave every other property unchanged.',
         dict(intent='camera_lens', target='VistaOptic', amount=87, unit='mm')),
        ('For compositor Glare node EveningAura, use threshold 1.35 and strength 0.38 as a fraction.',
         dict(intent='glow', target='EveningAura', threshold=1.35, strength=.38, unit='fraction')),
        ('The existing glare node is named DawnBloom. Only set its threshold to 0.95 and its strength to 72 percent.',
         dict(intent='glow', target='DawnBloom', threshold=.95, strength=72, unit='percent')),
        ('Area light WindowSoftbox should output 0.84 kW. Keep its color and location.',
         dict(intent='light_power', target='WindowSoftbox', amount=.84, unit='kW')),
        ('On mesh ResinShell, preserve the material color while setting roughness to 62 percent and metallic to 15 percent.',
         dict(intent='surface', target='ResinShell', roughness=62, metallic=15, unit='percent')),
    ]
    for i, (prompt, frame) in enumerate(controls):
        rows.append(labeled(f'challenge-control-{i}', prompt, frame, 'challenge-controls', 'test'))
    refusals = [
        ('new_geometry', 'Starting with no mesh, sculpt a newly created anatomical foot.'),
        ('animation', 'Produce keyframed poses of this character climbing a ladder over three seconds.'),
        ('simulation', 'Use a physics simulation to bake interacting liquid droplets.'),
        ('multi_step', 'Set CamRed to 43 mm and also set LightBlue to 910 W in a single command.'),
        ('ambiguous', 'Alter an unspecified item by an unspecified amount.'),
    ]
    for kind, prompt in refusals:
        rows.append(labeled('challenge-refuse-'+kind, prompt,
                            dict(intent='unsupported', feature=kind), 'challenge-refusals', 'test'))
    return rows


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    rows = build()
    out = Path(args.output)
    out.mkdir(parents=True, exist_ok=False)
    path = out/'test.jsonl'
    path.write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf-8')
    (out/'cases.json').write_text(json.dumps(rows, indent=2), encoding='utf-8')
    (out/'manifest.json').write_text(json.dumps(dict(profile='intent', system=SYSTEM,
        compiler_sha256=hashlib.sha256(Path(__file__).with_name('intent_ops.py').read_bytes()).hexdigest(),
        files=dict(test=dict(count=len(rows), sha256=hashlib.sha256(path.read_bytes()).hexdigest())),
        gates=dict(all_valid=20, exact_minimum=18, correctly_refused=5),
        scope='20 authored prompts, frozen before refinement01 training; synthetic existing-element language only. No training split.',
        limitations='Independent wording and names but same human-authored schema/domain. Not customer or artistic validation.'), indent=2), encoding='utf-8')
    (out/'intent_challenge.py.snapshot').write_bytes(Path(__file__).read_bytes())
    print(json.dumps(dict(count=len(rows), gates=dict(all_valid=20, exact_minimum=18, correctly_refused=5))))


if __name__ == '__main__':
    main()
