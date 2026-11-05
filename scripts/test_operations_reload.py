"""Serialization regression: unchanged saved scenes pass, actual edits fail."""
import json
import sys
import tempfile
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
from modeling_lab.operation_blender import mesh_state

bpy.ops.mesh.primitive_cube_add()
obj = bpy.context.object
obj.modifiers.new('test_bevel', 'BEVEL').width = .01
bpy.context.view_layer.update()
keys = ('mesh_sha256', 'world_matrix', 'weights_sha256', 'materials', 'modifiers')
expected = json.loads(json.dumps(mesh_state(obj)))
with tempfile.TemporaryDirectory(prefix='scene-forge-reload-') as folder:
    path = str(Path(folder) / 'fixture.blend')
    name = obj.name
    bpy.ops.wm.save_as_mainfile(filepath=path)
    bpy.ops.wm.open_mainfile(filepath=path, use_scripts=False)
    obj = bpy.data.objects[name]
    actual = mesh_state(obj)
    differences = [k for k in keys if actual[k] != expected[k]]
    assert not differences, f'Unchanged saved scene differs: {differences}'
    obj.data.vertices[0].co.x += .02
    assert mesh_state(obj)['mesh_sha256'] != expected['mesh_sha256']
    obj.location.x += .1
    bpy.context.view_layer.update()
    assert mesh_state(obj)['world_matrix'] != expected['world_matrix']
print('OPERATIONS_RELOAD_REGRESSION_PASS', flush=True)
