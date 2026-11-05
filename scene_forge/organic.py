"""Editable procedural creature anatomy and a portrait set. No neural mesh generation.

The semantic controls are intentionally bounded. Shape, skin, rig, eyelids and set are
ordinary Blender data; model output never becomes executable code.
"""
import math
import random

import bpy
import bmesh
from mathutils import Vector


def smooth(obj):
    for face in obj.data.polygons:
        face.use_smooth = True
    return obj


def ellipsoid(name, location, scale, material=None, segments=32, rings=20):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    if material:
        obj.data.materials.append(material)
    return smooth(obj)


def surface(name, verts, faces, material):
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return smooth(obj)


def tube(name, points, radius, material):
    curve = bpy.data.curves.new(name, 'CURVE')
    curve.dimensions = '3D'
    curve.resolution_u = 12
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    spline = curve.splines.new('BEZIER')
    spline.bezier_points.add(len(points) - 1)
    for point, co in zip(spline.bezier_points, points):
        point.co = co
        point.handle_left_type = point.handle_right_type = 'AUTO'
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def shader(name, color, roughness=0.45, metal=0, emission=0):
    from scene_forge.blender_scene import rgba
    mat = bpy.data.materials.new(name)
    mat.use_nodes = True
    mat.diffuse_color = rgba(color)
    node = mat.node_tree.nodes.get('Principled BSDF')
    node.inputs['Base Color'].default_value = rgba(color)
    node.inputs['Roughness'].default_value = roughness
    node.inputs['Metallic'].default_value = metal
    node.inputs['Emission Color'].default_value = rgba(color)
    node.inputs['Emission Strength'].default_value = emission
    return mat


