"""Bounded offline CPU TripoSR inference; saves raw learned mesh and provenance."""
import argparse
import json
import os
from pathlib import Path
import sys
import time

os.environ['HF_HUB_OFFLINE']='1'
os.environ['TRANSFORMERS_OFFLINE']='1'
os.environ['CUDA_VISIBLE_DEVICES']=''
os.environ['TOKENIZERS_PARALLELISM']='false'

from geometry_lab.prepare_triposr import digest
from geometry_lab.bundle import verify
from geometry_lab.preprocess import foreground


def run(args,out):
    os.environ['HF_HOME']=str(out/'offline-cache/huggingface')
    os.environ['TRANSFORMERS_CACHE']=str(out/'offline-cache/transformers')
    import numpy as np
    import psutil
    from PIL import Image
    import torch
    bundle=Path(args.bundle).resolve()
    manifest=verify(bundle)
    image_path=Path(args.image).resolve()
    image_sha=digest(image_path)
    image,preprocessing=foreground(Image.open(image_path))
    image.save(out/'input.png')
    os.environ['SCENEFORGE_TRIPOSR_DINO_CONFIG']=str(bundle/'dino/config.json')
    sys.path.insert(0,str(Path(manifest['adapted_source'])))
    from omegaconf import OmegaConf
    from tsr.system import TSR
    torch.set_num_threads(2)
    torch.manual_seed(28401)
    start=time.perf_counter()
    snapshot=out/'source_snapshot'
    snapshot.mkdir()
    for path in Path(__file__).parent.glob('*.py'):
        (snapshot/path.name).write_bytes(path.read_bytes())
    process=psutil.Process()
    timings={}
    def stage(name):
        print(json.dumps(dict(stage=name,elapsed_seconds=time.perf_counter()-start,
                              rss_mb=process.memory_info().rss/1024**2)),flush=True)
    stage('load_model')
    config=OmegaConf.load(bundle/'model/config.yaml')
    OmegaConf.resolve(config)
    model=TSR(config).eval().to('cpu')
    weights=torch.load(bundle/'model/model.ckpt',map_location='cpu',weights_only=True)
    model.load_state_dict(weights,strict=True)
    del weights
    model.renderer.set_chunk_size(args.chunk)
    timings['load_seconds']=time.perf_counter()-start
    stage('predict_triplane')
    before=time.perf_counter()
    with torch.inference_mode():
        codes=model([image],device='cpu')
    timings['prediction_seconds']=time.perf_counter()-before
    stage('extract_mesh')
    before=time.perf_counter()
    with torch.inference_mode():
        mesh=model.extract_mesh(codes,True,resolution=args.resolution)[0]
    timings['extraction_seconds']=time.perf_counter()-before
    if (len(mesh.vertices)<4 or len(mesh.faces)<4 or not np.isfinite(mesh.vertices).all()
            or not np.isfinite(mesh.vertex_normals).all()):
        raise ValueError('Model produced an empty or nonfinite mesh')
    # Preserve raw model geometry. GLB is additionally converted from TripoSR Z-up to standard Y-up.
    mesh.export(out/'raw_mesh.obj')
    glb=mesh.copy()
    glb.apply_transform(np.array([[1,0,0,0],[0,0,1,0],[0,-1,0,0],[0,0,0,1]],dtype=float))
    glb.export(out/'mesh.glb')
    if digest(image_path)!=image_sha:
        raise RuntimeError('Reference image changed')
    result=dict(complete=True,provider='pretrained_TripoSR',weights_updated=False,device='cpu',
        geometry_generation=True,rig_generated=False,animation_generated=False,
        vertices=len(mesh.vertices),triangles=len(mesh.faces),watertight=bool(mesh.is_watertight),
        winding_consistent=bool(mesh.is_winding_consistent),bounds_raw_z_up=mesh.bounds.tolist(),
        timings=timings,model_stages_seconds=time.perf_counter()-start,
        windows_peak_working_set_mb=process.memory_info().peak_wset/1024**2,
        input_image=str(image_path),input_sha256=image_sha,preprocessing=preprocessing,
        provider_manifest=str(bundle/'source-manifest.json'),provider_manifest_sha256=digest(bundle/'source-manifest.json'),
        source_integrity_sha256=digest(bundle/'source-integrity.json'),
        outputs={name:digest(out/name) for name in ('raw_mesh.obj','mesh.glb','input.png')},
        extraction='Explicit scikit-image CPU adapter; analytical axis/winding checks required. No native torchmcubes claim.',
        scope='New static geometry from pretrained specialist. Not our trained geometry model, rigging, anatomy quality or cinematic animation.',
        human_visual_review='pending')
    (out/'result.json').write_text(json.dumps(result,indent=2,allow_nan=False),encoding='utf-8')
    stage('saved')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--bundle',required=True)
    parser.add_argument('--image',required=True)
    parser.add_argument('--output',required=True)
    parser.add_argument('--resolution',type=int,default=128)
    parser.add_argument('--chunk',type=int,default=4096)
    args=parser.parse_args()
    if not 32<=args.resolution<=256 or not 256<=args.chunk<=16384:
        parser.error('Probe resolution/chunk outside local budget')
    out=Path(args.output).resolve()
    out.mkdir(parents=True,exist_ok=False)
    try:
        run(args,out)
    except Exception as exc:
        (out/'failure.json').write_text(json.dumps(dict(error=str(exc),complete=False)),encoding='utf-8')
        raise


if __name__=='__main__':
    main()
