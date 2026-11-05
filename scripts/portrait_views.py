"""Render diagnostic views from an existing organic project without saving over it."""
import argparse
import json
from pathlib import Path
import sys
import bpy
from mathutils import Vector
sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
from scene_forge.organic import select_render_device

parser=argparse.ArgumentParser()
parser.add_argument('--project',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.open_mainfile(filepath=str(Path(args.project).resolve()))
scene=bpy.context.scene
scene.render.engine='CYCLES'
scene.cycles.samples=16
select_render_device(scene)
scene.render.resolution_x,scene.render.resolution_y=640,360
scene.camera.data.dof.use_dof=False
# Diagnostic angles must not be overwritten by the original dolly's animation curves.
scene.camera.animation_data_clear()
scene.render.use_persistent_data=True
out=Path(args.output).resolve()
out.mkdir(parents=True,exist_ok=False)
origin=next(o for o in scene.objects if o.get('forge_role')=='actor').location.copy()
for name,position,frame in (
    ('front',(0,-5.4,2.9),1),
    ('profile',(5.4,-0.3,2.9),1),
    ('blink',(0,-5.4,2.9),round(scene.frame_end*0.3)),
):
    scene.frame_set(frame)
    scene.camera.location=origin+Vector(position)
    bpy.context.view_layer.update()
    scene.render.filepath=str(out/(name+'.png'))
    bpy.ops.render.render(write_still=True)
body=next(o for o in scene.objects if o.get('forge_role')=='organic_body')
(out/'inspection.json').write_text(json.dumps({
    'body_vertices':len(body.data.vertices), 'body_faces':len(body.data.polygons),
    'views':['front','profile','blink'], 'renderer':'CYCLES',
    'note':'Views are diagnostic renders, not an automatic artistic-quality score.'
},indent=2),encoding='utf-8')
print('PORTRAIT_VIEWS_COMPLETE',flush=True)
