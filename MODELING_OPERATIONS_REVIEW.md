# Qwen modeling operations: development review

**Historical report:** the failures below were recorded on 21 October and remain unchanged.
Subsequent small-model LoRA training is documented separately in [QWEN_TRAINING.md](QWEN_TRAINING.md).
It does not turn any failed run below into a successful one.

21 October 2026. Animation remains paused. No Qwen weights were trained or downloaded.
This experiment uses the already-installed unchanged `qwen3:4b` through local Ollama,
with one comparison against the already-installed unchanged `qwen3.5:4b`.

## Preserved baseline

| Run | Result | Evidence |
|---|---|---|
| `output/modeling-ops-bust-v1` | Failed: degenerate meshes in first response; repair request timed out. No generated bust. | `planner_attempt_1.json`, `status.json` |
| `output/modeling-ops-humanoid-v1` | Local mesh edit executed, but shifted the chest rather than broadening both sides. Semantic check failed. | `plan.json`, `acceptance.json`, `scene/execution.json` |
| Original humanoid reload | Initially reported failed because modifier tuples were compared with JSON lists. No recorded geometry, material, transform or rig difference existed. | Original `reopen.json` and separate `output/modeling-ops-evaluation-v2/original-humanoid-reopen.json` |
| `output/modeling-ops-humanoid-v2` | Infrastructure failure before model inference: Ollama was still discovering its GPU when the readiness check timed out. | `status.json`; no model response was produced |
| `output/modeling-ops-humanoid-v3` | Failed: Qwen emitted zero translation and identity scale, so no vertices moved. Executor rejected the no-op. | `plan.json`, `planner_attempt_1.json`, `blender.log` |
| `output/modeling-ops-bust-v2` | Failed: first attempt and automatic repair both contained degenerate faces. First attempt also had overlapping eyes, missing materials and incorrect proportions. | Both `planner_attempt_*.json`, `status.json`; elapsed 465 seconds |
| `output/modeling-ops-humanoid-v4` | Failed: with the schema visible, Qwen3 still emitted an identity edit and repeated it after validation feedback. Stopped before Blender execution. | Both `planner_attempt_*.json`, `status.json`; elapsed 163 seconds |
| `output/modeling-ops-humanoid-qwen35-v1` | Failed: Qwen3.5 proposed nonidentity X scaling, but put the edit center at Y=1.35 rather than Z=1.35. No moving vertices were selected; Blender rejected it. | `plan.json`, `planner_attempt_1.json`, `blender.log`; elapsed 82 seconds |

The original runs have not been rewritten to mark them successful. Reopening the old
humanoid with the corrected verifier passed, without saving or changing that `.blend`.
Its failed instruction-following result still stands.
The full-schema/no-op-validation changes did not fix Qwen3's chest-edit decision in
this test. They did make the failure explicit before launching Blender.
The Qwen3.5 comparison used the same prompt, schema, input inventory and executor as
the last Qwen3 test. It changed the selected local model only. One failure per setup
does not establish a general ranking of these models.

**Outcome:** no successful new construction or requested chest broadening was produced
in this continuation. No new model-generated bust exists to preview. The revision test
was not run because it depends on a successfully generated bust. No failed example was
approved for training, no adapter was trained, and no weights changed. Old renders are
not substituted as new results. This round improved failure detection and reproducible
evidence collection; it did not demonstrate realistic humanoid generation.

## Changes after seeing baseline failures

- Fixed modifier serialization so unchanged saved scenes compare correctly. The small
  Blender save/reopen regression failed on the original code and passed after the fix.
  It also checks that deliberate vertex and transform edits are detected.
- Added field-level mismatch reports to reload verification.
- Avoided repeating the evaluated-mesh bounds calculation for review staging; cached
  the object transform during that calculation and formatted embedded provenance over
  multiple lines instead of putting megabytes on one text line.
- Clarified general operation semantics in Qwen's system instructions: create each ID
  once, avoid line-shaped polygon faces, assign requested materials, and distinguish
  region scaling from translation. No bust recipe or manually corrected model plan
  was added.
