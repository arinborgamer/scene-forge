# Training data and model index

Generated from actual artifact metadata by `scripts/index_training_data.py`. Refresh after training or evaluation. Original datasets, scenes and checkpoints stay in place.

## Datasets

| Dataset | Split sizes | File hashes | Blender target checks |
|---|---|---|---|
| [output/qwen-balanced-corpus-v1](output/qwen-balanced-corpus-v1/manifest.json) | train: 128, validation: 16, test: 32 | Match | 176 |
| [output/qwen-contrast-corpus-v2](output/qwen-contrast-corpus-v2/manifest.json) | train: 128, validation: 12, test: 18 | Match | 158 |
| [output/qwen-intent-challenge-v1](output/qwen-intent-challenge-v1/manifest.json) | test: 20 | Match | 15 executed; 5 refused |
| [output/qwen-intent-corpus-v1](output/qwen-intent-corpus-v1/manifest.json) | train: 256, validation: 26, test: 56 | Match | 316 executed; 22 refused |
| [output/qwen-intent-corpus-v2](output/qwen-intent-corpus-v2/manifest.json) | train: 256, validation: 26, test: 56 | Match | 316 executed; 22 refused |
| [output/qwen-intent-corpus-v3](output/qwen-intent-corpus-v3/manifest.json) | train: 192, validation: 26, test: 56 | Match | Not verified; generation failed |
| [output/qwen-intent-corpus-v4](output/qwen-intent-corpus-v4/manifest.json) | train: 192, validation: 26, test: 56 | Match | 220 executed; 54 refused |
| [output/qwen-scene-intent-corpus-v1](output/qwen-scene-intent-corpus-v1/manifest.json) | train: 192, validation: 26, test: 56, regression: 56, vfx: 4, challenge: 20 | Match | Not verified; generation failed |
| [output/qwen-scene-intent-corpus-v2](output/qwen-scene-intent-corpus-v2/manifest.json) | train: 192, validation: 26, test: 56, regression: 56, vfx: 4, challenge: 20 | Match | 295 executed; 59 refused |
| [output/qwen-scene-intent-corpus-v3](output/qwen-scene-intent-corpus-v3/manifest.json) | train: 192, validation: 26, test: 56, regression: 56, vfx: 4, challenge: 20 | Match | 295 executed; 59 refused |
| [output/qwen-scene-intent-corpus-v4](output/qwen-scene-intent-corpus-v4/manifest.json) | train: 192, validation: 26, test: 56, regression: 56, vfx: 4, challenge: 20 | Match | 295 executed; 59 refused |
| [output/qwen-training-corpus-v1](output/qwen-training-corpus-v1/manifest.json) | train: 160, validation: 16, test: 16 | Match | 192 |
| [output/qwen-vfx-corpus-v2](output/qwen-vfx-corpus-v2/manifest.json) | train: 320, validation: 12, test: 24 | Match | 356 |

## Training runs

| Run | Recorded state | Recorded updates | Dataset | Saved adapter checksum | Recorded gate |
|---|---|---|---|---|---|
| [output/qwen-intent-refinement01-run](output/qwen-intent-refinement01-run/result.json) | completed | 96/96 | output/qwen-intent-corpus-v4 | Match | Rejected |
| [output/qwen-intent-scene01-run](output/qwen-intent-scene01-run/result.json) | incomplete: training | 5/96 | output/qwen-scene-intent-corpus-v4 | Not verified | Not evaluated |
| [output/qwen-lora-balanced-v1](output/qwen-lora-balanced-v1/result.json) | completed | 64/64 | output/qwen-balanced-corpus-v1 | Match | Rejected |
| [output/qwen-lora-contrast-v1](output/qwen-lora-contrast-v1/result.json) | completed | 64/64 | output/qwen-contrast-corpus-v2 | Match | Not evaluated |
| [output/qwen-lora-intent-v1](output/qwen-lora-intent-v1/result.json) | interrupted | 0/128 | output/qwen-intent-corpus-v1 | Not verified | Not evaluated |
| [output/qwen-lora-intent-v2](output/qwen-lora-intent-v2/result.json) | completed | 127/128 | output/qwen-intent-corpus-v2 | Match | Rejected |
| [output/qwen-lora-local-ops-v1](output/qwen-lora-local-ops-v1/result.json) | completed | 80/80 | output/qwen-training-corpus-v1 | Match | Not evaluated |
| [output/qwen-lora-vfx-v1](output/qwen-lora-vfx-v1/result.json) | completed | 160/160 | output/qwen-vfx-corpus-v2 | Match | Not evaluated |

