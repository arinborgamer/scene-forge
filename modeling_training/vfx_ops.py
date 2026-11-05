"""Bounded CGI look-development controls; no simulations or movie generation."""
from scene_forge.schema import obj,enum,number,validate
from modeling_lab.operations import NAME,validate_plan
from modeling_training.corpus import wrapped,SYSTEM as MODELING_SYSTEM

SCHEMAS = {
 'light_power':obj({'op':enum('light_power'),'target':NAME,'watts':number(1,5000)}),
 'camera_lens':obj({'op':enum('camera_lens'),'target':NAME,'millimeters':number(12,200)}),
 'surface':obj({'op':enum('surface'),'target':NAME,'roughness':number(0,1),'metallic':number(0,1)}),
 'glow':obj({'op':enum('glow'),'target':NAME,'threshold':number(0,10),'strength':number(0,1)})
}
SYSTEM = MODELING_SYSTEM + '''
Additional CGI/VFX operations, editing EXISTING named scene elements:
{"op":"light_power","target":name,"watts":number}: area-light power in watts.
{"op":"camera_lens","target":name,"millimeters":number}: camera focal length in millimetres.
{"op":"surface","target":name,"roughness":number,"metallic":number}: existing mesh Principled material values 0..1.
{"op":"glow","target":name,"threshold":number,"strength":number}: existing compositor Glare node Threshold and Strength inputs; no node creation.
Unit conversions: 100 cm = 1 m; 1000 mm = 1 m; 1 cm = 10 mm; 1 kW = 1000 W. Percent values become fractions for material and glow strength.
The user identifies the existing object/node. Preserve its exact name. Return ONE operation only.'''

def validate_operation(op,existing):
    if isinstance(op,dict) and op.get('op') in SCHEMAS:
        validate(op,SCHEMAS[op['op']],'vfx_operation')
        if op['target'] not in existing:
            raise ValueError('Unknown CGI/VFX target')
        return op
    validate_plan(wrapped(op),existing)
    return op

def apply_vfx(op):
    import bpy
    kind=op['op']
    if kind=='glow':
        tree=bpy.context.scene.compositing_node_group
        node=tree.nodes.get(op['target']) if tree else None
        if node is None or node.bl_idname!='CompositorNodeGlare':
            raise ValueError('Target is not an existing compositor Glare node')
        node.inputs['Threshold'].default_value=op['threshold']
        node.inputs['Strength'].default_value=op['strength']
        return {'threshold':node.inputs['Threshold'].default_value,'strength':node.inputs['Strength'].default_value}
    target=bpy.data.objects.get(op['target'])
    if target is None:
        raise ValueError('Missing CGI/VFX object')
    if kind=='light_power':
        if target.type!='LIGHT' or target.data.type!='AREA':
            raise ValueError('Target must be an area light')
        target.data.energy=op['watts']
        return {'watts':target.data.energy}
    if kind=='camera_lens':
        if target.type!='CAMERA' or target.data.type!='PERSP':
            raise ValueError('Target must be a perspective camera')
        target.data.lens=op['millimeters']
        return {'millimeters':target.data.lens}
    if kind=='surface':
        mat=target.active_material if target.type=='MESH' else None
        bsdf=mat.node_tree.nodes.get('Principled BSDF') if mat and mat.use_nodes else None
        if bsdf is None or mat.users>1:
            raise ValueError('Target requires its own existing Principled material')
        bsdf.inputs['Roughness'].default_value=op['roughness']
        bsdf.inputs['Metallic'].default_value=op['metallic']
        return {'roughness':bsdf.inputs['Roughness'].default_value,'metallic':bsdf.inputs['Metallic'].default_value}
    raise ValueError('Unsupported VFX operation')
