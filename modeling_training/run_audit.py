"""Audit update budgets and frozen training evidence, independently of accuracy gates."""
import argparse
from collections import Counter
import hashlib
import json
import math
from pathlib import Path


def digest(path):
    checksum = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            checksum.update(block)
    return checksum.hexdigest()


def inspect_budget(config, rows, records):
    updates = skips = 0
    indices, previous = [], None
    checks = dict(successful_update_semantics=config.get('step_budget') == 'successful_optimizer_updates',
                  attempt_sequence=True, counters=True, batches=True, retries=True,
                  finite_successes=True, skip_budget=True, completed_budget=True,
                  no_attempts_after_completion=True)
    for attempt, record in enumerate(records, 1):
        checks['no_attempts_after_completion'] &= updates < config.get('steps', 0)
        updated = record.get('optimizer_updated')
        if type(updated) is not bool:
            checks['counters'] = False
            continue
        updates += int(updated)
        skips += int(not updated)
        checks['attempt_sequence'] &= record.get('attempt') == attempt
        checks['counters'] &= (record.get('step') == updates
                               and record.get('successful_optimizer_steps') == updates
                               and record.get('skipped_optimizer_steps') == skips)
        batch = record.get('batch_indices')
        valid_batch = (isinstance(batch, list) and len(batch) == config.get('accumulate')
                       and all(type(i) is int and 0 <= i < len(rows) for i in batch))
        checks['batches'] &= valid_batch
        if previous is not None and previous.get('optimizer_updated') is False:
            checks['retries'] &= batch == previous.get('batch_indices')
        norm, loss = record.get('gradient_norm'), record.get('loss')
        checks['finite_successes'] &= (isinstance(loss, (int, float)) and math.isfinite(loss)
            and (record.get('gradients_finite') is True and isinstance(norm, (int, float)) and math.isfinite(norm)
                 if updated else record.get('gradients_finite') is False and norm is None))
        if updated and valid_batch:
            indices.extend(batch)
        previous = record
    checks['skip_budget'] = skips <= config.get('max_skipped_updates', 16)
    checks['completed_budget'] = updates == config.get('steps')
    visits = Counter(indices)
    if config.get('steps', 0)*config.get('accumulate', 0) == len(rows):
        checks['one_complete_pass'] = len(visits) == len(rows) and all(v == 1 for v in visits.values())
    return dict(passed=all(checks.values()), checks=checks,
                optimizer_attempts=len(records), successful_updates=updates, skipped_updates=skips,
                unique_training_rows=len(visits), successful_example_visits=len(indices),
                exposed_intents=dict(Counter(rows[i]['operation']['intent'] for i in indices)))


def audit(folder):
    folder = Path(folder)
    read = lambda path: json.loads(Path(path).read_text(encoding='utf-8'))
    config, weight = read(folder/'config.json'), read(folder/'weight-change.json')
    data = Path(config['data'])
    rows = [json.loads(line) for line in (data/'train.jsonl').read_text().splitlines()]
    def strict_constant(value):
        raise ValueError('Nonstandard JSON constant: '+value)
    records = [json.loads(line, parse_constant=strict_constant)
               for line in (folder/'training-log.jsonl').read_text().splitlines()]
    budget = inspect_budget(config, rows, records)
    saved = folder/'adapter/adapter_model.safetensors'
    checks = dict(update_evidence=budget['passed'],
                  saved_count_matches=weight.get('successful_optimizer_steps') == budget['successful_updates'],
                  saved_attempts_match=weight.get('optimizer_attempts') == budget['optimizer_attempts']
                      and weight.get('skipped_optimizer_steps') == budget['skipped_updates'],
                  saved_adapter_checksum=digest(saved) == weight['adapter_file_sha256'],
                  weights_changed=weight.get('weights_changed') is True
                      and all(isinstance(weight.get(k), str) and len(weight[k]) == 64
                              for k in ('before_sha256', 'after_sha256'))
                      and weight.get('before_sha256') != weight.get('after_sha256'),
                  source_snapshot=all(digest(folder/'source_snapshot'/name) == sha
                                      for name, sha in config['source_hashes'].items()),
                  frozen_data=all(digest(data/(split+'.jsonl')) == info['sha256']
                                  for split, info in config['dataset_manifest']['files'].items()))
    if config.get('initial_adapter'):
        origin = config['initial_adapter_weights']
        checks['warm_start_unchanged'] = digest(Path(config['initial_adapter'])/origin['file']) == origin['sha256']
    from safetensors import safe_open
    import torch
    with safe_open(saved, framework='pt', device='cpu') as tensors:
        names = list(tensors.keys())
        checks['all_saved_tensors_finite'] = bool(names) and all(torch.isfinite(tensors.get_tensor(n)).all().item() for n in names)
        changed_tensors = None
        if config.get('initial_adapter') and config['initial_adapter_weights']['file'].endswith('.safetensors'):
            with safe_open(Path(config['initial_adapter'])/config['initial_adapter_weights']['file'],
                           framework='pt', device='cpu') as original:
                checks['warm_start_tensor_keys_match'] = set(original.keys()) == set(names)
                changed_tensors = sum(not torch.equal(tensors.get_tensor(n), original.get_tensor(n))
                                      for n in names) if checks['warm_start_tensor_keys_match'] else 0
                checks['saved_tensor_values_changed'] = changed_tensors > 0
    return dict(training_evidence_passed=all(checks.values()), checks=checks, budget=budget,
                adapter_tensor_count=len(names), changed_tensors_vs_warm_start=changed_tensors,
                adapter_sha256=digest(saved),
                scope='Integrity and training exposure only. Does not establish language, geometry, animation or visual quality.',
                evaluations_complete=(read(folder/'result.json').get('status') == 'completed') if (folder/'result.json').exists() else False)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run', required=True)
    parser.add_argument('--output', required=True)
    args=parser.parse_args()
    report=audit(args.run)
    with Path(args.output).open('x',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2,allow_nan=False)
    print(json.dumps(report,indent=2,allow_nan=False))


if __name__=='__main__':
    main()
