"""Generic Blender modeling executor and inspect/reopen tool. No asset-specific geometry."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import bmesh
from mathutils import Vector
from modeling_lab.operations import validate_plan, deform_points, loft_geometry


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def rig_signature():
    return {o.name: digest([(b.name, b.parent.name if b.parent else None, list(b.head_local), list(b.tail_local),
                             [list(row) for row in b.matrix_local]) for b in o.data.bones])
            for o in bpy.data.objects if o.type == 'ARMATURE'}


def mesh_state(o, full=False):
    points = [list(v.co) for v in o.data.vertices]
    faces = [list(p.vertices) for p in o.data.polygons]
    weights = [[(g.group, g.weight) for g in v.groups] for v in o.data.vertices]
    materials = []
    for m in o.data.materials:
        if m:
            bsdf = m.node_tree.nodes.get('Principled BSDF') if m.use_nodes else None
            materials.append({'name': m.name, 'color': list(bsdf.inputs['Base Color'].default_value) if bsdf else list(m.diffuse_color)})
    state = {'id': o.name, 'vertices': len(points), 'faces': len(faces), 'mesh_sha256': digest([points, faces]),
             'topology_sha256': digest(faces), 'weights_sha256': digest(weights), 'materials': materials,
             'location': list(o.location), 'scale': list(o.scale), 'rotation': list(o.rotation_euler),
             'world_matrix': [list(row) for row in o.matrix_world],
             'modifiers': [[m.name, m.type] for m in o.modifiers]}
    if points:
        state['local_min'] = [min(p[i] for p in points) for i in range(3)]
        state['local_max'] = [max(p[i] for p in points) for i in range(3)]
    if full:
        state['points'] = points
    return state


def inventory(names):
    chosen = [bpy.data.objects[name] for name in names] if names else [o for o in bpy.data.objects if o.type == 'MESH' and not o.name.startswith('_op_review')]
    result = {'objects': [], 'rigs': {o.name: len(o.data.bones) for o in bpy.data.objects if o.type == 'ARMATURE'}}
    for o in chosen:
        if o.type != 'MESH':
            raise ValueError('Editable targets must be meshes')
        state = mesh_state(o)
        result['objects'].append({k: state[k] for k in ('id', 'vertices', 'faces', 'local_min', 'local_max', 'location', 'scale', 'materials')})
    return result


def make_mesh(name, vertices, faces):
    mesh = bpy.data.meshes.new(name + '_mesh')
    mesh.from_pydata(vertices, [], faces)
    if mesh.validate():
        raise ValueError('Blender found invalid mesh data; no silent geometry repair')
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def execute(plan, editable):
    validate_plan(plan, editable)
    original_rigs = rig_signature()
    original_weights = {name: mesh_state(bpy.data.objects[name])['weights_sha256'] for name in editable}
    created, modified, trace = [], set(), []
    for index, step in enumerate(plan['operations']):
        kind = step['op']
        if 'id' in step and step['id'] in bpy.data.objects:
            raise ValueError('ID conflicts with an existing scene object')
        record = {'index': index, 'operation': step}
        if kind == 'mesh':
            target = make_mesh(step['id'], step['vertices'], step['faces'])
            created.append(target.name)
        elif kind == 'loft':
            vertices, faces = loft_geometry(step['rings'])
            target = make_mesh(step['id'], vertices, faces)
            target.location = step['location']
            created.append(target.name)
            for p in target.data.polygons:
                p.use_smooth = len(p.vertices) == 4
        elif kind == 'primitive':
            if step['kind'] == 'box':
                bpy.ops.mesh.primitive_cube_add(size=1)
            elif step['kind'] == 'sphere':
                bpy.ops.mesh.primitive_uv_sphere_add(segments=32, ring_count=20, radius=.5)
            else:
                bpy.ops.mesh.primitive_cylinder_add(vertices=32, radius=.5, depth=1)
            target = bpy.context.object
            target.name = step['id']
            # Bake primitive size into the cage; modifiers remain measured in metres.
            for v in target.data.vertices:
                for axis in range(3):
                    v.co[axis] *= step['dimensions'][axis]
            target.location = step['location']
            target.rotation_euler = [math.radians(x) for x in step['rotation_degrees']]
            if step['kind'] != 'box':
                for p in target.data.polygons:
                    p.use_smooth = len(p.vertices) < 5
            created.append(target.name)
        elif kind == 'duplicate':
            source = bpy.data.objects[step['source']]
            target = source.copy()
            target.data = source.data.copy()
            target.name = step['id']
            bpy.context.scene.collection.objects.link(target)
            target.location += Vector(step['translation'])
            created.append(target.name)
        else:
            target = bpy.data.objects[step['target']]
            if target.type != 'MESH':
                raise ValueError('Only meshes can be modeled')
            modified.add(target.name)
            record['before_mesh_sha256'] = mesh_state(target)['mesh_sha256']
            if kind == 'modifier':
                mapping = {'bevel': 'BEVEL', 'subdivide': 'SUBSURF', 'solidify': 'SOLIDIFY'}
                existing_levels = sum(m.levels for m in target.modifiers if m.type == 'SUBSURF')
                if len(target.modifiers) >= 5 or (kind == 'modifier' and step['kind'] == 'subdivide' and existing_levels + step['value'] > 2):
                    raise ValueError('Modifier budget exceeded')
                modifier = target.modifiers.new('AI_' + step['kind'], mapping[step['kind']])
                if step['kind'] == 'bevel':
                    modifier.width, modifier.segments = step['value'], 3
                elif step['kind'] == 'subdivide':
                    modifier.levels = modifier.render_levels = int(step['value'])
                else:
                    modifier.thickness = step['value']
            elif kind == 'material':
                color = tuple(int(step['color'][i:i+2], 16) / 255 for i in (1, 3, 5))
                mat = bpy.data.materials.new(target.name + '_AI_material')
                mat.diffuse_color = (*color, 1)
                mat.use_nodes = True
                bsdf = mat.node_tree.nodes.get('Principled BSDF')
                bsdf.inputs['Base Color'].default_value = (*color, 1)
                bsdf.inputs['Metallic'].default_value = step['metallic']
                bsdf.inputs['Roughness'].default_value = step['roughness']
                target.data.materials.clear()
                target.data.materials.append(mat)
                for p in target.data.polygons:
                    p.material_index = 0
            elif kind == 'transform':
                target.location += Vector(step['translation'])
                for axis in range(3):
                    target.scale[axis] *= step['scale'][axis]
                    target.rotation_euler[axis] += math.radians(step['rotation_degrees'][axis])
            elif kind == 'deform':
                if target.data.shape_keys:
                    raise ValueError('Deformation of shape-key meshes is not implemented')
                before = [tuple(v.co) for v in target.data.vertices]
                after, changed = deform_points(before, step)
                if not changed:
                    raise ValueError('Deformation selected no moving vertices')
                for v, point in zip(target.data.vertices, after):
                    v.co = point
                target.data.update()
                record['changed_vertices'] = changed
                record['max_displacement_m'] = max(math.dist(a, b) for a, b in zip(before, after))
                record['selection_bounds'] = [[min(p[axis] for p in before if math.sqrt(sum(((p[i]-step['center'][i])/step['radius'][i])**2 for i in range(3))) < 1) for axis in range(3)],
                                              [max(p[axis] for p in before if math.sqrt(sum(((p[i]-step['center'][i])/step['radius'][i])**2 for i in range(3))) < 1) for axis in range(3)]]
        bpy.context.view_layer.update()
        if len(target.data.vertices) > 150000:
            raise ValueError('Control mesh exceeds budget')
        if not all(math.isfinite(x) for v in target.data.vertices for x in v.co):
            raise ValueError('Non-finite generated coordinates')
        record['after'] = mesh_state(target)
        trace.append(record)
    if original_rigs != rig_signature():
        raise ValueError('Rig changed unexpectedly')
    for name, expected in original_weights.items():
        if mesh_state(bpy.data.objects[name])['weights_sha256'] != expected:
            raise ValueError('Original skin weights changed unexpectedly')
    return {'operations': trace, 'created': created, 'modified': sorted(modified), 'rigs_preserved': True, 'weights_preserved': True}


def inspect_objects(names, full=False):
    bpy.context.view_layer.update()
    states = []
    for name in names:
        o = bpy.data.objects[name]
        state = mesh_state(o, full)
        evaluated = o.evaluated_get(bpy.context.evaluated_depsgraph_get())
        mesh = evaluated.to_mesh()
        if len(mesh.vertices) > 1000000 or not mesh.vertices:
            raise ValueError('Evaluated mesh budget exceeded or empty')
        matrix = o.matrix_world.copy()
        points = [matrix @ v.co for v in mesh.vertices]
        if not all(math.isfinite(v) for p in points for v in p):
            raise ValueError('Non-finite evaluated geometry')
        state['evaluated_vertices'] = len(mesh.vertices)
        state['world_min'] = [min(p[i] for p in points) for i in range(3)]
        state['world_max'] = [max(p[i] for p in points) for i in range(3)]
        state['zero_area_faces'] = sum(p.area < 1e-12 for p in mesh.polygons)
        evaluated.to_mesh_clear()
        states.append(state)
    return states


def stage(names, states=None):
    states = states if states is not None else inspect_objects(names)
    low = Vector([min(s['world_min'][i] for s in states) for i in range(3)])
    high = Vector([max(s['world_max'][i] for s in states) for i in range(3)])
    center, extent = (low + high) / 2, max(high - low)
    # Review setup is deterministic and outside the model's geometry operations.
    for o in list(bpy.data.objects):
        if o.name.startswith('_op_review'):
            bpy.data.objects.remove(o, do_unlink=True)
    scene = bpy.context.scene
    for label, delta, energy, color in [('key', (2, -3, 3), 500, (1, .88, .78)),
                                       ('fill', (-2, -2, 1), 300, (.7, .84, 1)),
                                       ('rim', (1, 2, 2), 600, (.8, .9, 1))]:
        data = bpy.data.lights.new('_op_review_' + label, 'AREA')
        o = bpy.data.objects.new(data.name, data)
        scene.collection.objects.link(o)
        o.location = center + Vector(delta) * extent
        o.rotation_euler = (center - o.location).to_track_quat('-Z', 'Y').to_euler()
        data.energy, data.size = energy * extent * extent, extent * 2
        data.color = color
    data = bpy.data.cameras.new('_op_review_camera')
    camera = bpy.data.objects.new(data.name, data)
    scene.collection.objects.link(camera)
    camera.location = center + Vector((2, -4, 1.2)) * extent
    camera.rotation_euler = (center - camera.location).to_track_quat('-Z', 'Y').to_euler()
    data.type, data.ortho_scale = 'ORTHO', extent * 1.45
    scene.camera = camera
    scene.render.engine = 'CYCLES'
    scene.cycles.samples, scene.cycles.use_denoising = 20, True
    scene.render.resolution_x, scene.render.resolution_y = 800, 800
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.world.color = (.08, .08, .08)
    scene.view_settings.view_transform = 'AgX'
    return center, extent


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input')
    parser.add_argument('--editable', nargs='*', default=[])
    parser.add_argument('--inventory')
    parser.add_argument('--plan')
    parser.add_argument('--output')
    parser.add_argument('--verify')
    parser.add_argument('--render', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    original = Path(args.input).resolve() if args.input else None
    original_hash = hashlib.sha256(original.read_bytes()).hexdigest() if original else None
    # Resolve output paths before opening a .blend changes Blender's relative base path.
    output = Path(args.output).resolve() if args.output else None
    inventory_path = Path(args.inventory).resolve() if args.inventory else None
    verify_path = Path(args.verify).resolve() if args.verify else None
    plan_path = Path(args.plan).resolve() if args.plan else None
    if original:
        bpy.ops.wm.open_mainfile(filepath=str(original), use_scripts=False)
    else:
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=False)
    if inventory_path:
        inventory_path.write_text(json.dumps(inventory(args.editable), indent=2))
        return
    if verify_path:
        saved = json.loads(bpy.data.texts['QWEN_MODELING_PROVENANCE'].as_string())
        names = saved['inspection_objects']
        states = inspect_objects(names, True)
        expected = saved['states']
        keys = ('mesh_sha256', 'world_matrix', 'weights_sha256', 'materials', 'modifiers')
        mismatches = {a['id']: [k for k in keys if a[k] != b[k]] for a, b in zip(states, expected)}
        matching = len(states) == len(expected) and not any(mismatches.values())
        matching = matching and rig_signature() == saved['rigs']
        # Actual editable vertex test with restoration, no disk save.
        o = bpy.data.objects[names[0]]
        prior = o.data.vertices[0].co.copy()
        o.data.vertices[0].co.x += .001
        edited = abs(o.data.vertices[0].co.x - prior.x) > .0009
        o.data.vertices[0].co = prior
        source_unchanged = hashlib.sha256(original.read_bytes()).hexdigest() == original_hash
        report = {'passed': matching and edited and source_unchanged,
                  'geometry_matches_saved_execution': matching, 'vertex_editable': edited, 'source_unchanged': True,
                  'states': states, 'rigs': rig_signature(), 'mismatches': mismatches}
        report['source_unchanged'] = source_unchanged
        verify_path.write_text(json.dumps(report, indent=2))
        if not report['passed']:
            raise ValueError('Saved operation result verification failed')
        print('MODELING_REOPEN_PASS', flush=True)
        return
    output.mkdir(parents=True, exist_ok=False)
    plan = json.loads(plan_path.read_text())
    editable = args.editable or [x['id'] for x in inventory([])['objects']]
    before = {name: mesh_state(bpy.data.objects[name], True) for name in editable}
    trace = execute(plan, editable)
    names = list(dict.fromkeys(editable + trace['created']))
    states = inspect_objects(names, True)
    report = {'structural_passed': True, 'semantic_passed': None, 'inspection_objects': names,
              'states': states, 'before': before, 'trace': trace, 'rigs': rig_signature(),
              'input_sha256': original_hash, 'input_path': str(original) if original else None,
              'generated_by': 'Qwen operation plan; generic deterministic Blender executor',
              'plan': plan, 'visual_quality_approved': False}
    (output / 'execution.json').write_text(json.dumps(report, indent=2))
    text = bpy.data.texts.get('QWEN_MODELING_PROVENANCE') or bpy.data.texts.new('QWEN_MODELING_PROVENANCE')
    text.clear()
    text.write(json.dumps(report, indent=2))
    center, extent = stage(names, states)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / 'model.blend'))
    if original and hashlib.sha256(original.read_bytes()).hexdigest() != original_hash:
        raise RuntimeError('Input file changed unexpectedly')
    if args.render:
        for view, direction in [('three_quarter', (2, -4, 1.2)), ('front', (0, -4, 0)), ('profile', (4, 0, 0))]:
            bpy.context.scene.camera.location = center + Vector(direction) * extent
            bpy.context.scene.camera.rotation_euler = (center - bpy.context.scene.camera.location).to_track_quat('-Z', 'Y').to_euler()
            bpy.context.scene.render.filepath = str(output / (view + '.png'))
            bpy.ops.render.render(write_still=True)
    print('MODELING_EXECUTION_PASS', flush=True)


if __name__ == '__main__':
    main()
