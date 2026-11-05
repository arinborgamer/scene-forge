"""Download a pinned official Qwen snapshot; no remote model code is executed."""
import argparse
import hashlib
import json
from pathlib import Path
from huggingface_hub import HfApi, snapshot_download


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as file:
        for block in iter(lambda: file.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    path = Path(args.output).resolve()
    path.mkdir(parents=True, exist_ok=False)
    repo = 'Qwen/Qwen3-0.6B'
    revision = HfApi().model_info(repo).sha
    (path/'download-request.json').write_text(json.dumps({'repo': repo, 'revision': revision}, indent=2))
    snapshot_download(repo, revision=revision, local_dir=str(path),
                      allow_patterns=['*.json', '*.safetensors', '*.txt', '*.model', 'LICENSE', 'README.md'])
    files = {p.name: sha(p) for p in path.iterdir() if p.is_file() and p.name != 'download-request.json'}
    (path/'source-manifest.json').write_text(json.dumps({'repo': repo, 'revision': revision, 'files': files,
                                                        'license': 'Apache-2.0; see downloaded LICENSE'}, indent=2))
    print('BASE_SNAPSHOT_READY', revision, flush=True)


if __name__ == '__main__':
    main()
