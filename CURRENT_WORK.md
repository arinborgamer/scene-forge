# Active work and safe continuation

Updated 28 October 2026. User authorized useful work until the Codex allowance runs out.
External spending remains zero. Existing prototype scenes/checkpoints are preserved.

## Current bounded experiment: scene01 (launched)

The scene-aware experiment is now launched through `scripts/run_intent_experiment.ps1`.
Current source and wrapper are frozen/snapshotted for this run. Do not hot-patch training,
evaluation, compiler or final-review code while it is active. Do not launch duplicates.

- Run/logs: `output/qwen-intent-scene01-run/` and `output/qwen-intent-scene01-logs/`.
- Final: `output/qwen-intent-scene01-final/result.json` after the bounded pipeline.
- Data: `output/qwen-scene-intent-corpus-v4/`: 192 train,26validation,56primary,
  56olderregression,4CGI,20newchallenge; all354 Blender cases passed (295executed,
  59refused), all unselected catalog elements unchanged. Maximum encoded753, limit768,
  no truncation. JSON companions, canaries and source scene hashes are frozen.
- Warm start refinement01, profile `scene_intent`,96successfulupdates,accumulation2,
  learningrate0.0001,16skipbudget. New output requires explicit increase/decrease and
  unsigned scale percentage. The compiler never reads prose or fixes a wrong direction.
- Scene metadata: actual unfiltered source inventory, shuffled independently of editable
  authorization. Both supplied scenes have8meshchoices; real transfer checks require>=3.
- Mandatory extra physical negative-scale canary, in addition to original2mesh edits,
  rig probes,4CGIcontrols,new20challenge and unchanged acceptance thresholds.
- 141 unit tests passed with5optionalgeometry skips; the isolated geometry suite covers
  its8tests. Independent read-only Python review found no remaining launch blocker.
- Baseline/reference comparisons run before weight updates. No new score or saved
  scene01 weights are claimed until their completed reports exist.
- Completed new-interface comparisons: unchanged base12/56exact,17valid;
  starting refinement01 adapter46/56exact,56valid. Actual training has begun
  (2successfulupdates recorded at this note). Candidate results remain pending.
  Compare against these same-interface scores, not the older53/56protocol score.
- A separate bounded CPU audit waits up to120minutes for saved weights and writes
  `output/qwen-intent-scene01-run/update-audit.json`; it does not promote the model.

Read `SCENE_INTENT_TRAINING.md` for exact command, hypotheses, ablation and fixed gates.
`output/preservation-audit-20261028-v1.json` confirms both original characters and
both previous adapters still match earlier saved checksums. The bounded engineering
self-review is saved in `output/self-evaluation-20261028.md`; it explicitly leaves
completion and model adoption pending.
Prior scene corpus preparations remain: v1 failed missing older fixture facts; v2
predates companion sealing; v3 was superseded before training for independent catalog
shuffling. V4 alone is the intended input. No defaults changed.

## Completed bounded experiment: refinement01

The unique local run `refinement01` completed through `scripts/run_intent_experiment.ps1`.
Its source wrapper is retained in its logs directory. Do not rerun it over existing outputs.

- Run: `output/qwen-intent-refinement01-run/`.
- Logs: `output/qwen-intent-refinement01-logs/`.
- Completed final report: `output/qwen-intent-refinement01-final/result.json`.
- Data: `output/qwen-intent-corpus-v4/`, 192 train, 26 validation and the unchanged
  56-case development regression. All 274 Blender target/refusal checks passed;
  maximum encoded length 611, no truncation.
- New 20-prompt challenge: `output/qwen-intent-challenge-v1/`, frozen before training.
  All targets/refusals passed Blender verification. It compares v2 and candidate;
  all 20 valid, >=18 exact and 5/5 refusals are required. This is limited synthetic
  evidence with different authored wording/names, not customer or artistic validation.
- Warm start: intent-v2 adapter, 96 successful updates, accumulation 2, learning rate
  0.0001, fresh optimizer. Maximum 16 skipped AMP updates. The repaired trainer counts
  actual optimizer calls and retries the same examples after overflow, with fresh dropout.
- 105 unit tests passed before launch. Real CPU GradScaler tests cover overflow, scale
  growth, finite-weight safeguards, bounded retries and callback cleanup. Independent
  read-only review found no remaining blocker.