def skin_material(color):
    from scene_forge.blender_scene import rgba
    mat = shader('Living skin — pigment, pores and subsurface', color, 0.48)
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Subsurface Weight'].default_value = 0.12
    bsdf.inputs['Subsurface Radius'].default_value = (0.5, 0.25, 0.12)
    bsdf.inputs['Subsurface Scale'].default_value = 0.08
    noise = nodes.new('ShaderNodeTexNoise')
    noise.name = 'Skin pigment variation'
    noise.inputs['Scale'].default_value = 7
    noise.inputs['Detail'].default_value = 4
    ramp = nodes.new('ShaderNodeValToRGB')
    c = rgba(color)
    ramp.color_ramp.elements[0].position = 0.18
    ramp.color_ramp.elements[0].color = tuple(v * 0.25 for v in c[:3]) + (1,)
    ramp.color_ramp.elements[1].position = 0.82
    ramp.color_ramp.elements[1].color = tuple(min(1, v * 1.35 + 0.035) for v in c[:3]) + (1,)
    links.new(noise.outputs['Fac'], ramp.inputs[0])
    links.new(ramp.outputs['Color'], bsdf.inputs['Base Color'])
    pores = nodes.new('ShaderNodeTexNoise')
    pores.name = 'Fine pores'
    pores.inputs['Scale'].default_value = 145
    pores.inputs['Detail'].default_value = 2
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.22
    bump.inputs['Distance'].default_value = 0.012
    links.new(pores.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


def bind(obj, rig, bone):
    # Preserve initial world placement while following a bone's rest-to-pose transform.
    if obj.type == 'CURVE':
        bpy.ops.object.select_all(action='DESELECT')
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.convert(target='MESH')
        obj = bpy.context.object
    obj.parent = rig
    group = obj.vertex_groups.new(name=bone)
    group.add(list(range(len(obj.data.vertices))), 1, 'REPLACE')
    arm = obj.modifiers.new('Follow skeleton', 'ARMATURE')
    arm.object = rig
    return obj


def make_rig(identifier):
    data = bpy.data.armatures.new(identifier + ' skeleton')
    rig = bpy.data.objects.new(identifier, data)
    bpy.context.collection.objects.link(rig)
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    bpy.ops.object.mode_set(mode='EDIT')
    bones = {
        'root': ((0, 0, 0), (0, 0, 1.05), None),
        'spine': ((0, 0, 1.05), (0, 0, 1.85), 'root'),
        'neck': ((0, 0, 1.85), (0, 0, 2.35), 'spine'),
        'head': ((0, 0, 2.35), (0, 0, 3.35), 'neck'),
    }
    for side, sign in (('l', -1), ('r', 1)):
        shoulder, elbow = (sign*0.38, 0, 1.92), (sign*0.53, -0.02, 1.48)
        wrist, fingers = (sign*0.58, -0.065, 1.13), (sign*0.59, -0.075, 0.86)
        hip, knee = (sign*0.18, 0, 1.05), (sign*0.195, 0, 0.57)
        ankle, toes = (sign*0.20, 0, 0.13), (sign*0.20, -0.25, 0.08)
        bones.update({
            'arm_'+side: (shoulder, elbow, 'spine'),
            'forearm_'+side: (elbow, wrist, 'arm_'+side),
            'hand_'+side: (wrist, fingers, 'forearm_'+side),
            'leg_'+side: (hip, knee, 'root'),
            'shin_'+side: (knee, ankle, 'leg_'+side),
            'foot_'+side: (ankle, toes, 'shin_'+side),
        })
    for name, (a, b, parent) in bones.items():
        bone = data.edit_bones.new(name)
        bone.head, bone.tail = a, b
        if parent:
            bone.parent = data.edit_bones[parent]
    bpy.ops.object.mode_set(mode='OBJECT')
    rig.show_in_front = True
    rig['forge_id'], rig['forge_role'] = identifier, 'actor'
    rig['forge_character_provider'] = 'procedural_organic_v2'
    rig['expected_bones'] = len(bones)
    return rig


def fused_body(identifier, controls, mat, rig):
    w, muzzle, cheeks = controls['head_width'], controls['muzzle_length'], controls['cheek_fullness']
    parts = []
    def part(name, pos, size):
        obj = ellipsoid(name, pos, size)
        parts.append(obj)
        return obj
    part('Pelvis', (0, 0.015, 1.05), (0.29, 0.23, 0.29))
    part('Abdomen', (0, 0, 1.43), (0.26, 0.20, 0.42))
    part('Ribcage', (0, 0.015, 1.82), (0.40, 0.24, 0.37))
    part('Neck', (0, 0.02, 2.21), (0.17, 0.17, 0.37))
    part('Cranium', (0, 0.035, 2.87), (0.43 * w, 0.34, 0.53))
    part('Jaw', (0, -0.07, 2.56), (0.29 * w, 0.25, 0.22))
    part('Chin', (0, -0.20, 2.51), (0.17, 0.15, 0.11))
    part('Nose bridge', (0, -0.265, 2.82), (0.10, 0.135 * muzzle, 0.20))
    part('Nose tip', (0, -0.35, 2.72), (0.125, 0.105 * muzzle, 0.075))
    for side in (-1, 1):
        part('Cheek', (side * 0.245 * w, -0.16, 2.70), (0.19 * cheeks, 0.21, 0.15))
        brow = part('Brow', (side * 0.20 * w, -0.23, 3.035 + controls['brow_height']), (0.23, 0.15, 0.09))
        brow.rotation_euler.y = side * 0.15
        part('Shoulder', (side * 0.39, 0, 1.94), (0.20, 0.20, 0.23))
        part('Upper arm', (side * 0.48, 0, 1.67), (0.135, 0.14, 0.34))
        part('Forearm', (side * 0.55, -0.035, 1.30), (0.105, 0.12, 0.30))
        part('Palm', (side * 0.59, -0.07, 1.05), (0.115, 0.085, 0.16))
        for finger in range(3):
            part('Finger', (side * (0.52 + finger * 0.065), -0.075, 0.91), (0.029, 0.038, 0.13))
        part('Thumb', (side * 0.47, -0.11, 1.05), (0.05, 0.05, 0.10))
        part('Thigh', (side * 0.18, 0.01, 0.8), (0.16, 0.18, 0.34))
        part('Shin', (side * 0.20, 0.005, 0.40), (0.105, 0.13, 0.32))
        part('Foot', (side * 0.20, -0.12, 0.10), (0.135, 0.24, 0.11))
    bpy.ops.object.select_all(action='DESELECT')
    for obj in parts:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.join()
    body = bpy.context.object
    body.name = identifier + ' | connected sculpt surface'
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
    remesh = body.modifiers.new('Fused anatomy', 'REMESH')
    remesh.mode = 'VOXEL'
    remesh.voxel_size = 0.018
    remesh.use_smooth_shade = True
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    soften = body.modifiers.new('Surface relaxation', 'SMOOTH')
    soften.factor, soften.iterations = 0.6, 4
    bpy.ops.object.modifier_apply(modifier=soften.name)
    body.data.materials.clear()
    body.data.materials.append(mat)
    smooth(body)
    body.parent = rig
    from scene_forge.organic_motion import skin_weights
    groups = {bone.name: body.vertex_groups.new(name=bone.name) for bone in rig.data.bones}
    for vertex in body.data.vertices:
        weights = skin_weights(vertex.co.x, vertex.co.z)
        for bone, weight in weights.items():
            if weight > 0:
                groups[bone].add([vertex.index], weight, 'REPLACE')
    arm = body.modifiers.new('Weighted character skeleton', 'ARMATURE')
    arm.object = rig
    arm.use_deform_preserve_volume = True
    sub = body.modifiers.new('Sculpt surface subdivision', 'SUBSURF')
    sub.levels, sub.render_levels = 1, 2
    body['forge_role'] = 'organic_body'
    body['sculpt_note'] = 'Editable connected voxel-remeshed surface; not animation-ready quad retopology.'
    return body


def leaf(name, start, end, width, material, curl=0.08):
    start, end = Vector(start), Vector(end)
    axis = end-start
    sideways = axis.cross(Vector((0, -1, 0))).normalized()
    vertices, faces = [], []
    for j in range(13):
        t = j/12
        center = start.lerp(end, t) + Vector((0, -curl*math.sin(t*math.pi), 0))
        span = width * math.sin(math.pi*t) ** 0.7 + 0.002
        for across in (-1, 0, 1):
            vertices.append(center + sideways*span*across + Vector((0, 0.03*abs(across)*math.sin(t*math.pi), 0)))
    for j in range(12):
        for k in range(2):
            a=j*3+k
            faces.append((a,a+1,a+4,a+3))
    obj = surface(name, vertices, faces, material)
    solid = obj.modifiers.new('Membrane thickness', 'SOLIDIFY')
    solid.thickness = 0.015
    sub = obj.modifiers.new('Organic curvature', 'SUBSURF')
    sub.levels = sub.render_levels = 2
    return obj


def eyelid(name, center, upper, material, rig, scene):
    # A spherical shell sweeps over the eye; the closed key reaches the optical axis.
    rx, ry, rz = 0.183, 0.143, 0.165
    verts, closed, faces = [], [], []
    for row in range(7):
        s=row/6
        for col in range(25):
            phi = math.pi*col/24 + (0 if upper else math.pi)
            for target, opening in ((verts, 1.03), (closed, 0.015)):
                theta = opening + (1.83-opening)*s
                target.append(Vector(center)+Vector((rx*math.sin(theta)*math.cos(phi),
                    -ry*math.cos(theta), rz*math.sin(theta)*math.sin(phi))))
    for row in range(6):
        for col in range(24):
            a=row*25+col
            faces.append((a,a+1,a+26,a+25))
    obj=surface(name, verts, faces, material)
    obj.shape_key_add(name='Basis')
    key=obj.shape_key_add(name='Blink')
    for vertex, co in zip(key.data, closed):
        vertex.co=co
    # Two restrained blinks, kept inside any supported clip duration.
    for frame in (1, scene.frame_end):
        key.value=0
        key.keyframe_insert('value', frame=frame)
    for ratio in (0.30, 0.78):
        center_frame=round(scene.frame_end*ratio)
        for offset, value in ((-3, 0), (0, 1), (2, 1), (5, 0)):
            key.value=value
            key.keyframe_insert('value', frame=max(1,min(scene.frame_end, center_frame+offset)))
    key.value=0
    sub=obj.modifiers.new('Smooth eyelid', 'SUBSURF')
    sub.levels=sub.render_levels=1
    bind(obj, rig, 'head')
    return obj


def create_character(item, scene):
    from scene_forge.schema import DEFAULT_MORPHOLOGY
    controls=item.get('morphology', DEFAULT_MORPHOLOGY)
    skin=skin_material(item['color'])
    dark=shader('Deep teal creases', '#102d2c', 0.6)
    iris=shader('Amber iris', '#d99537', 0.32, 0.05)
    sclera=shader('Olive sclera', '#3c4931', 0.27)
    nodes,links=iris.node_tree.nodes,iris.node_tree.links
    grain=nodes.new('ShaderNodeTexNoise')
    grain.inputs['Scale'].default_value=32
    grain.inputs['Detail'].default_value=3
    pigment=nodes.new('ShaderNodeValToRGB')
    pigment.color_ramp.elements[0].position=0.3
    pigment.color_ramp.elements[0].color=(0.045,0.018,0.003,1)
    pigment.color_ramp.elements[1].position=0.7
    pigment.color_ramp.elements[1].color=(0.62,0.30,0.045,1)
    links.new(grain.outputs['Fac'],pigment.inputs[0])
    links.new(pigment.outputs[0],nodes.get('Principled BSDF').inputs['Base Color'])
    pupil=shader('Obsidian pupil', '#030907', 0.12)
    bronze=shader('Brushed ancient bronze', '#b18c50', 0.3, 0.7)
    membrane=shader('Ear membrane', '#71968a', 0.54)
    glow=shader('Bioluminescent freckles', '#70e4c5', 0.34, emission=1.8)
    rig=make_rig(item['id'])
    body=fused_body(item['id'], controls, skin, rig)
    w=controls['head_width']
    for side in (-1, 1):
        center=(side*0.205*w, -0.275, 2.885)
        eye=ellipsoid('Eye globe', center, (0.175, 0.13, 0.155), sclera, 48, 32)
        bind(eye,rig,'head')
        vertices,faces=[],[]
        for row in range(9):
            radius=0.002+row*0.016
            for col in range(49):
                a=math.tau*col/48
                vertices.append((center[0]+radius*math.cos(a),
                    center[1]-0.132*math.sqrt(1-(radius/0.175)**2)-0.003,
                    center[2]+radius*0.885*math.sin(a)))
        for row in range(8):
            for col in range(48):
                a=row*49+col
                faces.append((a,a+1,a+50,a+49))
        bind(surface('Textured iris',vertices,faces,iris),rig,'head')
        vertices,faces=[],[]
        # Conform the pupil to the globe so it cannot poke through closed eyelids.
        for row in range(7):
            radius=0.01+row*0.99/6
            for col in range(33):
                a=math.tau*col/32
                x,z=0.034*radius*math.cos(a),0.088*radius*math.sin(a)
                y=center[1]-0.134*math.sqrt(1-(x/0.175)**2-(z/0.155)**2)-0.004
                vertices.append((center[0]+x,y,center[2]+z))
        for row in range(6):
            for col in range(32):
                a=row*33+col
                faces.append((a,a+1,a+34,a+33))
        bind(surface('Vertical pupil',vertices,faces,pupil),rig,'head')
        # Radial streaks make the iris readable in close-up without bitmap assets.
        for i in range(28):
            a=math.tau*i/28
            pts=[(center[0]+r*math.cos(a), center[1]-0.132*math.sqrt(1-(r/0.175)**2)-0.006,
                  center[2]+r*0.88*math.sin(a)) for r in (0.055, 0.09, 0.13)]
            bind(tube('Iris radial fiber',pts,0.0012,iris),rig,'head')
        for upper in (True,False):
            eyelid('Upper eyelid' if upper else 'Lower eyelid',center,upper,skin,rig,scene)
        nostril_y=-0.35-0.082*controls['muzzle_length']
        bind(ellipsoid('Nostril', (side*0.07,nostril_y,2.705), (0.027,0.014,0.016),dark),rig,'head')
        start=(side*0.35*w,0.01,2.94)
        end=(side*(0.43*w+0.47*controls['ear_length']),0.10,3.27)
        bind(leaf('Long sensory ear',start,end,0.16,skin),rig,'head')
        bind(leaf('Inner ear', (start[0],-0.018,start[2]+0.02),
                  (end[0]*0.94,0.035,end[2]-0.03),0.105,membrane),rig,'head')
        bind(tube('Ear ridge',[start, (side*0.61,-0.07,3.12),end],0.018,skin),rig,'head')
        for i in range(9):
            x=side*(0.12+i*0.025)*w
            z=3.12+0.09*math.sin(i*0.5)
            # Surface projection onto the cranium, above the brow.
            y=0.035-0.34*math.sqrt(max(0.05,1-(x/(0.43*w))**2-((z-2.87)/0.53)**2))
            bind(ellipsoid('Luminous brow pore',(x,y-0.009,z),(0.009,0.007,0.009),glow,12,8),rig,'head')
    bind(tube('Mouth crease',[(-0.16,-0.287,2.574),(-0.08,-0.326,2.562),(0,-0.339,2.558),
                             (0.08,-0.326,2.562),(0.16,-0.287,2.574)],0.009,dark),rig,'head')
    bind(tube('Lower lip',[(-0.13,-0.29,2.547),(0,-0.331,2.532),(0.13,-0.29,2.547)],0.019,skin),rig,'head')
    # A crest of organic fins makes this an original creature rather than a human template.
    for i in range(5):
        x=(i-2)*0.095
        bind(leaf('Crown fin',(x,0.055,3.23),(x*1.35,0.14,3.58-abs(i-2)*0.06),0.065,skin),rig,'head')
    # Neck ornament, visible in the portrait; no cloth simulation is claimed.
    for z,r in ((2.20,0.19),(2.16,0.205),(2.12,0.22)):
        pts=[(r*math.cos(i*math.tau/24),r*math.sin(i*math.tau/24),z) for i in range(25)]
        bind(tube('Bronze collar',pts,0.014,bronze),rig,'neck')
    for side in (-1,1):
        bind(tube('Pendant chain',[(side*0.16,-0.13,2.13),(side*0.15,-0.25,1.96),(0,-0.27,1.82)],0.012,bronze),rig,'spine')
    bind(ellipsoid('Pendant bezel',(0,-0.27,1.80),(0.075,0.03,0.10),bronze),rig,'spine')
    bind(ellipsoid('Pendant stone',(0,-0.302,1.81),(0.047,0.014,0.065),glow),rig,'spine')
    rig.location=item['start']
    from scene_forge.organic_motion import animate
    animate(rig, scene, item['action'])
    for name,value in controls.items():
        rig['sculpt_'+name]=value
    rig['sculpt_controls_note']='Recorded recipe values; regenerate from scene.json to change proportions.'
    return rig


def create_set(spec, scene, rig):
    from scene_forge.blender_scene import light, empty, rgba
    from scene_forge.organic_motion import wind_leaf
    rng=random.Random(spec['seed'])
    jade=shader('Forest leaves','#19594b',0.48)
    dark=shader('Forest trunks','#112e2b',0.82)
    nodes, links = dark.node_tree.nodes, dark.node_tree.links
    bark = nodes.new('ShaderNodeTexNoise')
    bark.inputs['Scale'].default_value = 11
    bark.inputs['Detail'].default_value = 4
    bump = nodes.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.5
    bump.inputs['Distance'].default_value = 0.05
    links.new(bark.outputs['Fac'], bump.inputs['Height'])
    links.new(bump.outputs['Normal'], nodes.get('Principled BSDF').inputs['Normal'])
    spores=shader('Warm spores','#f2ba6e',0.3,emission=3)
    blue=shader('Luminous fungi','#3dd4d1',0.35,emission=2.5)
    base=Vector(spec['actors'][0]['start'])
    # A rising forest floor hides the finite stage horizon in wide shots.
    # Soft procedural color variation supplies distant depth without downloaded imagery.
    distant = shader('Distant forest haze', spec['ground_color'], 0.72)
    nodes, links = distant.node_tree.nodes, distant.node_tree.links
    coords = nodes.new('ShaderNodeTexCoord')
    stretch = nodes.new('ShaderNodeVectorMath')
    stretch.operation = 'MULTIPLY'
    stretch.inputs[1].default_value = (18, 1, 1.5)
    texture = nodes.new('ShaderNodeTexNoise')
    texture.inputs['Scale'].default_value = 2.5
    texture.inputs['Detail'].default_value = 2
    colors = nodes.new('ShaderNodeValToRGB')
    colors.color_ramp.elements[0].color = (0.008, 0.022, 0.020, 1)
    colors.color_ramp.elements[1].color = (0.035, 0.075, 0.065, 1)
    links.new(coords.outputs['Generated'], stretch.inputs[0])
    links.new(stretch.outputs[0], texture.inputs['Vector'])
    links.new(texture.outputs['Fac'], colors.inputs[0])
    height = nodes.new('ShaderNodeSeparateXYZ')
    fade = nodes.new('ShaderNodeMapRange')
    fade.inputs['From Min'].default_value = 0.04
    fade.inputs['From Max'].default_value = 0.18
    mix = nodes.new('ShaderNodeMixRGB')
    mix.inputs[1].default_value = rgba(spec['ground_color'])
    glow_strength = nodes.new('ShaderNodeMath')
    glow_strength.operation = 'MULTIPLY'
    glow_strength.inputs[1].default_value = 0.12
    links.new(coords.outputs['Generated'], height.inputs[0])
    links.new(height.outputs['Z'], fade.inputs['Value'])
    links.new(fade.outputs[0], mix.inputs[0])
    links.new(colors.outputs[0], mix.inputs[2])
    links.new(mix.outputs[0], nodes.get('Principled BSDF').inputs['Base Color'])
    links.new(mix.outputs[0], nodes.get('Principled BSDF').inputs['Emission Color'])
    links.new(fade.outputs[0], glow_strength.inputs[0])
    links.new(glow_strength.outputs[0], nodes.get('Principled BSDF').inputs['Emission Strength'])
    verts, faces = [], []
    for y,z in ((5.5,-0.02),(7,0),(9,0.6),(12,2.5),(16,7),(20,15),(24,25)):
        for x in (-35,35):
            verts.append(base+Vector((x,y,z)))
    for j in range(6):
        a=j*2
        faces.append((a,a+1,a+3,a+2))
    backdrop = surface('Continuous distant forest floor', verts, faces, distant)
    curved = backdrop.modifiers.new('Smooth forest horizon', 'SUBSURF')
    curved.levels = curved.render_levels = 3
    def foliage(name, start, end, width, phase, curl=0.12):
        obj = leaf(name, start, end, width, jade, curl)
        wind_leaf(obj, start, end, scene, phase, strength=0.065)
        return obj
    # Branches, exposed roots and attached leaves form a bounded original forest set.
    for i in range(12):
        x=rng.uniform(-4,4)
        y=rng.uniform(1.6,5)
        if abs(x)<0.55:
            x+=1.2
        trunk=tube('Forest stem',[base+Vector((x,y,0)),base+Vector((x+0.12,y,2)),base+Vector((x-0.25,y+0.2,8))],rng.uniform(0.08,0.17),dark)
        for point, radius in zip(trunk.data.splines[0].bezier_points, (1.4,1,0.35)):
            point.radius=radius
        for root in range(3):
            angle = root*math.tau/3+i
            offset = Vector((math.cos(angle), math.sin(angle), 0))
            foot = base+Vector((x,y,0))
            tube('Buttress root', [foot+Vector((0,0,0.45)), foot+offset*0.35+Vector((0,0,0.12)), foot+offset*0.85], 0.055, dark)
        for j in range(3):
            start=base+Vector((x,y,1+j*0.8))
            end = start+Vector(((-1)**j*1.1,-0.2,0.75))
            tube('Tree branch', [start, start.lerp(end,0.5)+Vector((0,0,0.1)),end], 0.025, dark)
            for k in range(3):
                attach = start.lerp(end, 0.35+k*0.28)
                tip = attach+Vector(((-1)**j*0.36, (-1)**k*0.36, 0.38))
                foliage('Canopy leaf', attach, tip, 0.13, i*0.6+j+k*0.3)
    for side in (-1,1):
        for j in range(5):
            a=0.4+j*0.22
            start=base+Vector((side*1.1,-0.05,0.05))
            end=base+Vector((side*(0.8+math.cos(a)),0.05,0.4+math.sin(a)))
            tube('Fern rachis',[start,start.lerp(end,0.5)+Vector((0,-0.06,0.04)),end],0.008,jade)
            for k in range(1,7):
                attach = start.lerp(end,k/7)
                spread = 0.19*math.sin(math.pi*k/8)
                for sign in (-1,1):
                    tip = attach+Vector((sign*spread,-0.08,0.12))
                    foliage('Fern leaflet',attach,tip,0.035,j*0.5+k*0.2+side)
        for j in range(4):
            x=side*(0.8+j*0.27)
            y=0.4+j*0.22
            h=0.22+j*0.07
            tube('Fungus stem',[base+Vector((x,y,0)),base+Vector((x+0.05,y,h))],0.018,dark)
            ellipsoid('Luminous mushroom',base+Vector((x+0.05,y,h)),(0.12,0.12,0.045),blue)
    for i in range(30):
        x,y,z=rng.uniform(-2.5,2.5),rng.uniform(0.7,4.2),rng.uniform(0.5,3.9)
        spore=ellipsoid('Floating spore',base+Vector((x,y,z)),(0.009,)*3,spores,8,6)
        origin=spore.location.copy()
        for frame in (1,scene.frame_end//2,scene.frame_end):
            t=(frame-1)/scene.render.fps
            spore.location=origin+Vector((0.06*math.sin(t+i),0.03*math.cos(t+i),0.035*t))
            spore.keyframe_insert('location',frame=frame)
    # Irregular mossy rocks ground the wider shot without blocking the character.
    moss=shader('Mossy forest stones','#344d3b',0.9)
    for i in range(18):
        x,y=rng.uniform(-4,4),rng.uniform(-0.3,5)
        if abs(x)<0.8 and y<1:
            continue
        rock=ellipsoid('Mossy stone',base+Vector((x,y,0.045)),(rng.uniform(0.1,0.25),rng.uniform(0.1,0.2),rng.uniform(0.06,0.14)),moss,16,10)
        rock.rotation_euler.z=rng.uniform(0,math.tau)
    # Lighting is aimed at the portrait, rather than the floor.
    for obj in list(scene.objects):
        if obj.type=='LIGHT':
            bpy.data.objects.remove(obj,do_unlink=True)
    mode=spec['lighting']
    warm=(1,0.78,0.51) if mode!='moonlight' else (0.7,0.9,1)
    for name,pos,power,color,size in (
        ('Portrait key',(-3,-4,5),450,warm,2.3),
        ('Soft teal fill',(3,-1,3.7),100,(0.26,0.75,0.72),2.5),
        ('Golden rim',(1,2.5,4.5),650,(1,0.64,0.30),2),
    ):
        lamp=light(name,'AREA',base+Vector(pos),power,color,size)
        lamp.rotation_euler=(base+Vector((0,0,2.7))-lamp.location).to_track_quat('-Z','Y').to_euler()
    cam_data=bpy.data.cameras.new('Portrait lens')
    cam=bpy.data.objects.new('Portrait camera',cam_data)
    scene.collection.objects.link(cam)
    scene.camera=cam
    focus=empty('Portrait eye focus')
    wide=spec['camera']=='full_body'
    focus.location=base+Vector((0,-0.1,1.85 if wide else 2.82))
    track=cam.constraints.new('TRACK_TO')
    track.target,track.track_axis,track.up_axis=focus,'TRACK_NEGATIVE_Z','UP_Y'
    cam_data.lens=44 if wide else 58
    cam_data.dof.use_dof=True
    cam_data.dof.focus_object=focus
    cam_data.dof.aperture_fstop=4 if wide else 1.8
    positions=((1,1.25,-10.3),(scene.frame_end,0.75,-9.8)) if wide else ((1,0.85,-5.5),(scene.frame_end,0.52,-5.15))
    for frame,x,y in positions:
        cam.location=base+Vector((x,y,2.25 if wide else 2.9))
        cam.keyframe_insert('location',frame=frame)
    return cam


def select_render_device(scene):
    """Prefer available CUDA devices for this bounded portrait, retain CPU fallback."""
    try:
        prefs=bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type='CUDA'
        prefs.get_devices()
        gpu=[d for d in prefs.devices if d.type=='CUDA']
        if gpu:
            for d in prefs.devices:
                d.use=d.type=='CUDA'
            scene.cycles.device='GPU'
            scene['forge_render_device']='CUDA: '+', '.join(d.name for d in gpu)
            return
    except (TypeError,RuntimeError,AttributeError):
        pass
    scene.cycles.device='CPU'
    scene['forge_render_device']='CPU'
