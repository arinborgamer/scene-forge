"""Import a recorded neural mesh, render CPU previews and verify editable geometry."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import bpy
from mathutils import Matrix, Vector


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def geometry(mesh):
    result=hashlib.sha256()
    for vertex in mesh.vertices:
        result.update(struct.pack('<3f',*vertex.co))
    for polygon in mesh.polygons:
        result.update(struct.pack('<I',len(polygon.vertices)))
        result.update(struct.pack('<'+'I'*len(polygon.vertices),*polygon.vertices))
    return result.hexdigest()


def aim(obj,target):
    obj.rotation_euler=(Vector(target)-obj.location).to_track_quat('-Z','Y').to_euler()


def colors(mesh):
    result=hashlib.sha256()
    for attribute in mesh.color_attributes:
        result.update((attribute.name+attribute.domain+attribute.data_type).encode())
        for value in attribute.data:
            result.update(struct.pack('<4f',*value.color))
    return result.hexdigest()


def build(source,out):
    report=json.loads((source/'result.json').read_text())
    raw=source/'mesh.glb'
    if report.get('complete') is not True or report.get('provider')!='pretrained_TripoSR':
        raise ValueError('A completed actual TripoSR inference report is required')
    if digest(raw)!=report['outputs']['mesh.glb']:
        raise ValueError('Inference mesh changed')
    out.mkdir(parents=True,exist_ok=False)
    (out/'review_geometry_blender.py.snapshot').write_bytes(Path(__file__).read_bytes())
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(raw))
    meshes=[o for o in bpy.context.scene.objects if o.type=='MESH']
    if len(meshes)!=1 or any(o.type=='ARMATURE' for o in bpy.context.scene.objects):
        raise ValueError('Expected one unrigged generated mesh')
    obj=meshes[0]
    obj.name='TripoSR_Generated_Mesh'
    obj.data.name='TripoSR_Editable_Geometry'
    bounds=[obj.matrix_world@Vector(p) for p in obj.bound_box]
    height=max(p.z for p in bounds)-min(p.z for p in bounds)
    if height<=0:
        raise ValueError('Generated mesh has no vertical extent')
    scale=1.8/height
    obj.matrix_world=Matrix.Diagonal((scale,scale,scale,1.))@obj.matrix_world
    bounds=[obj.matrix_world@Vector(p) for p in obj.bound_box]
    obj.location.z-=min(p.z for p in bounds)
    for p in obj.data.polygons:
        p.use_smooth=True
    obj['provider']='pretrained TripoSR; static geometry, no trained rig or animation'
    obj['raw_glb_sha256']=digest(raw)
    scene=bpy.context.scene
    scene.unit_settings.system='METRIC'
    scene.render.engine='CYCLES'
    scene.cycles.device='CPU'
    scene.cycles.samples=16
    scene.cycles.use_denoising=True
    scene.render.threads_mode='FIXED'
    scene.render.threads=2
    scene.render.resolution_x=640
    scene.render.resolution_y=800
    scene.render.resolution_percentage=100
    scene.render.image_settings.file_format='PNG'
    scene.world=bpy.data.worlds.new('Neutral review world')
    scene.world.use_nodes=True
    scene.world.node_tree.nodes['Background'].inputs['Color'].default_value=(.07,.08,.1,1)
    for name,location,power in [('Key',(2,-3,4),500),('Fill',(-3,-1,2),300),('Rim',(1,3,3),600)]:
        data=bpy.data.lights.new(name,'AREA')
        light=bpy.data.objects.new(name,data)
        scene.collection.objects.link(light)
        light.location=location
        data.energy=power
        data.shape='DISK'
        data.size=3
        aim(light,(0,0,.9))
    data=bpy.data.cameras.new('ReviewCamera')
    camera=bpy.data.objects.new('ReviewCamera',data)
    scene.collection.objects.link(camera)
    scene.camera=camera
    data.type='ORTHO'
    data.ortho_scale=2.2
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active=obj
    # TripoSR's canonical azimuth-zero camera lies on +X, with Z up.
    for name,location in [('front',(4,0,1)),('three_quarter',(4,-2.5,1.4))]:
        camera.location=location
        aim(camera,(0,0,.9))
        scene.render.filepath=str(out/(name+'.png'))
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'mesh.blend'))
    if digest(raw)!=report['outputs']['mesh.glb']:
        raise RuntimeError('Original generated GLB changed')
    result=dict(complete=True,raw_glb=str(raw),raw_glb_sha256=digest(raw),
                inference_result=str(source/'result.json'),inference_result_sha256=digest(source/'result.json'),
                mesh=obj.name,vertices=len(obj.data.vertices),polygons=len(obj.data.polygons),
                geometry_sha256=geometry(obj.data),color_attributes_sha256=colors(obj.data),
                blend_sha256=digest(out/'mesh.blend'),review_script_sha256=digest(__file__),
                front_camera_axis='+X',
                normalization=dict(display_height_m=1.8,uniform_scale=scale,
                                   note='Authored presentation scaling; input has no measured physical units.'),
                rig_count=0,animation_generated=False,human_visual_review='pending',
                scope='Editable static pretrained-model geometry, authored camera/lighting; not a trained character rig or cinematic scene.')
    (out/'build.json').write_text(json.dumps(result,indent=2),encoding='utf-8')


def reopen(out):
    report=json.loads((out/'build.json').read_text())
    if report.get('review_script_sha256')!=digest(__file__):
        raise ValueError('Review implementation changed between build and fresh reopen')
    saved=out/'mesh.blend'
    before=digest(saved)
    bpy.ops.wm.open_mainfile(filepath=str(saved),load_ui=False,use_scripts=False)
    obj=bpy.data.objects[report['mesh']]
    intact=geometry(obj.data)==report['geometry_sha256']
    vertex=obj.data.vertices[0]
    original=vertex.co.copy()
    vertex.co.x+=.001
    obj.data.update()
    bpy.context.view_layer.update()
    evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
    changed=(evaluated.vertices[0].co-original).length>.0005
    obj.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
    obj.data.vertices[0].co=original
    obj.data.update()
    bpy.context.view_layer.update()
    checks=dict(saved_geometry_matches=intact,actual_vertex_edit=changed,
                saved_vertex_colors_match=colors(obj.data)==report['color_attributes_sha256'],
                edit_restored=geometry(obj.data)==report['geometry_sha256'],
                saved_file_unchanged=digest(saved)==before==report['blend_sha256'],
                original_glb_unchanged=digest(report['raw_glb'])==report['raw_glb_sha256'],
                no_invented_rig=not any(o.type=='ARMATURE' for o in bpy.context.scene.objects))
    with (out/'reopen.json').open('x',encoding='utf-8') as stream:
        json.dump(dict(passed=all(checks.values()),checks=checks,rig_generated=False,
                       scope='Fresh Blender reload and editable mesh only; visual/anatomy acceptance separate.'),stream,indent=2)
    if not all(checks.values()):
        raise RuntimeError('Fresh editable geometry checks failed')


parser=argparse.ArgumentParser()
parser.add_argument('mode',choices=['build','reopen'])
parser.add_argument('--source')
parser.add_argument('--output',required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
out=Path(args.output).resolve()
if args.mode=='build':
    if not args.source:
        parser.error('build requires --source')
    build(Path(args.source).resolve(),out)
else:
    reopen(out)
print('GEOMETRY_REVIEW_'+args.mode.upper()+'_PASS',flush=True)