Weight training has completed: 96 successful updates in 97 attempts, one overflow
retried on identical batch indices, 1,276.15 seconds, peak allocated 2,250.02 MiB.
Adapter SHA-256: `878176f038d1c03cf89bb11e3a0ea7adf28e73a7b8cdacc25effb4bd83bbc790`.
`update-audit.json` passed independently: all 192 training rows used exactly once,
all 112 tensors finite and different from the warm start, source/data/checksum checks
passed. Base and prior-adapter comparisons reproduced 21/56 and 48/56. New accuracy
and downstream results are now complete: primary 53/56 exact, 56 valid; old modeling
23/32 and CGI24/24; fresh challenge17/20 exact,19 valid. Both mesh edits, post-edit rigs,
four CGI controls and fresh-reopened editable CGI fixture passed. Final decision rejected;
do not adopt. All three primary failures are unsigned reductions, older name extraction
still fails, and the fresh challenge misses two contractions and one glow control.

Details and fixed gates: `INTENT_REFINEMENT.md`. No default model changes automatically.
The corpus-v3 snapshot-write failure was preserved before training; v4 is its verified
replacement. No failed test prompts were copied into the training set.

The data index now distinguishes recorded progress, completion, and process liveness.
Partial counts in `data-management/catalog.json` must not be reported as final scores.

## Separate CPU geometry probe in preparation

Read `LOW_MEMORY_GEOMETRY.md`. TripoSR code and pretrained weights are MIT; static
image-to-3D is a separate capability, not our trained Qwen model or learned rigging.
Pinned source: `output/research-triposr-107cefdc/`. Verified/adapted CPU bundle:
`output/research-triposr-cpu-v1/`. Downloads completed (1,677,248,183 bytes of model/config).
The original upstream checkout is clean and unchanged. Two imports in its copied
source explicitly use our CPU marching-cubes adapter and pinned local DINO config.
`source-integrity.json` binds every copied Python source plus LICENSE to the pristine
revision plus the two declared patches; `geometry_lab/bundle.py` verifies exact loaded
file paths, revisions, hashes and source inventory before model import.

Isolated `.venv-geometry/` uses Python 3.11 and Torch 2.6 CPU; do not install into the
active training `.venv/`. First dependency attempt failed hub/tokenizers compatibility;
logs preserved. Corrected installation uses `geometry_lab/requirements-cpu.txt`
(hub0.17.3/tokenizers0.14.1) completed. All six geometry compatibility/bundle/preprocessing
tests passed, including the actual analytical asymmetric-axis and outward-winding test.
For future runs, require
`test_geometry_*.py` to pass including the analytical asymmetric-ellipsoid axis/winding
test; the main environment skips missing optional geometry dependencies.

Reference RGBA rendered successfully on CPU: `output/geometry-reference-athletic-v1/`.
It uses the supplied CC0-family humanoid, not new generated geometry; original scene
hash is preserved. Both actual CPU image-to-3D runs completed: grid128 produced4084
vertices/8160triangles, grid256 produced16584vertices/33160triangles. Raw meshes, GLBs,
editable .blend files, CPU previews and fresh-process actual vertex-edit/restoration
checks passed. The denser run also preserved vertex colors. Both shapes are visibly
inferior to the supplied character, especially face/hands; do not adopt them as a rigged
character or approved training target. GEOMETRY_PROBE.md records timings, provenance,
reconstruction errors (~55–57mm under declared alignment), and limits. Commands use
`geometry_lab.generate` and `scripts/review_geometry_blender.py`; both refuse reused
outputs. Any output remains unrigged, with anatomy/topology/artistic acceptance pending.

## Completed prior intent-v2 experiment

Training/evaluation process: `output/qwen-lora-intent-v2/`, data `output/qwen-intent-corpus-v2/`,
profile `intent`, target 128 loop attempts, accumulation 2, learning rate 0.0002, fresh
rank-8 LoRA from unchanged `output/qwen3-06b-base-v1`. Base score is completed: 21/56 exact.
Weight training has now finished: 128 attempts, 127 successful updates, 1 skipped overflow
at attempt 36, 1926.39 seconds (about 32.1 minutes), peak allocated memory about 2251.64 MiB.
Saved adapter SHA-256: `9084ca707d0da7f715d61bd8baefee69294ce00ec5d19da53e856b3449caf6cc`.
All 112 saved adapter tensors passed a finite-value check. The update counter matches
the log and checksum; `integrity-audit.json` records that the strict all-updates gate
is not met and the old overflow log contains nonstandard JSON Infinity. Completed
new-suite evaluation: 48/56 exact, 51/56 valid, versus base 21/56 exact.
Local/whole translation each passed 18/18; scales 3/6, refusals 1/6 and CGI 8/8.
Older modeling passed 22/32 and CGI 22/24. Combined final review rejected this adapter.
Both detailed-mesh edits and post-edit rig checks passed, but one CGI node-name response
failed, so no repaired look-development fixture was rendered.

