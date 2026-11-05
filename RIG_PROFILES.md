# Explicit rig profiles and deformation checks

Implemented and checked locally on 28 October 2026. This prepares the reusable rig
interface for the cinematic-demo milestone; it does not generate an animation.

`scene_forge/rig_profile.py` defines version-1 skeleton metadata and validates finite
units, FPS, named bones, rest transforms, parent links, nonzero bone lengths, acyclic
hierarchies and explicit canonical-joint mappings. Missing or duplicated assignments
fail. Consumers can resolve `left_elbow`, `right_wrist`, `neck`, `jaw` and other semantic
joint names without hardcoding those assets' bone names into every operation.

`modeling_lab/inspect_rig.py` reads an existing `.blend`, confirms its mesh is bound to
the chosen armature, exports the actual hierarchy/rest matrices, and runs 14 in-memory
probes: both shoulders, elbows, wrists, hips, knees, index fingers, plus neck and jaw.
Each must deform at least four vertices, preserve vertices uninfluenced by that bone's
subtree, and restore the mesh to rest within 0.001 mm. Bone-group weights must normalize.
The file hash and animation datablock names must remain unchanged. Nothing is saved
over the supplied Blender project and no animation curves are created.

This probe policy currently accepts neutral, unconstrained static rigs. Animated,
driver-controlled, constrained or already posed rigs fail explicitly rather than
having their state cleared. Bone coordinates are armature-local; rig/mesh world matrices,
explicit metres-per-unit convention, up/forward axes and FPS are exported for later use.

## Actual results

| Fixture | Bones | Deformation probes | Source file |
|---|---:|---:|---|
| Supplied athletic adult shape | 163 | 14/14 | Unchanged |
| Supplied older adult shape | 163 | 14/14 | Unchanged |
| In-memory renamed athletic skeleton and explicit mapping | 163 | 14/14 | Unchanged |

Reports and profiles: `output/cinematic-rig-profiles-v1/`.
These are two shapes from the same MPFB topology/skeleton family. Renaming bones tests
the mapping boundary, not generalization to an independently designed skeleton.
An unrelated rig requires its own explicit mapping and deformation/axis validation.

## Reproduce

Run from this project directory, using a new output folder:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' `
  --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 1 `
  --python modeling_lab/inspect_rig.py -- `
  --input output/modeling-review-athletic-v2/scene/humanoid.blend `
  --output output/my-rig-inspection
```

The default MPFB name mapping is an explicit adapter. Supply `--mapping path/to/map.json`
for a different name layout, with one bone name per canonical joint listed in
`MPFB_JOINTS`. Select armature/mesh names with `--rig` and `--mesh`, and declare coordinate
scale with `--meters-per-unit`. `--rename-prefix Alternate_` runs the same-family mapping
fixture in memory; it does not alter the disk asset.

## Remaining work

Mapping names is only one prerequisite for retargeting. Rest-axis orientation, IK
controls, corrective shapes, contact constraints, foot sliding, self-intersections,
facial performance and motion quality still require implementation and separate tests.
The inherited anatomy, topology, weights and skeleton were not learned by Qwen.
