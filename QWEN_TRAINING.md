# First Qwen LoRA experiment

Started 22 October 2026. Free local compute only; animation work remains paused.

## Completed training result

The first run completed **80/80 optimizer updates**, processing all 160 training examples
once with gradient accumulation two. The final **4,602,248-byte LoRA adapter** is saved at
`output/qwen-lora-local-ops-v1/adapter/adapter_model.safetensors`. It contains updates to
**1,146,880 trainable parameters**; the base model is frozen. Weight hashes changed and
all 80 optimizer steps executed. This is actual Qwen adaptation, not prompt-only changes.

| Measurement | Unchanged Qwen3-0.6B | With trained adapter |
|---|---:|---:|
| Valid operation JSON on 16 test cases | 8/16 | 16/16 |
| Exact requested operation on those cases | 4/16 | 14/16 |
| Validation assistant-token loss | 0.09209 | 0.01024 |
| Exact operations on 4 separate language/unit challenges | 1/4 | 1/4 |

**No improvement on the separate language challenge.** The adapter correctly handled
the differently worded eight-percent chest scale, but failed both centimetre-to-metre
conversions (20/30/40 were treated as metres), changed one target name to `object`, and
translated along X instead of the requested Z in another case. Raw answers and the
disabled/enabled-adapter comparison are preserved in `output/qwen-lora-language-challenge-v1/`.
This sharply limits the 14/16 result: the improvement is on a narrow synthetic curriculum,
not reliable free-form natural language. No retraining was done after observing these tests.

Training took **780.3 seconds (13.0 minutes)**. Peak allocated PyTorch GPU memory was
**1,929.7 MiB**; total driver/device memory can be higher. Setup, baseline generation and
post-training evaluation took additional time. The project test suite passed 51 tests.

**Remaining failures:** test-013 requested a negative-Y local translation, but the
adapter emitted negative X and Z translations. Test-014 requested a negative-Z whole
object move, but it emitted negative X. Both were valid JSON and incorrect instructions.
These failures are retained; neither was corrected or used for additional training.

This result is limited to 16 held-out synthetic examples from the same task/language
families. It does not establish professional modeling quality or reliable free-form
requests. The adapter is experimental and is not installed into the existing UI.

Evidence: `result.json`, raw `baseline-test.json`/`trained-test.json`, `training-log.jsonl`,
`weight-change.json`, and `first-update-proof.json` in the run directory.
Final adapter SHA256: `776e32773125bcf306319d84d7e8a1dfd9271b9153f8eaebe4dc5ba8e6f79dc9`.

### Actual editable-mesh result

The saved adapter was loaded in a **fresh Python process** and emitted exactly the
declared upper-chest edit, without output correction. Blender applied it and saved
[the editable project](output/qwen-trained-humanoid-review-v1/scene/model.blend).
Fresh Blender reopening and vertex editability passed. The original input hash remained
unchanged. All 15 numerical/integrity checks in `acceptance.json` passed:

- 1,098 control vertices moved, with maximum displacement **7.7664 mm**.
- Motion was outward along X, limited to the requested local region.
- Outside-region coordinates, topology, skin weights, materials, object transform and
  the input rig were preserved.

Review [three-quarter render](output/qwen-trained-humanoid-review-v1/scene/three_quarter.png),
[front](output/qwen-trained-humanoid-review-v1/scene/front.png),
[profile](output/qwen-trained-humanoid-review-v1/scene/profile.png), and
[measured edit map](output/qwen-trained-humanoid-review-v1/edit-map.svg).
The map highlights actual changed control vertices; it is not an AI-generated picture.

The renders were visually inspected. The source remains a bald, mannequin-like body
study with simple materials and some noisy fine edges in the low-sample views. This
run did not improve face detail, skin realism, clothing construction or rig design.
**The adapter selected the local edit; the existing asset supplied the human anatomy
and skeleton; Blender performed the mesh operation and rendering.** Artistic approval
remains false for user review. This is a successful numerical edit, not a new human
created from scratch or a production-quality character endorsement.

### Smallest next improvement

Expand the training curriculum with independently authored sentence forms, balanced
positive/negative X/Y/Z moves, object-name variation and explicit unit conversions.
Keep an entire set of language templates and parameter combinations out of training.
If the current failure cases become training examples, retire them from the independent
test set and freeze new tests first. Repeat the same unchanged-base/adapter comparison,
plus preservation checks on multiple detailed meshes. Do not promote this adapter into
the default scene planner until it passes those checks; the existing UI is unchanged.

## What is being trained

This experiment adapts the official **Qwen3-0.6B** checkpoint, revision
`c1899de289a04d12100db370d81485cdf75e47ca`, using LoRA. It is smaller than the unchanged
Qwen3:4b model used by the existing Ollama prototype. The 4B model is not overwritten
or fine-tuned by this experiment. The small NumPy humanoid shape network is unrelated.

The target is **single-operation modeling tool use**: select XYZ axes, translate a
percentage into a scale multiplier, specify a bounded local edit, move an object, or
create a simple primitive. This is not anatomy learning, realistic character synthesis,
rig generation, sculpt-detail synthesis, or a model capable of producing a whole scene.

