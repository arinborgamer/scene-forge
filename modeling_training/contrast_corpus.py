"""Paired local/whole-object instructions; old benchmarks are not training data."""
import argparse
import hashlib
import json
import random
from pathlib import Path
from modeling_training.vfx_corpus import rows as vfx_rows, validate_row
from modeling_training.vfx_ops import SYSTEM


def paired_rows(split, pairs, seed):
    rng = random.Random(seed)
    result = []
    for i in range(pairs):
        name = f'{split}_{rng.choice(["body_shell", "shoulder_panel", "surface_patch"])}_{i:03d}'
        axis = i % 3
        sign = -1 if (i // 3) % 2 else 1
        cm = rng.choice([1, 2, 3, 4])
        distance = sign * cm / 100
        delta = [0, 0, 0]; delta[axis] = distance
        center = [rng.choice([-.04, .02, .06]), .02, rng.choice([1.1, 1.2, 1.3])]
        radius = [.25, .2, .18]
        amount = [f'{sign*cm} centimetres', f'{sign*cm*10} millimetres', f'{distance:g} metres'][i % 3]
        region = f'ellipsoid centred at {center} metres with radii {radius} metres'
        letter = 'XYZ'[axis]
        for local in (True, False):
            facts = dict(axis=letter, distance=distance, input_centimeters=sign*cm)
            if local:
                facts.update(mode='translate', center=center, radius=radius)
                op = dict(op='deform', target=name, center=center, radius=radius, translation=delta, scale=[1,1,1])
                variants = [
                    f'On mesh "{name}", shift vertices inside the {region} by {amount} along {letter}. Leave the object transform and outside vertices unchanged; do not scale.',
                    f'Apply a local vertex displacement to "{name}": {letter} offset {amount}, {region}. No scaling, no object-level movement, no changes outside the region.',
                    f'Mesh name: "{name}". The object itself stays fixed. Move only its vertices within the {region} by {amount} on {letter}, using the usual smooth falloff. Keep scale at one.',
                ]
                heldout = f'Keep "{name}" in place as an object. Inside the {region}, give the mesh vertices a {amount} {letter} displacement with smooth falloff. Do not scale or alter vertices outside that patch.'
            else:
                op = dict(op='transform', target=name, translation=delta, scale=[1,1,1], rotation_degrees=[0,0,0])
                variants = [
                    f'Shift the entire object "{name}" by {amount} along {letter}. Do not edit its local vertices or change rotation or scale.',
                    f'Apply an object-level displacement to "{name}": {letter} offset {amount}. Preserve its mesh data, orientation, scale and all remaining coordinates.',
                    f'Mesh name: "{name}". Keep the local geometry intact and move the whole object {amount} on {letter}. No rotation or scaling.',
                ]
                heldout = f'Keep the mesh data of "{name}" intact. Give the object itself a {amount} {letter} displacement. Preserve its orientation, size and other coordinates.'
            row = dict(id=f'{split}-contrast-{i:03d}-{"local" if local else "whole"}', split=split,
                       prompt=heldout if split=='test' else variants[i % 3], operation=op, facts=facts,
                       provenance='Original authored contrast pairs; no previous failed prompt copied into training',
                       language_family='heldout contrast wording' if split=='test' else 'contrast curriculum')
            validate_row(row)
            result.append(row)
    return result


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--output',required=True);args=parser.parse_args()
    out=Path(args.output);out.mkdir(parents=True,exist_ok=False)
    manifest=dict(system=SYSTEM,files={},scope='Local versus whole-object displacement and exact target names, with CGI replay; no anatomy generation',
                  split_limitations='Separately worded test pairs and names; same operation families and numerical ranges. Developed after inspecting earlier failures; older tests are now regression tests.',
                  license_note='Original synthetic instructions; no external teacher outputs or downloaded assets.')
    all_rows={}
    for split,pairs,seed in [('train',48,27151),('validation',6,27152),('test',9,27153)]:
        items=paired_rows(split,pairs,seed)
        if split=='train':
            replay=vfx_rows('train',70,27154)
            # Eight examples from each CGI-control family; exclude old movement wording.
            for family in ['light_power','camera_lens','surface','glow']:
                selected=[r for r in replay if r['operation']['op']==family][:8]
                items.extend(selected)
            random.Random(seed).shuffle(items)
        all_rows[split]=items
    assert len({r['prompt'] for items in all_rows.values() for r in items})==sum(map(len,all_rows.values()))
    names=[{r['operation']['target'] for r in items} for items in all_rows.values()]
    assert all(not names[i]&names[j] for i in range(3) for j in range(i+1,3))
    for split,items in all_rows.items():
        path=out/(split+'.jsonl');path.write_text(''.join(json.dumps(r)+'\n' for r in items),encoding='utf-8')
        manifest['files'][split]={'count':len(items),'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    print(json.dumps(manifest['files']))


if __name__=='__main__':main()
