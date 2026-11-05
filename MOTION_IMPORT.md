# Compatible-rig editable motion import

The new motion boundary accepts samples for an explicitly matching rest skeleton and
bakes them into editable Blender actions. It does not generate motions or retarget
between skeletons. Current validation clips are authored test fixtures; none are
claimed to have come from Kimodo, Qwen or a learned motion model.

## Data contract

`scene_forge/motion_clip.py` validates version 1 JSON with exactly these fields:

- `skeleton_signature`: hash of bone names, hierarchy, endpoints, rest transforms,
  canonical joint map and coordinate convention from a validated rig profile.
- `fps`, `start_frame`, `root_offsets_m`: 2–601 samples, at most 20 seconds. Root
  offsets are world displacements in metres relative to the supplied rig placement.
- `joint_rotations`: canonical-joint tracks of unit WXYZ quaternions, representing
  Blender pose-bone basis rotations relative to that exact rest skeleton.
- `source`: declared origin (`authored_fixture`, `imported_capture`, `model_output`)
  and an ID. This metadata is declarative; it does not prove a model ran.

Unknown joints, incompatible rest skeletons, non-finite values, mismatched sample counts,
unsupported fields and non-unit quaternions fail before construction. Equivalent
quaternion signs are made continuous to avoid interpolation through zero; this is a
representation change, not motion correction. Different rest poses need a separately
validated retargeting adapter. Raw Kimodo global/local rotation matrices cannot be
substituted for these basis quaternions.

## Blender behavior

`modeling_lab/import_motion.py` opens a supplied neutral static rig, checks its observed
rest signature, and writes a new `.blend` copy with linear editable action curves.
Existing rig animation, drivers, constraints, parent transforms or non-neutral poses
require an explicit merge policy and are rejected by this first importer. It preserves
control geometry, topology, skin weights and material identifiers/colors. It does not
claim whole-scene merge support, retargeting, IK, contacts or artistic animation quality.

Fresh-process verification checks every declared root/joint sample, sampled evaluated
mesh movement, and a real keyframe edit that changes the pose AND actual deformed mesh.
It restores the edited curve, verifies the entire clip again, and confirms the file hash
did not change. The input character source file is also preserved during import.

## Regression and evidence

The original 25-sample fixture caught an edit-restoration failure. A one-joint, two-frame
reduction reproduced it. Blender `FCurve.update()` relocates keyframe RNA storage, so
a retained keyframe reference becomes stale. Reacquiring the live curve point before
restoration fixed the reduced test. The regression drives the real verifier:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' `
  --background --factory-startup --disable-autoexec --threads 2 --python-exit-code 1 `
  --python scripts/test_motion_restore_blender.py -- `
  --input output/motion-keyframe-minimal-v1/imported/motion.blend `
  --output output/my-new-motion-restoration-report.json
```

Preserved red/green reports: `output/motion-keyframe-regression-red-v1.json` and
`output/motion-keyframe-regression-green-v1.json`. The green run checks 14 keyframe points,
actual mesh response and full restoration; `motion_generation_verified` remains false.
Targeted diagnostics remain in the clearly named ignored `output/motion-keyframe-debug-v1.*`.

`scripts/test_compatible_motion_import.py --output output/my-new-motion-fixtures` creates
and verifies two authored layouts on the supplied athletic/older characters, with
different FPS, sample counts and joint tracks. Both full reruns passed under
`output/compatible-motion-fixtures-v2/`: 375 keyframe points for the 25-sample/24-FPS
athletic fixture and 555 for the 37-sample/30-FPS older fixture. Fresh Blender verification
confirmed saved sample agreement, evaluated mesh motion, real keyframe-to-mesh response,
successful restoration and unchanged source files. Failed v1 evidence remains intact.

The next provider integration needs real source/target rest-pose conversion and verified
model/encoder access. See MOTION_MODEL_FEASIBILITY.md. No pretrained motion model was
downloaded or run by this importer work.
