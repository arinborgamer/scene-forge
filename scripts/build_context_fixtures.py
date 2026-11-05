"""Create three real selectable elements per diagnostic case; export observed names."""
import hashlib
import json
from pathlib import Path
import sys

import bpy

root=Path(sys.argv[sys.argv.index('--')+1]).resolve()
rows=json.loads((root/'cases.json').read_text())
out=root/'fixtures'
out.mkdir(exist_ok=False)
observations=[]
for row in rows:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene=[]
    for i,name in enumerate(row['planned_names']):
        if row['element_type']=='MESH':
            bpy.ops.mesh.primitive_cube_add(size=1,location=(2*i,0,0))
            obj=bpy.context.object
            obj.name=name
            scene.append(dict(name=obj.name,type=obj.type))
        elif row['element_type']=='GLARE_NODE':
            sc=bpy.context.scene
            if sc.compositing_node_group is None:
                sc.compositing_node_group=bpy.data.node_groups.new('ContextCompositor','CompositorNodeTree')
            node=sc.compositing_node_group.nodes.new('CompositorNodeGlare')
            node.name=name
            scene.append(dict(name=node.name,type='GLARE_NODE'))
        else:
            raise ValueError('Unsupported diagnostic fixture type')
    if [e['name'] for e in scene]!=row['planned_names']:
        raise ValueError('Fixture names did not survive actual Blender creation')
    path=out/(row['id']+'.blend')
    bpy.ops.wm.save_as_mainfile(filepath=str(path))
    observations.append(dict(id=row['id'],scene=scene,blend=str(path),
                             blend_sha256=hashlib.sha256(path.read_bytes()).hexdigest()))
with (root/'observed-catalogs.json').open('x',encoding='utf-8') as stream:
    json.dump(observations,stream,indent=2)
print('CONTEXT_FIXTURES_OBSERVED',len(observations),flush=True)
