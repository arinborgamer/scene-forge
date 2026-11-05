"""Small Blender fixture and independent observation for CGI operation tests."""
def fixture(op):
    import bpy
    bpy.ops.wm.read_factory_settings(use_empty=True)
    name=op['target'];kind=op['op']
    if kind=='light_power':
        data=bpy.data.lights.new(name,'AREA');data.energy=10
        ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob)
    elif kind=='camera_lens':
        data=bpy.data.cameras.new(name);data.lens=12
        ob=bpy.data.objects.new(name,data);bpy.context.collection.objects.link(ob)
    elif kind=='surface':
        bpy.ops.mesh.primitive_uv_sphere_add();ob=bpy.context.object;ob.name=name
        mat=bpy.data.materials.new('FixtureMaterial');mat.use_nodes=True;ob.data.materials.append(mat)
    elif kind=='glow':
        tree=bpy.data.node_groups.new('FixtureCompositor','CompositorNodeTree')
        bpy.context.scene.compositing_node_group=tree
        node=tree.nodes.new('CompositorNodeGlare');node.name=name

def observe(op):
    import bpy
    name=op['target'];kind=op['op']
    if kind=='light_power': return {'watts':bpy.data.objects[name].data.energy}
    if kind=='camera_lens': return {'millimeters':bpy.data.objects[name].data.lens}
    if kind=='surface':
        n=bpy.data.objects[name].active_material.node_tree.nodes.get('Principled BSDF')
        return {'roughness':n.inputs['Roughness'].default_value,'metallic':n.inputs['Metallic'].default_value}
    n=bpy.context.scene.compositing_node_group.nodes[name]
    return {'threshold':n.inputs['Threshold'].default_value,'strength':n.inputs['Strength'].default_value}
