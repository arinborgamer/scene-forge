"""Bake declared compatible-rig samples to editable Blender actions in a new copy."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import bpy
import numpy as np
from mathutils import Quaternion, Vector
from scene_forge.motion_clip import skeleton_signature, validate_clip, continuous_quaternions
from modeling_lab.operation_blender import mesh_state


def bone_data(rig):
    return [dict(name=b.name, parent=b.parent.name if b.parent else None, head=list(b.head_local),
                 tail=list(b.tail_local), rest_matrix=[list(row) for row in b.matrix_local]) for b in rig.data.bones]


def curves(rig):
    if not rig.animation_data or not rig.animation_data.action:
        return []
    return [c for layer in rig.animation_data.action.layers for strip in layer.strips
            if strip.type == 'KEYFRAME' for bag in strip.channelbags for c in bag.fcurves]


def sample_check(rig, profile, clip, base_world):
    tracks = {k: continuous_quaternions(v) for k, v in clip['joint_rotations'].items()}
    checks = []
    for i in range(len(clip['root_offsets_m'])):
        bpy.context.scene.frame_set(clip['start_frame']+i)
        bpy.context.view_layer.update()
        expected = Vector(base_world)+Vector(clip['root_offsets_m'][i])/profile['coordinates']['meters_per_unit']
        root_ok = (rig.matrix_world.translation-expected).length < 1e-5
        joints_ok = all(abs(Quaternion(track[i]).dot(rig.pose.bones[profile['joints'][joint]].rotation_quaternion.normalized())) > 1-1e-5
                        for joint, track in tracks.items())
        checks.append(root_ok and joints_ok)
    return all(checks)


def evaluated_points(body):
    bpy.context.view_layer.update()
    ob = body.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = ob.to_mesh()
    try:
        return np.array([v.co[:] for v in mesh.vertices])
    finally:
        ob.to_mesh_clear()


def mesh_motion(body, clip):
    frames = [clip['start_frame']+i for i in [0, len(clip['root_offsets_m'])//2, len(clip['root_offsets_m'])-1]]
    points = []
    for frame in frames:
        bpy.context.scene.frame_set(frame)
        points.append(evaluated_points(body))
    differences = [np.linalg.norm(p-points[0], axis=1) for p in points[1:]]
    return dict(evaluated_vertices=len(points[0]), frames=frames,
                moved_vertices=max(int(np.sum(d > 1e-5)) for d in differences),
                maximum_local_displacement=float(max(np.max(d) for d in differences)))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True); parser.add_argument('--output', required=True)
    parser.add_argument('--profile'); parser.add_argument('--clip'); parser.add_argument('--verify', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    source, out = Path(args.input).resolve(), Path(args.output).resolve()
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    if args.verify:
        bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
        saved = json.loads(bpy.data.texts['MOTION_IMPORT_PROVENANCE'].as_string())
        profile, clip = saved['profile'], saved['clip']
        validate_clip(clip, profile)
        rig = bpy.data.objects[profile['rig']]
        body = bpy.data.objects[profile['mesh']]
        matches = sample_check(rig, profile, clip, saved['base_world_translation'])
        actual_mesh_motion = mesh_motion(body, clip)
        expected_mesh_motion = saved['sampled_mesh_motion']
        geometry_matches = (actual_mesh_motion['moved_vertices'] == expected_mesh_motion['moved_vertices']
                            and math.isclose(actual_mesh_motion['maximum_local_displacement'], expected_mesh_motion['maximum_local_displacement'], abs_tol=1e-5))
        action_curves = curves(rig)
        joint = next(iter(clip['joint_rotations']))
        bone = rig.pose.bones[profile['joints'][joint]]
        prior_pose = bone.rotation_quaternion.normalized()
        prior_mesh = evaluated_points(body)
        component = min(range(4), key=lambda i: abs(prior_pose[i]))
        curve = next(c for c in action_curves if c.data_path == bone.path_from_id('rotation_quaternion') and c.array_index == component)
        point = curve.keyframe_points[-1]
        prior = point.co.y
        point.co.y += .05; curve.update()
        bpy.context.scene.frame_set(clip['start_frame']); bpy.context.scene.frame_set(clip['start_frame']+len(clip['root_offsets_m'])-1)
        editable = prior_pose.rotation_difference(bone.rotation_quaternion.normalized()).angle > .001
        actual_mesh_edit = float(np.max(np.linalg.norm(evaluated_points(body)-prior_mesh, axis=1))) > 1e-7
        # update() can relocate RNA keyframe storage; reacquire the live point.
        curve.keyframe_points[-1].co.y = prior; curve.update()
        restored = sample_check(rig, profile, clip, saved['base_world_translation'])
        report = dict(passed=matches and geometry_matches and editable and actual_mesh_edit and restored and hashlib.sha256(source.read_bytes()).hexdigest() == digest,
                      samples_match_saved_clip=matches, keyframes_editable=editable,
                      keyframe_edit_changed_actual_pose=editable, edit_restored=restored,
                      keyframe_edit_deformed_actual_mesh=actual_mesh_edit, sampled_mesh_motion=actual_mesh_motion,
                      saved_mesh_motion_matches=geometry_matches,
                      keyframe_points=sum(len(c.keyframe_points) for c in action_curves),
                      file_unchanged=hashlib.sha256(source.read_bytes()).hexdigest() == digest,
                      motion_generation_verified=False, declared_source=clip['source'])
        with out.open('x', encoding='utf-8') as file: json.dump(report, file, indent=2)
        if not report['passed']: raise ValueError('Saved motion import failed reinspection')
        print('MOTION_IMPORT_REOPEN_PASS', json.dumps(report), flush=True)
        return
    profile = json.loads(Path(args.profile).read_text())
    clip = json.loads(Path(args.clip).read_text())
    validate_clip(clip, profile)
    if not clip['joint_rotations']:
        raise ValueError('This first importer requires at least one joint track for editability checks')
    bpy.ops.wm.open_mainfile(filepath=str(source), use_scripts=False)
    rig = bpy.data.objects[profile['rig']]
    body = bpy.data.objects[profile['mesh']]
    before_mesh = mesh_state(body)
    actual = {**profile, 'bones': bone_data(rig)}
    if skeleton_signature(actual) != clip['skeleton_signature']:
        raise ValueError('Actual Blender rest skeleton differs from declared profile')
    if rig.animation_data and (rig.animation_data.action or rig.animation_data.nla_tracks or rig.animation_data.drivers):
        raise ValueError('Existing animation/drivers require an explicit merge policy; none are overwritten')
    if rig.parent is not None or any(b.constraints for b in rig.pose.bones):
        raise ValueError('This importer requires an unparented unconstrained deformation rig')
    if any(max(abs(v-(1 if i == j else 0)) for i, row in enumerate(b.matrix_basis) for j, v in enumerate(row)) > 1e-6 for b in rig.pose.bones):
        raise ValueError('Existing posed state requires an explicit merge policy')
    out.mkdir(parents=True, exist_ok=False)
    base = rig.matrix_world.copy()
    tracks = {k: continuous_quaternions(v) for k, v in clip['joint_rotations'].items()}
    scene = bpy.context.scene
    scene.render.fps, scene.render.fps_base = clip['fps'], 1
    scene.frame_start = clip['start_frame']; scene.frame_end = clip['start_frame']+len(clip['root_offsets_m'])-1
    for i, root_offset in enumerate(clip['root_offsets_m']):
        frame = clip['start_frame']+i
        rig.matrix_world = base.copy()
        rig.matrix_world.translation = base.translation+Vector(root_offset)/profile['coordinates']['meters_per_unit']
        rig.keyframe_insert('location', frame=frame)
        for joint, track in tracks.items():
            bone = rig.pose.bones[profile['joints'][joint]]
            bone.rotation_mode = 'QUATERNION'; bone.rotation_quaternion = track[i]
            bone.keyframe_insert('rotation_quaternion', frame=frame)
    for curve in curves(rig):
        for point in curve.keyframe_points: point.interpolation = 'LINEAR'
    if not sample_check(rig, profile, clip, list(base.translation)):
        raise ValueError('Baked motion does not match declared samples')
    after_mesh = mesh_state(body)
    preservation_keys = ['mesh_sha256', 'topology_sha256', 'weights_sha256', 'materials', 'modifiers']
    if any(before_mesh[k] != after_mesh[k] for k in preservation_keys):
        raise ValueError('Motion import altered control geometry, weights or materials')
    provenance = dict(profile=profile, clip=clip, input_sha256=digest, base_world_translation=list(base.translation),
                      control_mesh_and_weights_preserved=True,
                      sampled_mesh_motion=mesh_motion(body, clip),
                      motion_generation_verified=False,
                      scope='Generic compatible-rig motion import. Source label is declarative; fixtures are not learned motions. No retargeting or contact-quality claim.')
    bpy.data.texts.new('MOTION_IMPORT_PROVENANCE').write(json.dumps(provenance))
    scene.frame_set(scene.frame_start)
    bpy.ops.wm.save_as_mainfile(filepath=str(out/'motion.blend'))
    if hashlib.sha256(source.read_bytes()).hexdigest() != digest: raise ValueError('Original source file changed')
    (out/'execution.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')
    print('MOTION_IMPORT_PASS', flush=True)


if __name__ == '__main__': main()
