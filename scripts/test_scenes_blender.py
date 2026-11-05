"""Exercise alternate camera, material and actor configurations in real Blender."""
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scene_forge.schema import demo_scene, validate_scene
from scene_forge.blender_scene import build, inspect_scene

scene = demo_scene()
scene["duration_seconds"] = 3
scene["camera"] = "orbit"
scene["lighting"] = "moonlight"
scene["style"] = "low_poly"
scene["actors"][0].update(start=[-1, 0, 0], end=[-1, 0, 0], action="wave")
scene["actors"].append({"id": "friend", "color": "#4678dd", "start": [1, 0, 0],
                         "end": [1, 0, 0], "action": "idle", "walk_until": 0.5})
scene["props"] = [
    {"id": "metal_cube", "kind": "cube", "position": [3, 2, 0], "scale": 1, "color": "#bb8833", "material": "metal"},
    {"id": "glass_orb", "kind": "sphere", "position": [-3, 2, 0], "scale": 1, "color": "#88ccee", "material": "glass"},
    {"id": "pillar", "kind": "pillar", "position": [0, 4, 0], "scale": 1, "color": "#bbbbaa", "material": "matte"},
]
validate_scene(scene)
blender_scene, rigs = build(scene)
report = inspect_scene(scene, blender_scene, rigs)
assert report["passed"], report
assert len(rigs) == 2
print("ALTERNATE_SCENE_PASS", len(report["checks"]))
