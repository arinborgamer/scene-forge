"""Two authored validation clips. This script never generates learned motion."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scene_forge.motion_clip import skeleton_signature, validate_clip


def main():
    parser = argparse.ArgumentParser(); parser.add_argument('--output', required=True)
    parser.add_argument('--blender', default=r'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe')
    args = parser.parse_args()
    out = Path(args.output).resolve(); out.mkdir(parents=True, exist_ok=False)
    fixtures = [('athletic', 25, 24, {'left_elbow': (0, .45), 'right_shoulder': (0, .25), 'neck': (1, .12)}),
                ('older', 37, 30, {'right_wrist': (0, .3), 'left_hip': (0, .2), 'jaw': (0, .12)})]
    results = []
    for name, count, fps, joints in fixtures:
        profile_path = ROOT/'output/cinematic-rig-profiles-v1'/name/'profile.json'
        profile = json.loads(profile_path.read_text())
        tracks = {}
        for joint, (axis, amplitude) in joints.items():
            values = []
            for i in range(count):
                angle = amplitude*math.sin(math.pi*i/(count-1))
                q = [math.cos(angle/2), 0, 0, 0]; q[axis+1] = math.sin(angle/2); values.append(q)
            tracks[joint] = values
        clip = dict(schema_version=1, skeleton_signature=skeleton_signature(profile), fps=fps, start_frame=1,
                    root_offsets_m=[[.02*i/(count-1), -.01*i/(count-1), 0] for i in range(count)], joint_rotations=tracks,
                    source=dict(declared_kind='authored_fixture', id=name+'-import-validation-only'))
        validate_clip(clip, profile)
        path = out/(name+'-fixture.json'); path.write_text(json.dumps(clip, indent=2), encoding='utf-8')
        destination = out/name
        base = [args.blender, '--background', '--factory-startup', '--disable-autoexec', '--threads', '2',
                '--python-exit-code', '1', '--python', str(ROOT/'modeling_lab/import_motion.py'), '--']
        stages = [('import', ['--input', profile['source_path'], '--profile', str(profile_path), '--clip', str(path), '--output', str(destination)]),
                  ('reopen', ['--input', str(destination/'motion.blend'), '--output', str(out/(name+'-reopen.json')), '--verify'])]
        passed = True
        for stage, flags in stages:
            with (out/(name+'-'+stage+'.log')).open('w') as log:
                process = subprocess.run(base+flags, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=300)
            if process.returncode:
                passed = False; break
        report_path = out/(name+'-reopen.json')
        report = json.loads(report_path.read_text()) if report_path.exists() else {}
        passed = passed and report.get('passed') is True and report.get('sampled_mesh_motion', {}).get('moved_vertices', 0) > 4
        results.append(dict(id=name, passed=passed, report=str(report_path), keyframe_points=report.get('keyframe_points')))
        (out/'result.json').write_text(json.dumps(dict(complete=False, records=results), indent=2), encoding='utf-8')
        print(json.dumps(results[-1]), flush=True)
    summary = dict(complete=True, passed=all(r['passed'] for r in results), count=2, records=results,
                   motion_generation_verified=False, scope='Authored import fixtures on two shapes of one supplied rig family; no learned motion or retargeting claim')
    (out/'result.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    if not summary['passed']: raise RuntimeError('Motion fixture failed; outputs and source files preserved')


if __name__ == '__main__': main()
