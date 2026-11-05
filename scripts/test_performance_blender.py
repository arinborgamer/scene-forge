"""Real evaluated geometry: limb deformation, planted feet, wind, framing and detail."""
import json
from pathlib import Path
import sys
import bpy
from bpy_extras.object_utils import world_to_camera_view
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scene_forge.schema import organic_scene
from scene_forge.blender_scene import build, inspect_scene

spec = organic_scene()
spec['duration_seconds'] = 3
spec['camera'] = 'full_body'
spec['actors'][0]['action'] = 'wave'
scene, rigs = build(spec)
rig = rigs[0]
assert inspect_scene(spec, scene, rigs)['passed']
body = next(o for o in scene.objects if o.get('forge_role') == 'organic_body')
assert len(body.data.vertices) > 30000
sub = next(m for m in body.modifiers if m.type == 'SUBSURF')
assert sub.render_levels == 2
sub.show_viewport = False
feet = [v.index for v in body.data.vertices if v.co.z < 0.14]
legs = [v.index for v in body.data.vertices if v.co.z < 1 and abs(v.co.x) < 0.38]
hand = [v.index for v in body.data.vertices if v.co.x > 0.5 and 0.84 < v.co.z < 1.04]
assert len(feet) > 20 and len(hand) > 20
for vertex in body.data.vertices:
    if vertex.co.x > 0.42 and vertex.co.z < 1.06:
        weights = {body.vertex_groups[g.group].name: g.weight for g in vertex.groups}
        assert weights.get('hand_r', 0) > 0.99, (tuple(vertex.co),weights)

def positions(frame):
    scene.frame_set(frame)
    graph = bpy.context.evaluated_depsgraph_get()
    evaluated = body.evaluated_get(graph)
    return [evaluated.matrix_world @ v.co for v in evaluated.data.vertices]

rest = positions(1)
raised = positions(scene.frame_end//2)
foot_drift = max((raised[i]-rest[i]).length for i in feet)
hand_travel = sum((raised[i]-rest[i]).length for i in hand)/len(hand)
assert foot_drift < 0.001, foot_drift
assert max((raised[i]-rest[i]).length for i in legs) < 0.001
assert hand_travel > 0.5, hand_travel
# Sample the actual skin across the entire gesture, including lateral arm extent.
for frame in range(1, scene.frame_end+1, 4):
    verts = positions(frame)
    graph = bpy.context.evaluated_depsgraph_get()
    camera = scene.camera.evaluated_get(graph)
    for v in verts[::12]:
        p = world_to_camera_view(scene, camera, v)
        assert 0.01 < p.x < 0.99 and 0.01 < p.y < 0.99 and p.z > 0, (frame, list(p))
foliage = [o for o in scene.objects if o.get('forge_role') == 'wind_foliage']
assert len(foliage) >= 200
blade = foliage[0]
keys = blade.data.shape_keys.key_blocks
assert (keys['Wind'].data[1].co-keys['Basis'].data[1].co).length < 1e-6
assert max((a.co-b.co).length for a,b in zip(keys['Wind'].data, keys['Basis'].data)) > 0.02
scene.frame_set(1)
before = keys['Wind'].value
scene.frame_set(24)
assert abs(before-keys['Wind'].value) > 0.01
print('PERFORMANCE_PASS', json.dumps({'base_vertices':len(body.data.vertices),
    'base_faces':len(body.data.polygons), 'bones':len(rig.data.bones),
    'foot_drift_m':foot_drift, 'mean_hand_travel_m':hand_travel,
    'wind_leaves':len(foliage), 'framing_samples':len(range(1,scene.frame_end+1,4))}))
