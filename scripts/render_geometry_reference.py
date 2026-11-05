"""Render a supplied CC0-family humanoid as RGBA; never save over the source scene."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
from mathutils import Vector


parser=argparse.ArgumentParser()
parser.add_argument('--input',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
source,out=Path(args.input).resolve(),Path(args.output).resolve()
before=hashlib.sha256(source.read_bytes()).hexdigest()
out.mkdir(parents=True,exist_ok=False)
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
body=bpy.data.objects['Humanoid_Trained_Shape']
points=[body.matrix_world@Vector(v) for v in body.bound_box]
low=min(v.z for v in points)
high=max(v.z for v in points)
height=high-low
stage=bpy.data.objects.get('Review_Stage')
if stage is None or height<=0:
    raise ValueError('Unexpected reference scene')
stage.hide_render=True
scene=bpy.context.scene
camera=scene.camera
target=Vector((body.location.x,body.location.y,(low+high)/2))
camera.location=target+Vector((0,-3*height,0))
camera.rotation_euler=(target-camera.location).to_track_quat('-Z','Y').to_euler()
camera.data.type='ORTHO'
camera.data.ortho_scale=height*1.18
scene.render.engine='CYCLES'
scene.cycles.device='CPU'
scene.cycles.samples=16
scene.render.threads_mode='FIXED'
scene.render.threads=2
scene.render.film_transparent=True
scene.render.resolution_x=scene.render.resolution_y=640
scene.render.resolution_percentage=100
scene.render.image_settings.file_format='PNG'
scene.render.image_settings.color_mode='RGBA'
scene.render.filepath=str(out/'reference.png')
bpy.ops.render.render(write_still=True)
if hashlib.sha256(source.read_bytes()).hexdigest()!=before:
    raise RuntimeError('Original source scene changed')
(out/'provenance.json').write_text(json.dumps(dict(source_blend=str(source),source_sha256=before,
    original_preserved=True,reference_sha256=hashlib.sha256((out/'reference.png').read_bytes()).hexdigest(),
    scope='Supplied MPFB CC0-family anatomy rendered by authored Blender setup. Input reference, not a newly generated geometry result.'),indent=2),encoding='utf-8')
print('GEOMETRY_REFERENCE_SAVED',flush=True)
