"""Actual assistant-only LoRA training, with unmodified-model baseline and saved evidence."""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import random

os.environ.setdefault('HF_HUB_OFFLINE', '1')
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model, PeftModel
from modeling_lab.operations import validate_plan
from modeling_training.corpus import SYSTEM, wrapped
from modeling_training.optimizer_steps import train_updates, require_finite_weights

PROFILE = 'modeling'

def configure_profile(profile):
    global SYSTEM, PROFILE
    PROFILE = profile
    if profile == 'vfx':
        from modeling_training.vfx_ops import SYSTEM as VFX_SYSTEM
        SYSTEM = VFX_SYSTEM
    elif profile == 'scene_intent':
        from modeling_training.scene_intent_ops import SYSTEM as SCENE_SYSTEM
        SYSTEM = SCENE_SYSTEM
    elif profile == 'intent':
        from modeling_training.intent_ops import SYSTEM as INTENT_SYSTEM
        SYSTEM = INTENT_SYSTEM
    elif profile == 'modeling':
        from modeling_training.corpus import SYSTEM as MODELING_SYSTEM
        SYSTEM = MODELING_SYSTEM
    else:
        raise ValueError('Unknown training profile')


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2, allow_nan=False), encoding='utf-8')


def read_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def prompt_tokens(tokenizer, prompt):
    return tokenizer.apply_chat_template([{'role': 'system', 'content': SYSTEM}, {'role': 'user', 'content': prompt}],
                                          tokenize=True, add_generation_prompt=True, enable_thinking=False)


def encode(tokenizer, row, max_length=768):
    prefix = prompt_tokens(tokenizer, row['prompt'])
    answer = tokenizer.encode(json.dumps(row['operation'], separators=(',', ':')) + tokenizer.eos_token,
                              add_special_tokens=False)
    ids = prefix + answer
    if len(ids) > max_length:
        raise ValueError(f'Example {row["id"]} has {len(ids)} tokens; never silently truncate targets')
    return {'input_ids': torch.tensor([ids], dtype=torch.long),
            'attention_mask': torch.ones((1, len(ids)), dtype=torch.long),
            'labels': torch.tensor([[-100]*len(prefix) + answer], dtype=torch.long)}


def equivalent(a, b):
    if isinstance(b, dict):
        return isinstance(a, dict) and a.keys() == b.keys() and all(equivalent(a[k], b[k]) for k in b)
    if isinstance(b, list):
        return isinstance(a, list) and len(a) == len(b) and all(equivalent(x, y) for x, y in zip(a, b))
    if isinstance(b, (int, float)):
        return isinstance(a, (int, float)) and not isinstance(a, bool) and math.isfinite(a) and abs(a-b) < 1e-5
    return a == b


def score(raw, row):
    if PROFILE == 'scene_intent':
        from modeling_training.scene_intent_eval import score as score_scene
        return score_scene(raw,row)
    if PROFILE == 'intent':
        from modeling_training.intent_eval import score as score_intent
        return score_intent(raw, row)
    result = {'schema_valid': False, 'intent_exact': False}
    try:
        op = json.loads(raw)
        expected = row['operation']
        existing = [expected['target']] if 'target' in expected else []
        if PROFILE == 'vfx':
            from modeling_training.vfx_ops import validate_operation
            validate_operation(op, existing)
        else:
            validate_plan(wrapped(op), existing)
        result.update(schema_valid=True, intent_exact=equivalent(op, expected), operation=op)
    except (ValueError, TypeError, KeyError) as exc:
        result['error'] = str(exc)
    return result


@torch.no_grad()
def evaluate(model, tokenizer, rows, path):
    model.eval()
    records = []
    for row in rows:
        ids = torch.tensor([prompt_tokens(tokenizer, row['prompt'])], device='cuda')
        generated = model.generate(input_ids=ids, attention_mask=torch.ones_like(ids), do_sample=False,
                                   max_new_tokens=192, use_cache=True, pad_token_id=tokenizer.eos_token_id)
        raw = tokenizer.decode(generated[0, ids.shape[1]:], skip_special_tokens=True).strip()
        records.append({'id': row['id'], 'prompt': row['prompt'], 'raw': raw, **score(raw, row)})
        write(path, {'complete': False, 'records': records})
        print(json.dumps({'event': 'evaluation', 'set': Path(path).stem, 'case': row['id'],
                          'schema_valid': records[-1]['schema_valid'], 'intent_exact': records[-1]['intent_exact']}), flush=True)
    summary = {'complete': True, 'count': len(records),
               'schema_valid': sum(r['schema_valid'] for r in records),
               'intent_exact': sum(r['intent_exact'] for r in records), 'records': records}
    write(path, summary)
    return summary


@torch.no_grad()
def validation_loss(model, batches):
    model.eval()
    losses = []
    for batch in batches:
        with torch.autocast('cuda', dtype=torch.float16):
            loss = model(**{k: v.to('cuda') for k, v in batch.items()}, use_cache=False).loss
        if not torch.isfinite(loss).item():
            raise RuntimeError('Nonfinite validation loss')
        losses.append(loss.item())
    return sum(losses)/len(losses)


