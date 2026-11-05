"""Fresh-process adapter transfer checks; no response repair or training."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from modeling_training.transfer_review import assess


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base', required=True)
    parser.add_argument('--adapter', required=True)
    parser.add_argument('--cases', default='examples/cinematic-modeling-canaries.json')
    parser.add_argument('--output', required=True)
    parser.add_argument('--blender', default=r'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe')
    parser.add_argument('--profile', choices=['modeling', 'vfx', 'intent','scene_intent'], default='vfx')
    args = parser.parse_args()
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    cases_path = Path(args.cases).resolve()
    cases = json.loads(cases_path.read_text(encoding='utf-8'))
    (out/'provenance.json').write_text(json.dumps({**vars(args), 'case_sha256': hashlib.sha256(cases_path.read_bytes()).hexdigest(),
                                                'method': 'Fresh process per request; raw responses applied without corrections. Expectations are review-only.'}, indent=2), encoding='utf-8')
    records = []
    for case in cases:
        job = out/case['id']
        command = [sys.executable, '-u', '-m', 'modeling_training.infer', '--base', args.base,
                   '--adapter', args.adapter, '--profile', args.profile, '--prompt', case['prompt'],
                   '--input', case['input'], '--editable', case['editable'], '--output', str(job),
                   '--blender', args.blender]
        with (out/(case['id']+'.log')).open('w', encoding='utf-8') as log:
            process = subprocess.run(command, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT, timeout=1800)
        if process.returncode:
            report = {'passed': False, 'error': 'Inference or Blender execution failed; inspect raw response and logs',
                      'exit_code': process.returncode}
        else:
            def read(path):
                return json.loads(path.read_text(encoding='utf-8'))
            report = assess(case, read(job/'scene/execution.json'), read(job/'reopen.json'), read(job/'request.json'))
        if job.exists():
            with (job/'acceptance.json').open('x', encoding='utf-8') as file:
                json.dump(report, file, indent=2)
        records.append({'id': case['id'], **report})
        (out/'result.json').write_text(json.dumps({'complete': False, 'records': records}, indent=2), encoding='utf-8')
        print(json.dumps(records[-1]), flush=True)
    summary = {'complete': True, 'passed': all(r['passed'] for r in records), 'count': len(records),
               'passed_count': sum(r['passed'] for r in records), 'records': records,
               'scope': 'Supplied shapes from one topology/rig family; not unrestricted mesh or rig generalization'}
    (out/'result.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
