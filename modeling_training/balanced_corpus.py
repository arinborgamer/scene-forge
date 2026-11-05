"""Cross axis, unit and wording independently; retain scaling and CGI controls."""
import argparse
import hashlib
import itertools
import json
import random
from pathlib import Path

from modeling_training.corpus import build_rows
from modeling_training.vfx_corpus import rows as vfx_rows, validate_row
from modeling_training.vfx_ops import SYSTEM


def displacement_rows(split, seed):
    rng = random.Random(seed)
    variants = range(4) if split == 'train' else range(1)
    combinations = list(itertools.product(range(3), range(3), variants))
    if split == 'validation':
        combinations = [(0, 1, 0), (1, 2, 0), (2, 0, 0)]
    result = []
    for i, (axis, unit, variant) in enumerate(combinations):
        name = f'{split}_panel_{i:03d}'
        sign = -1 if (axis + unit + variant) % 2 else 1
        centimeters = sign * rng.choice([1, 2, 3, 4])
        distance = centimeters / 100
        amount = [f'{centimeters} centimetres', f'{centimeters*10} millimetres',
                  f'{distance:g} metres'][unit]
        letter = 'XYZ'[axis]
        delta = [0, 0, 0]
        delta[axis] = distance
        center = [rng.choice([-.04, .02, .06]), .02, rng.choice([1.1, 1.2, 1.3])]
        radius = [.25, .2, .18]
        region = f'ellipsoid centred at {center} metres with radii {radius} metres'
        for local in (True, False):
            facts = dict(axis=letter, distance=distance, input_centimeters=centimeters)
            if local:
                facts.update(mode='translate', center=center, radius=radius)
                op = dict(op='deform', target=name, center=center, radius=radius,
                          translation=delta.copy(), scale=[1, 1, 1])
                texts = [
                    f'Locally move the vertices of {name} by {amount} on {letter}, inside the {region}. Preserve object transforms, outside vertices and all scale factors.',
                    f'For {name}, apply a vertex offset of {amount} along {letter} using the {region}. No scaling; keep the object itself fixed.',
                    f'Edit mesh {name} inside the {region}: shift the patch {amount} along {letter} with smooth falloff. Leave everything outside and the object transform unchanged. Scale stays one.',
                    f'Target {name}: local {letter} translation {amount}; {region}. Preserve other coordinates, use smooth falloff and keep scale [1,1,1].',
                ]
                heldout = f'The object {name} must stay in place. Give only vertices within the {region} a smooth {letter} offset of {amount}, with no resizing or outside changes.'
            else:
                op = dict(op='transform', target=name, translation=delta.copy(),
                          scale=[1, 1, 1], rotation_degrees=[0, 0, 0])
                texts = [
                    f'Move the entire object {name} by {amount} on {letter}. Preserve mesh data, orientation and scale.',
                    f'For {name}, apply an object offset of {amount} along {letter}. No resizing, rotation or vertex edits.',
                    f'Keep the local geometry of {name} intact and displace the object {amount} along {letter}. All scale factors remain one and all rotations remain zero.',
                    f'Target {name}: whole-object {letter} translation {amount}; preserve all other coordinates, rotation [0,0,0] and scale [1,1,1].',
                ]
                heldout = f'Transport {name} as a complete object {amount} along {letter}. Its dimensions, orientation and local vertex coordinates must remain exactly as before.'
            row = dict(id=f'{split}-balanced-{i:03d}-{"local" if local else "whole"}',
                       split=split, prompt=heldout if split == 'test' else texts[variant],
                       operation=op, facts=facts, unit_family=unit, wording_family=variant,
                       provenance='Original synthetic request; axes, units and training wording crossed independently')
            validate_row(row)
            result.append(row)
    return result


def build(split, seed):
    result = displacement_rows(split, seed)
    scale_per_axis = {'train': 8, 'validation': 2, 'test': 2}[split]
    pool = build_rows(split+'_scale', 120, seed+100)
    for letter in 'XYZ':
        selected = [r for r in pool if r['operation']['op'] == 'deform'
                    and r['facts']['mode'] == 'scale' and r['facts']['axis'] == letter]
        for row in selected[:scale_per_axis]:
            row['split'] = split
            result.append(row)
    controls_per_family = {'train': 8, 'validation': 1, 'test': 2}[split]
    controls = vfx_rows(split, 112 if split == 'train' else 12, seed+200)
    for family in ('light_power', 'camera_lens', 'surface', 'glow'):
        result.extend([r for r in controls if r['operation']['op'] == family][:controls_per_family])
    for row in result:
        validate_row(row)
    random.Random(seed).shuffle(result)
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    out = Path(args.output)
    all_rows = {s: build(s, seed) for s, seed in
                [('train', 28101), ('validation', 28102), ('test', 28103)]}
    names = [{r['operation']['target'] for r in rows} for rows in all_rows.values()]
    assert all(not names[i] & names[j] for i in range(3) for j in range(i+1, 3))
    prompts = [r['prompt'] for rows in all_rows.values() for r in rows]
    assert len(set(prompts)) == len(prompts)
    out.mkdir(parents=True, exist_ok=False)
    manifest = dict(system=SYSTEM, files={},
                    scope='Single existing-element operations; crossed axes/units/wording, local scaling replay and CGI controls',
                    split_limitations='Synthetic families and number ranges are shared. Earlier observed tests are regression evidence. Test wording is separate; this is not an independent real-world benchmark.',
                    license_note='Original synthetic instructions; no movie imagery, downloaded assets or teacher-model outputs.')
    for split, rows in all_rows.items():
        path = out/(split+'.jsonl')
        path.write_text(''.join(json.dumps(r)+'\n' for r in rows), encoding='utf-8')
        manifest['files'][split] = dict(count=len(rows), sha256=hashlib.sha256(path.read_bytes()).hexdigest())
    (out/'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest['files']))


if __name__ == '__main__':
    main()
