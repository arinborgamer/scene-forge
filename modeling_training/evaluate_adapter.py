"""Independent language challenge, same base weights with adapter disabled/enabled."""
import argparse
import hashlib
import json
from pathlib import Path
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import PeftModel
from modeling_training.finetune import evaluate,configure_profile,adapter_source


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--base', required=True)
    p.add_argument('--adapter', required=True)
    p.add_argument('--cases', required=True)
    p.add_argument('--output', required=True)
    p.add_argument('--profile', choices=['modeling','vfx','intent','scene_intent'], default='modeling')
    p.add_argument('--compare-adapter', help='Optional frozen reference adapter instead of disabled-adapter baseline')
    args = p.parse_args()
    configure_profile(args.profile)
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    cases_path = Path(args.cases)
    rows = json.loads(cases_path.read_text())
    if args.profile=='scene_intent':
        from modeling_training.scene_intent_data import verify_companion
        rows,_=verify_companion(cases_path)
    comparison = 'reference_adapter' if args.compare_adapter else 'unchanged_base'
    (output/'provenance.json').write_text(json.dumps({**vars(args), 'cases_sha256': hashlib.sha256(cases_path.read_bytes()).hexdigest(),
                                                    'candidate_weights': adapter_source(args.adapter),
                                                    'reference_weights': adapter_source(args.compare_adapter) if args.compare_adapter else None,
                                                    'comparison': comparison,
                                                    'method': 'Same frozen base, reference vs candidate; no training'}, indent=2))
    torch.set_num_threads(4)
    tokenizer = AutoTokenizer.from_pretrained(args.adapter, local_files_only=True)
    base = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=torch.float16, local_files_only=True,
                                              trust_remote_code=False, attn_implementation='sdpa').to('cuda')
    model = PeftModel.from_pretrained(base, args.adapter, is_trainable=False).eval()
    model.generation_config.temperature = None
    model.generation_config.top_p = None
    model.generation_config.top_k = None
    if args.compare_adapter:
        model.load_adapter(args.compare_adapter, adapter_name='reference', is_trainable=False)
        model.set_adapter('reference')
        model.eval()
        before = evaluate(model, tokenizer, rows, output/'baseline.json')
        model.set_adapter('default')
        model.eval()
    else:
        with model.disable_adapter():
            before = evaluate(model, tokenizer, rows, output/'baseline.json')
    after = evaluate(model, tokenizer, rows, output/'trained.json')
    summary = {'baseline_exact': before['intent_exact'], 'trained_exact': after['intent_exact'],
               'count': len(rows), 'comparison': comparison,
               'scope': 'Evaluation only; this invocation does not update weights. Benchmark independence depends on case provenance.'}
    (output/'result.json').write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary), flush=True)


if __name__ == '__main__':
    main()
