"""Review typed-intent experiments from raw responses and frozen cases."""
import argparse
import hashlib
import json
from pathlib import Path

from modeling_training.intent_eval import score


def inspect(evaluation, rows, scorer=score):
    expected = {r['id']: r for r in rows}
    records = evaluation.get('records', [])
    if (evaluation.get('complete') is not True or evaluation.get('count') != len(rows)
            or len(records) != len(rows) or len(expected) != len(rows)
            or {r.get('id') for r in records} != expected.keys()):
        return None
    groups = {}
    exact = valid = 0
    for record in records:
        row = expected[record['id']]
        if record.get('prompt') != row['prompt']:
            return None
        measured = scorer(record.get('raw', ''), row)
        if any(record.get(k) is not measured[k] for k in ('schema_valid', 'intent_exact')):
            return None
        key = row['operation']['intent']
        counts = groups.setdefault(key, dict(count=0, exact=0))
        counts['count'] += 1
        counts['exact'] += int(measured['intent_exact'])
        valid += int(measured['schema_valid']); exact += int(measured['intent_exact'])
    if evaluation.get('schema_valid') != valid or evaluation.get('intent_exact') != exact:
        return None
    return dict(count=len(rows), schema_valid=valid, intent_exact=exact, groups=groups)


def evaluation_bound(provenance,config,adapter_hash):
    try:
        return (isinstance(provenance.get('candidate_weights'),dict)
                and provenance['candidate_weights'].get('sha256')==adapter_hash
                and provenance.get('profile')==config['profile']
                and Path(provenance['base']).resolve()==Path(config['base']).resolve())
    except (KeyError,TypeError):
        return False


def assess(result, candidate, regression, weights_verified, snapshots_verified,regression_bound=True):
    checks = dict(
        training_completed=result.get('status') == 'completed',
        saved_updates=result.get('weights_changed') is True and result.get('training_steps', 0) > 0
            and result.get('successful_optimizer_steps') == result.get('training_steps'),
        weights_verified=weights_verified is True,
        regression_model_binding=regression_bound is True,
        case_and_compiler_snapshots_verified=snapshots_verified is True,
        primary_complete=candidate is not None and candidate['count'] == 56,
        primary_all_valid=candidate is not None and candidate['schema_valid'] == 56,
        primary_at_least_51_exact=candidate is not None and candidate['intent_exact'] >= 51,
        not_worse_than_base=candidate is not None and result.get('baseline_test', {}).get('complete') is True
            and candidate['intent_exact'] >= result['baseline_test'].get('intent_exact', 57),
        regression_all_valid=regression is not None and regression['count'] == 56 and regression['schema_valid'] == 56,
    )
    minimums = {'local_translate': 16, 'object_translate': 16, 'local_scale': 5, 'unsupported': 6}
    for kind, minimum in minimums.items():
        checks[kind+'_slice'] = candidate is not None and candidate['groups'].get(kind, {}).get('exact', 0) >= minimum
    checks['cgi_slice'] = candidate is not None and sum(candidate['groups'].get(k, {}).get('exact', 0)
                                                      for k in ('light_power', 'camera_lens', 'surface', 'glow')) >= 7
    # Regression subgroup counts are provided only after raw records have been re-scored.
    checks['older_modeling_at_least_29_of_32'] = regression is not None and regression.get('modeling_exact', 0) >= 29
    checks['older_cgi_at_least_22_of_24'] = regression is not None and regression.get('cgi_exact', 0) >= 22
    return dict(passed=all(checks.values()), decision='eligible_for_blender_review' if all(checks.values()) else 'keep_previous_adapter',
                checks=checks, failed_checks=[k for k, v in checks.items() if not v], candidate=candidate, regression=regression,
                default_model_changed=False, production_ready=False,
                scope='Language and compiled-action gates only. Blender transfer and artistic acceptance are separate; compiler invariants are not learned model skills.')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True); parser.add_argument('--regression', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--profile',choices=['intent','scene_intent'],default='intent')
    args = parser.parse_args()
    run, reg = Path(args.run), Path(args.regression)
    def read(path):
        return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    config, result = read(run/'config.json'), read(run/'result.json')
    data = Path(config['data'])
    manifest = read(data/'manifest.json')
    rows = [json.loads(line) for line in (data/'test.jsonl').read_text().splitlines()]
    regression_path = Path(read(reg/'provenance.json')['cases'])
    regression_rows = read(regression_path)
    if args.profile=='scene_intent':
        from modeling_training.scene_intent_data import verify_manifest,verify_companion
        verify_manifest(data,config['dataset_manifest'])
        if regression_path.resolve()!=(data/'regression.json').resolve():
            raise ValueError('Regression did not consume the frozen companion')
        regression_rows,_=verify_companion(regression_path,config['dataset_manifest'])
    scorer=score
    if args.profile=='scene_intent':
        from modeling_training.scene_intent_eval import score as scorer
    candidate = inspect(read(run/'trained-test.json'), rows,scorer)
    regression = inspect(read(reg/'trained.json'), regression_rows,scorer)
    if regression:
        actual = {r['id']: r for r in read(reg/'trained.json')['records']}
        for tag, count in [('balanced', 32), ('cgi', 24)]:
            selected = [r for r in regression_rows if r['id'].startswith('regression-'+tag+'-')]
            regression['modeling_exact' if tag == 'balanced' else 'cgi_exact'] = sum(actual[r['id']]['intent_exact'] for r in selected) if len(selected) == count else -1
    weight = run/'adapter/adapter_model.safetensors'
    weight_ok = weight.is_file() and hashlib.sha256(weight.read_bytes()).hexdigest() == read(run/'weight-change.json').get('adapter_file_sha256')
    if args.profile=='scene_intent':
        from modeling_training.scene_intent_ops import compiler_sha256
        compiler_hash=compiler_sha256()
    else:compiler_hash = hashlib.sha256(Path(__file__).with_name('intent_ops.py').read_bytes()).hexdigest()
    snapshots_ok = (manifest.get('profile')==args.profile==config.get('profile')
                    and manifest.get('compiler_sha256') == compiler_hash
                    and hashlib.sha256((data/'test.jsonl').read_bytes()).hexdigest() == manifest['files']['test']['sha256']
                    and hashlib.sha256(regression_path.read_bytes()).hexdigest() == read(reg/'provenance.json').get('cases_sha256'))
    bound=evaluation_bound(read(reg/'provenance.json'),config,hashlib.sha256(weight.read_bytes()).hexdigest()) if weight.is_file() else False
    report = assess(result, candidate, regression, weight_ok, snapshots_ok,bound)
    report.update(run=str(run.resolve()), regression_directory=str(reg.resolve()), compiler_sha256=compiler_hash)
    output = Path(args.output)
    with output.open('x', encoding='utf-8') as f:
        json.dump(report, f, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
