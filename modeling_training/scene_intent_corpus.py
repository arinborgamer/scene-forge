"""Freeze a scene-aware representation; preserve raw requests and regression lineage."""
import argparse
from collections import defaultdict
import hashlib
import json
from pathlib import Path
import random
from decimal import Decimal

from modeling_training.intent_refinement import labeled
from modeling_training.intent_ops import compile_intent as legacy_compile
from modeling_training.scene_intent_ops import (SYSTEM,ELEMENT_TYPES,from_legacy,prompt,
                                                compile_intent,compiler_sha256)
from modeling_training.transfer_review import equivalent


def physical_facts(operation,frame):
    if operation is None:
        return dict(unsupported_feature=frame['feature'])
    if operation['op'] not in ('deform','transform'):
        return {k:v for k,v in operation.items() if k not in ('op','target')}
    moving=any(abs(v)>1e-9 for v in operation['translation'])
    sizing=any(abs(v-1)>1e-9 for v in operation['scale'])
    if moving==sizing:
        raise ValueError('Expected exactly one translation or scale change')
    values=operation['translation'] if moving else [v-1 for v in operation['scale']]
    axes=[i for i,v in enumerate(values) if abs(v)>1e-9]
    if len(axes)!=1:
        raise ValueError('Expected one-axis action')
    axis=axes[0]
    facts=dict(axis='XYZ'[axis],mode='translate' if moving else 'scale')
    if operation['op']=='deform':
        facts.update(center=operation['center'],radius=operation['radius'])
    if moving:facts['distance']=operation['translation'][axis]
    else:facts['percent']=float((Decimal(str(operation['scale'][axis]))-1)*100)
    return facts


def convert(rows,seed,shared_scene=None):
    pools=defaultdict(set)
    for row in rows:
        frame=row['operation']
        if 'target' in frame:
            pools[ELEMENT_TYPES[frame['intent']]].add(frame['target'])
    result=[]
    for i,row in enumerate(rows):
        frame=from_legacy(row['operation'])
        kind=ELEMENT_TYPES.get(frame['intent'],'MESH')
        rng=random.Random(seed+i)
        pool=sorted(pools[kind]-{frame.get('target')})
        candidate_index=0
        while len(pool)<3:
            name=f'Element_{seed}_{kind}_{candidate_index}'
            candidate_index+=1
            if name not in pool and name!=frame.get('target'):
                pool.append(name)
        if shared_scene is None:
            if 'target' in frame:
                other=rng.sample(pool,2)
                names=[frame['target'],*other]
                rng.shuffle(names)
            else:
                names=rng.sample(pool,3)
                rng.shuffle(names)
            scene=[dict(name=name,type=kind) for name in names]
        else:
            scene=[dict(x) for x in shared_scene]
            rng.shuffle(scene)
        expected=row.get('expected_operation')
        if expected is None and frame['intent']!='unsupported':
            expected=legacy_compile(row['operation'],[row['operation']['target']])
        if expected is not None and not equivalent(compile_intent(frame,scene),expected):
            raise ValueError('Representation changed the intended physical edit')
        result.append({**row,'request':row['prompt'],'prompt':prompt(row['prompt'],scene),
                       'scene':scene,'operation':frame,'expected_operation':expected,
                       'facts':physical_facts(expected,frame),
                       'provenance':'Original/replayed authored synthetic request; verified scene catalog and literal direction compilation. No teacher model outputs.'})
    return result


