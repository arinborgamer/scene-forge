"""Original synthetic tool-use curriculum with independent numerical checks.

No previous model failures, downloaded meshes or human anatomy claims are training data.
Splits have different object names and numeric tuples, but share operation families.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import random
from modeling_lab.operations import validate_plan, deform_points

SYSTEM = '''Return exactly one Blender modeling operation as JSON, with no prose or markdown.
Coordinates and vectors are ordered [X,Y,Z], in metres; Z is up. Preserve unspecified axes.
For a local edit use {"op":"deform","target":name,"center":[x,y,z],"radius":[rx,ry,rz],"translation":[dx,dy,dz],"scale":[sx,sy,sz]}.
Local scaling is about center with smooth ellipsoid falloff; outside the region is unchanged.
Widen/increase by p percent means scale 1+p/100; narrow/reduce means 1-p/100. Translation stays zero when scaling.
For whole-object edits use {"op":"transform","target":name,"translation":[dx,dy,dz],"scale":[sx,sy,sz],"rotation_degrees":[rx,ry,rz]}.
For new geometry use {"op":"primitive","id":name,"kind":"box" or "sphere" or "cylinder","location":[x,y,z],"dimensions":[x,y,z],"rotation_degrees":[0,0,0]}.
Dimensions are full sizes, not radii. Defaults: translation/rotation zero, scale one.
Do not add other operations, objects or fields.'''


def wrapped(operation):
    return {'title': 'Trained modeling operation', 'operations': [operation], 'unsupported_requests': []}


def validate_example(row):
    op = row['operation']
    validate_plan(wrapped(op), [op['target']] if 'target' in op else [])
    facts = row['facts']
    # Reconstruct intent from independently recorded scalar facts, not output equality.
    axis = 'XYZ'.index(facts['axis']) if 'axis' in facts else None
    if op['op'] == 'deform':
        assert op['center'] == facts['center'] and op['radius'] == facts['radius']
        center = facts['center']
        radius = facts['radius']
        probes = [center.copy()]
        for i in range(3):
            for distance in (-1.1, -.5, .5, 1.1):
                p = center.copy()
                p[i] += distance * radius[i]
                probes.append(p)
        changed, count = deform_points(probes, op)
        assert count > 0
        for p, q in zip(probes, changed):
            d2 = sum(((p[i]-center[i])/radius[i])**2 for i in range(3))
            weight = (1-d2)**2 if d2 < 1 else 0
            expected = p.copy()
            if facts['mode'] == 'scale':
                expected[axis] += weight * (p[axis]-center[axis]) * facts['percent']/100
            else:
                expected[axis] += weight * facts['distance']
            assert all(math.isclose(a, b, abs_tol=1e-10) for a, b in zip(q, expected))
    elif op['op'] == 'transform':
        assert op['scale'] == [1, 1, 1] and op['rotation_degrees'] == [0, 0, 0]
        assert all(math.isclose(n, facts['distance'] if i == axis else 0, abs_tol=1e-10)
                   for i, n in enumerate(op['translation']))
    else:
        assert op['dimensions'] == facts['dimensions'] and op['kind'] == facts['kind']
        assert op['location'] == facts['location'] and op['rotation_degrees'] == [0, 0, 0]
    return True


def build_rows(split, count, seed):
    rng = random.Random(seed)
    rows = []
    for index in range(count):
        name = f'{split}_part_{index:03d}'
        axis = index % 3
        center = [rng.choice([-.12, 0, .08]), rng.choice([-.05, 0, .1]), round(rng.uniform(.7, 1.6), 2)]
        radius = [rng.choice([.18, .25, .35]), rng.choice([.15, .22, .3]), rng.choice([.1, .15, .2])]
        family = index % 8
        facts = {'axis': 'XYZ'[axis]}
        if family < 6:
            op = dict(op='deform', target=name, center=center, radius=radius, translation=[0, 0, 0], scale=[1, 1, 1])
            facts.update(center=center, radius=radius)
            region = f'center X={center[0]}, Y={center[1]}, Z={center[2]}; ellipsoid radii X={radius[0]}, Y={radius[1]}, Z={radius[2]} metres'
            if family < 4:
                percent = rng.choice([-15, -10, -5, 5, 8, 10, 15, 20])
                op['scale'][axis] = round(1 + percent/100, 4)
                facts.update(mode='scale', percent=percent)
                verb = 'Increase' if percent > 0 else 'Reduce'
                prompt = f'{verb} the local {facts["axis"]} extent of {name} by {abs(percent)} percent. Use {region}. Keep other axes, all outside vertices and the object transform unchanged.'
            else:
                distance = rng.choice([-.02, -.01, .01, .015, .02])
                op['translation'][axis] = distance
                facts.update(mode='translate', distance=distance)
                prompt = f'Locally move vertices of {name} by {distance} metres along {facts["axis"]}, using {region}. No scaling, no whole-object transform; preserve everything outside.'
        elif family == 6:
            distance = rng.choice([-.2, -.1, .1, .15, .25])
            translation = [0, 0, 0]
            translation[axis] = distance
            facts.update(distance=distance)
            op = dict(op='transform', target=name, translation=translation, scale=[1, 1, 1], rotation_degrees=[0, 0, 0])
            prompt = f'Move the whole object {name} by {distance} metres along {facts["axis"]}. Do not change its shape, scale, rotation or other location axes.'
        else:
            kind = rng.choice(['box', 'sphere', 'cylinder'])
            dimensions = [rng.choice([.12, .2, .3, .45]) for _ in range(3)]
            facts = dict(kind=kind, dimensions=dimensions, location=center)
            op = dict(op='primitive', id=name, kind=kind, location=center, dimensions=dimensions, rotation_degrees=[0, 0, 0])
            prompt = f'Create one {kind} named {name}. Center it at X={center[0]}, Y={center[1]}, Z={center[2]} metres. Full sizes: X={dimensions[0]}, Y={dimensions[1]}, Z={dimensions[2]} metres. Zero rotation.'
        row = {'id': f'{split}-{index:03d}', 'split': split, 'prompt': prompt, 'operation': op, 'facts': facts,
               'provenance': 'Original programmatically authored numerical tool-use example; no external teacher model',
               'review_scope': 'Schema and independent numerical checks; not artistic or anatomy approval'}
        validate_example(row)
        rows.append(row)
    return rows


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--output', required=True)
    args = p.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    manifest = {'system': SYSTEM, 'scope': 'Synthetic single-operation tool use, not realistic asset generation',
                'split_limitations': 'Disjoint names and numeric tuples; same synthetic task families and language templates',
                'license_note': 'Original project-generated instructions and operations. No downloaded asset data in corpus.', 'files': {}}
    for split, count, seed in [('train', 160, 22101), ('validation', 16, 22102), ('test', 16, 22103)]:
        rows = build_rows(split, count, seed)
        path = output / (split + '.jsonl')
        path.write_text(''.join(json.dumps(r) + '\n' for r in rows), encoding='utf-8')
        manifest['files'][split] = {'count': len(rows), 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()}
    (output / 'manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps(manifest['files']), flush=True)


if __name__ == '__main__':
    main()
