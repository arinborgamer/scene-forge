"""Approximate surface discrepancy with declared alignment and sampling-floor baseline."""
import argparse
import json
from pathlib import Path

from geometry_lab.prepare_triposr import digest


def sample(vertices,triangles,count,seed):
    import numpy as np
    tri=vertices[triangles]
    area=np.linalg.norm(np.cross(tri[:,1]-tri[:,0],tri[:,2]-tri[:,0]),axis=1)/2
    if not np.isfinite(tri).all() or not np.isfinite(area).all() or area.sum()<=0:
        raise ValueError('Invalid reference/candidate surface')
    rng=np.random.default_rng(seed)
    chosen=tri[rng.choice(len(tri),count,p=area/area.sum())]
    root=np.sqrt(rng.random(count))[:,None]
    fraction=rng.random(count)[:,None]
    return (1-root)*chosen[:,0]+root*(1-fraction)*chosen[:,1]+root*fraction*chosen[:,2]


def distances(a,b):
    import numpy as np
    from scipy.spatial import cKDTree
    d=cKDTree(b).query(a,workers=1)[0]*1000
    return dict(mean_mm=float(np.mean(d)),median_mm=float(np.median(d)),
                p95_mm=float(np.percentile(d,95)),maximum_mm=float(np.max(d)))


def evaluate(reference_vertices,reference_triangles,vertices,triangles,count=30000):
    import numpy as np
    # Known provider +X front -> reference -Y front, both Z up. No ICP/nonrigid fitting.
    rotation=np.array([[0,1,0],[-1,0,0],[0,0,1]],dtype=float)
    aligned=vertices@rotation.T
    lower,upper=reference_vertices.min(0),reference_vertices.max(0)
    lo,hi=aligned.min(0),aligned.max(0)
    if hi[2]<=lo[2] or upper[2]<=lower[2]:
        raise ValueError('Zero-height geometry')
    scale=(upper[2]-lower[2])/(hi[2]-lo[2])
    aligned*=scale
    lo,hi=aligned.min(0),aligned.max(0)
    offset=(lower+upper)/2-(lo+hi)/2
    aligned+=offset
    truth=sample(reference_vertices,reference_triangles,count,74101)
    baseline=sample(reference_vertices,reference_triangles,count,74102)
    candidate=sample(aligned,triangles,count,74103)
    return dict(reference_to_candidate=distances(truth,candidate),
                candidate_to_reference=distances(candidate,truth),
                independent_same_surface_sampling_floor=distances(truth,baseline),
                alignment=dict(rotation_matrix=rotation.tolist(),uniform_scale=float(scale),translation=offset.tolist(),
                               method='Declared canonical axes, matching height and bounding-box center; no optimized/nonrigid fit'),
                sample_points_per_surface=count,
                scope='Nearest sampled surface-point distances, not exact surface distances, anatomy recognition, realism, rigging or artistic acceptance.')


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--reference',required=True)
    parser.add_argument('--candidate',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    import numpy as np
    import trimesh
    reference,candidate=Path(args.reference).resolve(),Path(args.candidate).resolve()
    provenance=json.loads((reference/'provenance.json').read_text())
    if digest(reference/'surface.npz')!=provenance['surface_sha256']:
        raise ValueError('Reference surface changed')
    inference=json.loads((candidate/'result.json').read_text())
    raw=candidate/'raw_mesh.obj'
    if inference.get('complete') is not True or digest(raw)!=inference['outputs']['raw_mesh.obj']:
        raise ValueError('Candidate is incomplete or changed')
    with np.load(reference/'surface.npz',allow_pickle=False) as bundle:
        vertices,triangles=bundle['vertices'],bundle['triangles']
    mesh=trimesh.load(raw,force='mesh',process=False)
    report=evaluate(vertices,triangles,mesh.vertices,mesh.faces)
    report.update(reference_surface_sha256=digest(reference/'surface.npz'),candidate_mesh_sha256=digest(raw),
                  complete=True,production_ready=False,human_visual_review='pending',
                  input_geometry_was_evaluation_only=True)
    with Path(args.output).open('x',encoding='utf-8') as stream:
        json.dump(report,stream,indent=2,allow_nan=False)
    print(json.dumps(report,indent=2),flush=True)


if __name__=='__main__':
    main()
