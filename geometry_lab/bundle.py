"""Bind integrity checks to the exact source and model paths inference will use."""
import json
from pathlib import Path

from geometry_lab.prepare_triposr import CODE, MODEL, DINO, digest, source_files


def verify(bundle):
    bundle=Path(bundle).resolve()
    manifest=json.loads((bundle/'source-manifest.json').read_text())
    inventory=json.loads((bundle/'source-integrity.json').read_text())
    source=(bundle/'source').resolve()
    if (manifest.get('code_revision')!=CODE or inventory.get('code_revision')!=CODE
            or Path(manifest['adapted_source']).resolve()!=source):
        raise ValueError('Unexpected or moved source bundle; prepare an explicit new bundle')
    if (inventory.get('complete') is not True
            or inventory.get('provider_manifest_sha256')!=digest(bundle/'source-manifest.json')
            or inventory.get('source_files')!=source_files(source)):
        raise ValueError('Full executable source inventory changed or was not verified')
    if digest(Path(__file__).with_name('triposr_compat.py'))!=manifest['compatibility_sha256']:
        raise ValueError('Extraction/config adapter changed after preparation')
    expected={('stabilityai/TripoSR',MODEL,'config.yaml'):bundle/'model/config.yaml',
              ('stabilityai/TripoSR',MODEL,'model.ckpt'):bundle/'model/model.ckpt',
              ('facebook/dino-vitb16',DINO,'config.json'):bundle/'dino/config.json'}
    files=manifest['files']
    keys=[(f['repo'],f['revision'],f['file']) for f in files]
    if len(keys)!=len(expected) or set(keys)!=expected.keys():
        raise ValueError('Unexpected model/config inventory')
    for info,key in zip(files,keys):
        local=expected[key].resolve()
        if Path(info['path']).resolve()!=local:
            raise ValueError('Verified model/config path differs from inference path')
        if local.stat().st_size!=info['bytes'] or digest(local)!=info['sha256']:
            raise ValueError('Pinned model/config artifact changed: '+info['file'])
    return manifest
