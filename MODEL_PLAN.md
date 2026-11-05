# Specialized Blender AI: model and compute plan

**28 October update:** typed-intent v2 completed 127 real optimizer updates in 128
attempts and scored 48/56 exact versus base 21/56. It failed acceptance and was not
adopted. The corrective `refinement01` experiment is launched with 96 successful updates,
a verified 192-example curriculum and a newly frozen 20-prompt challenge. See
[CURRENT_WORK.md](CURRENT_WORK.md) and [INTENT_REFINEMENT.md](INTENT_REFINEMENT.md).
This is specialization of existing-element instructions; general geometry generation,
cinematic motion and movie-quality production remain unproven.

**22 October update:** actual local LoRA training on Qwen3-0.6B has completed 80 optimizer
updates and saved changed adapter weights. This is a separate single-operation experiment,
not an update to the existing Qwen3:4b planner or a realistic geometry foundation model.
See [QWEN_TRAINING.md](QWEN_TRAINING.md) for scope, evidence and evaluation.

**Current modeling status:** a separate 13,187-parameter shape predictor and fitted PCA
decoder have been trained locally on synthetic combinations of CC0 MPFB adult body
shapes. The Qwen planner used by that shape experiment and pretrained geometry foundation
models have not been fine-tuned; the small Qwen adapter above is a separate experiment.
[MODELING.md](MODELING.md) records the exact scope, checkpoint and measured limitations.
The older plan below is retained as context; its "no custom weights" statements predate
this limited shape experiment. Animation development is currently paused.

Research checked 18 October 2026. This is an implementation plan, not a claim that training or artist acceptance has happened.

## What we are building

Build a Blender production system around pretrained models, then specialize the components that fail measurable tasks. The current system uses unchanged local `qwen3:4b` weights to produce bounded scene instructions. Blender creates the geometry and animation procedurally. No custom neural weights have been trained; see [the recorded evidence](VALIDATION.md).

The immediate implementation is an original organic portrait with semantic anatomy controls, editable geometry, materials, lighting, and a short presentation shot. This improves our modeling tools and supplies an evaluation task. It is not neural mesh generation, unrestricted sculpting, facial performance, or Avatar-quality production. Avatar remains a long-term quality reference, not a promised output or training dataset.

## Candidate components

