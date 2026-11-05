"""Build an editable trained-shape specimen, test its inherited rig and render review views.

Run with Blender --background --factory-startup --python this_file -- --spec ...
This is a separate modeling experiment: no animation recipe or old output is touched.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import bpy
from mathutils import Vector
import numpy as np
from modeling_lab.assets import ASSETS, PREFIX, read_obj
from modeling_lab.shape_model import predict_vertices, CONTROL_NAMES


def material(name, color, roughness=.5, skin=False):
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = (*color, 1)
    mat.use_nodes = True
    nodes, links = mat.node_tree.nodes, mat.node_tree.links
    bsdf = nodes.get('Principled BSDF')
    bsdf.inputs['Base Color'].default_value = (*color, 1)
    bsdf.inputs['Roughness'].default_value = roughness
    if skin:
        bsdf.inputs['Subsurface Weight'].default_value = .08
        bsdf.inputs['Subsurface Radius'].default_value = (1, .42, .24)
        bsdf.inputs['Subsurface Scale'].default_value = .015
        noise = nodes.new('ShaderNodeTexNoise')
        noise.inputs['Scale'].default_value = 220
        noise.inputs['Detail'].default_value = 2
        bump = nodes.new('ShaderNodeBump')
        bump.inputs['Strength'].default_value = .14
        bump.inputs['Distance'].default_value = .00025
        links.new(noise.outputs['Fac'], bump.inputs['Height'])
        links.new(bump.outputs['Normal'], bsdf.inputs['Normal'])
    return mat


def aim(obj, point):
    obj.rotation_euler = (Vector(point) - obj.location).to_track_quat('-Z', 'Y').to_euler()


def evaluated_vertices(obj):
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    coords = np.array([v.co[:] for v in mesh.vertices])
    evaluated.to_mesh_clear()
    return coords


def build(spec_path, checkpoint, output, render=True):
    spec_path, checkpoint, output = Path(spec_path).resolve(), Path(checkpoint).resolve(), Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    spec = json.loads(spec_path.read_text())
    controls = [spec[k] for k in CONTROL_NAMES]
    verts = predict_vertices(checkpoint, controls)
    _, uvs, all_faces, all_uv_faces, groups = read_obj()
    selected_faces = groups['body']
    old_indices = sorted(set(v for f in selected_faces for v in all_faces[f]))
    mapping = {old: new for new, old in enumerate(old_indices)}
    body_verts = verts[old_indices]
    height = spec.get('height_m', 1.8)
    if not isinstance(height, (int, float)) or not 1.45 <= height <= 2.1:
        raise ValueError('height_m must be between 1.45 and 2.1')
    floor = float(body_verts[:, 2].min())
    scale = height / float(np.ptp(body_verts[:, 2]))
    verts[:, 2] -= floor
    verts *= scale
    faces = [[mapping[i] for i in all_faces[f]] for f in selected_faces]
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    mesh = bpy.data.meshes.new('Humanoid_Editable_Quad_Cage')
    mesh.from_pydata(verts[old_indices].tolist(), [], faces)
    mesh.update()
    body = bpy.data.objects.new('Humanoid_Trained_Shape', mesh)
    bpy.context.collection.objects.link(body)
    uv_layer = mesh.uv_layers.new(name='MakeHuman_CC0_UV')
    for poly, source_face in zip(mesh.polygons, selected_faces):
        poly.use_smooth = True
        for loop_i, uv_i in zip(poly.loop_indices, all_uv_faces[source_face]):
            uv_layer.data[loop_i].uv = uvs[uv_i]

    rig_spec = json.loads((ASSETS / (PREFIX + 'rigs/standard/rig.default.json')).read_text())

    def endpoint(data):
        strategy = data['strategy']
        if strategy == 'CUBE':
            indices = sorted(set(v for fi in groups[data['cube_name']] for v in all_faces[fi]))
        elif strategy == 'VERTEX':
            indices = [data['vertex_index']]
        elif strategy == 'MEAN':
            indices = data['vertex_indices']
        else:
            raise ValueError('Unknown rig joint strategy: ' + strategy)
        return verts[indices].mean(0)

    armature = bpy.data.armatures.new('MakeHuman_CC0_163_Bone_Skeleton')
    rig = bpy.data.objects.new('Humanoid_Rig', armature)
    bpy.context.collection.objects.link(rig)
    bpy.context.view_layer.objects.active = rig
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    for name, data in rig_spec.items():
        bone = armature.edit_bones.new(name)
        bone.head, bone.tail = endpoint(data['head']), endpoint(data['tail'])
        bone.roll = data['roll']
        if bone.length < 1e-6:
            raise ValueError('Zero length bone: ' + name)
    for name, data in rig_spec.items():
        bone = armature.edit_bones[name]
        if data['parent']:
            bone.parent = armature.edit_bones[data['parent']]
        bone.use_connect = data.get('use_connect', False)
        bone.use_inherit_rotation = data.get('use_inherit_rotation', True)
    bpy.ops.object.mode_set(mode='OBJECT')
    rig.show_in_front = True
    armature.display_type = 'OCTAHEDRAL'
    source_weights = json.loads((ASSETS / (PREFIX + 'rigs/standard/weights.default.json')).read_text())['weights']
    totals = np.zeros(len(old_indices))
    for name, weights in source_weights.items():
        if name not in rig_spec:
            raise ValueError('Weight references absent bone: ' + name)
        for old, value in weights:
            if old in mapping:
                totals[mapping[old]] += value
    if np.any(totals < .0001):
        raise ValueError(f'{int(np.sum(totals < .0001))} body vertices lack skin weights')
    for name, weights in source_weights.items():
        group = body.vertex_groups.new(name=name)
        for old, value in weights:
            if old in mapping:
                i = mapping[old]
                group.add([i], value / totals[i], 'REPLACE')
    body.parent = rig
    modifier = body.modifiers.new('163 bone skin deformation', 'ARMATURE')
    modifier.object = rig
    modifier.use_deform_preserve_volume = True

    skin = material('Skin — procedural shader, not learned texture', (.40, .215, .145), skin=True)
    suit = material('Graphite fitted study suit — material region only', (.025, .045, .061), .62)
    nails = material('Nail study', (.43, .29, .235), .34)
    for mat in (skin, suit, nails):
        mesh.materials.append(mat)
    # Present an anatomy study in a simple material-based body suit. It is not a
    # generated garment and does not alter the learned mesh geometry.
    neck_z = float(armature.bones['neck01'].head_local.z) - .025 * scale
    hand_groups = {group.index for group in body.vertex_groups if group.name.startswith(('finger', 'wrist', 'metacarpal'))}
    region = mesh.attributes.new('skin_region', 'FLOAT', 'POINT')
    for vertex in mesh.vertices:
        hand_weight = sum(g.weight for g in vertex.groups if g.group in hand_groups)
        neck_mask = min(1, max(0, (vertex.co.z - neck_z) / .025 + .5))
        region.data[vertex.index].value = max(neck_mask, hand_weight)
    # Interpolate the material mask across the surface, rather than assigning whole
    # polygons and producing a visibly jagged collar/wrist boundary.
    nodes, links = skin.node_tree.nodes, skin.node_tree.links
    cloth_bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    cloth_bsdf.inputs['Base Color'].default_value = (.025, .045, .061, 1)
    cloth_bsdf.inputs['Roughness'].default_value = .62
    attribute = nodes.new('ShaderNodeAttribute')
    attribute.attribute_name = 'skin_region'
    threshold = nodes.new('ShaderNodeMath')
    threshold.operation = 'GREATER_THAN'
    threshold.inputs[1].default_value = .5
    blend = nodes.new('ShaderNodeMixShader')
    links.new(attribute.outputs['Fac'], threshold.inputs[0])
    links.new(threshold.outputs[0], blend.inputs[0])
    links.new(cloth_bsdf.outputs[0], blend.inputs[1])
    links.new(nodes.get('Principled BSDF').outputs[0], blend.inputs[2])
    links.new(blend.outputs[0], nodes.get('Material Output').inputs['Surface'])

    # Separate editable eye components fitted from inherited eye joints.
    whites = material('Eye sclera', (.73, .76, .72), .22)
    iris_mat = material('Iris warm brown', (.17, .069, .024), .24)
    pupil_mat = material('Pupil', (.003, .004, .004), .15)
    for side in ('L', 'R'):
        bone = armature.bones['eye.' + side]
        center = bone.head_local.copy()
        direction = (bone.tail_local - center).normalized()
        radius = .0115 * scale
        for label, shift, size, mat in [('Sclera', 0, (radius,) * 3, whites),
                                      ('Iris', radius * .94, (radius * .49, radius * .49, radius * .10), iris_mat),
                                      ('Pupil', radius * 1.035, (radius * .21, radius * .21, radius * .035), pupil_mat)]:
            bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, location=center + direction * shift)
            eye = bpy.context.object
            eye.name = f'{label}.{side}'
            eye.rotation_euler = direction.to_track_quat('Z', 'Y').to_euler()
            eye.scale = size
            bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
            eye.data.materials.append(mat)
            for polygon in eye.data.polygons:
                polygon.use_smooth = True
            transform = eye.matrix_world.copy()
            eye.parent, eye.parent_type, eye.parent_bone = rig, 'BONE', 'eye.' + side
            eye.matrix_world = transform

    # Numerical deformation probes, not animation clips or claims of artistic posing.
    rest = evaluated_vertices(body)
    tests = []
    for bone_name, axis, angle in [('upperarm01.L', 0, .6), ('lowerarm01.L', 0, .7),
                                  ('finger2-1.L', 0, .5), ('upperleg01.L', 0, .4),
                                  ('lowerleg01.L', 0, .6), ('neck01', 1, .3), ('jaw', 0, .2)]:
        pb = rig.pose.bones[bone_name]
        pb.rotation_mode = 'XYZ'
        pb.rotation_euler[axis] = angle
        posed = evaluated_vertices(body)
        displacement = np.linalg.norm(posed - rest, axis=1)
        tests.append({'bone': bone_name, 'angle_radians': angle, 'moved_vertices': int(np.sum(displacement > 1e-5)),
                      'max_displacement_m': float(displacement.max()), 'finite': bool(np.isfinite(posed).all()),
                      'passed': bool(np.isfinite(posed).all() and np.sum(displacement > 1e-5) > 4)})
        pb.rotation_euler = (0, 0, 0)
    restored = evaluated_vertices(body)
    residual = float(np.abs(restored - rest).max())
    subdiv = body.modifiers.new('Detail level — editable subdivision', 'SUBSURF')
    subdiv.levels, subdiv.render_levels = 1, 2
    detailed = evaluated_vertices(body)
    checks = {'passed': bool(all(x['passed'] for x in tests) and residual < 1e-6 and np.isfinite(detailed).all()),
              'bones': len(armature.bones), 'base_vertices': len(mesh.vertices), 'base_faces': len(mesh.polygons),
              'quad_faces': sum(len(p.vertices) == 4 for p in mesh.polygons),
              'viewport_subdivision_vertices': len(detailed), 'render_subdivision_levels': 2,
              'unweighted_body_vertices': int(np.sum(totals < .0001)), 'rest_restore_max_error_m': residual,
              'deformation_tests': tests, 'artistic_quality_approved': False,
              'limitations': ['Inherited weights; no corrective shape keys or IK controls added',
                              'Movement checks do not prove contact, no intersections, or good extreme poses',
                              'Procedural skin, bald head, material-only suit; not photorealistic',
                              'Subdivision adds smoothness, not newly learned anatomical detail']}
    (output / 'validation.json').write_text(json.dumps(checks, indent=2))
    (output / 'spec.json').write_text(json.dumps(spec, indent=2))
    provenance = {'checkpoint': str(checkpoint), 'checkpoint_sha256': hashlib.sha256(checkpoint.read_bytes()).hexdigest(),
                  'controls': dict(zip(CONTROL_NAMES, controls)), 'height_postprocess_m': height,
                  'mesh_generation': 'trained neural predictor plus fitted PCA decoder',
                  'source_assets': str(ASSETS / 'manifest.json'), 'rig': 'CC0 MPFB template, refitted to predicted joint vertices',
                  'Qwen_fine_tuned': False, 'animation_created': False}
    (output / 'provenance.json').write_text(json.dumps(provenance, indent=2))
    text = bpy.data.texts.new('MODEL_PROVENANCE.json')
    text.write(json.dumps(provenance, indent=2))
    text = bpy.data.texts.new('MODELING_README')
    text.write('Trained shape experiment. Select Humanoid_Trained_Shape to edit the quad cage.\n'
               'Subdivision is non-destructive: viewport 1, render 2; set 0 for the low-detail cage.\n'
               'Select Humanoid_Rig and enter Pose Mode for 163 inherited bones. No keyframes.\n'
               'The rig, skin weights, topology and anatomical templates are MPFB CC0 assets.\n'
               'The neural network learned only bounded body-shape interpolation. Qwen was not trained.\n'
               'The body suit is a material region, not a separate generated garment.\n')
    if not checks['passed']:
        raise RuntimeError('Rig/model verification failed; see validation.json')

    # Neutral review stage, not a cinematic animation scene.
    floor_mat = material('Studio floor', (.065, .083, .105), .8)
    bpy.ops.mesh.primitive_plane_add(size=200, location=(0, 0, -.007))
    bpy.context.object.name = 'Review_Stage'
    bpy.context.object.data.materials.append(floor_mat)
    for name, location, energy, size, color in [
        ('Key', (2.5, -3.5, 4), 450, 3, (1, .86, .75)),
        ('Fill', (-2, -2, 2.6), 260, 2.5, (.72, .84, 1)),
        ('Rim', (1, 2, 3), 600, 2, (.8, .9, 1))]:
        data = bpy.data.lights.new(name, 'AREA')
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = location
        data.energy, data.shape, data.size, data.color = energy, 'DISK', size, color
        aim(light, (0, 0, height * .6))
    scene = bpy.context.scene
    scene.world.color = (.17, .17, .17)
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 24
    scene.cycles.use_denoising = True
    # Use the installed CUDA device if Blender exposes one; CPU remains portable.
    try:
        preferences = bpy.context.preferences.addons['cycles'].preferences
        preferences.compute_device_type = 'CUDA'
        preferences.get_devices()
        cuda = [device for device in preferences.devices if device.type == 'CUDA']
        for device in preferences.devices:
            device.use = device in cuda
        if cuda:
            scene.cycles.device = 'GPU'
    except (TypeError, RuntimeError):
        scene.cycles.device = 'CPU'
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.view_settings.view_transform = 'AgX'
    scene.unit_settings.system = 'METRIC'
    camera_data = bpy.data.cameras.new('Review camera')
    camera = bpy.data.objects.new('Review camera', camera_data)
    bpy.context.collection.objects.link(camera)
    scene.camera = camera
    camera_data.type = 'ORTHO'
    camera_data.ortho_scale = height * 1.16
    camera.location = (2.5, -5, height * .65)
    aim(camera, (0, 0, height * .51))
    scene.render.resolution_x, scene.render.resolution_y = 720, 900
    bpy.ops.object.select_all(action='DESELECT')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    for screen in bpy.data.screens:
        for area in screen.areas:
            if area.type == 'VIEW_3D':
                area.spaces.active.region_3d.view_distance = height * 1.7
                area.spaces.active.region_3d.view_location = (0, 0, height * .52)
                area.spaces.active.region_3d.view_rotation = camera.rotation_euler.to_quaternion()
    bpy.ops.wm.save_as_mainfile(filepath=str(output / 'humanoid.blend'))
    if render:
        for view, location in [('three_quarter', (2.5, -5, height * .65)), ('front', (0, -5, height * .54)), ('profile', (5, 0, height * .54))]:
            camera.location = location
            aim(camera, (0, 0, height * .51))
            scene.render.filepath = str(output / f'{view}.png')
            bpy.ops.render.render(write_still=True)
        # Face review exposes anatomical/material limitations rather than hiding them.
        camera_data.ortho_scale = height * .25
        camera.location = (1.1, -4, height * .95)
        aim(camera, (0, 0, height * .905))
        scene.render.resolution_x, scene.render.resolution_y = 800, 800
        scene.render.filepath = str(output / 'face.png')
        bpy.ops.render.render(write_still=True)
    print('HUMANOID_BUILD_PASS ' + json.dumps(checks), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', required=True)
    parser.add_argument('--checkpoint', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--no-render', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    build(args.spec, args.checkpoint, args.output, not args.no_render)
