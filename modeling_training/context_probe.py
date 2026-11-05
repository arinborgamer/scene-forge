"""Paired raw/catalog diagnostic on known failures; no weight updates or output repairs."""
import argparse
import hashlib
import json
from pathlib import Path
import random
import subprocess
import sys


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def selected():
    sources=[('output/qwen-intent-regression-cases-v1.json','output/qwen-intent-refinement01-regression/trained.json'),
             ('output/qwen-intent-challenge-v1/cases.json','output/qwen-intent-refinement01-challenge/trained.json')]
    rows=[]
    lineage=[]
    for case_file,result_file in sources:
        cases=json.loads(Path(case_file).read_text())
        result=json.loads(Path(result_file).read_text())
        if result.get('complete') is not True:
            raise ValueError('Select only completed diagnostic evidence')
        actual={r['id']:r for r in result['records']}
        for case in cases:
            if actual[case['id']]['intent_exact'] or 'target' not in case['operation']:
                continue
            try:
                frame=json.loads(actual[case['id']]['raw'])
            except ValueError:
                continue
            if frame.get('target')==case['operation']['target']:
                continue
            kind='GLARE_NODE' if case['operation']['intent']=='glow' else 'MESH'
            if kind=='MESH' and case['operation']['intent']!='object_translate':
                continue
            pool=sorted({r['operation']['target'] for r in cases if 'target' in r['operation']
                         and (r['operation']['intent']=='glow' if kind=='GLARE_NODE'
                              else r['operation']['intent']=='object_translate')
                         and r['operation']['target']!=case['operation']['target']})
            # The fresh suite has only two glare nodes: use an existing regression
            # glare name as the third fixture, never a labelled 'decoy' marker.
            if len(pool)<2:
                older=json.loads(Path(sources[0][0]).read_text())
                pool=sorted(set(pool)|{r['operation']['target'] for r in older if r['operation']['intent']=='glow'})
            rng=random.Random(int(hashlib.sha256(case['id'].encode()).hexdigest()[:8],16))
            names=[case['operation']['target'],*rng.sample(pool,2)]
            rng.shuffle(names)
            rows.append({**case,'element_type':kind,'planned_names':names})
        lineage.append(dict(cases=case_file,cases_sha256=sha(case_file),results=result_file,results_sha256=sha(result_file)))
    return rows,lineage


def prepare(out,blender):
    rows,lineage=selected()
    if not rows:
        raise ValueError('No known target-selection failures to diagnose')
    out.mkdir(parents=True,exist_ok=False)
    (out/'cases.json').write_text(json.dumps(rows,indent=2),encoding='utf-8')
    with (out/'fixture-build.log').open('x',encoding='utf-8') as stream:
        subprocess.run([blender,'--background','--factory-startup','--disable-autoexec','--threads','2',
                        '--python-exit-code','1','--python','scripts/build_context_fixtures.py','--',str(out)],
                       stdout=stream,stderr=subprocess.STDOUT,check=True,timeout=300)
    (out/'provenance.json').write_text(json.dumps(dict(selection='Known failed target-name cases; diagnostic only, not unseen/generalization evidence.',
        lineage=lineage,cases_sha256=sha(out/'cases.json'),catalogs_sha256=sha(out/'observed-catalogs.json'),
        probe_source_sha256=sha(__file__),weights_updated=False),indent=2),encoding='utf-8')
    print(json.dumps(dict(prepared_cases=len(rows),output=str(out))),flush=True)


def score(raw,row,scene):
    from modeling_training.intent_ops import compile_intent
    from modeling_training.transfer_review import equivalent
    try:
        actual=compile_intent(json.loads(raw),[x['name'] for x in scene])
        expected=row.get('expected_operation') or compile_intent(row['operation'],[x['name'] for x in scene])
        return dict(schema_valid=True,intent_exact=equivalent(actual,expected),compiled_operation=actual)
    except (ValueError,TypeError,KeyError) as exc:
        return dict(schema_valid=False,intent_exact=False,error=str(exc))


