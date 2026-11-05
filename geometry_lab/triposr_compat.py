"""Explicit CPU extraction/config adapters for the pinned TripoSR probe."""
import os
from pathlib import Path


def local_dino_config(*, repo_id, filename):
    if repo_id != 'facebook/dino-vitb16' or filename != 'config.json':
        raise ValueError('Unexpected model request; offline adapter only permits pinned DINO config')
    path = Path(os.environ['SCENEFORGE_TRIPOSR_DINO_CONFIG'])
    if not path.is_absolute() or not path.is_file():
        raise ValueError('A prepared absolute DINO config path is required')
    return str(path)


def marching_cubes(volume, level):
    import numpy as np
    import torch
    from skimage.measure import marching_cubes as extract
    if volume.device.type != 'cpu' or volume.ndim != 3 or min(volume.shape) < 2:
        raise ValueError('CPU-only three-dimensional scalar field required')
    field = volume.detach().float().numpy()
    if not np.isfinite(field).all() or not np.isfinite(level):
        raise ValueError('Nonfinite scalar field or threshold')
    vertices, faces, _, _ = extract(field, level=float(level), gradient_direction='ascent',
                                     allow_degenerate=False)
    # torchmcubes reports reversed coordinate order; TripoSR reverses it back.
    return (torch.from_numpy(np.ascontiguousarray(vertices[:, ::-1])),
            torch.from_numpy(np.ascontiguousarray(faces, dtype=np.int64)))