def new_challenge():
    rows=[]
    center,radius=[-.01,.02,1.29],[.23,.19,.14]
    region=f'ellipsoid center {center} metres, radii {radius} metres'
    for i,(axis,amount,unit) in enumerate([('X',-1.4,'cm'),('Y',7.5,'mm'),('Z',.0225,'m')]):
        name=f'BronzeSubject{i}'
        rows.append(labeled(f'new-local-{i}',f'In {name}, offset only vertices inside {region}: {amount:g} {unit} on {axis}. Use smooth falloff; leave the object placement fixed.',
            dict(intent='local_translate',target=name,axis=axis,amount=amount,unit=unit,center=center,radius=radius),'new-patch','test'))
        name=f'GalleryObject{i}'
        rows.append(labeled(f'new-whole-{i}',f'As a placement edit, relocate {name} by {amount:g} {unit} along {axis}. Its local vertex coordinates, rotation and scale must remain unchanged.',
            dict(intent='object_translate',target=name,axis=axis,amount=amount,unit=unit),'new-placement','test'))
    for i,(axis,value,verb) in enumerate([('X',-8,'Shrink'),('Y',-11,'Reduce'),('Z',16,'Lengthen')]):
        name=f'PorcelainShape{i}'
        rows.append(labeled(f'new-scale-{i}',f'{verb} the local {axis} extent on {name} by {abs(value)} percent inside {region}, with smooth falloff. Preserve the other axes, outside vertices and object position.',
            dict(intent='local_scale',target=name,axis=axis,percent=value,center=center,radius=radius),'new-size','test'))
    controls=[
        ('The existing camera CopperLens needs 3.7 cm focal length; keep its transform fixed.',dict(intent='camera_lens',target='CopperLens',amount=3.7,unit='cm')),
        ('Use a 91 mm lens on the named camera IndigoLens. Keep its position.',dict(intent='camera_lens',target='IndigoLens',amount=91,unit='mm')),
        ('Glare node HaloCopper should use threshold 1.15 and strength 0.42 as a fraction.',dict(intent='glow',target='HaloCopper',threshold=1.15,strength=.42,unit='fraction')),
        ('Keep the existing compositor node HaloIndigo, with threshold 0.75 and strength 64 percent.',dict(intent='glow',target='HaloIndigo',threshold=.75,strength=64,unit='percent')),
        ('Set only area light VelvetKey output to 0.92 kW.',dict(intent='light_power',target='VelvetKey',amount=.92,unit='kW')),
        ('For the material on mesh CopperShell, keep the color and use roughness 27 percent and metallic 63 percent.',dict(intent='surface',target='CopperShell',roughness=27,metallic=63,unit='percent')),
    ]
    for i,(request,frame) in enumerate(controls):
        rows.append(labeled(f'new-control-{i}',request,frame,'new-controls','test'))
    refusals=[('new_geometry','Construct an entirely new sculpted insect without an input mesh.'),
              ('animation','Insert a timed sequence of keyframes showing a character leaping.'),
              ('simulation','Bake physics-based spray and droplet collisions.'),
              ('multi_step','Set LensCopper to 44 mm and LampIndigo to 820 W in the same edit.'),
              ('ambiguous','Adjust an unspecified object until it looks nicer.')]
    for kind,request in refusals:
        rows.append(labeled('new-refuse-'+kind,request,dict(intent='unsupported',feature=kind),'new-refusals','test'))
    return rows


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',default='output/qwen-intent-corpus-v4')
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    source,out=Path(args.source),Path(args.output)
    old_manifest=json.loads((source/'manifest.json').read_text())
    values={}
    lineage=[]
    for i,split in enumerate(('train','validation','test')):
        path=source/(split+'.jsonl')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=old_manifest['files'][split]['sha256']:
            raise ValueError('Frozen source data changed')
        values[split]=convert([json.loads(line) for line in path.read_text().splitlines()],28501+100*i)
        lineage.append(dict(file=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    for split,file in [('regression','output/qwen-intent-regression-cases-v1.json'),
                       ('vfx','output/qwen-intent-vfx-review-cases-v1.json')]:
        path=Path(file)
        rows=json.loads(path.read_text())
        shared=[dict(name=r['operation']['target'],type=ELEMENT_TYPES[r['operation']['intent']]) for r in rows] if split=='vfx' else None
        values[split]=convert(rows,28801 if split=='regression' else 28901,shared)
        lineage.append(dict(file=str(path.resolve()),sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
    values['challenge']=convert(new_challenge(),29001)
    training_requests={r['request'] for r in values['train']}
    if any(training_requests & {r['request'] for r in rows} for split,rows in values.items() if split!='train'):
        raise ValueError('Training request overlaps evaluation')
    out.mkdir(parents=True,exist_ok=False)
    manifest=dict(profile='scene_intent',system=SYSTEM,compiler_sha256=compiler_sha256(),files={},lineage=lineage,
        seed=28501,scope='Scene-aware existing-element edits; direction separated from unsigned scale magnitude. No learned anatomy or motion.',
        split_limitations='Primary/older requests are observed regressions with a changed interface, not comparable unseen benchmarks. New20challenge frozen before training but authored by same AI-assisted process.',
        license_note='AI-assisted authored synthetic project templates, executable checks, no downloaded movie assets or teacher outputs.')
    for split,rows in values.items():
        path=out/(split+'.jsonl')
        path.write_text(''.join(json.dumps(r)+'\n' for r in rows),encoding='utf-8')
        (out/(split+'.json')).write_text(json.dumps(rows,indent=2),encoding='utf-8')
        manifest['files'][split]=dict(count=len(rows),sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
                                     json_sha256=hashlib.sha256((out/(split+'.json')).read_bytes()).hexdigest())
    manifest['artifacts']={}
    manifest['canary_sources']={}
    for name,source_file in [('positive-transfer.json','examples/cinematic-modeling-canaries.json'),
                              ('negative-transfer.json','examples/negative-modeling-canary.json')]:
        path=Path(source_file)
        (out/name).write_bytes(path.read_bytes())
        manifest['artifacts'][name]=dict(sha256=hashlib.sha256(path.read_bytes()).hexdigest(),source=source_file)
        for case in json.loads(path.read_text()):
            source_blend=Path(case['input']).resolve()
            manifest['canary_sources'][str(source_blend)]=hashlib.sha256(source_blend.read_bytes()).hexdigest()
    (out/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    (out/'scene_intent_corpus.py.snapshot').write_bytes(Path(__file__).read_bytes())
    print(json.dumps({k:len(v) for k,v in values.items()}),flush=True)


if __name__=='__main__':
    main()
