# Pretrained body-motion feasibility

Research date: **28 October 2026**. Research only: no installation, model downloads, inference, account changes, token inspection, or laptop timing/quality measurements. Target supplied by owner: Windows, Blender 5.1, GTX 1650 4 GB, i5-9300H, approximately 24 GB RAM; GPU currently occupied by Qwen training.

**Recommendation:** trial Kimodo-SOMA-RP-v1.2 first, after owner encoder access is confirmed and the local training GPU is free. It has a documented low-VRAM route and direct BVH export. Neither candidate currently provides a verified, ungated, arbitrary-new-prompt workflow on this laptop. This is a feasibility judgment, not a successful integration claim.

## Reproducible candidates

| Candidate | Exact revision observed | Published download size, excluding text encoder |
|---|---|---|
| Kimodo-SOMA-RP-v1.2 | HF `0e3c89024d896064b6851201373f7834784a386b`; [revision](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.2/commit/0e3c89024d896064b6851201373f7834784a386b) | [1.13 GB repository / model.safetensors](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.2/tree/main) |
| ARDY-SOMA-RP-30FPS-Horizon60 | HF `244215084b22fcd29ab743017330e87411fe168a`; [revision](https://huggingface.co/nvidia/ARDY-SOMA-RP-30FPS-Horizon60/commit/244215084b22fcd29ab743017330e87411fe168a) | [769 MB: 627 MB denoiser + 142 MB tokenizer](https://huggingface.co/nvidia/ARDY-SOMA-RP-30FPS-Horizon60/tree/main) |

Source revisions: Kimodo [`e1c219c99b4b94ba48be1fb6a1cbc64ecee4c954`](https://github.com/nv-tlabs/kimodo/commit/e1c219c.patch); ARDY [`e706e27acc88070918308a10922b8f7174d0825e`](https://github.com/nv-tlabs/ardy/commit/e706e27.patch). Sizes are rounded upstream listings, not measured transfer totals. Default loaders fetch unpinned snapshots; a future install must explicitly preserve these model/source revisions and resolve encoder/dependency revisions. [Kimodo loader](https://raw.githubusercontent.com/nv-tlabs/kimodo/main/kimodo/model/load_model.py), [ARDY loader](https://raw.githubusercontent.com/nv-tlabs/ardy/main/ardy/model/load_model.py).

Kimodo has 282M parameters; v1.2 corrects v1.1 training/test leakage. ARDY SOMA has approximately 192M parameters excluding its encoder and generates autoregressively. These are different inference systems; Kimodo's ArdyRep variant is not ARDY itself. [Kimodo card](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.2), [ARDY card](https://huggingface.co/nvidia/ARDY-SOMA-RP-30FPS-Horizon60), [representation distinction](https://github.com/nv-tlabs/kimodo#model-update-log).

## Encoder, cache, and memory

Both loaders select `McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp` plus `...-mntp-supervised`, default bfloat16, 4096-dimensional embeddings. The MNTP adapter explicitly references gated `meta-llama/Meta-Llama-3-8B-Instruct`; official installation requires owner HF approval and token. McGill's MIT labels do not remove Meta's base-model terms. [Loaders](https://raw.githubusercontent.com/nv-tlabs/kimodo/main/kimodo/model/load_model.py), [adapter config](https://huggingface.co/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp/blob/main/adapter_config.json), [access requirements](https://research.nvidia.com/labs/sil/projects/kimodo/docs/getting_started/installation.html).

The public McGill repositories list [177 MB MNTP](https://huggingface.co/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp/tree/main) and [168 MB supervised adapter](https://huggingface.co/McGill-NLP/LLM2Vec-Meta-Llama-3-8B-Instruct-mntp-supervised/tree/main), excluding gated base weights. Exact base transfer total was not established. Arithmetic estimate: 8B parameters need roughly 16 GB at 2 bytes/parameter or 32 GB at float32, before runtime overhead. Thus CPU placement may strain 24 GB system RAM, especially alongside Blender/training; it is not free memory.

Kimodo documents approximately 17 GB all-GPU versus **under 3 GB VRAM with `TEXT_ENCODER_DEVICE=cpu`**. This is upstream guidance, not a GTX1650 measurement. ARDY offers CPU bfloat16/float32 encoder settings, but no verified 4 GB whole-pipeline budget. Both CLIs contain CPU fallback; neither proves usable CPU latency. Kimodo lists Windows but tests newer GPUs; ARDY's card lists Linux and Ampere/Blackwell/Hopper, with RTX4090/A100 tests. [Kimodo quick start](https://research.nvidia.com/labs/sil/projects/kimodo/docs/getting_started/quick_start.html), [ARDY setup/settings](https://github.com/nv-tlabs/ardy), [CPU fallback](https://raw.githubusercontent.com/nv-tlabs/ardy/main/scripts/generate.py).

Kimodo's cache keys include exact text, model, and encoder identity; misses call the encoder. Existing embeddings can condition fresh sampled motion for those texts, but cannot encode **new uncached prompts**. Local weight paths permit authorized offline use after acquisition. Cached example motion playback is not inference. [Cache source](https://raw.githubusercontent.com/nv-tlabs/kimodo/main/kimodo/demo/embedding_cache.py), [local encoder paths](https://raw.githubusercontent.com/nv-tlabs/kimodo/main/kimodo/model/llm2vec/llm2vec_wrapper.py).

## Editable Blender path and dependencies

Kimodo predicts **SOMA30**, omitting most finger/hand detail, and expands exports to **SOMA77**; expansion does not create learned finger performance. NPZ contains root positions and local/global rotations. `--bvh --bvh_standard_tpose` exports SOMA77 in centimeters at 30fps. Proposed Blender adapter: import BVH, verify axes/scale/rest pose, retarget to the studio rig, bake an editable Action. That adapter remains unimplemented/unverified. [Skeletons](https://research.nvidia.com/labs/sil/projects/kimodo/docs/key_concepts/skeleton.html), [output specification](https://research.nvidia.com/labs/sil/projects/kimodo/docs/user_guide/output_formats.html).

ARDY's CLI similarly expands SOMA30 to77 and writes NPZ with rotations/root/fps/text; it has no documented BVH CLI flag, so requires conversion. [Generation source](https://raw.githubusercontent.com/nv-tlabs/ardy/main/scripts/generate.py). Kimodo pins `transformers==5.1.0` and builds motion-correction through CMake; Windows build branches exist. ARDY requires PyTorch>=2.4, CMake>=3.15 and C++17; TensorRT is optional. Use an isolated external environment, never Blender's Python or the training environment. [Kimodo dependencies](https://raw.githubusercontent.com/nv-tlabs/kimodo/main/pyproject.toml), [build](https://raw.githubusercontent.com/nv-tlabs/kimodo/main/setup.py), [ARDY setup](https://github.com/nv-tlabs/ardy#setup).

### Selected Kimodo NPZ adapter contract

Per-sample arrays have no batch axis. [Output specification](https://research.nvidia.com/labs/sil/projects/kimodo/docs/user_guide/output_formats.html):

| Key | Shape | Meaning |
|---|---|---|
| `posed_joints` | `[T,77,3]` | World positions |
| `global_rot_mats` | `[T,77,3,3]` | World rotation matrices |
| `local_rot_mats` | `[T,77,3,3]` | Parent-relative rotation matrices |
| `root_positions` | `[T,3]` | Actual Hips trajectory |
| `smooth_root_pos` | `[T,3]` | Smoothed trajectory |
| `global_root_heading` | `[T,2]` | Heading cos/sin |
| `foot_contacts` | `[T,4]` | Left heel/toe, right heel/toe |

Convention: meters, Y-up, +Z-forward; 30fps. Rotations are matrices, with no Euler/quaternion component order. Column-transform FK composes `G_child=G_parent@L_child`; `L_child=G_parent.T@G_child`. [Coordinates](https://research.nvidia.com/labs/sil/projects/kimodo/docs/user_guide/output_formats.html), [FK](https://raw.githubusercontent.com/nv-tlabs/kimodo/main/kimodo/skeleton/kinematics.py), [inverse](https://raw.githubusercontent.com/nv-tlabs/kimodo/main/kimodo/skeleton/transforms.py). Array joint order/hierarchy is `SOMASkeleton77.bone_order_names_with_parents`, Hips index0; neutral positions come separately from `kimodo/assets/skeletons/somaskel77/joints.p`. [Definition](https://raw.githubusercontent.com/nv-tlabs/kimodo/main/kimodo/skeleton/definitions.py), [asset loader](https://raw.githubusercontent.com/nv-tlabs/kimodo/main/kimodo/skeleton/base.py).

Kimodo's NPZ saver adds no guaranteed prompt/FPS/skeleton metadata; record these in an adapter manifest. `--save_example_dir` writes separate `meta.json`, `motion.npz`, and optional `constraints.json`. [Saver](https://raw.githubusercontent.com/nv-tlabs/kimodo/main/kimodo/exports/motion_io.py), [CLI](https://raw.githubusercontent.com/nv-tlabs/kimodo/main/kimodo/scripts/generate.py). Official docs describe bundled pre-generated SOMA examples; public source points to `kimodo/assets/demo/examples`. No encoder gate is described for reading examples, but individual binary accessibility/layout was not verified or downloaded. [Examples](https://research.nvidia.com/labs/sil/projects/kimodo/docs/interactive_demo/examples.html), [path](https://raw.githubusercontent.com/nv-tlabs/kimodo/main/kimodo/assets.py).

## Commercial conditions and next step

Both codebases are Apache-2.0; weights are separate. Kimodo's bundled NVIDIA license permits commercial use, claims no output ownership, requires license/Notice when distributing models, and incorporates Trustworthy AI, guardrail and trade conditions. **ARDY discrepancy:** its card links the April2026 Open Model Agreement, while its bundled LICENSE contains the October2025 Open Model License. Resolve before product redistribution. [Kimodo LICENSE](https://huggingface.co/nvidia/Kimodo-SOMA-RP-v1.2/blob/main/LICENSE), [ARDY LICENSE](https://huggingface.co/nvidia/ARDY-SOMA-RP-30FPS-Horizon60/blob/main/LICENSE), [linked newer agreement](https://www.nvidia.com/en-us/agreements/enterprise-software/nvidia-open-model-agreement/).

Meta separately requires applicable license/Notice, product attribution, acceptable-use compliance; it restricts improving other LLMs using Llama materials/results and has additional terms above 700M monthly users. [Meta license](https://huggingface.co/meta-llama/Meta-Llama-3-8B-Instruct/blob/main/LICENSE). No blanket commercial clearance is claimed. Motion limitations include skating, prompt failures, and lack of scene-object awareness. [ARDY limitations](https://huggingface.co/nvidia/ARDY-SOMA-RP-30FPS-Horizon60#explainability).

**Independent work now:** define the NPZ/BVH adapter contract and a two-second original-prompt acceptance test. **Owner-dependent:** obtain any required Meta access through the owner account. Public free downloads/installations already fit the existing authorization; serialize any later local inference with Qwen training. Then test one Kimodo sample with CPU encoder, log peak RAM/VRAM/time, inspect retargeting and foot contacts, and save an editable `.blend`. No alternative is endorsed without equally convincing license/hardware evidence.
