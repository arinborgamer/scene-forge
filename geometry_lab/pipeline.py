"""Repeatable CPU geometry probe with bounded stages and preserved raw failures."""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time

from geometry_lab.prepare_triposr import digest

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--image',required=True)
    parser.add_argument('--bundle',default='output/research-triposr-cpu-v1')
    parser.add_argument('--name',required=True)
    parser.add_argument('--resolution',type=int,default=128)
    parser.add_argument('--chunk',type=int,default=4096)
    parser.add_argument('--blender',default=r'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe')
    args=parser.parse_args()
    if not re.fullmatch('[a-z0-9][a-z0-9-]{0,47}',args.name):
        parser.error('Use a new lowercase alphanumeric/hyphen name')
    if not 32<=args.resolution<=256 or not 256<=args.chunk<=16384:
        parser.error('Probe resolution/chunk outside local budget')
    image,bundle=Path(args.image).resolve(),Path(args.bundle).resolve()
    python=ROOT/'.venv-geometry/Scripts/python.exe'
    for path in (image,python,Path(args.blender),bundle/'source-manifest.json',bundle/'source-integrity.json'):
        if not path.is_file():
            parser.error('Missing prepared dependency: '+str(path))
    out=ROOT/'output'/('geometry-'+args.name)
    out.mkdir(parents=True,exist_ok=False)
    request={**vars(args),'image':str(image),'input_sha256':digest(image),'bundle':str(bundle),
             'pipeline_source_sha256':digest(__file__),'scope':'Pretrained static image-to-3D CPU probe; no trained rig or animation.'}
    (out/'request.json').write_text(json.dumps(request,indent=2),encoding='utf-8')
    (out/'pipeline.py.snapshot').write_bytes(Path(__file__).read_bytes())
    start=time.perf_counter()
    stage='prepared'
    def command(name,argv,timeout):
        nonlocal stage
        stage=name
        print(json.dumps(dict(stage=name,output=str(out))),flush=True)
        with (out/(name+'.log')).open('x',encoding='utf-8') as stream:
            subprocess.run(argv,cwd=ROOT,stdout=stream,stderr=subprocess.STDOUT,timeout=timeout,check=True)
    try:
        command('geometry-tests',[str(python),'-m','unittest','discover','-s','tests','-p','test_geometry_*.py'],180)
        command('inference',[str(python),'-u','-m','geometry_lab.generate','--bundle',str(bundle),
                '--image',str(image),'--output',str(out/'generated'),'--resolution',str(args.resolution),
                '--chunk',str(args.chunk)],1800)
        base=[args.blender,'--background','--factory-startup','--disable-autoexec','--threads','2',
              '--python-exit-code','1','--python',str(ROOT/'scripts/review_geometry_blender.py'),'--']
        command('build',[*base,'build','--source',str(out/'generated'),'--output',str(out/'review')],900)
        command('reopen',[*base,'reopen','--output',str(out/'review')],300)
        generation=json.loads((out/'generated/result.json').read_text())
        reopened=json.loads((out/'review/reopen.json').read_text())
        passed=generation.get('complete') is True and reopened.get('passed') is True
        if digest(image)!=request['input_sha256']:
            raise RuntimeError('Reference image changed')
        result=dict(complete=True,editable_workflow_passed=passed,production_ready=False,
                    generated_vertices=generation['vertices'],generated_triangles=generation['triangles'],
                    elapsed_seconds=time.perf_counter()-start,human_visual_review='pending',
                    weights_updated=False,rig_generated=False,animation_generated=False,
                    blend=str(out/'review/mesh.blend'),preview=str(out/'review/three_quarter.png'),
                    scope=request['scope'],reports={name:digest(out/name) for name in
                        ('generated/result.json','review/build.json','review/reopen.json')})
    except Exception as exc:
        result=dict(complete=False,editable_workflow_passed=False,failed_stage=stage,error=str(exc),
                    elapsed_seconds=time.perf_counter()-start,scope=request['scope'],production_ready=False)
        (out/'result.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
        raise
    (out/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    print(json.dumps(result,indent=2),flush=True)
    if not passed:
        raise RuntimeError('Editable workflow did not pass; reports preserved')


if __name__=='__main__':
    main()
