"""Reopen a generated project, verify its baked actions, optionally render a draft.

Run with background Blender and -- --project scene.blend --report report.json.
Never saves changes to the input .blend.
"""
import argparse
import json
from pathlib import Path
import sys
import bpy

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scene_forge.blender_scene import inspect_scene

parser = argparse.ArgumentParser()
parser.add_argument('--project', required=True)
parser.add_argument('--report', required=True)
parser.add_argument('--preview-dir')
args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
args.report = str(Path(args.report).resolve())
if args.preview_dir:
    args.preview_dir = str(Path(args.preview_dir).resolve())
bpy.ops.wm.open_mainfile(filepath=str(Path(args.project).resolve()))
scene = bpy.context.scene
spec = json.loads(bpy.data.texts['Scene Forge - scene.json'].as_string())
rigs = [bpy.data.objects[item['id']] for item in spec['actors']]
report = inspect_scene(spec, scene, rigs)
assert report['passed'], report
rig = rigs[0]
curves = [curve for layer in rig.animation_data.action.layers for strip in layer.strips
          for bag in strip.channelbags for curve in bag.fcurves]
head_curve = next(c for c in curves if c.data_path == 'pose.bones["head"].rotation_quaternion')
point = head_curve.keyframe_points[-1]
before = point.co.y
scene.frame_set(scene.frame_end)
property_before = rig.pose.bones['head'].rotation_quaternion[head_curve.array_index]
point.co.y += .1
head_curve.update()
scene.frame_set(1)
scene.frame_set(scene.frame_end)
property_after = rig.pose.bones['head'].rotation_quaternion[head_curve.array_index]
assert abs(property_after-property_before) > .09
point.co.y = before
head_curve.update()
scene.frame_set(1)
report['reopened_project'] = str(Path(args.project).resolve())
report['in_memory_keyframe_edit_verified'] = True
report['original_project_saved'] = False
report['rig_keyframe_points'] = sum(len(c.keyframe_points) for c in curves)
Path(args.report).write_text(json.dumps(report, indent=2))
print('SAVED_SEQUENCE_PASS', report['rig_keyframe_points'])
if args.preview_dir:
    out = Path(args.preview_dir)
    out.mkdir(parents=True, exist_ok=False)
    scene.render.engine = 'BLENDER_WORKBENCH'
    scene.render.resolution_x, scene.render.resolution_y = 640, 360
    scene.render.resolution_percentage = 100
    scene.display.shading.light = 'STUDIO'
    scene.display.shading.color_type = 'MATERIAL'
    scene.display.shading.show_shadows = True
    scene.display.shading.show_cavity = True
    scene.display.shading.background_type = 'WORLD'
    rate = 6
    for index in range(round(spec['duration_seconds']*rate)):
        frame = 1+index*scene.render.fps/rate
        scene.frame_set(int(frame), subframe=frame-int(frame))
        scene.render.filepath = str(out/f'{index+1:04d}.png')
        bpy.ops.render.render(write_still=True)
    print('DRAFT_FRAMES_READY', out)
