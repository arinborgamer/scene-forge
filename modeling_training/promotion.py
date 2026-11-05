"""Fail-closed experiment gates; passing only allows a Blender review, not release."""
import argparse
import hashlib
import json
import math
from pathlib import Path


def verified_counts(evaluation, expected):
    records = evaluation.get('records', [])
    if (evaluation.get('complete') is not True or evaluation.get('count') != expected
            or len(records) != expected or len({r.get('id') for r in records}) != expected
            or any(not isinstance(r.get(k), bool) for r in records for k in ('schema_valid', 'intent_exact'))):
        return None
    schema = sum(r['schema_valid'] for r in records)
    exact = sum(r['intent_exact'] for r in records)
    if (evaluation.get('schema_valid') != schema or evaluation.get('intent_exact') != exact
            or any(r['intent_exact'] and not r['schema_valid'] for r in records)):
        return None
    return {'count': expected, 'schema_valid': schema, 'intent_exact': exact}


def assess(result, trained, regression, weights_verified, expected=32, regression_expected=24):
    current = verified_counts(trained, expected)
    older = verified_counts(regression, regression_expected)
    previous = result.get('previous_adapter_test') or {}
    summary = result.get('trained_test') or {}
    checks = {
        'training_completed': result.get('status') == 'completed',
        'actual_updates_saved': result.get('weights_changed') is True
            and result.get('successful_optimizer_steps') == result.get('training_steps')
            and isinstance(result.get('training_steps'), int) and result['training_steps'] > 0,
        'saved_weight_checksum_matches': weights_verified is True,
        'candidate_evaluation_complete_and_consistent': current is not None
            and all(summary.get(k) == v for k, v in (current or {}).items()),
        'all_candidate_outputs_schema_valid': current is not None and current['schema_valid'] == expected,
        'candidate_exact_at_least_90_percent': current is not None and current['intent_exact'] >= math.ceil(.9*expected),
        'no_drop_on_same_suite': current is not None and previous.get('complete') is True
            and previous.get('count') == expected and isinstance(previous.get('intent_exact'), int)
            and current['intent_exact'] >= previous['intent_exact'],
        'regression_complete_and_consistent': older is not None,
        'all_regression_outputs_schema_valid': older is not None and older['schema_valid'] == regression_expected,
        'cgi_regression_at_least_previous_22_of_24': older is not None and older['intent_exact'] >= 22,
    }
    passed = all(checks.values())
    return {'decision': 'eligible_for_blender_review' if passed else 'keep_previous_adapter',
            'passed': passed, 'checks': checks,
            'failed_checks': [k for k, v in checks.items() if not v],
            'candidate_counts': current, 'regression_counts': older,
            'production_ready': False, 'default_model_changed': False,
            'scope': 'Synthetic single-operation gates only. Detailed-mesh execution, visual quality and cinematic motion require separate acceptance.'}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--regression', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--regression-cases', default='output/qwen-contrast-regression-cases.json')
    args = parser.parse_args()
    run, regression = Path(args.run), Path(args.regression)
    def read(path):
        return json.loads(path.read_text(encoding='utf-8')) if path.is_file() else {}
    weight = run/'adapter/adapter_model.safetensors'
    recorded = read(run/'weight-change.json').get('adapter_file_sha256')
    report = assess(read(run/'result.json'), read(run/'trained-test.json'),
                    read(regression/'trained.json'),
                    weight.is_file() and hashlib.sha256(weight.read_bytes()).hexdigest() == recorded)
    cases = Path(args.regression_cases)
    expected_hash = hashlib.sha256(cases.read_bytes()).hexdigest() if cases.is_file() else None
    report['checks']['regression_case_snapshot_matches'] = expected_hash is not None and read(regression/'provenance.json').get('cases_sha256') == expected_hash
    report['failed_checks'] = [k for k, v in report['checks'].items() if not v]
    report['passed'] = not report['failed_checks']
    report['decision'] = 'eligible_for_blender_review' if report['passed'] else 'keep_previous_adapter'
    report['run'] = str(run.resolve())
    report['regression'] = str(regression.resolve())
    report['evidence_hashes'] = {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in
                                 [run/'result.json', run/'trained-test.json', regression/'trained.json'] if p.is_file()}
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open('x', encoding='utf-8') as file:
        json.dump(report, file, indent=2)
    print(json.dumps(report, indent=2))
    # A rejected candidate is an expected experiment outcome, not a process crash.


if __name__ == '__main__':
    main()
