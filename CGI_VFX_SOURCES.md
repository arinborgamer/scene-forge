# CGI/VFX sources and a bounded first training curriculum

Research date: 24 October 2026. Scope: free tools and local compute; current target is a GTX 1650 with 4 GB VRAM. This note records source research and recommendations, not a completed CGI/VFX training run. No external model, asset library, or dataset was downloaded by this research task.

## Recommendation

Extend the existing Qwen tool-use experiment with explicit lighting, camera, material and compositor instructions. Start with a small curriculum whose effects can be inspected in an editable `.blend` file. Use original scene fixtures first; introduce a few CC0 assets to test transfer afterward. Keep the existing modeling checkpoint intact and measure each new adapter against the unchanged base and the previous adapter.

The project's [QWEN_TRAINING.md](QWEN_TRAINING.md) records real Qwen3-0.6B LoRA training, but also unchanged 1/4 performance on a separate language/unit challenge. Its successful chest edit used existing anatomy and a rig. That evidence supports another bounded tool-use experiment; it does not establish a learned human generator or a general VFX model. These local results were read from the project report, not rerun during this research.

## Five useful candidates

### 1. Qwen3-0.6B: keep the existing language-to-operation base

- **Type:** a text-generating causal language model with 0.6 billion parameters; not a mesh, motion or rendered-video model.
- **License/access:** Apache-2.0 in the official model card. The card documents thinking/non-thinking generation and Transformers support from 4.51.0 onward. [Official model card](https://huggingface.co/Qwen/Qwen3-0.6B), [license](https://huggingface.co/Qwen/Qwen3-0.6B/blob/main/LICENSE).
- **Use here:** train structured outputs for approved Blender operations. Blender executes those operations; the model learns selection, arguments, units and composition.
- **Compute decision:** retain the already downloaded, pinned base and local training runtime described in `QWEN_TRAINING.md`. Its prior approximately 1.93 GiB peak allocated GPU memory is a local measurement for that specific short sequence configuration, not a guarantee that longer VFX examples fit.
- **Do not claim:** feeding it a collection of meshes automatically teaches realistic anatomy, lighting aesthetics or image understanding. The training representation must explicitly connect instructions to correct outcomes.

### 2. Poly Haven: CC0 environment, material and object assets

- **Type:** HDRIs, texture maps and 3D models. These can supply scene content and controlled variations, but are not ready-made prompt-to-Blender-operation pairs.
- **License:** the asset collection is CC0. Its FAQ explicitly permits AI training. The asset license differs from website and API service terms. [Asset license](https://polyhaven.com/license), [training permission in FAQ](https://docs.polyhaven.com/en/faq?q=commercial).
- **Access:** current API terms permit free personal, academic and commercial access. Applications must identify requests using a unique Referer or User-Agent and visibly credit Poly Haven when presenting content through the live API; that service attribution rule does not attach to downloaded CC0 assets. Avoid disruptive usage. [Current API terms](https://github.com/Poly-Haven/Public-API/blob/master/ToS.md), [official API overview](https://polyhaven.com/our-api).
- **Use here:** later select two small HDRIs and two materials at 1K, plus one modest model if needed. Record asset ID, source URL, resolution, file hashes and dependencies. Treat this as a proposed cap, not an already acquired dataset.
- **Compute decision:** optional small asset additions are preferable to bulk high-resolution downloads. First training can use procedural fixtures without any external assets.

### 3. BlenderProc: procedural scene and label generation

- **Type:** a Blender-based procedural renderer supporting object poses, materials, lighting, camera poses and RGB/depth/normal/segmentation output. Standard examples write rendered data and annotations, not language instructions. It can load `.blend` scenes and provides a Blender GUI debugging route. [Official repository](https://github.com/DLR-RM/BlenderProc).
- **License/access:** GPL-3.0 code, publicly available. Imported datasets and assets need their own provenance checks; the code license is not blanket permission for every supported asset source. [Repository license](https://github.com/DLR-RM/BlenderProc/blob/main/LICENSE).
- **Use here:** reference its controlled scene randomization and camera/material examples when designing original fixtures and validators. If later adopting its code, retain applicable notices and distribution obligations.
- **Compute decision:** not required for the first corpus. It brings another execution layer and Blender environment assumptions; do not replace the working runtime just to use it. No local compatibility or speed benchmark was performed.
- **Missing bridge:** explicitly save editable scenes and pair each scene transformation with our instruction, operation and independent postconditions. Image annotations alone do not provide those labels.

### 4. Kubric: synthetic video, depth, flow and segmentation

- **Type:** a procedural data generation framework built on Blender and PyBullet, with annotated multi-object video and generated `.blend` scenes for inspection. Its README documents a Docker route and Blender 2.93. It is potentially useful later for occlusion, tracking and compositing evaluation. [Official repository](https://github.com/google-research/kubric).
- **License/access:** the repository code is Apache-2.0. Do not infer that every third-party asset or published challenge dataset has identical terms; inspect the selected asset manifest and dataset license before ingestion. [Repository license](https://github.com/google-research/kubric/blob/main/LICENSE).
- **Compute decision:** defer. Its older Blender/Docker workflow adds integration cost to the existing Windows/Blender setup. No container or large public dataset was downloaded.
- **Missing bridge:** segmentation, depth and optical flow supervise visual tasks; they are not equivalent to natural-language tool instructions. Use a small generated fixture set if such supervision becomes part of a specific model experiment.

### 5. Hunyuan3D-2mini: a later geometry specialist, not today's teacher

- **Type:** a 0.6B image-to-shape model whose example returns a mesh. This is a different capability from Qwen emitting Blender operations. It does not establish animation-ready topology, humanoid bones or skin weights. [Official mini model card](https://huggingface.co/tencent/Hunyuan3D-2mini).
- **Compute:** the parent project's README states 6 GB VRAM for shape generation and 16 GB for shape plus texture. The mini card does not establish a tested 4 GB configuration. Do not promise a local fit or download it during this sprint. [Official project README](https://github.com/Tencent-Hunyuan/Hunyuan3D-2).
- **License/access:** custom Tencent Hunyuan 3D 2.0 Community License, not Apache-2.0. It excludes the EU, UK and South Korea from its territory and has distribution/use conditions. Section 5(b) restricts using its works, outputs or results to improve other AI models except Hunyuan3D-2 or its derivatives. **Do not add Hunyuan outputs to the Qwen training corpus.** A separate integration needs its own license review. [Full license](https://github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/main/LICENSE).

## What counts as training data for this system

| Data kind | Useful for | What it does not establish |
|---|---|---|
| Rendered image or video | Visual inspection, perception or image/video training with a suitable model | Editable object state, node connections, rig structure or correct tool instructions |
| Mesh, material, HDRI or `.blend` asset | Scene fixtures, reusable content, geometry evaluation | A natural-language request paired with the right edit |
| Prompt + scene context + expected operations + checks | The existing language-to-Blender-operation approach | Learned creation of the fixture's anatomy or original asset |
| Pretrained specialist weights | A separate geometry/perception/motion component | Permission to distill that model or proof it fits local hardware |

The immediate corpus should contain original instructions and validated scene operations. It can reference external asset identifiers, but should not bulk-copy documentation, arbitrary GitHub repositories or movie footage as if these were correct training answers.

## Proposed first CGI/VFX corpus

These are proposed curriculum boundaries, not implemented capabilities or measured results. Start with the first row; add another operation only when its executor and checks exist.

| Operation family | Example task | Independent acceptance check |
|---|---|---|
| Lighting | Set a named area light to an explicit power, size and color | Read actual light type, energy, dimensions and color from a freshly reopened file; verify other lights unchanged |
| Camera | Set a named camera to 50 mm with explicit focus distance and f-stop | Read actual camera and DOF properties; verify transforms and unrelated objects unchanged |
| Materials | Change a named material's roughness/metallic/base color | Inspect the intended Principled inputs and material assignment; verify other material and mesh data unchanged |
| Compositing | Add a bounded glare operation to an existing render chain | Inspect node type, parameters and links after reload; render a tiny emissive fixture and verify a visible effect without replacing the scene |

The [official Blender glare documentation](https://docs.blender.org/manual/en/4.4/compositing/types/filter/glare.html) describes bloom, fog glow and their controls. This 4.4 documentation supports the concept, not compatibility with the installed 5.1 Python API. Inspect the installed node properties/sockets and use version-specific tests before implementing labels. Direct 5.1 API pages could not be fetched during this research.

Suggested bounded dataset size: **240 training, 40 validation and 48 frozen test examples**, balanced over implemented operations, plus 12 hand-authored review requests. This is a starting experiment size, not an estimate of data needed for production quality.

Each example should carry:

- A stable ID, split, original prompt and scene preconditions, including existing target names and types.
- The expected operation with explicit units, and whether unsupported or ambiguous requests should be rejected.
- Independently specified expected scalar properties or invariants, not merely a copy of the executor output.
- Fixture provenance, source license, file hash, Blender version and generator seed.

Create target `.blend` states in fresh output directories and verify them before training. Use numeric parameter coverage, varied target names, sentence structures and supported unit conversions. Keep whole language templates, numeric combinations and some fixture/asset families out of training. Previously failed examples may become training material only if replacement independent tests are frozen first.

For the first run, single-operation instructions are preferable to long scenes. Freeze any two-operation composition tests separately and report their results as transfer tests unless compositions were actually trained. Invalid targets and unsupported smoke, fire or tracking requests should produce an explicit unsupported result, not a fabricated successful edit.

## Evidence required before calling the new run successful

1. Preserve existing base and adapters. Save the new dataset manifest/hashes and a distinct experiment directory.
2. Record real optimizer updates and changed adapter-weight hashes. Extending prompts or tools alone is not training.
3. Compare unchanged base, previous adapter and new adapter on the same frozen prompts, with raw model outputs retained.
4. Measure parsing, exact target/units/parameters and unsupported-request handling separately. Valid JSON is not a correct scene edit.
5. Execute valid predictions without manual correction; save and reopen editable `.blend` scenes in a fresh process. Report rejected, failed and repaired outputs separately.
6. Inspect before/after renders on at least three different fixtures, including an existing detailed asset. Numerical correctness and visual approval are separate outcomes.
7. Report run time and peak memory for the actual run. Serialize training and Blender rendering to avoid competing for the 4 GB GPU.

The first credible outcome is reliable instructions for a few editable CGI/VFX controls. It is not a new realistic-human foundation model, a simulation engine trained from scratch, live-action camera tracking, cloth/fire/fluid synthesis, or movie-level autonomous production. A longer run should follow a clean frozen evaluation protocol and adequate data coverage, rather than simply increasing steps on the same templates.

## Research limits

Primary READMEs, model cards, official documentation and license texts were inspected. The external pipelines were not installed, benchmarked or subjected to code/security audits. No external pretrained model was fine-tuned, no cloud service was provisioned, and no training or render job was started by this research task. The selected sources are candidates with different roles; they are not an already assembled CGI/VFX dataset.
