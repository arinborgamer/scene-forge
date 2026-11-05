"""Reopen, inspect and edit a saved humanoid in memory; never save over the input."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import bpy
import numpy as np


def coordinates(obj):
    bpy.context.view_layer.update()
    evaluated = obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh = evaluated.to_mesh()
    result = np.array([v.co[:] for v in mesh.vertices])
    evaluated.to_mesh_clear()
    return result


def verify(path, output):
    path, output = Path(path).resolve(), Path(output).resolve()
    before = hashlib.sha256(path.read_bytes()).hexdigest()
    bpy.ops.wm.open_mainfile(filepath=str(path))
    rig = bpy.data.objects['Humanoid_Rig']
    body = bpy.data.objects['Humanoid_Trained_Shape']
    subdivision = next(m for m in body.modifiers if m.type == 'SUBSURF')
    counts = {}
    for level in (0, 1, 2):
        subdivision.levels = level
        coords = coordinates(body)
        if not np.isfinite(coords).all():
            raise ValueError('Non-finite detail level')
        counts[str(level)] = len(coords)
    subdivision.levels = 0
    rest = coordinates(body)
    finger = rig.pose.bones['finger2-1.L']
    finger.rotation_mode = 'XYZ'
    finger.rotation_euler.x = .5
    changed = coordinates(body)
    finger.rotation_euler.x = 0
    restored = coordinates(body)
    # Edit an actual control vertex, observe the evaluation, then restore it.
    original = body.data.vertices[0].co.copy()
    body.data.vertices[0].co.x += .002
    body.data.update()
    edited = coordinates(body)
    body.data.vertices[0].co = original
    body.data.update()
    weights = [sum(g.weight for g in v.groups) for v in body.data.vertices]
    tests = {
        '163_bones': len(rig.data.bones) == 163,
        'quad_control_cage': all(len(p.vertices) == 4 for p in body.data.polygons),
        'normalized_weights': max(abs(w - 1) for w in weights) < 1e-5,
        'finger_edit_deforms_mesh': int(np.sum(np.linalg.norm(changed - rest, axis=1) > 1e-5)) > 4,
        'rest_pose_restored': float(np.max(np.abs(restored - rest))) < 1e-6,
        'mesh_vertex_editable': float(np.max(np.abs(edited - rest))) > .001,
        'no_animation_actions': len(bpy.data.actions) == 0,
        'embedded_provenance': 'MODEL_PROVENANCE.json' in bpy.data.texts,
        'input_file_unchanged': hashlib.sha256(path.read_bytes()).hexdigest() == before,
    }
    bones = [{'name': b.name, 'parent': b.parent.name if b.parent else None,
              'head': list(b.head_local), 'tail': list(b.tail_local)} for b in rig.data.bones]
    report = {'passed': all(tests.values()), 'checks': tests, 'subdivision_vertices': counts,
              'blend_sha256': before, 'bones': bones}
    with output.open('x', encoding='utf-8') as file:
        json.dump(report, file, indent=2)
    # Diagram is derived from the actual saved armature, not a decorative rig image.
    height = max(p[2] for b in bones for p in (b['head'], b['tail']))
    factor = 740 / height
    svg = ['<svg xmlns="http://www.w3.org/2000/svg" width="720" height="900" viewBox="0 0 720 900">',
           '<rect width="720" height="900" fill="#111b25"/>',
           '<text x="36" y="43" fill="#edf3f8" font-family="sans-serif" font-size="24">163 bones · saved armature</text>',
           '<text x="36" y="72" fill="#a4b5c5" font-family="sans-serif" font-size="15">MPFB CC0 skeleton fitted to predicted shape · front view</text>']
    for bone in bones:
        h, t = bone['head'], bone['tail']
        x1, y1 = 360 + h[0] * factor, 850 - h[2] * factor
        x2, y2 = 360 + t[0] * factor, 850 - t[2] * factor
        svg.append(f'<g><title>{bone["name"]}</title><line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" stroke="#58c8bb" stroke-width="2"/><circle cx="{x1:.2f}" cy="{y1:.2f}" r="2.2" fill="#f7cb88"/></g>')
    svg.append('</svg>')
    output.with_suffix('.svg').write_text('\n'.join(svg), encoding='utf-8')
    print('SAVED_HUMANOID_' + ('PASS ' if report['passed'] else 'FAIL ') + json.dumps(tests), flush=True)
    if not report['passed']:
        raise RuntimeError('Saved humanoid verification failed')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--blend', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args(sys.argv[sys.argv.index('--') + 1:])
    verify(args.blend, args.output)
