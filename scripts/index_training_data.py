"""Refresh a read-only inventory of datasets, runs and their recorded lineage."""
import hashlib,json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0,str(ROOT))
from modeling_training.progress import summarize

def read(path):
    if not path.is_file():return None
    try:return json.loads(path.read_text(encoding='utf-8-sig'))
    except (ValueError,UnicodeError):return None

def build(root):
    datasets=[];runs=[];reviews=[]
    gates={}
    for folder in sorted((root/'output').iterdir()):
        if not folder.is_dir() or folder.name.startswith('research-'):continue
        gate=read(folder/'gate.json')
        if isinstance(gate,dict) and gate.get('run'):
            gates.setdefault(str(Path(gate['run']).resolve()),[]).append(
                dict(report=gate,file=(folder/'gate.json').relative_to(root).as_posix()))
    for folder in sorted((root/'output').iterdir()):
        if not folder.is_dir() or folder.name.startswith('research-'):continue
        rel=folder.relative_to(root).as_posix()
        manifest=read(folder/'manifest.json')
        if manifest and isinstance(manifest.get('files'),dict):
            files={}
            for split,info in manifest['files'].items():
                p=folder/(split+'.jsonl')
                if not isinstance(info,dict):continue
                files[split]={**info,'exists':p.is_file(),'hash_matches':p.is_file() and hashlib.sha256(p.read_bytes()).hexdigest()==info.get('sha256')}
            verify=read(folder/'blender-verification.json') or {}
            datasets.append({'id':rel,'files':files,'blender_verified':verify.get('passed',False),'verified_count':verify.get('count'),
                             'executed_count':verify.get('executed_count',verify.get('count')),'refusal_count':verify.get('refusal_count',0),
                             'generation_failure':read(folder/'generation-failure.json'),'scope':manifest.get('scope','')})
        config=read(folder/'config.json')
        result=read(folder/'result.json')
        if config and 'dataset_manifest' in config:
            changes=read(folder/'weight-change.json') or {}
            adapter=folder/'adapter/adapter_model.safetensors'
            checkpoints=sorted(p.name for p in folder.glob('checkpoint-*') if p.is_dir())
            progress=summarize(folder,config)
            gate=read(folder/'promotion.json')
            gate_records=([dict(report=gate,file=rel+'/promotion.json')] if gate else [])
            gate_records+=gates.get(str(folder.resolve()),[])
            decisions={(r['report'].get('passed'),r['report'].get('decision')) for r in gate_records}
            gate_conflict=len(decisions)>1
            gate=gate_records[0]['report'] if gate_records and not gate_conflict else None
            gate_file=gate_records[0]['file'] if gate_records and not gate_conflict else None
            runs.append({'id':rel,'status':(result or {}).get('status','interrupted' if (folder/'interrupted.json').exists() else 'failed' if (folder/'failure.json').exists() else 'incomplete'),
                         'dataset':config.get('data'),'base':config.get('base'),'initial_adapter':config.get('initial_adapter'),
                         'planned_steps':config.get('steps'),'completed_updates':changes.get('successful_optimizer_steps',progress['recorded_successful_updates']),
                         'progress':progress,'profile':config.get('profile','modeling'),
                         'adapter':adapter.relative_to(root).as_posix() if adapter.exists() else None,
                         'adapter_hash_matches':adapter.exists() and hashlib.sha256(adapter.read_bytes()).hexdigest()==changes.get('adapter_file_sha256'),
                         'checkpoints':checkpoints,'result':result,'promotion':gate,'gate_file':gate_file,
                         'gate_records':gate_records,'gate_conflict':gate_conflict,'optimizer_resume_saved':False})
        if result and not config:
            reviews.append({'id':rel,'result':result,'evidence_file':'result.json','provenance':read(folder/'provenance.json')})
        acceptance=read(folder/'acceptance.json')
        if acceptance:reviews.append({'id':rel,'acceptance':acceptance,'evidence_file':'acceptance.json'})
        reopened=read(folder/'reopen.json')
        if reopened:reviews.append({'id':rel,'blender_reopen':reopened,'evidence_file':'reopen.json'})
    return {'schema_version':2,'scope':'Top-level output metadata only; original artifacts unchanged. Does not verify process liveness, assess artistic quality or index third-party research clones.','datasets':datasets,'runs':runs,'evaluations_and_reviews':reviews}

def main():
    catalog=build(ROOT);dest=ROOT/'data-management';dest.mkdir(exist_ok=True)
    (dest/'catalog.json').write_text(json.dumps(catalog,indent=2),encoding='utf-8')
    lines=['# Training data and model index','','Generated from actual artifact metadata by `scripts/index_training_data.py`. Refresh after training or evaluation. Original datasets, scenes and checkpoints stay in place.','','## Datasets','','| Dataset | Split sizes | File hashes | Blender target checks |','|---|---|---|---|']
    for d in catalog['datasets']:
        counts=', '.join(f"{k}: {v.get('count','?')}" for k,v in d['files'].items())
        valid=all(v['hash_matches'] for v in d['files'].values()) and bool(d['files'])
        verified=(f"{d['executed_count']} executed; {d['refusal_count']} refused" if d['refusal_count'] else str(d['verified_count'])) if d['blender_verified'] else 'Not verified'
        if d['generation_failure']:verified+='; generation failed'
        lines.append(f"| [{d['id']}]({d['id']}/manifest.json) | {counts} | {'Match' if valid else 'MISSING / MISMATCH'} | {verified} |")
    lines+=['','## Training runs','','| Run | Recorded state | Recorded updates | Dataset | Saved adapter checksum | Recorded gate |','|---|---|---|---|---|---|']
    for r in catalog['runs']:
        gate=r.get('promotion')
        decision='CONFLICT: inspect all gate records' if r['gate_conflict'] else 'Not evaluated' if not gate else ('Eligible for Blender review' if gate.get('passed') is True else 'Rejected')
        state=r['status'] if r['status']!='incomplete' else 'incomplete: '+r['progress']['last_recorded_stage']
        lines.append(f"| [{r['id']}]({r['id']}/result.json) | {state} | {r['completed_updates']}/{r['planned_steps']} | {r['dataset']} | {'Match' if r['adapter_hash_matches'] else 'Not verified'} | {decision} |")
    lines+=['','Stages and update counts come from saved reports/logs; they do not prove a process is alive. Partial evaluation counts in catalog.json are not final scores. Full Blender and human review are separate from a language gate.','','The VFX adapter warm-starts the first modeling adapter. Its optimizer starts fresh. Checkpoints contain adapter weights, not exact optimizer/RNG resume state. A higher score on one small benchmark does not establish general production capability.','','## Evaluations and reviews','']
    for r in catalog['evaluations_and_reviews']:
        filename=r['evidence_file']
        lines.append(f"- [{r['id']}]({r['id']}/{filename})")
    lines+=['','## Using the index','','- Run `.venv\\Scripts\\python.exe scripts/index_training_data.py` to refresh this index and `data-management/catalog.json`.','- Dataset file hashes and final adapter hashes are checked; missing or changed files are flagged.','- Use unique output directories for experiments. Never infer a run succeeded from a checkpoint folder alone.','- Use Graphify for source/document relationships; use this catalog for measured experiment status. They serve different purposes.','']
    (ROOT/'DATA_INDEX.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({'datasets':len(catalog['datasets']),'runs':len(catalog['runs']),'evaluations_and_reviews':len(catalog['evaluations_and_reviews'])}))

if __name__=='__main__':main()
