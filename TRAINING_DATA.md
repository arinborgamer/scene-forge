# Preparing examples for a specialized model

**Update, 22 October 2026:** the separate `modeling_training` experiment has trained a
small Qwen3-0.6B LoRA adapter on an original synthetic single-operation curriculum.
See [QWEN_TRAINING.md](QWEN_TRAINING.md). It does not use the scene-job exporter below;
failed modeling jobs have not been approved or imported as training targets.

The original production scene planner remains unchanged. The humanoid shape experiment
described in [MODELING.md](MODELING.md) has its own dataset and trained checkpoint;
it does not use this exporter. This exporter prepares reviewed planning examples
for a future experiment; it does not download weights, train, upload, or grant data rights.

New AI jobs capture the exact initial system message, user request, schema and example in
`provenance.json`. A successful Blender build is only a structural check, not an artistic
approval. Demos, failed jobs, old jobs without captured prompts and revisions are excluded
from the current exporter. Revision outputs need a separate patch-oriented dataset.

## Review an example

Inspect the actual project, renders, prompt and specification. Check requested changes,
anatomy, framing, surface artifacts, animation and unsupported claims. Record permission
to use all relevant source material. In particular, do not mix model outputs whose terms
restrict training other models into this corpus; see MODEL_PLAN.md.

Only after that review, create `review.json` inside the job folder with these fields:

```json
{
  "approved": false,
  "scene_sha256": "canonical digest of the reviewed scene",
  "reviewer": "name of the person reviewing",
  "rights_note": "source ownership or applicable permission",
  "quality_notes": "what was inspected, known limitations and corrections"
}
```

Set approval true only when the review is actually complete. `scene_forge.dataset.scene_digest`
computes the canonical digest from the validated scene dictionary. Changes to the scene
invalidate that approval. A rights note is a record, not an automatic license check.

Export with Blender's bundled Python, from this project directory:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe' -m scene_forge export-dataset --jobs output --output training/reviewed-candidates.jsonl
```

The output path must not exist. The command prints counts and skip reasons, preserves the
original prompt context, appends the validated scene as the assistant target, and retains
review provenance. Identical scene specifications are deduplicated. An empty export is
expected until examples have explicit reviews. No production examples were automatically
approved during implementation.

## Before training

The resulting JSONL is a candidate corpus, not a ready-made benchmark. Group related
characters, edits, prompt paraphrases and source assets before splitting train/validation/
test sets. The exporter does not detect semantic duplicates or assign these splits.
Keep evaluation examples out of prompting and training. Measure the unchanged model first,
then accept an adapter only after held-out improvement. The synthetic tests in `tests/`
exercise export logic and are not training examples or artist approval.