| Role | Candidate and evidence | Decision |
|---|---|---|
| Understand requests; choose validated Blender operations | **Qwen3-4B**, a text model under Apache-2.0. The existing quantized Ollama installation has already produced working plans locally. [Model card](https://huggingface.co/Qwen/Qwen3-4B), [license](https://huggingface.co/Qwen/Qwen3-4B/blob/main/LICENSE). | Keep as the baseline. It does not directly generate meshes or inspect rendered images. |
| Generate draft geometry from a reference image | **Hunyuan3D-2mini**, a 0.6B shape model; full Hunyuan3D-2 separates shape and texture generation. Upstream reports 6 GB VRAM for shape and 16 GB for shape plus texture, and supports Windows/Linux/macOS. The mini card does not establish a reliable 4 GB requirement. [Mini card](https://huggingface.co/tencent/Hunyuan3D-2mini), [upstream requirements](https://github.com/Tencent-Hunyuan/Hunyuan3D-2). | First candidate for a bounded geometry experiment after suitable free compute is verified. Do not promise it fits this laptop. |
| Generate geometry and PBR materials | **TRELLIS.2**, a 4B image-to-3D model. Upstream requires at least 24 GB NVIDIA memory, tests Linux and A100/H100, and releases its model/code under MIT. Some dependencies have separate terms. [Repository](https://github.com/microsoft/TRELLIS.2), [license](https://github.com/microsoft/TRELLIS.2/blob/main/LICENSE). | Later comparison on suitable Linux compute. Published H100 timings are not predictions for this machine. |
| Sculpt edits, rigging, motion and quality checks | Initially deterministic Blender tools plus human-reviewed fixtures. | Do not treat static mesh generators as animation models. Add deformation tests, contact-aware motion, expressions and a separately evaluated visual critic in later milestones. |

Hunyuan uses a custom community license, not Apache/MIT. Its terms exclude the EU, UK and South Korea, impose distribution/service requirements and an additional commercial threshold, and prohibit using its works or outputs to improve unrelated AI models. Keep Hunyuan outputs out of the Qwen training corpus. Review the exact pinned model, code, dependencies and intended markets before shipping a service. [Hunyuan license](https://github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/main/LICENSE), [mini license](https://huggingface.co/tencent/Hunyuan3D-2mini/blob/main/LICENSE).

## Work sequence and acceptance gates

1. **Local organic workflow.** Finish a reproducible portrait and parameterized edits. Save the specification, editable project, renders, operation history and resource usage. Inspect front, profile and three-quarter views; geometry checks alone cannot establish artistic quality.
2. **Measure the unchanged planner.** Assemble an initial 300 reviewed request/scene/operation examples using our own assets and documented permissions. Reserve 60 examples before tuning, grouped by character and task family so paraphrases and related meshes cannot leak across splits. Include anatomy changes, materials, lighting, combined edits, unsupported requests and failures. These counts are a starting experiment, not proof of sufficient training data.
3. **Establish a baseline.** Record valid-operation rate, requested-edit success, preservation of untouched settings, build success, latency and peak memory. Separately score silhouette, anatomy, materials and motion through a documented human rubric. Proposed release gate: at least 95% valid operations and 90% correct edits on the held-out set, with no destructive edits; visual acceptance remains independent. Report all failures and retries.
4. **Fine-tune only a demonstrated gap.** Compare better prompting/examples with a Qwen LoRA or QLoRA adapter using the same hidden evaluation. LoRA trains small adapters while retaining the base model; it does not teach missing Blender capabilities automatically. Benchmark training memory first on verified compute, then publish adapter provenance, base revision, data manifest and evaluation deltas. Accept it only if it improves task success without regressions. [PEFT LoRA explanation](https://huggingface.co/docs/peft/main/en/conceptual_guides/lora).
5. **Expand by validated capability.** Neural assets must survive Blender import, topology/UV inspection, material checks and deformation tests before automatic rigging. Then add performance animation and shot continuity. Keep every model replaceable and every generated asset attributable.

## Compute boundary and next experiment

Current hardware is i5-9300H, approximately 24 GB RAM and GTX 1650 4 GB VRAM on Windows. Continue local planning, Blender tooling and bounded renders. A successful quantized inference run does not establish training capacity.

Next compute-bound experiment: run Hunyuan3D-2mini shape-only on five original reference images with fixed settings, on verified free GPU capacity. Record actual peak memory, elapsed time, failures, mesh quality and Blender import results. Its purpose is to decide whether neural geometry helps; no training is needed. Compare TRELLIS.2 only when its larger requirements are met. No weights were downloaded or services provisioned for this plan.

Oracle currently documents Always Free A1 capacity equivalent to 2 OCPUs/12 GB RAM and 200 GB combined boot/block storage, without a GPU shape. Capacity shortages and idle-instance reclamation are possible. It is not our GPU-training plan. [Oracle documentation](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm).

## Funding tied to evidence

The authorized external spend remains **zero**. First seek feedback on one repeatable workflow, then small paid pilots with clear deliverables. Log GPU hours per accepted result, retries, storage and support time. A later milestone budget should be measured GPU-hours × a verified rate, plus storage, data/artist work and contingency; no defensible funding amount exists yet.

Startup credits, such as [AWS Activate](https://aws.amazon.com/startups/credits/), require eligibility and approval. They are service credits, not cash; GPU quota and availability still need confirmation. Pursue funding for a demonstrated next milestone. The proposed $200 subscription remains a pricing hypothesis until quality, demand and unit costs are measured.
