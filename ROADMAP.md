# Product roadmap

**28 October 2026:** the next requested milestone is an original short alien-forest demo,
with a target review on 28 December. [CINEMATIC_DEMO_PLAN.md](CINEMATIC_DEMO_PLAN.md)
defines scope and acceptance gates. Actual local shape-network and Qwen LoRA training
have occurred; older "no weights trained" statements below describe earlier versions.
The current bounded modeling experiment is recorded in [BALANCED_TRAINING.md](BALANCED_TRAINING.md).
Detailed-character animation remains an unverified future capability.

## Resource boundary

The user authorized free tools and compute only. Do not add paid APIs, start paid cloud
jobs or buy assets. Do not assume that an installed local model is Blender-specialized.
This computer: approximately 24 GB RAM, Intel i5-9300H, GTX 1650 with 4 GB VRAM, Blender 5.1.
This differs materially from the laptop assumed by the original research PDF.

## 0.1 - A complete small workflow

Text -> local AI scene specification -> procedural assets and rig -> animation -> materials
and lighting -> camera -> render -> editable project. Prove it in real Blender and preserve
job provenance. Explicitly separate the no-AI demo from actual model-generated plans.

## 0.2 - Organic character portrait and specialization groundwork

The user's quality reference is Avatar: detailed organic assets and cinematic performance.
The first deliverable toward that reference is an original stylized organic portrait,
not a film-quality character. Connected anatomy, semantic proportion controls, skin
shading, eyes/eyelids and idle performance are procedural. Qwen chooses the recipe.

Capture actual planner context and export only reviewed examples. Keep a separate
evaluation of visual quality; passing topology tests does not imply artist approval.
The concrete candidate-model and funding sequence is in MODEL_PLAN.md. Training-data
review and export are documented in TRAINING_DATA.md. No weights have been fine-tuned.

## 0.3 - Articulated greeting and living forest

Add a full-body camera, a stationary right-arm greeting with shoulder/elbow/wrist
deformation, denser skin and render subdivision. Branching trees, roots and fern leaflets
replace the simpler set; wind bends leaves at their attachment and spores drift.
Validate actual hand travel, fixed feet, normalized skinning and sampled mesh framing in
Blender. This is authored procedural performance; no model weights are trained by it.

## Next - Generalized motion and dependable revisions

- Add a versioned imported-motion interface with skeleton metadata, rest pose, units, FPS
  and contact labels. Evaluate the current Kimodo implementation against exported fixtures.
- Implement and test retargeting and contact-aware foot cleanup before enabling a motion model.
- Add scene-aware edits that preserve manually created Blender objects and animation.
- Measure completion and revision correctness across a held-out scene suite.
- Improve gait quality and camera composition; add occlusion/collision checks and a visual critic.

## Asset generation

- Separate procedural models, supplied assets and neural mesh generation in the job plan.
- Verify each exact model/weight/dependency license and hardware requirement.
- Evaluate mesh topology, UVs, material fidelity and deformability before enabling auto-rigging.
- Maintain reusable asset and character identities across shots.
- Use free remote GPU resources only when eligibility, quota and actual available memory fit.

## Production capabilities

Add dialogue/lip-sync, expressions, interactions, multi-shot continuity, effects and
compositing as independently validated capabilities. Do not advertise Blender-wide
automation before those workflows are implemented and measured.

## Model specialization

Record successful and failed tasks with scene state, operations and previews. Obtain
appropriate consent and rights for training data. Fine-tune only after a base-model
evaluation identifies repeatable gaps, and compare on held-out tasks.

## Commercial product

Before subscriptions: user trials, reliable installers, asset and model licensing,
isolated execution, project storage/recovery, queues, usage accounting and support.
Measure inference, rendering, storage and retry costs before setting a subscription
allowance. $200/month is a hypothesis, not a validated price or unlimited film budget.
