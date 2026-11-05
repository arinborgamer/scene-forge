"""Run in real Blender: topology, animation, and meaningful morphology changes."""
from pathlib import Path
import sys

import bpy
import bmesh
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from scene_forge.schema import organic_scene
from scene_forge.blender_scene import build, inspect_scene

spec=organic_scene()
scene,rigs=build(spec)
report=inspect_scene(spec,scene,rigs)
assert report['passed'], report
body=next(o for o in scene.objects if o.get('forge_role')=='organic_body')
bm=bmesh.new()
bm.from_mesh(body.data)
remaining=set(bm.verts)
components=0
while remaining:
    components+=1
    queue=[remaining.pop()]
    while queue:
        vertex=queue.pop()
        for edge in vertex.link_edges:
            other=edge.other_vert(vertex)
            if other in remaining:
                remaining.remove(other)
                queue.append(other)
assert components==1, f'Expected one connected skin component; found {components}'
bm.free()
width=max(abs(v.co.x) for v in body.data.vertices if 2.6<v.co.z<3.15)
scene.frame_set(1)
head_start=rigs[0].pose.bones['head'].matrix.copy()
lids=[o for o in scene.objects if o.type=='MESH' and o.data.shape_keys and o.data.shape_keys.key_blocks.get('Blink')]
assert len(lids)==4
assert all(o.data.shape_keys.key_blocks['Blink'].value==0 for o in lids)
scene.frame_set(round(scene.frame_end*0.30))
assert all(o.data.shape_keys.key_blocks['Blink'].value>0.99 for o in lids)
assert rigs[0].pose.bones['head'].matrix!=head_start
# Pupils must remain inside the closed lid ellipsoid in rest coordinates.
for pupil in (o for o in scene.objects if o.name.startswith('Vertical pupil')):
    center_x=-0.205 if sum(v.co.x for v in pupil.data.vertices)<0 else 0.205
    for vertex in pupil.data.vertices:
        x,y,z=vertex.co
        assert ((x-center_x)/0.183)**2+((y+0.275)/0.143)**2+((z-2.885)/0.165)**2<1
spec['actors'][0]['morphology']['head_width']=1.2
spec['actors'][0]['morphology']['ear_length']=1.3
scene,rigs=build(spec)
body=next(o for o in scene.objects if o.get('forge_role')=='organic_body')
new_width=max(abs(v.co.x) for v in body.data.vertices if 2.6<v.co.z<3.15)
assert new_width>width*1.1, (width,new_width)
assert inspect_scene(spec,scene,rigs)['passed']
print('ORGANIC_TOPOLOGY_ANIMATION_MORPHOLOGY_PASS',len(body.data.vertices),components,width,new_width)
