# Balanced operation experiment

Prepared 28 October 2026 before the new weights were trained. This is a bounded local
experiment toward the original alien-forest demo in CINEMATIC_DEMO_PLAN.md.

## Decision and hypothesis

The contrast adapter completed 64 optimizer updates and improved its synthetic test from
4/18 (previous adapter) to 15/18. Three remaining whole-object requests incorrectly changed
scale; two were schema-invalid. The earlier generator correlated X/cm, Y/mm and Z/metres,
and training wording also followed the axis index. Its low validation loss does not prove
generalization. The next experiment crosses those factors independently and restores
local-scale examples that the contrast-only movement curriculum omitted.

## Frozen data and budget

`output/qwen-balanced-corpus-v1`: 128 train, 16 validation, 32 test. Training contains 72
paired local/whole translations (3 axes x 3 units x 4 wordings x 2 scopes), 24 local-scale
examples and 32 CGI controls. The test contains 18 translations, 6 local scales and 8 CGI
controls. All 176 targets passed actual Blender fixture execution. Unit tests check factor
coverage, split/name separation, replay coverage and rejection of incorrect scale/units.

These are original synthetic instructions. Test wording is separate but operation families
and numerical ranges are shared. This is a curriculum evaluation, not a broad independent
benchmark. The older CGI suite remains regression evidence; it informed development.

Warm start the preserved VFX adapter, `output/qwen-lora-vfx-v1/adapter`, rather than silently
replacing it with the unaccepted contrast checkpoint. Train 64 updates, accumulation 2,
learning rate 0.0001, same local Qwen3-0.6B frozen base. Save adapter and changed-weight
evidence; optimizer starts fresh. Use the `vfx` system profile for training and inference.
The existing inference CLI now accepts `--profile` so these contexts can match explicitly.

## Gates declared before training

`modeling_training.promotion` requires:

- Completed run, all 64 actual updates, and matching saved adapter checksum.
- Complete per-case results and summary counts that agree.
- 32/32 schema-valid and at least 29/32 exact new-suite operations, with no reduction
  against the same-suite previous-adapter baseline.
- At least the previous 22/24 exact on the frozen older CGI regression suite.
  All 24 regression outputs must remain schema-valid and the case-file hash must match.

Passing only makes a checkpoint eligible for Blender review. It does not change the
application's default model or establish cinematic/production readiness. A failed gate
retains the previous adapter; raw responses and failed outputs stay available.

Two review-only cases are frozen in `examples/cinematic-modeling-canaries.json` before
training: an athletic-body local offset using 12.5 mm, and an older-body local Y scaling
edit using 6 percent. They are not in the corpus. They exercise different supplied shapes
from the same MPFB topology/rig family, not independent skeletons. Expectations are used
only after inference; no output repair or test-based retraining occurs during this run.
Review checks the declared operation, all expected vertex displacements, unchanged outside
vertices, topology, skinning, materials, object transforms, rig and fresh Blender reload.
Visual/anatomical acceptance remains a separate human judgment.
The existing executor also adds authored review lighting and a camera to the output copy.
These checks concern the target mesh and rig; they do not certify preservation of every
setting in an arbitrary production scene. The original source file remains unchanged.

For later runs, `scripts/run_balanced_experiment.ps1 -Name trial02` executes the same
freeze -> Blender verification -> training/evaluation -> regression -> gates -> two
fresh-process detailed-mesh checks -> evidence-index sequence. It requires existing
local dependencies, rejects existing destinations and active model jobs, and does not
download models or switch the application default. Inspect the final JSON reports;
an experiment can finish successfully while its candidate fails the quality gate.

## Completed training and suite results

The run completed 64/64 optimizer updates in 969.34 seconds of training (about 16.2 minutes),
with 2,278.89 MiB peak allocated GPU memory. The saved adapter checksum is
`e71efce03bd49ac182715fb490c5bcc4ca77dd55aa259b0c2eeb1170b9fd3be0`.

| Evaluation | Unchanged base | Previous VFX adapter | Balanced candidate |
|---|---:|---:|---:|
| New 32-case curriculum suite, exact | 5/32 | 16/32 | 23/32 |
| New suite, valid schema | 10/32 | 17/32 | 32/32 |
| Older CGI regression, exact | 6/24 | 22/24 | 19/24 |

The balanced candidate gets all 9 whole-object translations, 6 local scales and 8 CGI
controls exact on its new suite, but all 9 local translations wrong. Each of those
requests is returned as a whole-object transform. The previous adapter got 2/9 local
translations; aggregate improvement therefore hides a worse important slice.

The older regression has 4 local/whole-object failures plus a focal-length conversion
error: 6.5 centimetres is returned as 6.5 millimetres rather than 65. That camera output
also violates the schema minimum. Regression schema validity is 23/24.

The automatic decision is **keep_previous_adapter**. Three gates fail: new-suite exact
accuracy, all-valid regression output, and the previous 22/24 regression threshold.
No application default was changed. See `output/qwen-lora-balanced-v1/promotion.json`
and `error-analysis.json`. The raw generic scope label in the older evaluation helper's
result is not a claim of untouched tests: these older cases are explicitly regression
evidence. Future helper output states that evaluation itself does not update weights.

Next hypothesis: separately measure interpretation of edit scope across sentence forms
and normalize explicit units deterministically at the tool boundary. Use newly authored
training examples and a separately frozen evaluation, not copies of these failed prompts.
More epochs of this same corpus have not been justified. A Blender canary success cannot
override this failed language/regression gate.

## Detailed-mesh diagnostic result

Both fresh-process canaries passed without response correction. The athletic local
offset moved 998 control vertices, with 9.907 mm maximum displacement after falloff.
The older local Y scale moved 1,328 vertices, maximum 3.564 mm. Both match the declared
numerical operation and expected vertex positions; checked outside vertices, topology,
skin weights, material names/colors, modifier names/types, object transform and rig are
preserved. Both `.blend` outputs were reopened in fresh Blender processes and their
original source files remain unchanged. Reports: `output/qwen-balanced-transfer-v1/result.json`.

These precise prompts share supported operation vocabulary with the curriculum. They
show that the executor and model can perform these particular requests on detailed
meshes, while the failed differently phrased requests establish language brittleness.
They do not override the failed gate or establish visual quality, realistic anatomy
generation, independent-rig support or animation. Separate fresh checks on both source
files confirmed 163 inherited bones, normalized weights, finger deformation and editable
vertices: `output/cinematic-rig-baseline-v1/`.

All 65 unit tests passed during this iteration. The reusable PowerShell runner's syntax
was checked; the underlying training/evaluation/Blender stages were run as the current
bounded experiment, not through a second duplicate full runner invocation.

## Artifacts

- Training: `output/qwen-lora-balanced-v1/`.
- Older CGI regression: `output/qwen-balanced-regression-v1/`.
- Gate decision: `output/qwen-lora-balanced-v1/promotion.json`.
- Fresh detailed-mesh checks: `output/qwen-balanced-transfer-v1/`.
- Independent raw logs: `output/qwen-balanced-run-v1.log`,
  `output/qwen-balanced-regression-v1.log`, `output/qwen-balanced-transfer-v1.log`.

See the saved result files for completion state. A launched job or checkpoint directory
alone is not evidence that evaluation passed. No anatomy, rig, learned motion, fluid VFX
or realistic text-to-3D foundation model is trained by this experiment.