def evaluate(data,out,adapter,reuse=None):
    provenance=json.loads((data/'provenance.json').read_text())
    if sha(data/'cases.json')!=provenance['cases_sha256'] or sha(data/'observed-catalogs.json')!=provenance['catalogs_sha256']:
        raise ValueError('Prepared diagnostic changed')
    rows=json.loads((data/'cases.json').read_text())
    observed={r['id']:r for r in json.loads((data/'observed-catalogs.json').read_text())}
    for fixture in observed.values():
        if sha(fixture['blend'])!=fixture['blend_sha256']:
            raise ValueError('Observed source fixture changed')
    import torch
    from transformers import AutoTokenizer,AutoModelForCausalLM
    from peft import PeftModel
    from modeling_training.finetune import configure_profile,prompt_tokens
    configure_profile('intent')
    out.mkdir(parents=True,exist_ok=False)
    adapter_hash=sha(adapter/'adapter_model.safetensors')
    cached={}
    if reuse is not None:
        summary=json.loads((reuse/'result.json').read_text())
        prior=json.loads((reuse/'responses.json').read_text())
        if (summary.get('adapter_sha256')!=adapter_hash or summary.get('cases_sha256')!=sha(data/'cases.json')
                or summary.get('catalogs_sha256')!=sha(data/'observed-catalogs.json') or prior.get('complete') is not True):
            raise ValueError('Cannot reuse responses from a different model or diagnostic')
        cached={(r['id'],r['condition']):r for r in prior['records']}
        expected={(r['id'],c) for r in rows for c in ('raw','catalog')}
        if set(cached)!=expected or len(prior['records'])!=len(expected):
            raise ValueError('Cached diagnostic pairs incomplete or duplicated')
    tokenizer=AutoTokenizer.from_pretrained(adapter,local_files_only=True,trust_remote_code=False)
    torch.set_num_threads(4)
    base=AutoModelForCausalLM.from_pretrained('output/qwen3-06b-base-v1',torch_dtype=torch.float16,
                local_files_only=True,trust_remote_code=False,attn_implementation='sdpa').to('cuda')
    model=PeftModel.from_pretrained(base,adapter,is_trainable=False).eval()
    model.generation_config.temperature=model.generation_config.top_p=model.generation_config.top_k=None
    records=[]
    for i,row in enumerate(rows):
        scene=observed[row['id']]['scene']
        presentations=dict(raw=row['prompt'],wrapper=json.dumps(dict(request=row['prompt']),separators=(',',':')),
                           catalog=json.dumps(dict(request=row['prompt'],scene=scene),separators=(',',':')))
        order=('raw','wrapper','catalog') if i%2==0 else ('catalog','wrapper','raw')
        for condition in order:
            prompt=presentations[condition]
            saved=cached.get((row['id'],condition))
            if saved is not None:
                if saved['presented_prompt']!=prompt or score(saved['raw'],row,scene)['intent_exact'] is not saved['intent_exact']:
                    raise ValueError('Cached request or raw score differs')
                raw=saved['raw']
            else:
                ids=torch.tensor([prompt_tokens(tokenizer,prompt)],device='cuda')
                with torch.no_grad():
                    tokens=model.generate(input_ids=ids,attention_mask=torch.ones_like(ids),do_sample=False,
                                          max_new_tokens=192,use_cache=True,pad_token_id=tokenizer.eos_token_id)
                raw=tokenizer.decode(tokens[0,ids.shape[1]:],skip_special_tokens=True).strip()
            record=dict(id=row['id'],condition=condition,presented_prompt=prompt,raw=raw,
                        response_source='verified_cached' if saved is not None else 'fresh_inference',**score(raw,row,scene))
            records.append(record)
            (out/'responses.json').write_text(json.dumps(dict(complete=False,records=records),indent=2),encoding='utf-8')
            print(json.dumps(dict(case=row['id'],condition=condition,intent_exact=record['intent_exact'])),flush=True)
    if sha(adapter/'adapter_model.safetensors')!=adapter_hash:
        raise RuntimeError('Adapter file changed')
    result=dict(complete=True,count_per_condition=len(rows),
        scores={c:sum(r['intent_exact'] for r in records if r['condition']==c) for c in ('raw','wrapper','catalog')},
        adapter_sha256=adapter_hash,weights_updated=False,
        cases_sha256=sha(data/'cases.json'),catalogs_sha256=sha(data/'observed-catalogs.json'),
        reused_response_file=str(reuse/'responses.json') if reuse else None,
        reused_response_sha256=sha(reuse/'responses.json') if reuse else None,
        probe_source_sha256=sha(__file__),
        scope='Paired diagnostic on known failures. Same model/system, real fixture catalogs, no output correction. No production/generalization claim.')
    (out/'responses.json').write_text(json.dumps(dict(complete=True,records=records),indent=2),encoding='utf-8')
    (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=['prepare','evaluate'])
    parser.add_argument('--output',required=True)
    parser.add_argument('--data')
    parser.add_argument('--adapter',default='output/qwen-intent-refinement01-run/adapter')
    parser.add_argument('--reuse-responses',help='Verified raw/catalog conditions; run the added wrapper-only control fresh')
    parser.add_argument('--blender',default=r'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe')
    args=parser.parse_args()
    if args.mode=='prepare':
        prepare(Path(args.output).resolve(),args.blender)
    else:
        if not args.data:
            parser.error('evaluate requires --data')
        evaluate(Path(args.data).resolve(),Path(args.output).resolve(),Path(args.adapter).resolve(),
                 Path(args.reuse_responses).resolve() if args.reuse_responses else None)


if __name__=='__main__':
    main()
