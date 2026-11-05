# CGI control adapter experiment

27 October 2026. **Training completed: 160/160 optimizer updates, with changed weights saved. The Blender review and regression check also finished.**

| Frozen 24-case benchmark | Exact intent | Valid JSON/schema |
|---|---:|---:|
| Unchanged base | 6/24 | 12/24 |
| Previous modeling adapter | 7/24 | 13/24 |
| New CGI-control adapter | 22/24 | 24/24 |

The two remaining failures (`test-vfx-005`, `test-vfx-023`) turn a requested local vertex displacement into a whole-object translation. They are preserved without correction. Validation loss decreased from 0.42773 to 0.03143. Peak allocated GPU memory was 2,281.5 MiB.

The elapsed training timer reports 24,003.8 seconds, but one step accounts for 21,845.8 seconds and the median step is 13.70 seconds. This strongly suggests a long interruption/suspension; it is not a reliable uninterrupted-compute benchmark. The exact cause was not observed.

Fresh-process review inference passed all four predeclared light/camera/surface/glare prompts (base: 1/4; trained: 4/4), with no output correction. The adapter SHA256 is `014502f1cdbf423fa6d55d5069ad9dc0d2083927ed959c2a9a65642fdd77f11a` and the original adapter hash remains unchanged.

The completed experiment warm-started the saved Qwen3-0.6B modeling adapter, with a new optimizer and 160 updates. The original adapter is preserved. This trains single structured operations for existing Blender elements: area-light power, camera focal length, Principled roughness/metallic and compositor Glare threshold/strength. It also practices whole-object/local axis moves and unit conversion, with modeling replay examples. This is not realistic asset generation, learned anatomy, motion generation, fluid simulation or a complete VFX system.

The authored Blender fixture rendered before/after images and saved `output/qwen-vfx-blender-review-v1/review.blend`. Fresh-process reopening verified the requested properties, editable vertices and an unchanged saved file. The model supplied settings, not the fixture geometry. Glare artifacts remain visible; this is a functional demonstration, not a production-quality render.

The separate 20-case modeling/language regression scored 19/20 for the new adapter versus 5/20 for the base. The remaining `language-002` failure used target `object` instead of `casework` and was rejected. Evidence is in `output/qwen-vfx-regression-v1`; there was no retraining or correction after these tests.

## Frozen data and checks

- `output/qwen-vfx-corpus-v2`: 320 train, 12 validation, 24 test examples, all original synthetic instructions.
- 96 training examples replay the original modeling task families using new names/values. No external teacher outputs or asset dataset was ingested.
- Test sentence forms and object names differ from training; numeric ranges and task families overlap. The small test is not an industry benchmark. Movement test cases emphasize negative directions.
- All 356 expected targets executed successfully in Blender 5.1 before training. This validates target operations, not the model's future answers.
- 54 unit tests pass, including rejection of unknown targets, bad units, wrong axes and nonfinite values.
- New review prompts were saved before training in `examples/vfx-review.json`. Rendering is gated on all four uncorrected outputs matching their requested intent.
- `output/qwen-vfx-corpus-v1` is the preserved empty failed dataset attempt; local deformations exceeded the existing bound. No training used it.

## Reproducing the experiment

```powershell
.venv\Scripts\python.exe -u -m modeling_training.finetune --base output/qwen3-06b-base-v1 --data output/qwen-vfx-corpus-v2 --output output/qwen-lora-vfx-v1 --steps 160 --accumulate 2 --profile vfx --initial-adapter output/qwen-lora-local-ops-v1/adapter
```

Console: `output/qwen-vfx-run-v1.console.log`. Run evidence: `output/qwen-lora-vfx-v1/`. The command refuses an existing output directory. Checkpoints save adapter weights, not an exact optimizer/RNG resume state. Do not restart over the same folder or call an interrupted checkpoint a completed result.

The experiment compares unchanged base, previous adapter and final adapter on the same frozen 24 tests under the same expanded system prompt. Greedy raw responses, schema checks and exact numerical intent scores are retained. The model sees the operation API in its system prompt; baseline performance can therefore already include these operations. Improved scores must be measured, not attributed to training by assumption.

## Source research and MiroFish

See `CGI_VFX_SOURCES.md` for model/asset licensing and feasibility research, and `MIROFISH_RESEARCH.md` for the separate hypothetical-customer experiment. The original REA MCP analysis failed due a missing Windows native component; the pinned CLI fallback completed static analysis of eight JavaScript files without parse errors. Evidence is preserved in `output/mirofish-rea-evidence.json`. Static analysis does not prove runtime behavior or cover Python/backend functionality.

MiroFish dependencies are isolated from training. The first `.venv-mirofish` installation failed the Python-version compatibility check; the compatible retry uses `.venv-mirofish311`. The four-person/two-round run in `output/mirofish-customer-review-v1` generated two comments beyond its seeded post, but timed out at 1,200 seconds before completing both rounds. It used unchanged local Qwen3:4b, not the trained 0.6B adapter. See its `acceptance.json` and `REVIEW.md`. No real customers or real social-network posting were involved.
