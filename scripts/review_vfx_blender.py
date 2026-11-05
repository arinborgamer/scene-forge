"""Apply uncorrected model outputs to an authored look-development test scene."""
import json,sys,math,hashlib
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bpy
from mathutils import Vector
from modeling_training.vfx_ops import validate_operation,apply_vfx
from modeling_training.vfx_fixture import observe
from modeling_training.intent_ops import compile_intent
from modeling_training.transfer_review import equivalent

def write(path,data): path.write_text(json.dumps(data,indent=2),encoding='utf-8')

def material(name,color,metal=0,rough=.5,emission=0):
    m=bpy.data.materials.new(name);m.use_nodes=True
    n=m.node_tree.nodes.get('Principled BSDF')
    n.inputs['Base Color'].default_value=(*color,1)
    n.inputs['Metallic'].default_value=metal;n.inputs['Roughness'].default_value=rough
    n.inputs['Emission Color'].default_value=(*color,1);n.inputs['Emission Strength'].default_value=emission
    return m

def build_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=bpy.context.scene;scene.render.engine='CYCLES';scene.cycles.device='CPU';scene.cycles.samples=24
    scene.render.resolution_x=640;scene.render.resolution_y=480;scene.render.resolution_percentage=100
    scene.world=bpy.data.worlds.new('ReviewWorld');scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs[0].default_value=(.09,.11,.16,1)
    scene.world.node_tree.nodes['Background'].inputs[1].default_value=.25
    bpy.ops.mesh.primitive_uv_sphere_add(segments=64,ring_count=32,location=(0,0,1.1))
    sphere=bpy.context.object;sphere.name='ReviewSphere';sphere.data.materials.append(material('ReviewMetal',(.08,.3,.5)))
    for p in sphere.data.polygons:p.use_smooth=True
    bpy.ops.mesh.primitive_plane_add(size=200);bpy.context.object.name='ReviewFloor'
    bpy.context.object.data.materials.append(material('Floor',(.025,.035,.05),rough=.4))
    bpy.ops.mesh.primitive_torus_add(major_radius=1.35,minor_radius=.025,location=(0,.35,1.25),rotation=(math.pi/2,0,0))
    ring=bpy.context.object;ring.name='ReviewEmissionRing';ring.data.materials.append(material('Emission',(.1,.7,1),emission=12))
    for name,loc,energy,size,color in [('StudioKey',(-3,-3,5),150,4,(1,.8,.6)),('ReviewRim',(3,1,3),500,3,(.15,.5,1))]:
        light=bpy.data.lights.new(name,'AREA');light.energy=energy;light.shape='DISK';light.size=size;light.color=color
        ob=bpy.data.objects.new(name,light);scene.collection.objects.link(ob);ob.location=loc
        ob.rotation_euler=(Vector((0,0,1))-ob.location).to_track_quat('-Z','Y').to_euler()
    camera=bpy.data.cameras.new('ShotCamera');ob=bpy.data.objects.new('ShotCamera',camera);scene.collection.objects.link(ob)
    ob.location=(4,-7,3.5);ob.rotation_euler=(Vector((0,0,1))-ob.location).to_track_quat('-Z','Y').to_euler();camera.lens=40;scene.camera=ob
    tree=bpy.data.node_groups.new('ReviewCompositor','CompositorNodeTree');scene.compositing_node_group=tree
    tree.interface.new_socket(name='Image',in_out='OUTPUT',socket_type='NodeSocketColor')
    source=tree.nodes.new('CompositorNodeRLayers');glare=tree.nodes.new('CompositorNodeGlare');glare.name='ReviewGlow'
    glare.inputs['Strength'].default_value=0
    output=tree.nodes.new('NodeGroupOutput');tree.links.new(source.outputs['Image'],glare.inputs['Image']);tree.links.new(glare.outputs['Image'],output.inputs['Image'])

def snapshot():
    return {o.name:{'type':o.type,'location':list(o.location),'rotation':list(o.rotation_euler),'scale':list(o.scale),
                    'base_color':list(o.active_material.node_tree.nodes['Principled BSDF'].inputs['Base Color'].default_value) if o.type=='MESH' and o.active_material else None,
                    'light_color':list(o.data.color) if o.type=='LIGHT' else None,
                    'vertices':[list(v.co) for v in o.data.vertices] if o.type=='MESH' else None} for o in bpy.context.scene.objects}

