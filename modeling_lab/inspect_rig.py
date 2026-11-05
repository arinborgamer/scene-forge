"""Inspect/probe a saved static rig in memory; never save the input Blender file."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import numpy as np
from mathutils import Matrix
from scene_forge.rig_profile import MPFB_JOINTS, validate_profile


def coordinates(body):
    bpy.context.view_layer.update()
    ob = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ob.to_mesh()
    try:
        points = np.array([v.co[:] for v in mesh.vertices], dtype=float)
        matrix = np.array(ob.matrix_world)
        return points @ matrix[:3, :3].T + matrix[:3, 3]
    finally:
        ob.to_mesh_clear()


def inspect(args):
    source, out = Path(args.input).resolve(), Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
    rig, body = bpy.data.objects[args.rig], bpy.data.objects[args.mesh]
    if rig.type != 'ARMATURE' or body.type != 'MESH':
        raise ValueError('Explicit armature and mesh are required')
    if not any(m.type == 'ARMATURE' and m.object == rig and m.use_vertex_groups for m in body.modifiers):
        raise ValueError('The mesh is not bound to the declared rig through vertex groups')
    if rig.animation_data and (rig.animation_data.action or rig.animation_data.nla_tracks or rig.animation_data.drivers):
        raise ValueError('Neutral static-rig probes do not override animation or drivers')
    if any(b.constraints for b in rig.pose.bones):
        raise ValueError('Constrained rigs need a separate probe policy; no constraint removal')
    if any(max(abs(v-(1 if i == j else 0)) for i, row in enumerate(b.matrix_basis) for j, v in enumerate(row)) > 1e-6 for b in rig.pose.bones):
        raise ValueError('Neutral static-rig probes require the supplied rest pose')
    mapping = json.loads(Path(args.mapping).read_text()) if args.mapping else MPFB_JOINTS.copy()
    if args.rename_prefix:
        # Explicit mapping test on the same skeleton, not a second rig-family claim.
        old_names = list(rig.data.bones.keys())
        for name in old_names:
            rig.data.bones[name].name = args.rename_prefix+name
        for group in body.vertex_groups:
            if group.name in old_names:
                group.name = args.rename_prefix+group.name
        mapping = {joint: args.rename_prefix+bone for joint, bone in mapping.items()}
    scene = bpy.context.scene
    profile = dict(schema_version=1, source_path=str(source), source_sha256=digest,
                   rig=rig.name, mesh=body.name,
                   skeleton_family='custom_mapping' if args.mapping or args.rename_prefix else 'makehuman_mpfb_v1',
                   coordinates=dict(meters_per_unit=args.meters_per_unit, up_axis='Z', forward_axis='-Y',
                                    convention_source='Explicit CLI convention; coordinates are armature-local'),
                   fps=scene.render.fps/scene.render.fps_base, joints=mapping,
                   control_vertices=len(body.data.vertices), control_faces=len(body.data.polygons),
                   bones=[dict(name=b.name, parent=b.parent.name if b.parent else None,
                               head=list(b.head_local), tail=list(b.tail_local),
                               rest_matrix=[list(r) for r in b.matrix_local]) for b in rig.data.bones],
                   rig_world_matrix=[list(r) for r in rig.matrix_world],
                   mesh_world_matrix=[list(r) for r in body.matrix_world],
                   scope='Observed skeleton metadata and explicit mapping; not automatic retargeting, IK or anatomical approval')
    validate_profile(profile)
    basis = {b.name: b.matrix_basis.copy() for b in rig.pose.bones}
    subdivisions = [(m, m.show_viewport) for m in body.modifiers if m.type == 'SUBSURF']
    actions = sorted(a.name for a in bpy.data.actions)
    checks = []
    try:
        for modifier, _ in subdivisions:
            modifier.show_viewport = False
        rest = coordinates(body)
        if len(rest) != len(body.data.vertices) or not np.isfinite(rest).all():
            raise ValueError('Probe requires a finite deformation cage with stable vertex count')
        probes = [(side+'_'+part, axis, angle) for side in ('left', 'right')
                  for part, axis, angle in [('shoulder', 0, .35), ('elbow', 0, .45),
                                           ('wrist', 0, .25), ('hip', 0, .3), ('knee', 0, .4), ('index', 0, .3)]]
        probes += [('neck', 1, .2), ('jaw', 0, .15)]
        for joint, axis, angle in probes:
            name = mapping[joint]
            bone = rig.pose.bones[name]
            influenced_names = {name} | {b.name for b in rig.data.bones[name].children_recursive}
            influenced_groups = {g.index for g in body.vertex_groups if g.name in influenced_names}
            influenced = np.array([any(g.group in influenced_groups and g.weight > 1e-8 for g in v.groups) for v in body.data.vertices])
            bone.matrix_basis = basis[name] @ Matrix.Rotation(angle, 4, 'XYZ'[axis])
            posed = coordinates(body)
            distance = np.linalg.norm(posed-rest, axis=1)*args.meters_per_unit
            bone.matrix_basis = basis[name]
            restored = coordinates(body)
            residual = float(np.max(np.abs(restored-rest)))*args.meters_per_unit
            no_stray = float(np.max(distance[~influenced], initial=0)) < 1e-6
            passed = np.isfinite(posed).all() and int(np.sum(distance > 1e-5)) >= 4 and residual < 1e-6 and no_stray
            checks.append(dict(joint=joint, bone=name, moved_vertices=int(np.sum(distance > 1e-5)),
                               maximum_displacement_m=float(np.max(distance)), rest_residual_m=residual,
                               only_influenced_vertices_moved=no_stray, passed=bool(passed)))
    finally:
        for name, matrix in basis.items():
            rig.pose.bones[name].matrix_basis = matrix
        for modifier, enabled in subdivisions:
            modifier.show_viewport = enabled
        bpy.context.view_layer.update()
    bone_groups = {g.index for g in body.vertex_groups if g.name in rig.data.bones}
    weights = [sum(g.weight for g in v.groups if g.group in bone_groups) for v in body.data.vertices]
    report = dict(passed=all(c['passed'] for c in checks) and len(checks) == 14,
                  probes=checks, bone_count=len(rig.data.bones),
                  normalized_weights=max(abs(v-1) for v in weights) < 1e-5,
                  source_file_unchanged=hashlib.sha256(source.read_bytes()).hexdigest() == digest,
                  animation_datablocks_unchanged=sorted(a.name for a in bpy.data.actions) == actions,
                  renamed_mapping_test=bool(args.rename_prefix),
                  scope='In-memory static-rig deformation probes. Does not test foot contact, self-intersection, IK, retargeting or motion quality.')
    report['passed'] = report['passed'] and report['normalized_weights'] and report['source_file_unchanged'] and report['animation_datablocks_unchanged']
    (out/'profile.json').write_text(json.dumps(profile, indent=2), encoding='utf-8')
    (out/'acceptance.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print('RIG_PROFILE_'+('PASS' if report['passed'] else 'FAIL'), json.dumps(report), flush=True)
    if not report['passed']:
        raise ValueError('Static rig probe failed; evidence preserved')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True); parser.add_argument('--output', required=True)
    parser.add_argument('--rig', default='Humanoid_Rig'); parser.add_argument('--mesh', default='Humanoid_Trained_Shape')
    parser.add_argument('--mapping'); parser.add_argument('--rename-prefix', default='')
    parser.add_argument('--meters-per-unit', type=float, default=1)
    inspect(parser.parse_args(sys.argv[sys.argv.index('--')+1:]))