Stages and update counts come from saved reports/logs; they do not prove a process is alive. Partial evaluation counts in catalog.json are not final scores. Full Blender and human review are separate from a language gate.

The VFX adapter warm-starts the first modeling adapter. Its optimizer starts fresh. Checkpoints contain adapter weights, not exact optimizer/RNG resume state. A higher score on one small benchmark does not establish general production capability.

## Evaluations and reviews

- [output/compatible-motion-fixtures-v2](output/compatible-motion-fixtures-v2/result.json)
- [output/context-probe-results-v1](output/context-probe-results-v1/result.json)
- [output/context-probe-results-v2](output/context-probe-results-v2/result.json)
- [output/geometry-triposr-athletic-hires-v1](output/geometry-triposr-athletic-hires-v1/result.json)
- [output/geometry-triposr-athletic-v1](output/geometry-triposr-athletic-v1/result.json)
- [output/mirofish-customer-review-v1](output/mirofish-customer-review-v1/acceptance.json)
- [output/mirofish-customer-review-v2](output/mirofish-customer-review-v2/acceptance.json)
- [output/mirofish-customer-review-v3](output/mirofish-customer-review-v3/acceptance.json)
- [output/modeling-ops-humanoid-v1](output/modeling-ops-humanoid-v1/acceptance.json)
- [output/modeling-ops-humanoid-v1](output/modeling-ops-humanoid-v1/reopen.json)
- [output/motion-keyframe-minimal-v1](output/motion-keyframe-minimal-v1/reopen.json)
- [output/qwen-balanced-regression-v1](output/qwen-balanced-regression-v1/result.json)
- [output/qwen-balanced-transfer-v1](output/qwen-balanced-transfer-v1/result.json)
- [output/qwen-contrast-regression-v1](output/qwen-contrast-regression-v1/result.json)
- [output/qwen-intent-final-v2](output/qwen-intent-final-v2/result.json)
- [output/qwen-intent-refinement01-challenge](output/qwen-intent-refinement01-challenge/result.json)
- [output/qwen-intent-refinement01-final](output/qwen-intent-refinement01-final/result.json)
- [output/qwen-intent-refinement01-regression](output/qwen-intent-refinement01-regression/result.json)
- [output/qwen-intent-refinement01-transfer](output/qwen-intent-refinement01-transfer/result.json)
- [output/qwen-intent-refinement01-vfx-blender](output/qwen-intent-refinement01-vfx-blender/reopen.json)
- [output/qwen-intent-refinement01-vfx-inference](output/qwen-intent-refinement01-vfx-inference/result.json)
- [output/qwen-intent-regression-v2](output/qwen-intent-regression-v2/result.json)
- [output/qwen-intent-transfer-v2](output/qwen-intent-transfer-v2/result.json)
- [output/qwen-intent-vfx-inference-v2](output/qwen-intent-vfx-inference-v2/result.json)
- [output/qwen-lora-language-challenge-v1](output/qwen-lora-language-challenge-v1/result.json)
- [output/qwen-trained-humanoid-review-v1](output/qwen-trained-humanoid-review-v1/acceptance.json)
- [output/qwen-trained-humanoid-review-v1](output/qwen-trained-humanoid-review-v1/reopen.json)
- [output/qwen-vfx-blender-review-v1](output/qwen-vfx-blender-review-v1/reopen.json)
- [output/qwen-vfx-regression-v1](output/qwen-vfx-regression-v1/result.json)
- [output/qwen-vfx-review-inference-v1](output/qwen-vfx-review-inference-v1/result.json)

## Using the index

- Run `.venv\Scripts\python.exe scripts/index_training_data.py` to refresh this index and `data-management/catalog.json`.
- Dataset file hashes and final adapter hashes are checked; missing or changed files are flagged.
- Use unique output directories for experiments. Never infer a run succeeded from a checkpoint folder alone.
- Use Graphify for source/document relationships; use this catalog for measured experiment status. They serve different purposes.