- Increased the bounded inference timeout from 600 to 1,200 seconds and recorded it
  with inference settings. The model, context size and output token cap are unchanged.
- In the third implementation snapshot, included the complete JSON schema in model-visible
  instructions as well as the constrained output format. This follows
  [Ollama's structured-output guidance](https://github.com/ollama/ollama/blob/main/docs/capabilities/structured-outputs.mdx).
  Its effect on modeling quality must be measured, not assumed.
- Also in that snapshot, reject identity transforms/deformations during validation,
  before launching Blender. This lets the existing single validation-repair attempt
  address mathematically empty edits. It does not invent corrected operations.

These changes make subsequent attempts **development retests**, not an untouched
held-out evaluation and not evidence of fine-tuning. Frozen source hashes for both
versions and raw model responses remain under the evaluation/job output folders.

## Verification completed

- Python suite: 49 tests passed, including the new identity-edit regression and a check
  that Qwen receives the exact schema and user request. The identity-edit test first
  failed against the previous implementation.
- Generic Blender mesh/loft/modifier/duplicate/local-edit fixture passed.
- Saved-scene regression passed, including deliberate-change detection.
- Original detailed humanoid reopens and allows vertex editing; source file unchanged.
- Diagnostic replay of the old failed chest plan completed in 34.65 seconds without
  rendering after the executor changes. This reuses the old model output; it is not a
  new generation or a successful broadening result. Evidence: `replay-timing.json` and
  `replay-old-plan/` under `output/modeling-ops-evaluation-v2/`. No isolated performance
  attribution is claimed for the individual executor changes.

## Scope and training boundary

Qwen outputs structured modeling operations. The generic executor performs meshing;
Blender handles modifiers and saves editable meshes. For existing humanoid edits,
the inherited MakeHuman mesh, materials, skin weights and 163-bone rig come from the
input file. Qwen does not create or learn those bones during this test.

The shape-network checkpoint from the earlier experiment is separate and unchanged.
Pending operation examples must not be treated as approved training data. Structural
success alone cannot establish good anatomy, faithful instructions or artistic quality.
Meaningful Qwen adaptation still needs varied reviewed demonstrations, independent
evaluation tasks, and an actual adapter-training run with saved weight changes.

## Three remaining gaps

1. **Reliable spatial instructions.** Recorded failures include identity edits,
   one-sided shifts, overlapping components and degenerate faces. A schema-valid plan
   is insufficient. Keep failing requests, add early rejection for mathematically empty
   edits, and check actual geometry against explicit requested constraints.
2. **Detailed asset creation.** Current operations can assemble basic shapes and edit
   existing meshes. They cannot synthesize realistic anatomy, skin detail, facial rigs
   or production topology. Preserve the detailed rigged input for deformation tests;
   do not replace it with a primitive bust and describe that as progress in realism.
3. **A usable specialization dataset.** There is no approved operation corpus or Qwen
   adapter yet. Training on these failed outputs would teach the wrong behavior. Build
   reviewed instruction/operation pairs covering construction, local edits and revisions,
   with execution evidence and asset provenance. Split by asset and task family before
   training; paraphrases of the same example cannot be independent test cases.

The smallest practical training milestone is improved tool use on a bounded modeling
curriculum, measured against the unchanged model. It is not learning human anatomy from
scratch. Examples should include units, relative coordinates, left/right symmetry,
nondegenerate polygons, preserving unrelated parts, and explicit unsupported requests.
Any teacher-generated examples still require geometric and visual review. A later
adapter run must save actual changed weights, its base-model digest, dataset manifest,
training configuration and a before/after evaluation. GPU fit remains to be measured.

Before an adapter run, create a reviewed corpus with clearly named X/Y/Z coordinates,
nonidentity local scaling, region bounds and preserved-geometry checks. Pair instructions
with correct operations and actual Blender execution; keep model failures separately.
Include new prompts and new source meshes in evaluation. The current tests remain a
development set because their failures have already informed the prompt and validator.
