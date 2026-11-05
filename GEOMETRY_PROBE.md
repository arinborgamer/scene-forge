# Pretrained geometry probe — actual result

28 October 2026. TripoSR is a separately downloaded pretrained MIT model, not our
fine-tuned Qwen model. It received one transparent render of the supplied CC0-family
humanoid. It inferred a new mesh; no original mesh vertices, rig or skin weights were
given to the model. The full reference surface was exported later for evaluation only.

## Completed measurements

| Extraction grid | Generated vertices / triangles | Model stages | Whole workflow | Peak process working set | Blender edit/reopen |
|---|---|---|---|---|---|
| 128 | 4,084 / 8,160 | 119.6 s | 366.9 s | 3,911 MiB | Passed |
| 256 | 16,584 / 33,160 | 206.1 s | 308.0 s | 3,624 MiB | Passed, including vertex colors |

Both runs used CPU only, two Torch threads, the same model/reference and extraction
threshold, and the explicit scikit-image mesher adapter. Whole-workflow timings include
tests, cold imports, verification, rendering and Blender reload; warm caches differ,
so the timing rows are not a controlled speed comparison. Extraction density is not
newly learned anatomy. Both raw meshes were watertight with consistent winding.

Saved outputs:

- `output/geometry-triposr-athletic-v1/`: 128-grid raw OBJ, GLB, editable Blender file,
  previews, inference/source provenance and fresh-reopen actual-vertex-edit checks.
- `output/geometry-triposr-athletic-hires-v1/`: independently preserved 256-grid run.
- `output/geometry-reference-athletic-v1/`: original render and unchanged-source hash.
- `output/research-triposr-cpu-v1/`: pinned code/model/config, full source inventory,
  declared compatibility patches and hashes. Original upstream checkout is preserved.

The first preview camera treated -Y as front; the later review uses TripoSR's canonical
+X azimuth-zero direction. This changes inspection, not mesh geometry. Neither run
produced a skeleton, animation or animator-ready topology. Vertex colors are imported
from the model; authored lighting/cameras and 1.8 m presentation scaling are recorded.

## Quality decision

Visual inspection found blurred facial structure and fused/incomplete hands, also at
the denser grid. The denser mesh does not meet the character quality target. Keep the
existing supplied rigged body as the production-character baseline. These generated
meshes are review artifacts, not replacements or approved geometry-training targets.

Approximate reconstruction checks sampled 30,000 points per surface. Alignment used
declared canonical axes, a uniform height match and bounding-box centering, with no ICP
or nonrigid fitting. Nearest sampled-point distance means were about 54.8/54.9 mm in
the two directions at grid128, and 57.2/56.4 mm at grid256. Independently sampling the
same reference surface gave a 3.9 mm mean sampling floor. These are geometry discrepancies
under that alignment, not exact surface distances, anatomical recognition, statistical
significance or a realism score. Numerical reports are in each run's `reconstruction.json`.

More samples did not restore the missing anatomy in this example. Evaluate specialists
on appropriate assets and retain stronger baselines; do not improve a training set by
feeding it a visibly worse reconstruction merely because a model generated it.

## Reproduce a new local image request

From the project root, use a new name and an isolated foreground RGBA image:

```powershell
.\.venv-geometry\Scripts\python.exe -m geometry_lab.pipeline --image YOUR_RGBA_IMAGE.png --name new-review --resolution 256
```

The pipeline runs offline inference from prepared local artifacts, saves raw output,
imports it in Blender, renders CPU previews and starts a fresh Blender process to
verify a real mesh edit/restoration. It has per-stage timeouts, unique outputs and
failure reports. This interface accepts images; natural-language routing to it has
not been integrated into the main app. See LOW_MEMORY_GEOMETRY.md and the pinned
`geometry_lab/requirements-cpu.txt` for setup constraints and licenses.
