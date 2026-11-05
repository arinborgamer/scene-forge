"""Prepare pinned MIT code/weights without altering the active training environment."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess

CODE = '107cefdc244c39106fa830359024f6a2f1c78871'
MODEL = '5b521936b01fbe1890f6f9baed0254ab6351c04a'
DINO = 'f205d5d8e640a89a2b8ef0369670dfc37cc07fc2'


def digest(path):
    value=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):
            value.update(block)
    return value.hexdigest()


def source_files(folder):
    return {p.relative_to(folder).as_posix():digest(p) for p in folder.rglob('*')
            if p.is_file() and (p.suffix=='.py' or p.name=='LICENSE') and '__pycache__' not in p.parts}


def seal_source(source,out):
    manifest=json.loads((out/'source-manifest.json').read_text())
    actual=source_files(out/'source')
    expected={'tsr/'+p.relative_to(source/'tsr').as_posix():digest(p)
              for p in (source/'tsr').rglob('*.py')}
    expected['LICENSE']=digest(source/'LICENSE')
    for patch in manifest['patches']:
        if expected[patch['file']]!=patch['before_sha256']:
            raise ValueError('Patch base does not match pinned source')
        expected[patch['file']]=patch['after_sha256']
    if actual!=expected:
        raise ValueError('Adapted executable source inventory differs from the pinned source plus declared patches')
    with (out/'source-integrity.json').open('x',encoding='utf-8') as stream:
        json.dump(dict(provider_manifest_sha256=digest(out/'source-manifest.json'),
                       source_files=actual,code_revision=CODE,complete=True),stream,indent=2)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--seal-only',action='store_true',help='Add full source inventory to an existing prepared bundle')
    args=parser.parse_args()
    source,out=Path(args.source).resolve(),Path(args.output).resolve()
    revision=subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    dirty=subprocess.check_output(['git','-C',str(source),'status','--porcelain'],text=True).strip()
    if revision!=CODE or dirty:
        raise ValueError('Expected clean pinned upstream checkout')
    if args.seal_only:
        seal_source(source,out)
        print('SOURCE_INVENTORY_SEALED',flush=True)
        return
    out.mkdir(parents=True,exist_ok=False)
    adapted=out/'source'
    adapted.mkdir()
    shutil.copytree(source/'tsr',adapted/'tsr')
    shutil.copy2(source/'LICENSE',adapted/'LICENSE')
    edits=[('tsr/models/isosurface.py','from torchmcubes import marching_cubes',
            'from geometry_lab.triposr_compat import marching_cubes'),
           ('tsr/models/tokenizers/image.py','from huggingface_hub import hf_hub_download',
            'from geometry_lab.triposr_compat import local_dino_config as hf_hub_download')]
    patches=[]
    for name,before,after in edits:
        path=adapted/name
        text=path.read_text(encoding='utf-8')
        if text.count(before)!=1:
            raise ValueError('Unexpected upstream source: '+name)
        original=digest(path)
        path.write_text(text.replace(before,after),encoding='utf-8')
        patches.append(dict(file=name,before_sha256=original,after_sha256=digest(path),
                            original_import=before,adapted_import=after))
    from huggingface_hub import HfApi,hf_hub_download
    files=[]
    for repo,revision,names,dest in [('stabilityai/TripoSR',MODEL,['config.yaml','model.ckpt'],out/'model'),
                                      ('facebook/dino-vitb16',DINO,['config.json'],out/'dino')]:
        info=HfApi().model_info(repo,revision=revision,files_metadata=True,token=False)
        for name in names:
            metadata=next(x for x in info.siblings if x.rfilename==name)
            print(json.dumps(dict(stage='download',repo=repo,file=name,bytes=metadata.size)),flush=True)
            path=Path(hf_hub_download(repo_id=repo,revision=revision,filename=name,
                                     local_dir=dest,token=False))
            sha=digest(path)
            expected=(metadata.lfs.get('sha256') if isinstance(metadata.lfs,dict)
                      else getattr(metadata.lfs,'sha256',None)) if metadata.lfs else None
            if path.stat().st_size!=metadata.size or (expected and sha!=expected):
                raise ValueError('Downloaded artifact integrity mismatch: '+name)
            files.append(dict(repo=repo,revision=revision,file=name,path=str(path.resolve()),
                              bytes=path.stat().st_size,sha256=sha,lfs_sha256=expected))
    manifest=dict(code_repository='https://github.com/VAST-AI-Research/TripoSR',code_revision=CODE,
                  adapted_source=str(adapted),patches=patches,files=files,
                  compatibility_sha256=digest(Path(__file__).with_name('triposr_compat.py')),
                  device='cpu',code_and_weight_license='MIT per pinned upstream README/LICENSE',
                  scope='Pretrained static image-to-3D experiment; no fine-tuning, rigging or motion generation')
    (out/'source-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
    seal_source(source,out)
    print(json.dumps(dict(prepared=True,manifest=str(out/'source-manifest.json'))),flush=True)


if __name__=='__main__':
    main()