def main():
    args=sys.argv[sys.argv.index('--')+1:];mode=args[0];out=Path(args[1]).resolve()
    if mode=='fixture-check':
        build_scene()
        cases=json.loads(Path('examples/vfx-review.json').read_text());before=snapshot()
        for case in cases:
            op=case['operation'];validate_operation(op,[op['target']]);apply_vfx(op)
            assert all(math.isclose(observe(op)[k],v,abs_tol=1e-5) for k,v in op.items() if k not in ('op','target'))
        assert before==snapshot()
        print('VFX_FIXTURE_CHECK_PASS',flush=True);return
    if mode=='reopen':
        blend=out/'review.blend';digest=hashlib.sha256(blend.read_bytes()).hexdigest()
        bpy.ops.wm.open_mainfile(filepath=str(blend),use_scripts=False)
        provenance=json.loads(bpy.data.texts['VFX_MODEL_PROVENANCE'].as_string())
        checks=[]
        for record in provenance['records']:
            actual=observe(record['operation']);expected=record['observed']
            checks.append(all(math.isclose(actual[k],v,abs_tol=1e-5) for k,v in expected.items()))
        ob=bpy.data.objects['ReviewSphere'];prior=ob.data.vertices[0].co.copy();ob.data.vertices[0].co.x+=.01
        editable=abs(ob.data.vertices[0].co.x-prior.x)>.009;ob.data.vertices[0].co=prior
        result={'passed':all(checks) and editable and digest==hashlib.sha256(blend.read_bytes()).hexdigest(),'properties_match_saved_result':all(checks),'vertices_editable':editable,'file_unchanged':digest==hashlib.sha256(blend.read_bytes()).hexdigest()}
        write(out/'reopen.json',result);assert result['passed'];return
    responses=Path(args[2]).resolve();cases=Path(args[3]).resolve()
    records=json.loads(responses.read_text())['records'];expected={r['id']:r for r in json.loads(cases.read_text())}
    if not all(r['intent_exact'] and r['schema_valid'] for r in records) or len(records)!=len(expected):
        raise ValueError('Model failed declared review intent; no manual corrections or cherry-picked rendering')
    out.mkdir(parents=True,exist_ok=False);build_scene();before=snapshot()
    scene=bpy.context.scene;scene.render.filepath=str(out/'before.png');bpy.ops.render.render(write_still=True)
    checked=[]
    for r in records:
        model_output=json.loads(r['raw'])
        case=expected[r['id']]
        wanted=case.get('expected_operation',case['operation'])
        scene_typed=r.get('output_protocol')=='scene_intent_v1'
        typed=r.get('output_protocol') in ('typed_intent_v1','scene_intent_v1')
        if scene_typed:
            from modeling_training.scene_intent_ops import compile_intent as compile_scene
            op=compile_scene(model_output,case['scene'])
        else:op=compile_intent(model_output,[wanted['target']]) if typed else model_output
        assert equivalent(op,wanted),'Declared model action does not match review request'
        if typed:
            assert equivalent(op,r['compiled_operation']),'Stored compilation differs from raw intent'
        validate_operation(op,[wanted['target']]);apply_vfx(op);actual=observe(op)
        assert all(math.isclose(actual[k],v,abs_tol=1e-5) for k,v in wanted.items() if k not in ('op','target'))
        checked.append({'id':r['id'],'operation':op,'observed':actual,'model_output':model_output,
                        'output_protocol':r.get('output_protocol','direct_operation')})
    assert before==snapshot(),'Unrequested geometry or object-transform changes'
    provenance={'records':checked,'geometry_and_transforms_preserved':True,'model_responses_sha256':hashlib.sha256(responses.read_bytes()).hexdigest(),'scene_source':'Authored procedural test fixture; not generated geometry','model_role':'Uncorrected single-operation settings; four prompts coordinated by this script','artistic_quality_approved':False}
    if any(r.get('output_protocol')=='scene_intent_v1' for r in records):
        from modeling_training.scene_intent_ops import compiler_sha256
        provenance['compiler_sha256']=compiler_sha256()
        provenance['model_role']='Raw scene-aware typed intents, literal direction/unit compilation, four prompts coordinated by host.'
    elif any(r.get('output_protocol')=='typed_intent_v1' for r in records):
        from modeling_training import intent_ops
        provenance['compiler_sha256']=hashlib.sha256(Path(intent_ops.__file__).read_bytes()).hexdigest()
        provenance['model_role']='Raw typed model intents compiled by declared unit rules; no scope/target repair. Four prompts coordinated by host.'
    bpy.data.texts.new('VFX_MODEL_PROVENANCE').write(json.dumps(provenance,indent=2));write(out/'execution.json',provenance)
    scene.render.filepath=str(out/'after.png');bpy.ops.wm.save_as_mainfile(filepath=str(out/'review.blend'));bpy.ops.render.render(write_still=True)
    print('VFX_REVIEW_PASS',flush=True)

if __name__=='__main__':main()
