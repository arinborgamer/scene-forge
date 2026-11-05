"""Finish a bounded intent experiment from saved reports, with no model calls."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def combined(gate, transfer, lookdev, rigs, challenge=None,negative=None):
    checks = dict(language_and_regression_gate=gate.get('passed') is True,
                  two_mesh_requests=transfer.get('complete') is True and transfer.get('count') == 2
                      and transfer.get('passed_count') == 2 and transfer.get('passed') is True,
                  editable_cgi_fixture=lookdev.get('passed') is True,
                  two_post_edit_rig_checks=len(rigs) == 2 and all(r.get('passed') is True for r in rigs))
    if challenge is not None:
        checks['fresh_language_suite'] = (challenge.get('count') == 20 and challenge.get('schema_valid') == 20
                                         and challenge.get('intent_exact', 0) >= 18
                                         and challenge.get('groups', {}).get('unsupported', {}).get('exact') == 5)
    if negative is not None:
        checks['negative_scale_request']=(negative.get('complete') is True and negative.get('count')==1
                                         and negative.get('passed_count')==1 and negative.get('passed') is True)
    return dict(complete=True, passed=all(checks.values()), checks=checks,
                decision='eligible_for_human_visual_review' if all(checks.values()) else 'keep_previous_adapter',
                production_ready=False, default_model_changed=False, human_visual_review='pending',
                scope='Bounded existing-element edit workflow. Supplied anatomy and rig; no trained geometry/motion generation or cinematic-quality claim.')


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def verify_scene_transfer(folder,data,config,candidate_hash,artifact):
    """Bind passed transfer claims to raw requests, observed candidates and actual execution."""
    from modeling_training.scene_intent_data import verify_artifact
    from modeling_training.transfer_review import assess
    folder=Path(folder)
    provenance=read(folder/'provenance.json')
    cases=verify_artifact(provenance['cases'],data,config['dataset_manifest'])
    if Path(provenance['cases']).resolve()!=Path(data).resolve()/artifact or provenance.get('profile')!='scene_intent':
        raise ValueError('Transfer used another profile or canary artifact')
    if hashlib.sha256(Path(provenance['cases']).read_bytes()).hexdigest()!=provenance['case_sha256']:
        raise ValueError('Transfer case provenance changed')
    result=read(folder/'result.json')
    actual={r['id']:r for r in result.get('records',[])}
    if len(actual)!=len(cases) or len(result.get('records',[]))!=len(cases) or set(actual)!={c['id'] for c in cases}:
        raise ValueError('Transfer case identities are incomplete')
    checks=[]
    for case in cases:
        job=folder/case['id']
        if actual[case['id']].get('passed') is not True:
            checks.append(False)
            continue
        request=read(job/'request.json')
        if request.get('adapter_sha256')!=candidate_hash or request.get('profile')!='scene_intent':
            raise ValueError('Transfer used a different candidate')
        payload_file,inventory_file=job/'model-input.json',job/'source-inventory.json'
        if (hashlib.sha256(payload_file.read_bytes()).hexdigest()!=request.get('model_input_sha256')
                or hashlib.sha256(inventory_file.read_bytes()).hexdigest()!=request.get('observed_inventory_sha256')):
            raise ValueError('Model-visible scene evidence changed')
        payload,inventory=read(payload_file),read(inventory_file)
        observed=[dict(name=o['id'],type='MESH') for o in inventory['objects']]
        if (set(payload)!={'request','scene'} or payload['request']!=case['prompt']
                or sorted(payload['scene'],key=lambda e:e['name'])!=sorted(observed,key=lambda e:e['name'])
                or len(observed)<3):
            raise ValueError('Transfer did not offer independent observed scene choices')
        recomputed=assess(case,read(job/'scene/execution.json'),read(job/'reopen.json'),request)
        checks.append(recomputed.get('passed') is True)
    result['passed']=result.get('passed') is True and all(checks)
    result['independent_catalog_and_execution_rechecked']=all(checks)
    return result


def main():
    parser = argparse.ArgumentParser()
    for name in ['run', 'regression', 'transfer', 'vfx-inference', 'vfx-cases', 'vfx-output', 'output']:
        parser.add_argument('--'+name, required=True)
    parser.add_argument('--blender', default=r'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe')
    parser.add_argument('--challenge', help='Optional completed 20-case frozen challenge evaluation directory')
    parser.add_argument('--negative-transfer',help='Required scene-intent negative-scale Blender transfer')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    run, reg, transfer, vfx = [Path(p).resolve() for p in [args.run, args.regression, args.transfer, args.vfx_inference]]
    profile=read(run/'config.json').get('profile','intent')
    run_config=read(run/'config.json')
    from modeling_training.intent_gate import evaluation_bound
    candidate_hash=hashlib.sha256((run/'adapter/adapter_model.safetensors').read_bytes()).hexdigest()
    vfx_provenance=read(vfx/'provenance.json')
    if (not evaluation_bound(vfx_provenance,run_config,candidate_hash)
            or Path(vfx_provenance['cases']).resolve()!=Path(args.vfx_cases).resolve()
            or hashlib.sha256(Path(args.vfx_cases).read_bytes()).hexdigest()!=vfx_provenance['cases_sha256']):
        raise ValueError('CGI evaluation is not bound to this candidate/profile/case file')
    if profile=='scene_intent':
        from modeling_training.scene_intent_data import verify_companion,verify_artifact
        data=Path(run_config['data']).resolve()
        if Path(args.vfx_cases).resolve()!=data/'vfx.json':
            raise ValueError('CGI review did not consume the frozen companion')
        verify_companion(args.vfx_cases,run_config['dataset_manifest'])
        positive_provenance=read(transfer/'provenance.json')
        verify_artifact(positive_provenance['cases'],data,run_config['dataset_manifest'])
        if Path(positive_provenance['cases']).resolve()!=data/'positive-transfer.json':
            raise ValueError('Positive transfer used another canary set')
    if profile=='scene_intent' and (not args.challenge or not args.negative_transfer):
        raise ValueError('Scene-aware review requires fresh challenge and negative-scale transfer')
    out, lookdev = Path(args.output).resolve(), Path(args.vfx_output).resolve()
    if out.exists() or lookdev.exists():
        raise FileExistsError('Refusing to overwrite a review directory')
    for path in [run/'result.json', reg/'result.json', transfer/'result.json', vfx/'result.json']:
        read(path)
    transfer_result, vfx_result = read(transfer/'result.json'), read(vfx/'trained.json')
    if profile=='scene_intent':
        candidate_hash=hashlib.sha256((run/'adapter/adapter_model.safetensors').read_bytes()).hexdigest()
        transfer_result=verify_scene_transfer(transfer,data,run_config,candidate_hash,'positive-transfer.json')
    if not transfer_result.get('complete') or not vfx_result.get('complete'):
        raise ValueError('Required diagnostic reports are incomplete')
    out.mkdir(parents=True, exist_ok=False)

    def command(argv, log):
        try:
            with log.open('w', encoding='utf-8') as stream:
                process = subprocess.run(argv, cwd=root, stdout=stream, stderr=subprocess.STDOUT, timeout=900)
            return process.returncode == 0
        except subprocess.TimeoutExpired:
            with log.open('a', encoding='utf-8') as stream:
                stream.write('\nStage timed out; no success inferred.\n')
            return False

    if not command([sys.executable, '-m', 'modeling_training.intent_gate', '--run', str(run), '--regression', str(reg),
                    '--output', str(out/'gate.json'),'--profile',profile], out/'gate.log'):
        raise RuntimeError('Could not establish a consistent gate decision')
    gate = read(out/'gate.json')
    rigs = []
    for record in transfer_result['records']:
        name = record['id']
        blend = transfer/name/'scene/model.blend'
        rig_out = out/('rig-'+name)
        passed = record.get('passed') is True and blend.is_file()
        if passed:
            passed = command([args.blender, '--background', '--factory-startup', '--disable-autoexec', '--threads', '2',
                              '--python-exit-code', '1', '--python', str(root/'modeling_lab/inspect_rig.py'), '--',
                              '--input', str(blend), '--output', str(rig_out)], out/(name+'-rig.log'))
        report_path = rig_out/'acceptance.json'
        passed = passed and report_path.is_file() and read(report_path).get('passed') is True
        rigs.append(dict(id=name, passed=bool(passed), report=str(report_path) if report_path.exists() else None))
    records = vfx_result['records']
    fixture = dict(passed=False, reason='Model did not satisfy all four controls; no automatic correction or selective rendering')
    if len(records) == 4 and all(r.get('schema_valid') and r.get('intent_exact') for r in records):
        base = [args.blender, '--background', '--factory-startup', '--disable-autoexec', '--threads', '4',
                '--python-exit-code', '1', '--python', str(root/'scripts/review_vfx_blender.py'), '--']
        built = command([*base, 'build', str(lookdev), str(vfx/'trained.json'), str(Path(args.vfx_cases).resolve())], out/'lookdev-build.log')
        reopened = built and command([*base, 'reopen', str(lookdev)], out/'lookdev-reopen.log')
        report_path = lookdev/'reopen.json'
        if reopened and report_path.is_file():
            fixture = {**read(report_path), 'blend': str(lookdev/'review.blend')}
        else:
            fixture = dict(passed=False, reason='Blender build/render/reopen failed; logs preserved')
    challenge = None
    if args.challenge:
        from modeling_training.intent_gate import inspect
        challenge_path = Path(args.challenge)
        provenance = read(challenge_path/'provenance.json')
        candidate_hash = hashlib.sha256((run/'adapter/adapter_model.safetensors').read_bytes()).hexdigest()
        if (provenance.get('profile') != profile
                or provenance.get('candidate_weights', {}).get('sha256') != candidate_hash):
            raise ValueError('Challenge evaluated a different adapter or protocol')
        cases_path = Path(provenance['cases'])
        if profile=='scene_intent':
            if cases_path.resolve()!=data/'challenge.json':
                raise ValueError('Challenge did not consume the pretraining-frozen cases')
            verify_companion(cases_path,run_config['dataset_manifest'])
        if hashlib.sha256(cases_path.read_bytes()).hexdigest() != provenance['cases_sha256']:
            raise ValueError('Frozen challenge cases changed')
        if profile=='scene_intent':
            from modeling_training.scene_intent_eval import score as scorer
            challenge=inspect(read(challenge_path/'trained.json'),read(cases_path),scorer)
        else:challenge = inspect(read(challenge_path/'trained.json'), read(cases_path))
        if challenge is None:
            raise ValueError('Challenge evidence is incomplete or inconsistent')
    negative=read(Path(args.negative_transfer)/'result.json') if args.negative_transfer else None
    if negative is not None:
        from modeling_training.transfer_review import assess
        negative_root=Path(args.negative_transfer)
        negative_provenance=read(negative_root/'provenance.json')
        negative_cases=Path(negative_provenance['cases'])
        cases=read(negative_cases)
        if profile=='scene_intent':
            cases=verify_artifact(negative_cases,data,run_config['dataset_manifest'])
            if negative_cases.resolve()!=data/'negative-transfer.json':
                raise ValueError('Negative transfer used another canary set')
        if (hashlib.sha256(negative_cases.read_bytes()).hexdigest()!=negative_provenance['case_sha256']
                or negative_provenance.get('profile')!=profile or len(cases)!=1):
            raise ValueError('Negative-scale provenance does not match this experiment')
        case=cases[0]
        wanted=case['expected_operation']
        if (wanted['op']!='deform' or wanted['translation']!=[0,0,0]
                or not any(0<value<1 for value in wanted['scale'])
                or any(value>1 for value in wanted['scale'])):
            raise ValueError('Negative-scale transfer did not request a contraction')
        job=negative_root/case['id']
        request=read(job/'request.json')
        if request.get('adapter_sha256')!=hashlib.sha256((run/'adapter/adapter_model.safetensors').read_bytes()).hexdigest():
            raise ValueError('Negative-scale transfer evaluated a different adapter')
        if negative.get('passed') is True:
            recomputed=assess(case,read(job/'scene/execution.json'),read(job/'reopen.json'),request)
            negative['passed']=recomputed.get('passed') is True
            negative['recomputed_acceptance']=recomputed
        if profile=='scene_intent':
            negative=verify_scene_transfer(negative_root,data,run_config,candidate_hash,'negative-transfer.json')
    result = combined(gate, transfer_result, fixture, rigs, challenge,negative)
    if negative is not None:result['negative_scale_transfer']=negative
    if challenge is not None:
        result['challenge'] = challenge
    result.update(post_edit_rigs=rigs, lookdev=fixture,
                  evidence_hashes={str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                   [out/'gate.json', transfer/'result.json', vfx/'trained.json']})
    if args.challenge:
        for file in ('trained.json', 'provenance.json'):
            path = Path(args.challenge)/file
            result['evidence_hashes'][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
    if args.negative_transfer:
        for file in ('result.json','provenance.json'):
            path=Path(args.negative_transfer)/file
            result['evidence_hashes'][str(path)]=hashlib.sha256(path.read_bytes()).hexdigest()
    (out/'result.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    command([sys.executable, str(root/'scripts/index_training_data.py')], out/'index.log')
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
