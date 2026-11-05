"""Generic executor fixture. Not a model example or a prompt-specific asset recipe."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
from modeling_lab.operation_blender import execute, mesh_state, inspect_objects

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
ops = [
    dict(op='mesh', id='sheet', vertices=[[0, 0, 0], [.2, 0, 0], [.2, .3, 0], [0, .3, 0]], faces=[[0, 1, 2, 3]]),
    dict(op='modifier', target='sheet', kind='solidify', value=.01),
    dict(op='primitive', id='part', kind='box', location=[0, 0, .5], dimensions=[.2, .3, .4], rotation_degrees=[0, 0, 0]),
    dict(op='modifier', target='part', kind='bevel', value=.01),
    dict(op='material', target='part', color='#ff8800', metallic=.3, roughness=.4),
    dict(op='duplicate', source='part', id='copy', translation=[.8, 0, 0]),
    dict(op='transform', target='copy', translation=[0, .1, 0], scale=[1.2, 1, 1], rotation_degrees=[0, 0, 20]),
    dict(op='deform', target='part', center=[0, 0, 0], radius=[.5, .5, .5], scale=[1.1, 1, 1], translation=[0, 0, .01]),
    dict(op='loft', id='surface', location=[-1, 0, 0], rings=[dict(z=0, radius_x=.1, radius_y=.2, center_y=0), dict(z=.5, radius_x=.3, radius_y=.2, center_y=0), dict(z=.8, radius_x=.1, radius_y=.1, center_y=0)]),
    dict(op='modifier', target='surface', kind='subdivide', value=1),
]
trace = execute(dict(title='generic fixture', operations=ops, unsupported_requests=[]), [])
assert set(trace['created']) == {'sheet', 'part', 'copy', 'surface'}
assert trace['operations'][7]['changed_vertices'] == 8
assert mesh_state(bpy.data.objects['part'])['mesh_sha256'] != mesh_state(bpy.data.objects['copy'])['mesh_sha256']
states = inspect_objects(trace['created'])
assert all(s['evaluated_vertices'] > 0 and s['zero_area_faces'] == 0 for s in states)
print('GENERIC_OPERATIONS_BLENDER_PASS', flush=True)
