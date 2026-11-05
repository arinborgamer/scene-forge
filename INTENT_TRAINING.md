# Typed intent experiment

Prepared 28 October 2026, before this experiment's training/evaluation results.

## Hypothesis and model role

The previous adapter improved aggregate exact actions to 23/32 but failed all nine
differently phrased local translations and regressed to 19/24 on older CGI cases.
This experiment changes both the output interface and training corpus. Qwen chooses
the action kind/scope, exact target, axis, amount, original unit and region. A small
checked compiler converts those declarations into existing Blender operations.

For example, a model-declared camera amount of 6.5 with unit cm compiles to 65 mm.
The compiler does not read the prompt, infer a missing region, repair scope, select a
character preset or correct a wrong target. Wrong scope or quantities remain wrong.
Translation intents cannot include resizing or rotation fields. These are engine
invariants, not evidence that the model learned arithmetic or anatomy.

## Frozen data and execution

`output/qwen-intent-corpus-v2`: 256 train / 26 validation / 56 test, original synthetic
data only. Training has 144 translations (72 local / 72 whole), 36 local scales,
64 CGI controls and 12 refusals. Both scope classes mention object and vertex concepts,
and each crosses 3 axes, 3 units and 8 wording variants. Test translation wording,
names and amounts differ. Operation families and generator are still shared, so this
is a curriculum evaluation, not proof of broad natural-language understanding.

Supported targets must execute correctly in Blender fixtures; unsupported targets
must stop before execution. Corpus and compiler hashes are checked before training.
No old failed prompt is copied into training. Older 32-case modeling and 24-case CGI
suites are converted only to review labels in `output/qwen-intent-regression-cases-v1.json`.
Their original prompt text and final canonical expected actions are preserved. Old
tests already informed development and remain regression cases.

Train a new rank-8 Qwen3-0.6B LoRA from the unchanged local base for 128 optimizer updates,
accumulation 2, learning rate 0.0002, profile `intent`. It does not warm-start the older
direct-operation adapters because their output protocol differs. Compare unchanged base
and trained adapter under the same intent system message and decoding settings. Across
old/new interfaces, compare final Blender action correctness; do not attribute all
interface/compiler improvements to learned weights.

## Acceptance declared before results

- Completed updates, changed saved weights and matching adapter checksum.
- New suite: all 56 outputs valid, at least 51/56 exact after compilation.
  The trained exact score must not be lower than the unchanged-base score.
- Local translation at least 16/18; whole translation at least 16/18; local scale
  at least 5/6; CGI controls at least 7/8; unsupported requests 6/6 correctly refused.
- Older regression: at least 29/32 on the previous modeling suite, at least 22/24
  on older CGI, and every output valid.
- Fresh-process edits on both supplied detailed humanoid variants must preserve
  source files, requested geometry, topology, skin weights and inherited rigs.
- Four CGI fixture controls must match model instructions after reopening the saved
  editable Blender file. Visual quality remains a separate review.

Passing these gates only qualifies this bounded existing-element workflow for review;
it does not make a geometry, animation, VFX simulation or movie foundation model.
No default application model changes automatically. Any failed gate keeps the earlier
working prototype and all failed responses/checkpoints intact.

## Artifact paths

- `output/qwen-lora-intent-v2/`: training, raw evaluations, weights and source hashes.
- `output/qwen-intent-regression-v2/`: same old prompts, new protocol, compiled actions.
- `output/qwen-intent-transfer-v2/`: detailed-mesh inference and actual Blender checks.
- `output/qwen-intent-vfx-inference-v2/`: four model-selected CGI controls.
- `output/qwen-intent-vfx-blender-v2/`: editable fixture, renders and reopened checks.

Only saved completed reports establish results. Training duration or a saved checkpoint
alone does not establish capability. This work is local and uses no paid API/cloud.

After frozen data and target verification exist, `scripts/run_intent_experiment.ps1 -Name trial03`
reproduces training, old-case regression, detailed-mesh checks and the final CGI/rig
review under new artifact directories. It rejects existing outputs and concurrent model
jobs. The current version-2 job runs the same stages; the new wrapper itself has only
been syntax-checked, not used for an unnecessary duplicate training run.

`modeling_training.finish_intent_review` re-scores raw model responses, applies the
declared gates, probes both accepted edit copies, and builds/reopens the editable CGI
fixture only if all four model requests are satisfied. It never silently repairs scope,
targets or quantities. Its combined decision remains false if the language gate fails,
even when detailed mesh or rendered fixture checks succeed. Visual approval is pending.

## Protocol preflight history

Version 1 was interrupted during its initial base comparison, before any optimizer
updates. The field-list system prompt did not establish a usable flat/numerically typed
JSON format for the small base model. The partial responses, interrupted.json and exact
protocol/generator source snapshots are preserved. Do not report that as a completed
baseline or trained model.

Version 2 uses full JSON format examples, seed 28301, and newly authored test sentence
forms. Four training-split probe responses now use the flat structure but fail action,
unit or unsupported-feature constraints (0/4 exact). This is a prompt-format preflight,
not a hidden-test score or model capability claim. The full base comparison and actual
weight training are separate. All 338 version-2 corpus checks passed: 316 executed
operations and 22 refusals before execution. Maximum encoded example: 611 tokens,
with no truncation. The version-1 compiler/corpus files remain unchanged on disk.

## Live training-budget observation

The existing trainer's `--steps` loop counts attempts, while mixed-precision scaling
can skip an optimizer update. Version 2 has recorded at least one such skip, so 128
attempts must not be described as 128 successful updates. The final saved counter is
authoritative. Keep the strict declared gate; do not relax it to rescue this run.
The exact live training-module source was snapshotted and hash-checked under
`output/qwen-lora-intent-v2/source_snapshot/`. A future isolated trainer fix should count
actual updates, bound retry attempts and retry skipped examples with JSON-safe overflow
records. This live run was not hot-patched.
