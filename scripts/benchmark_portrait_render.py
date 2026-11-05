"""Compare reusable render settings against a saved scene; never overwrite its project."""
import argparse
import json
from pathlib import Path
import sys
import time
import bpy

parser=argparse.ArgumentParser()
parser.add_argument('--project',required=True)
parser.add_argument('--output',required=True)
parser.add_argument('--engine',choices=('CYCLES','BLENDER_EEVEE'),default='BLENDER_EEVEE')
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
bpy.ops.wm.open_mainfile(filepath=str(Path(args.project).resolve()))
scene=bpy.context.scene
scene.render.engine=args.engine
scene.render.use_persistent_data=True
scene.render.resolution_x,scene.render.resolution_y=640,360
scene.cycles.samples=12
if args.engine=='CYCLES':
    sys.path.insert(0,str(Path(__file__).resolve().parent.parent))
    from scene_forge.organic import select_render_device
    select_render_device(scene)
out=Path(args.output).resolve()
out.mkdir(parents=True,exist_ok=False)
timings=[]
for frame in (1,43,72):
    scene.frame_set(frame)
    scene.render.filepath=str(out/f'frame_{frame:04d}.png')
    began=time.monotonic()
    bpy.ops.render.render(write_still=True)
    timings.append({'frame':frame,'seconds':time.monotonic()-began})
    print('RENDER_TIMING',timings[-1],flush=True)
(out/'timings.json').write_text(json.dumps(timings,indent=2),encoding='utf-8')