def adapter_digest(model):
    h = hashlib.sha256()
    for name, parameter in model.named_parameters():
        if parameter.requires_grad:
            h.update(name.encode())
            h.update(parameter.detach().float().cpu().contiguous().numpy().tobytes())
    return h.hexdigest()


def adapter_source(path):
    """Match PEFT's local weight format precedence when recording a warm start."""
    for name in ('adapter_model.safetensors', 'adapter_model.bin'):
        file = Path(path)/name
        if file.is_file():
            return dict(file=name, sha256=hashlib.sha256(file.read_bytes()).hexdigest())
    raise ValueError('Warm start has no supported local adapter weight file')


def run(args, output):
    configure_profile(getattr(args, 'profile', 'modeling'))
    torch.set_num_threads(4)
    torch.manual_seed(22104)
    random.seed(22104)
    if not torch.cuda.is_available():
        raise RuntimeError('CUDA unavailable; no silent CPU training fallback')
    data = Path(args.data)
    manifest = json.loads((data/'manifest.json').read_text())
    if PROFILE=='scene_intent':
        from modeling_training.scene_intent_data import verify_manifest
        verify_manifest(data)
    for split, info in manifest['files'].items():
        if hashlib.sha256((data/(split+'.jsonl')).read_bytes()).hexdigest() != info['sha256']:
            raise ValueError('Dataset changed after freeze')
    verification = json.loads((data/'blender-verification.json').read_text())
    if not verification['passed'] or verification['count'] != sum(x['count'] for x in manifest['files'].values()):
        raise ValueError('Dataset lacks completed Blender target verification')
    if PROFILE=='scene_intent' and (verification.get('files')!=manifest['files']
            or verification.get('manifest_sha256')!=hashlib.sha256((data/'manifest.json').read_bytes()).hexdigest()):
        raise ValueError('Blender verification is not bound to this frozen manifest')
    if PROFILE in ('intent','scene_intent'):
        if PROFILE == 'scene_intent':
            from modeling_training.scene_intent_ops import compiler_sha256
            compiler_hash=compiler_sha256()
        else:
            compiler_hash = hashlib.sha256(Path(__file__).with_name('intent_ops.py').read_bytes()).hexdigest()
        if manifest.get('profile') != PROFILE or manifest.get('system') != SYSTEM:
            raise ValueError('Intent dataset/system profile mismatch')
        if manifest.get('compiler_sha256') != compiler_hash or verification.get('compiler_sha256') != compiler_hash:
            raise ValueError('Intent compiler changed after freeze or target verification')
    base = Path(args.base).resolve()
    sources = {p.name: p.read_bytes() for p in Path(__file__).parent.glob('*.py')}
    config = {**vars(args), 'seed': 22104, 'base': str(base), 'base_source': json.loads((base/'source-manifest.json').read_text()),
              'dataset_manifest': manifest, 'gpu': torch.cuda.get_device_name(0), 'torch': torch.__version__,
              'lora': {'r': 8, 'alpha': 16, 'dropout': .05, 'targets': ['q_proj', 'v_proj']},
              'step_budget': 'successful_optimizer_updates',
              'max_skipped_updates': getattr(args, 'max_skipped_updates', 16),
              'source_hashes': {name: hashlib.sha256(content).hexdigest() for name, content in sources.items()}}
    if getattr(args, 'initial_adapter', None):
        config['initial_adapter_weights'] = adapter_source(args.initial_adapter)
    write(output/'config.json', config)
    snapshot = output/'source_snapshot'
    snapshot.mkdir(exist_ok=False)
    for name, content in sources.items():
        (snapshot/name).write_bytes(content)
    tokenizer = AutoTokenizer.from_pretrained(base, local_files_only=True, trust_remote_code=False)
    tokenizer.pad_token = tokenizer.eos_token
    model = AutoModelForCausalLM.from_pretrained(base, torch_dtype=torch.float16, local_files_only=True,
                                                trust_remote_code=False, attn_implementation='sdpa').to('cuda')
    model.generation_config.temperature = None
    model.generation_config.top_p = None
    model.generation_config.top_k = None
    train_rows = read_rows(data/'train.jsonl')
    val_rows = read_rows(data/'validation.jsonl')
    test_rows = read_rows(data/'test.jsonl')
    batches = [encode(tokenizer, row) for row in train_rows]
    val_batches = [encode(tokenizer, row) for row in val_rows]
    write(output/'tokenization.json', {'max_tokens': max(b['input_ids'].shape[1] for b in batches+val_batches),
                                       'assistant_only_loss': True, 'truncated': False})
    baseline = evaluate(model, tokenizer, test_rows, output/'baseline-test.json')
    base_val = validation_loss(model, val_batches)
    previous = None
    if getattr(args, 'initial_adapter', None):
        model = PeftModel.from_pretrained(model, args.initial_adapter, is_trainable=True)
        previous = evaluate(model, tokenizer, test_rows, output/'previous-adapter-test.json')
    else:
        model = get_peft_model(model, LoraConfig(r=8, lora_alpha=16, target_modules=['q_proj', 'v_proj'],
                                                lora_dropout=.05, bias='none', task_type='CAUSAL_LM'))
    model.config.use_cache = False
    model.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    model.enable_input_require_grads()
    trainable = [p for p in model.parameters() if p.requires_grad]
    for p in trainable:
        p.data = p.data.float()
    initial = adapter_digest(model)
    write(output/'initial-adapter.json', {'sha256': initial, 'trainable_parameters': sum(p.numel() for p in trainable),
                                         'baseline_validation_loss': base_val})
    optimizer = torch.optim.AdamW(trainable, lr=args.learning_rate, weight_decay=.01)
    scaler = torch.amp.GradScaler('cuda')
    model.train()
    torch.cuda.reset_peak_memory_stats()

    def loss_for_batch(batch):
        with torch.autocast('cuda', dtype=torch.float16):
            return model(**{k: v.to('cuda') for k, v in batch.items()}, use_cache=False).loss

    def record_attempt(record):
        with (output/'training-log.jsonl').open('a', encoding='utf-8') as file:
            file.write(json.dumps(record, allow_nan=False)+'\n')
        print(json.dumps({'event': 'training', **record}, allow_nan=False), flush=True)

    def save_checkpoint(record):
        if record['step'] == 1 or record['step'] % 20 == 0:
            checkpoint = output/f'checkpoint-{record["step"]:04d}'
            model.save_pretrained(checkpoint, safe_serialization=True)
            write(checkpoint/'step.json', record)

    budget = train_updates(parameters=trainable, optimizer=optimizer, scaler=scaler,
                           batches=batches, loss_for_batch=loss_for_batch,
                           updates=args.steps, accumulate=args.accumulate,
                           max_skipped=getattr(args, 'max_skipped_updates', 16),
                           record=record_attempt, checkpoint=save_checkpoint,
                           peak_memory=lambda: torch.cuda.max_memory_allocated()/1024**2)
    require_finite_weights(trainable)
    final_digest = adapter_digest(model)
    if final_digest == initial or not budget['successful_optimizer_steps']:
        raise RuntimeError('No adapter weight updates occurred')
    adapter = output/'adapter'
    model.save_pretrained(adapter, safe_serialization=True)
    tokenizer.save_pretrained(adapter)
    write(output/'weight-change.json', {'before_sha256': initial, 'after_sha256': final_digest,
                                        'weights_changed': True, **budget,
                                        'adapter_file_sha256': hashlib.sha256((adapter/'adapter_model.safetensors').read_bytes()).hexdigest()})
    model.gradient_checkpointing_disable()
    tuned_val = validation_loss(model, val_batches)
    trained = evaluate(model, tokenizer, test_rows, output/'trained-test.json')
    result = {'status': 'completed', 'weights_changed': True, 'training_steps': args.steps,
              **budget, 'step_budget': 'successful_optimizer_updates',
              'peak_allocated_mb': torch.cuda.max_memory_allocated()/1024**2,
              'baseline_validation_loss': base_val, 'trained_validation_loss': tuned_val,
              'baseline_test': {k: v for k, v in baseline.items() if k != 'records'},
              'trained_test': {k: v for k, v in trained.items() if k != 'records'},
              'adapter': str(adapter.resolve()), 'production_ready': False,
              'previous_adapter_test': {k:v for k,v in previous.items() if k!='records'} if previous else None,
              'profile': PROFILE, 'optimizer_resumed': False,
              'scope': 'Small synthetic single-operation curriculum; no anatomy learning or general-modeling claim'}
    write(output/'result.json', result)
    print(json.dumps(result), flush=True)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base', required=True)
    p.add_argument('--data', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--steps', type=int, default=80)
    p.add_argument('--accumulate', type=int, default=2)
    p.add_argument('--max-skipped-updates', type=int, default=16,
                   help='Bounded AMP overflow retries; --steps counts successful updates')
    p.add_argument('--learning-rate', type=float, default=.0002)
    p.add_argument('--profile', choices=['modeling','vfx','intent','scene_intent'], default='modeling')
    p.add_argument('--initial-adapter', help='Warm start saved weights; optimizer starts fresh')
    args = p.parse_args()
    if (not 1 <= args.steps <= 1000 or not 1 <= args.accumulate <= 8
            or not 0 <= args.max_skipped_updates <= 64
            or not math.isfinite(args.learning_rate) or not 0 < args.learning_rate <= .01):
        p.error('Training budget out of bounds')
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    try:
        run(args, output)
    except Exception as exc:
        write(output/'failure.json', {'error': str(exc), 'type': type(exc).__name__})
        raise


if __name__ == '__main__':
    main()
