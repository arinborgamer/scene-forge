"""Acquire a small, pinned CC0 asset corpus. Never executes upstream source code."""
from concurrent.futures import ThreadPoolExecutor
import gzip
import hashlib
import itertools
import json
from pathlib import Path
import urllib.request

import numpy as np

REVISION = "3af0cd5a2ffba072e93a34e5f6f494fdc4813ddf"
REPO = "makehumancommunity/mpfb2"
ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "modeling_lab" / "data" / REVISION
PREFIX = "src/mpfb/data/"
SEX = ("female", "male")
AGE = ("young", "old")  # adults only; these are source morph categories, not ages in years
LEVEL = ("min", "average", "max")
COMBINATIONS = list(itertools.product(range(2), range(2), range(3), range(3)))


def source_paths():
    paths = ["LICENSE.md", "LICENSE.ASSETS.md", PREFIX + "3dobjs/base.obj",
             PREFIX + "rigs/standard/rig.default.json", PREFIX + "rigs/standard/weights.default.json"]
    for s, a in itertools.product(SEX, AGE):
        for ancestry in ("african", "asian", "caucasian"):
            paths.append(PREFIX + f"targets/macrodetails/{ancestry}-{s}-{a}.target.gz")
        for muscle, weight in itertools.product(LEVEL, LEVEL):
            paths.append(PREFIX + f"targets/macrodetails/universal-{s}-{a}-{muscle}muscle-{weight}weight.target.gz")
    return paths


def fetch():
    tree_url = f"https://api.github.com/repos/{REPO}/git/trees/{REVISION}?recursive=1"
    with urllib.request.urlopen(tree_url, timeout=60) as response:
        tree = json.load(response)
    entries = {x["path"]: x for x in tree["tree"]}
    ASSETS.mkdir(parents=True, exist_ok=True)

    def acquire(path):
        expected = entries[path]
        local = ASSETS / path
        url = f"https://raw.githubusercontent.com/{REPO}/{REVISION}/{path}"
        if local.exists():
            data = local.read_bytes()
        else:
            with urllib.request.urlopen(url, timeout=120) as response:
                data = response.read(expected["size"] + 1)
        digest = hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if digest != expected["sha"] or len(data) != expected["size"]:
            raise ValueError(f"Pinned asset integrity mismatch: {path}")
        if not local.exists():
            local.parent.mkdir(parents=True, exist_ok=True)
            local.write_bytes(data)
        return {"path": path, "url": url, "bytes": len(data), "git_blob": digest,
                "sha256": hashlib.sha256(data).hexdigest(), "license": "CC0-1.0" if path.startswith(PREFIX) else "license document"}

    with ThreadPoolExecutor(max_workers=4) as pool:
        files = list(pool.map(acquire, source_paths()))
    manifest = {"repository": REPO, "revision": REVISION, "files": files,
                "scope": "48 adult morph targets, one shared topology and rig; one asset family, not 48 independent scans"}
    (ASSETS / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"files": len(files), "bytes": sum(x["bytes"] for x in files), "assets": str(ASSETS)}), flush=True)


def read_obj(path=None):
    vertices, texcoords, faces, uv_faces, groups = [], [], [], [], {}
    group = "body"
    for line in (path or ASSETS / (PREFIX + "3dobjs/base.obj")).read_text().splitlines():
        fields = line.split()
        if not fields:
            continue
        if fields[0] == "v":
            vertices.append([float(n) for n in fields[1:4]])
        elif fields[0] == "vt":
            texcoords.append([float(n) for n in fields[1:3]])
        elif fields[0] == "g":
            group = fields[1]
        elif fields[0] == "f":
            indices = [int(v.split("/")[0]) - 1 for v in fields[1:]]
            faces.append(indices)
            uv_faces.append([int(v.split("/")[1]) - 1 for v in fields[1:]])
            groups.setdefault(group, []).append(len(faces) - 1)
    # MakeHuman decimetres, Y up -> Blender metres, Z up; front is -Y.
    v = np.asarray(vertices, dtype=np.float64)
    v = v[:, [0, 2, 1]] * np.array([0.1, -0.1, 0.1])
    return v, texcoords, faces, uv_faces, groups


def target(name, count):
    result = np.zeros((count, 3), dtype=np.float64)
    path = ASSETS / (PREFIX + f"targets/macrodetails/{name}.target.gz")
    for line in gzip.decompress(path.read_bytes()).decode().splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        i, x, y, z = line.split()
        result[int(i)] = float(x) * .1, -float(z) * .1, float(y) * .1
    return result


def prototypes():
    base, *_ = read_obj()
    variants = []
    for s, a, m, w in COMBINATIONS:
        # Equal mixture of the three supplied ancestry templates. This experiment
        # does not learn/predict ethnicity or infer body properties from photographs.
        adult = sum(target(f"{r}-{SEX[s]}-{AGE[a]}", len(base)) for r in ("african", "asian", "caucasian")) / 3
        build = target(f"universal-{SEX[s]}-{AGE[a]}-{LEVEL[m]}muscle-{LEVEL[w]}weight", len(base))
        variants.append(base + adult + build)
    return np.asarray(variants)


def teacher_weights(x):
    """Ground-truth synthetic interpolation; used ONLY in data preparation/evaluation."""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim != 2 or x.shape[1] != 4 or not np.isfinite(x).all() or np.any((x < 0) | (x > 1)):
        raise ValueError("Expected finite N x 4 controls in [0, 1]")
    levels = [np.stack((1 - x[:, i], x[:, i]), axis=1) for i in (0, 1)]
    levels += [np.maximum(0, 1 - 2 * abs(x[:, i, None] - np.array([0, .5, 1]))) for i in (2, 3)]
    return np.stack([levels[0][:, s] * levels[1][:, a] * levels[2][:, m] * levels[3][:, w]
                     for s, a, m, w in COMBINATIONS], axis=1)


if __name__ == "__main__":
    fetch()
