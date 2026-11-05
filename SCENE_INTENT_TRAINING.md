# Scene-aware intent experiment, frozen before launch

28 October 2026. No app default changes automatically. Preserve every earlier
checkpoint, failed preparation and diagnostic response.

## Evidence motivating the change

Refinement01 completed real training and scored 53/56 on the observed primary
development suite. Three reduction instructions still became positive scaling.
Older modeling was 23/32, with invalid target-name extraction; older CGI was 24/24.
Fresh challenge was 17/20, with two contraction errors and one wrong glare target.
The final acceptance gate rejected the candidate, despite all three kinds of
Blender/rig/CGI structural checks passing. See INTENT_REFINEMENT.md.

A diagnostic on ten selected known target failures used actual saved Blender
fixtures with three observed candidate elements. Same adapter and system, no training:
raw request 0/10, JSON wrapper alone 0/10, request plus catalog 9/10. Raw/catalog
responses were verified/reused for the wrapper-only control; the ten wrapper calls
were fresh. The remaining catalog error selected another real glare node, and remained
wrong. This is evidence about these selected failures, not general accuracy.
Artifacts: `output/context-probe-results-v1/`, `context-probe-results-v2/` and
`context-probe-fixtures-v1/`. No expected operations appear in model input.

## Interface and hypothesis

The separate `scene_intent` profile receives JSON containing only `request` and a
catalog of selectable/observed names and element types. Most outputs retain the old
format. Local scaling additionally requires explicit `direction` (increase/decrease)
and an unsigned percentage magnitude. The compiler consumes those declared fields
literally; it never reads request text, fixes a target, or changes a wrong direction.
Wrong but existing choices are valid syntax and incorrect semantics.

Hypothesis: explicit scene choices improve name binding, and separating direction
from magnitude reduces the small model's sign-generation error. This combines two
interface changes, so any gain is not an isolated causal estimate for either one.
Compare unchanged base, starting adapter and trained adapter under the **same new
interface**. Do not directly treat the new-interface score as an improvement over
53/56 on the previous interface.

## Frozen data and execution

Current data: `output/qwen-scene-intent-corpus-v4/`: train192, validation26, primary56,
older regression56, CGI review4 and a newly authored challenge20. Only train192 enters
gradient updates; validation selects no test targets. Primary/older raw requests are
retained development regressions with a changed interface. New20challenge is frozen
before training, but shares the AI-assisted author/schema and is limited synthetic
evidence. Ground-truth frames/actions never enter the model's user payload.

Catalog order is shuffled without an answer/default marker. The fixture verifier
creates **all** catalog choices, independently observes names/types, executes targets
or refusals, and checks every unselected element unchanged. JSON companions are hashed
in the pretraining manifest and must equal the verified JSONL records. Positive and
negative character-transfer cases and original source scene hashes are also frozen.

V1 stopped before training because older regression rows lacked physical fixture
facts; facts are now normalized from canonical physical actions. V2 predates companion
sealing. V3 was superseded before training to shuffle catalog positions independently.
These preparations remain preserved. V4 is the intended verified input.

Live character inference observes every source mesh through Blender inventory,
independently of the separately enforced editable authorization. The two source scenes
each contain eight actual mesh candidates. Catalog order is deterministically shuffled
from source hash and request; no expected-target filter appears in model input. The
chosen operation must still pass the editable authorization afterward. Real transfer
checks require at least three observed choices and recheck raw input/inventory hashes.

## Budget and unchanged acceptance thresholds

Planned `scene01`: base Qwen3-0.6B, warm-start refinement01, fresh optimizer,
96 **successful** updates, accumulation2, learning rate0.0001, rank8 LoRA, seed22104,
max16 overflow skips. One shuffled pass over192 examples, with same-batch retries.
No geometry, rigging, motion, high-resolution texture or movie training is claimed.

- Full trained weight/change/source/data integrity checks.
- Primary56: all valid, >=51 exact, no worse than unchanged base; local/whole
  translations >=16/18 each, local scales >=5/6, CGI >=7/8, refusals6/6.
- Older56: all valid, >=29/32 modeling, >=22/24 CGI.
- New20challenge: all valid, >=18 exact, all five refusals correct.
- Two precise detailed-mesh edits and post-edit rig probes; all four CGI controls,
  editable saved fixture and fresh process reopening.
- **Additional** negative-scale request on the supplied detailed humanoid must pass
  fresh inference, exact per-vertex behavior, untouched-region/topology/skin/rig checks
  and reload. No positive-only canary may stand in for it.

All gates only qualify for human visual review. Main interface and prior prototypes
remain unchanged; alternate/unrelated rig families and cinematic quality remain unproven.

## Reproduce after verification

```powershell
.\scripts\run_intent_experiment.ps1 -Name scene01 -TrainingProfile scene_intent -Data output/qwen-scene-intent-corpus-v4 -InitialAdapter output/qwen-intent-refinement01-run/adapter -Steps 96 -LearningRate 0.0001 -RegressionCases output/qwen-scene-intent-corpus-v4/regression.json -ReviewCases output/qwen-scene-intent-corpus-v4/vfx.json -ChallengeCases output/qwen-scene-intent-corpus-v4/challenge.json -PositiveCases output/qwen-scene-intent-corpus-v4/positive-transfer.json -NegativeCases output/qwen-scene-intent-corpus-v4/negative-transfer.json
```

Require completed Blender verification, full unit checks and read-only code review
before launch. New artifacts are under `output/qwen-intent-scene01-*`; never reuse names
or infer success from a checkpoint without the final reports.
