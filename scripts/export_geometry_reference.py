"""Export observed reference-body surface for evaluation only; do not change the scene."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

import bpy
import numpy as np


parser=argparse.ArgumentParser()
parser.add_argument('--input',required=True)
parser.add_argument('--output',required=True)
args=parser.parse_args(sys.argv[sys.argv.index('--')+1:])
source,out=Path(args.input).resolve(),Path(args.output).resolve()
sha=hashlib.sha256(source.read_bytes()).hexdigest()
out.mkdir(parents=True,exist_ok=False)
bpy.ops.wm.open_mainfile(filepath=str(source),load_ui=False,use_scripts=False)
obj=bpy.data.objects['Humanoid_Trained_Shape']
evaluated=obj.evaluated_get(bpy.context.evaluated_depsgraph_get())
mesh=evaluated.to_mesh()
try:
    mesh.calc_loop_triangles()
    vertices=np.array([tuple(obj.matrix_world@v.co) for v in mesh.vertices],dtype=np.float64)
    triangles=np.array([tuple(t.vertices) for t in mesh.loop_triangles],dtype=np.int64)
finally:
    evaluated.to_mesh_clear()
np.savez_compressed(out/'surface.npz',vertices=vertices,triangles=triangles)
if hashlib.sha256(source.read_bytes()).hexdigest()!=sha:
    raise RuntimeError('Reference source changed')
(out/'provenance.json').write_text(json.dumps(dict(source_blend=str(source),source_sha256=sha,
    surface_sha256=hashlib.sha256((out/'surface.npz').read_bytes()).hexdigest(),
    vertices=len(vertices),triangles=len(triangles),coordinate_frame='world metres, Z up, front -Y',
    scope='Evaluation-only supplied CC0-family body surface, including active subdivision. No geometry fed into the image-conditioned model.'),indent=2),encoding='utf-8')
print('REFERENCE_SURFACE_EXPORTED',flush=True)
