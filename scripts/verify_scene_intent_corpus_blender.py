"""Build every catalog, execute each target, and check all unselected elements unchanged."""
import hashlib
import itertools
import json
import math
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bpy
from modeling_lab.operation_blender import make_mesh,mesh_state,execute
from modeling_training.corpus import wrapped,validate_example
from modeling_training.scene_intent_ops import compile_intent,validate_scene,compiler_sha256
from modeling_training.intent_ops import UnsupportedIntent
from modeling_training.vfx_ops import apply_vfx,SCHEMAS
from modeling_training.vfx_fixture import observe
from modeling_training.transfer_review import equivalent
from modeling_training.scene_intent_data import verify_manifest


def create_scene(row):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    facts=row.get('facts',{})
    c,r=facts.get('center',[0,0,0]),facts.get('radius',[1,1,1])
    points=[[c[i]+signs[i]*r[i]*.25+(3*r[i] if outside and i==0 else 0) for i in range(3)]
            for outside in (False,True) for signs in itertools.product((-1,1),repeat=3)]
    faces=[[0,1,3,2],[4,6,7,5],[0,4,5,1],[2,3,7,6],[0,2,6,4],[1,5,7,3]]
    faces += [[i+8 for i in f] for f in faces.copy()]
    actual=[]
    for entry in row['scene']:
        name,kind=entry['name'],entry['type']
        if kind=='MESH':
            obj=make_mesh(name,points,faces)
            group=obj.vertex_groups.new(name='preserved_weight')
            group.add(list(range(16)),.75,'REPLACE')
            mat=bpy.data.materials.new(name+'_Material')
            mat.use_nodes=True
            obj.data.materials.append(mat)
            actual.append(dict(name=obj.name,type=obj.type))
        elif kind in ('LIGHT','CAMERA'):
            data=bpy.data.lights.new(name,'AREA') if kind=='LIGHT' else bpy.data.cameras.new(name)
            if kind=='LIGHT':data.energy=10
            else:data.lens=12
            obj=bpy.data.objects.new(name,data)
            bpy.context.collection.objects.link(obj)
            actual.append(dict(name=obj.name,type=obj.type))
        elif kind=='GLARE_NODE':
            scene=bpy.context.scene
            if scene.compositing_node_group is None:
                scene.compositing_node_group=bpy.data.node_groups.new('SceneIntentCompositor','CompositorNodeTree')
            node=scene.compositing_node_group.nodes.new('CompositorNodeGlare')
            node.name=name
            node.inputs['Strength'].default_value=0
            actual.append(dict(name=node.name,type='GLARE_NODE'))
    bpy.context.view_layer.update()
    if actual!=row['scene']:
        raise ValueError('Observed catalog differs from model input')
    return actual


def capture(entry):
    name,kind=entry['name'],entry['type']
    if kind=='GLARE_NODE':
        return observe(dict(op='glow',target=name))
    obj=bpy.data.objects[name]
    result=dict(location=list(obj.location),rotation=list(obj.rotation_euler),scale=list(obj.scale))
    if kind=='MESH':
        result.update(mesh=mesh_state(obj,True),surface=observe(dict(op='surface',target=name)))
    elif kind=='LIGHT':
        result.update(color=list(obj.data.color),power=obj.data.energy)
    else:result['lens']=obj.data.lens
    return result


root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
manifest=verify_manifest(root)
if manifest.get('profile')!='scene_intent' or manifest['compiler_sha256']!=compiler_sha256():
    raise ValueError('Wrong or changed scene compiler')
records=[]
refused=0
for split,info in manifest['files'].items():
    path=root/(split+'.jsonl')
    if hashlib.sha256(path.read_bytes()).hexdigest()!=info['sha256']:
        raise ValueError('Frozen data changed')
    for line in path.read_text().splitlines():
        row=json.loads(line)
        validate_scene(row['scene'])
        observed=create_scene(row)
        before={e['name']:capture(e) for e in observed}
        frame=row['operation']
        if frame['intent']=='unsupported':
            try:compile_intent(frame,observed)
            except UnsupportedIntent:pass
            else:raise AssertionError('Refusal reached execution')
            assert before=={e['name']:capture(e) for e in observed}
            refused+=1
            records.append(dict(id=row['id'],split=split,passed=True,execution='refused',observed_catalog=observed))
            continue
        op=compile_intent(frame,observed)
        assert equivalent(op,row['expected_operation']),row['id']
        if op['op'] in SCHEMAS:
            apply_vfx(op)
            values=observe(op)
            assert all(math.isclose(values[k],v,abs_tol=1e-5) for k,v in row['facts'].items()),row['id']
        else:
            validate_example({**row,'operation':op})
            execute(wrapped(op),[e['name'] for e in observed if e['type']=='MESH'])
            old=before[op['target']]['mesh']
            after=mesh_state(bpy.data.objects[op['target']],True)
            assert old['topology_sha256']==after['topology_sha256'] and old['weights_sha256']==after['weights_sha256']
            facts=row['facts']
            axis='XYZ'.index(facts['axis'])
            if op['op']=='transform':
                assert old['mesh_sha256']==after['mesh_sha256']
                assert math.isclose(bpy.data.objects[op['target']].location[axis],facts['distance'],abs_tol=1e-7)
            else:
                c,r=facts['center'],facts['radius']
                for p,q in zip(old['points'],after['points']):
                    d=sum(((p[i]-c[i])/r[i])**2 for i in range(3))
                    weight=max(0,1-d)**2 if d<1 else 0
                    wanted=p.copy()
                    wanted[axis]+=weight*((p[axis]-c[axis])*facts['percent']/100 if facts['mode']=='scale' else facts['distance'])
                    assert all(math.isclose(a,b,abs_tol=3e-7) for a,b in zip(q,wanted)),row['id']
        bpy.context.view_layer.update()
        assert all(before[e['name']]==capture(e) for e in observed if e['name']!=op['target']),row['id']
        records.append(dict(id=row['id'],split=split,passed=True,execution='executed',observed_catalog=observed,
                            unselected_elements_unchanged=True))
report=dict(passed=True,count=len(records),executed_count=len(records)-refused,refusal_count=refused,
            compiler_sha256=compiler_sha256(),cases=records,files=manifest['files'],
            manifest_sha256=hashlib.sha256((root/'manifest.json').read_bytes()).hexdigest(),
            scope='All catalog choices physically created; target/refusal and untouched-element checks. Synthetic fixtures, not artist or rig acceptance.')
with (root/'blender-verification.json').open('x',encoding='utf-8') as stream:
    json.dump(report,stream,indent=2)
print('SCENE_INTENT_CORPUS_PASS',len(records),flush=True)
