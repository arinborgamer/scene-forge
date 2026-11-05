"""Bind consumed JSON companions and canaries to the data frozen before training."""
import hashlib
import json
from pathlib import Path


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def verify_manifest(root,expected=None):
    root=Path(root).resolve()
    manifest=json.loads((root/'manifest.json').read_text())
    if manifest.get('profile')!='scene_intent' or (expected is not None and manifest!=expected):
        raise ValueError('Scene dataset manifest changed or has the wrong profile')
    for split,info in manifest['files'].items():
        if split not in ('train','validation','test','regression','vfx','challenge'):
            raise ValueError('Unknown scene dataset file')
        jsonl=root/(split+'.jsonl')
        companion=root/(split+'.json')
        if sha(jsonl)!=info['sha256'] or sha(companion)!=info['json_sha256']:
            raise ValueError('Frozen scene dataset/companion changed: '+split)
        rows=[json.loads(line) for line in jsonl.read_text().splitlines()]
        if len(rows)!=info['count'] or json.loads(companion.read_text())!=rows:
            raise ValueError('Consumed companion differs from verified JSONL: '+split)
    for name,info in manifest.get('artifacts',{}).items():
        if Path(name).name!=name or sha(root/name)!=info['sha256']:
            raise ValueError('Frozen canary artifact changed')
    for name,checksum in manifest.get('canary_sources',{}).items():
        if sha(name)!=checksum:
            raise ValueError('Original canary source scene changed')
    return manifest


def verify_companion(path,expected=None):
    path=Path(path).resolve()
    manifest=verify_manifest(path.parent,expected)
    if path.suffix!='.json' or path.stem not in manifest['files']:
        raise ValueError('Expected a frozen scene evaluation companion')
    return json.loads(path.read_text()),manifest


def verify_artifact(path,data,expected):
    data=Path(data).resolve()
    manifest=verify_manifest(data,expected)
    path=Path(path).resolve()
    if path.parent!=data or path.name not in manifest.get('artifacts',{}):
        raise ValueError('Canary is not the pretraining-frozen artifact')
    return json.loads(path.read_text())
