"""Quick single-frame visual gate before committing to a full animation render."""
import json
from pathlib import Path
import sys
import bpy
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scene_forge.schema import validate_scene
from scene_forge.blender_scene import build, inspect_scene

root=Path(__file__).resolve().parent.parent
spec=validate_scene(json.loads((root/'examples/organic-greeting.json').read_text()))
scene,rigs=build(spec)
assert inspect_scene(spec,scene,rigs)['passed']
scene.frame_set(scene.frame_end//2)
scene.render.resolution_x,scene.render.resolution_y=800,450
scene.cycles.samples=16
output=root/'tmp'/'greeting-check.png'
scene.render.filepath=str(output)
bpy.ops.render.render(write_still=True)
print('GREETING_VISUAL_GATE',str(output),flush=True)