Source: [official Qwen model card and Apache-2.0 license](https://huggingface.co/Qwen/Qwen3-0.6B).
Method: [PEFT LoRA](https://huggingface.co/docs/peft/package_reference/lora).
The isolated runtime uses the official [PyTorch CUDA 12.4 wheel](https://pytorch.org/get-started/previous-versions/).

## Data and checks

`output/qwen-training-corpus-v1/` contains 160 training, 16 validation and 16 test
examples, plus SHA256 hashes and a manifest. Instructions and target operations are
programmatically authored in this project. No failed planner output, downloaded mesh,
private data or external teacher-model answer is included in the corpus.

Every target passed schema checks and analytical coordinate checks. All 192 target
operations were executed in Blender on small geometric fixtures; deformation checks
compare actual vertex changes against independently recorded scalar facts. Topology
and test skin weights were preserved. This is technical verification, not artist review.

Object names and numeric tuples differ between splits. The splits still share task
families and language templates: results measure narrow within-curriculum generalization,
not unfamiliar modeling concepts or realistic humanoid quality. Test examples are not
used in the optimization loss. Validation loss is recorded before/after; this run does
not select checkpoints or adjust hyperparameters based on test results.

## Reproduce

The environment is `.venv/`, separate from Blender, Ollama and other applications.
Exact installed versions are in `modeling_training/environment-lock.txt`.

```powershell
uv venv .venv --python 3.12
uv pip install --python .venv/Scripts/python.exe torch==2.6.0 --index-url https://download.pytorch.org/whl/cu124
uv pip install --python .venv/Scripts/python.exe -r modeling_training/requirements.txt

# Every output directory below must be new.
& .venv/Scripts/python.exe -B -m modeling_training.corpus --output output/new-corpus
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup --disable-autoexec --threads 4 --python-exit-code 1 --python scripts/verify_training_corpus_blender.py -- output/new-corpus
& .venv/Scripts/python.exe -B -m modeling_training.download_base --output output/new-base
& .venv/Scripts/python.exe -B -m modeling_training.finetune --base output/new-base --data output/new-corpus --output output/new-training-run --steps 80 --accumulate 2
```

The downloader resolves and records the official repository commit, downloads
safetensors/tokenizer/config/license files, and hashes them. Training and inference
load local files with remote model code disabled. To reproduce this exact base revision,
reuse the recorded local snapshot; a newly resolved upstream revision may differ.

Training uses assistant-output-only loss, FP16 base weights, FP32 trainable LoRA weights,
gradient checkpointing, rank 8 on attention Q/V projections, AdamW at 0.0002, microbatch
one and accumulation two. Seed 22104. Examples longer than 768 tokens are rejected rather
than truncated. Generation is greedy with a 192-token cap, without schema-constrained
decoding, automatic repair or hand-corrected answers.

## Evidence to inspect

`output/qwen-lora-local-ops-v1/` records:

- `config.json`: base/dataset provenance, training settings, GPU and source hashes.
- `baseline-test.json`: raw unchanged-model outputs and exact numerical checks.
- `initial-adapter.json`: initial trainable-weight digest and parameter count.
- `training-log.jsonl`: actual loss, gradient norms, optimizer updates, timing and VRAM.
- `checkpoint-*/`: intermediate saved adapters; these alone do not prove useful learning.
- `adapter/adapter_model.safetensors`: final trained adapter, when training completes.
- `weight-change.json`: before/after trainable-weight hashes and successful update count.
- `trained-test.json`: raw post-training outputs on the same test set.
- `result.json`: final metrics and limitations; `failure.json` records an interrupted or failed run.

A saved adapter requires the corresponding base model. It is not a standalone full model.
The existing Blender extension still uses its old Ollama planner; this adapter is accessed
through the separate inference CLI until broader reliability has been established.

Intermediate checkpoints contain adapter weights, not a complete optimizer/RNG resume
state. They preserve learned parameters but are not advertised as exact training resumes.

`examples/qwen-training-language-challenge.json` adds four separately authored prompts
with different wording and centimetre-to-metre conversions. These were declared during
the fixed training run, before post-training output was seen, and are excluded from the
training corpus. `modeling_training.evaluate_adapter` compares the same frozen base with
the adapter disabled/enabled in a fresh process. This tiny challenge is additional evidence,
not a broad language or modeling benchmark. Review-case hashes are recorded in the run.

## Fresh-process detailed-mesh review

`examples/trained-modeling-review.json` declares a local upper-chest edit on the existing
163-bone humanoid. It uses the same language template as training, with a different object
name and region tuple. It is not a test of creating a realistic human from scratch.

```powershell
$case = Get-Content examples/trained-modeling-review.json -Raw | ConvertFrom-Json
& .venv/Scripts/python.exe -B -m modeling_training.infer --base output/qwen3-06b-base-v1 --adapter output/qwen-lora-local-ops-v1/adapter --prompt $case.prompt --input $case.input --editable $case.editable --output output/new-adapter-review --render
```

The CLI saves the uncorrected response, validates it, executes the operation in fresh
Blender, and reopens the saved `.blend`. Failed requests remain failures. The original
input is never saved over. Its detailed anatomy, topology and bones come from the existing
asset, not from this training run. Semantic and visual review are separate from execution.