Current dataset: 256 train, 26 validation, 56 test. All 338 target/refusal checks passed
(316 Blender executions, 22 refusals); 611-token maximum, no truncation.

Training-module source bytes were preserved in `output/qwen-lora-intent-v2/source_snapshot/`
and verified against the run's recorded source hashes. The v1 attempt was interrupted
before training because its field-list prompt caused unusable output formatting; v1
data, partial baseline and exact source snapshots remain preserved.

IMPORTANT: this prior run skipped one optimizer attempt because of gradient overflow.
Its old trainer counts attempts in `--steps`; actual successful updates are logged
separately. Do not claim 128 successful updates. Keep its strict rejection. The isolated
subsequent trainer repair implements actual update counting, bounded same-batch retries,
finite weights and strict JSON. Prior artifacts/source snapshots are unchanged; no live
process was hot-patched.

Its completed command chain recorded:

1. 56 older regression prompts -> `output/qwen-intent-regression-v2/`.
2. Raw-response language/action gates -> `output/qwen-lora-intent-v2/promotion.json`.
3. Two fresh-process detailed-mesh edits -> `output/qwen-intent-transfer-v2/`.
4. Four CGI review requests -> `output/qwen-intent-vfx-inference-v2/`.
5. A separate bounded completion job waits for the above, then runs
   `modeling_training.finish_intent_review`, rechecks edited rigs, and builds/reopens
   `output/qwen-intent-vfx-blender-v2/review.blend` only if all four requests pass.
   Final report: `output/qwen-intent-final-v2/result.json`.

Logs: `output/qwen-intent-training-v2.log`, `qwen-intent-regression-v2.log`,
`qwen-intent-transfer-v2.log`, `qwen-intent-vfx-inference-v2.log`, `qwen-intent-final-v2.log`.
No application default changes automatically. These are finite local jobs, not unattended
two-month training. If a process fails, inspect its preserved error/report instead of
launching duplicate runs or overwriting directories.

## Completed independent work

- Typed-intent compiler uses explicit units; wrong scope stays wrong. See INTENT_TRAINING.md.
- Versioned rig profiles and 42 actual static deformation probes passed on two supplied
  163-bone MPFB shapes plus one renamed same-family mapping fixture. See RIG_PROFILES.md.
- Kimodo/ARDY research is in MOTION_MODEL_FEASIBILITY.md. New uncached prompts require
  gated Llama encoder access; no model/encoder downloaded, installed or run. No relevant
  local model-cache directories were found; token contents were not inspected.
- Provider-neutral compatible-rig motion codec/importer exists. Its sources are authored
  validation fixtures, not AI-generated motions. No retargeting is claimed.

## Motion importer regression completed

`output/compatible-motion-fixtures-v1/athletic/motion.blend` imported correctly, but its
verification caught failure to restore an edited keyframe. Reduced repro:
`output/motion-keyframe-minimal-v1/imported/motion.blend` (one joint, two frames).
`scripts/test_motion_restore_blender.py` drove the real failure and saved
`output/motion-keyframe-regression-red-v1.json` with edit_restored=false.

Confirmed cause: Blender FCurve.update() relocates keyframe RNA storage. A retained point
reference no longer points at the live keyframe. Targeted trace is preserved in
`output/motion-keyframe-debug-v1.log`. The importer now reacquires
`curve.keyframe_points[-1]` before restoration. The reduced regression is now GREEN in
`output/motion-keyframe-regression-green-v1.json`: real mesh edit and full restoration
passed, input file unchanged. The original two fixture layouts both passed through
`scripts/test_compatible_motion_import.py` under `output/compatible-motion-fixtures-v2/`:
375 and 555 editable keyframe points, real pose/mesh response, full restoration,
saved-clip agreement and unchanged source files. See MOTION_IMPORT.md.
Diagnostic scripts live under ignored
output/ and must not be mistaken for production/model-generation code.

## Next continuation

Inspect refinement01 logs/results first; do not duplicate the live job or rerun prior
training/motion fixtures. Refresh DATA_INDEX.md and preserve acceptance failures.
Serving integration is eligible only after gates. Later work: explicit motion-provider/retarget
adapter after access requirements are met. Original short cinematic milestone remains
targeted for 28 December in CINEMATIC_DEMO_PLAN.md; Avatar-level quality is unproven.
