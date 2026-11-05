"""Read saved evidence without claiming a process is still alive or a partial score final."""
import json
from pathlib import Path


def read(path):
    try:
        value = Path(path).read_text(encoding='utf-8-sig')
        return json.loads(value)
    except (OSError, ValueError, UnicodeError):
        return None


def summarize(folder, config):
    folder = Path(folder)
    result = read(folder/'result.json') or {}
    failure = read(folder/'failure.json')
    weight = read(folder/'weight-change.json') or {}
    attempts = updates = malformed = 0
    nonstandard = False
    log = folder/'training-log.jsonl'
    if log.is_file():
        for line in log.read_text(encoding='utf-8').splitlines():
            try:
                record = json.loads(line)
                if not isinstance(record, dict) or type(record.get('optimizer_updated')) is not bool:
                    raise ValueError('No update flag')
                # Old runs retain Infinity in their raw logs; flag it, never rewrite it.
                def reject_constant(value):
                    raise ValueError(value)
                try:
                    json.loads(line, parse_constant=reject_constant)
                except ValueError:
                    nonstandard = True
                attempts += 1
                updates += int(record['optimizer_updated'])
            except ValueError:
                malformed += 1
    stages = {}
    for name in ('baseline-test', 'previous-adapter-test', 'trained-test'):
        evaluation = read(folder/(name+'.json'))
        if not isinstance(evaluation, dict):
            continue
        records = evaluation.get('records', [])
        stages[name] = dict(complete=evaluation.get('complete') is True,
                            recorded_cases=len(records),
                            exact_recorded=sum(r.get('intent_exact') is True for r in records),
                            valid_recorded=sum(r.get('schema_valid') is True for r in records))
    if failure:
        stage = 'failed'
    elif result.get('status') == 'completed':
        stage = 'completed'
    elif weight:
        stage = 'candidate_evaluation'
    elif attempts:
        stage = 'training'
    elif 'previous-adapter-test' in stages:
        stage = 'reference_evaluation'
    elif 'baseline-test' in stages:
        stage = 'base_evaluation'
    else:
        stage = 'prepared'
    return dict(last_recorded_stage=stage, planned_updates=config.get('steps'),
                recorded_optimizer_attempts=attempts, recorded_successful_updates=updates,
                recorded_skips=attempts-updates, malformed_log_lines=malformed,
                legacy_nonstandard_json=nonstandard,
                saved_count_matches_log=(weight.get('successful_optimizer_steps') == updates) if weight else None,
                evaluation=stages, liveness_verified=False,
                scope='Saved metadata only. Partial counts are not completed scores or proof of a live process.')
