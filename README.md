# Scene Forge

## Repository contents

This repository contains the source, tests, example requests, experiment documentation
and the small licensed MakeHuman base assets with their provenance and license files.
Local `output/` artifacts, trained checkpoints, downloaded foundation models, renders,
virtual environments, credentials and runtime logs are excluded. Experiment reports
refer to those local artifacts; cloning this repository does not download them.
Use the setup and training instructions below and in the linked experiment guides
to recreate the relevant workflows.

**Current milestone (28 October 2026):** an original short cinematic alien-forest demo,
targeted for review in two months with explicit quality gates, is defined in
[CINEMATIC_DEMO_PLAN.md](CINEMATIC_DEMO_PLAN.md). Work currently addresses reliable learned
modeling edits; it has not established film-quality geometry or performance animation.
See [CURRENT_WORK.md](CURRENT_WORK.md) for the active run and
[INTENT_REFINEMENT.md](INTENT_REFINEMENT.md) for the current experiment and evidence paths.

The completed typed-intent adapter scored 48/56 exact against 21/56 for its base,
but failed the declared acceptance gates. Its successor is being evaluated with
corrective language data, actual-update accounting and a fresh 20-prompt challenge.
No experiment has automatically replaced the unchanged Ollama planner. These adapters
learn structured existing-element instructions, not realistic anatomy or motion.

**Qwen training:** an actual Qwen3-0.6B LoRA adapter has now been trained locally for
single modeling operations. It is separate from the unchanged Qwen3:4b Ollama planner
and does not learn realistic anatomy or rig generation. See [QWEN_TRAINING.md](QWEN_TRAINING.md)
for the saved adapter, dataset, reproducible commands and measured evaluation results.

**Modeling experiment:** animation development is paused while we evaluate adult humanoid
modeling. A separate small neural shape predictor has been trained locally; the Qwen
planner used by that shape experiment remains unchanged. It uses CC0 MakeHuman topology and rigs, learns
bounded body-shape variation, and produces editable 163-bone humanoids. It does not yet
learn unrestricted sculpting or beat the original source interpolation. See
[MODELING.md](MODELING.md) for the checkpoints, evidence, provenance and commands.
The modeling experiment is a separate CLI and is not included in the 0.4 extension ZIP.

**Model-selected modeling operations:** a second experimental CLI lets unchanged Qwen
choose general mesh construction and local editing operations, instead of only selecting
body-shape controls. See [MODELING_OPERATIONS.md](MODELING_OPERATIONS.md) for usage and
[MODELING_OPERATIONS_REVIEW.md](MODELING_OPERATIONS_REVIEW.md) for failures and measured
results. Execution success is separate from satisfying the prompt or artistic quality.

Version 0.4 adds **timed action sequences for blocky/low-poly rigs**: walk, hold,
look at the camera, and wave can be arranged in different orders with explicit durations.
Known unsupported requests (including chairs and sitting) stop before construction;
the planner also reports unmet requirements. See [SEQUENCES.md](SEQUENCES.md) for the
format, tests, operating steps and remaining limits. Existing version-1 recipes still work.
This animation executor uses procedural motion controlled by the unchanged Ollama Qwen
planner. Its motion is not learned. The separate modeling adapters above have their own
trained checkpoints and evaluation paths.

Version 0.3 adds **full-body organic greetings and wind-moving foliage**: articulated
shoulders, elbows and wrists, planted feet, denser connected skin with render subdivision,
branching trees, fern leaflets and drifting spores. Portraits retain facial proportions,
procedural skin shading, amber eyes, animated eyelids and breathing. This is a stylized procedural character, not a trained
sculpting model or Avatar-level output. See `MODEL_PLAN.md` for the specialization path.

`examples/organic-portrait.json` preserves the tested AI-generated recipe and can be
rebuilt without another model request; see `examples/README.md`.
`examples/organic-greeting.json` preserves the AI-generated and AI-revised full-body
greeting recipe for the 0.3 builder.

A working local prototype for **text -> validated scene plan -> editable Blender project**.
The AI planner uses your installed Ollama model. Blender code constructs objects, materials,
rigs, procedural motion, lighting and an animated camera. No paid services are used.

This is an early production-system component, not a new foundation model or a general
movie generator. The AI chooses the scene parameters; it does not yet synthesize new
geometry, body motion, speech or VFX using specialist neural models.

## Start on Windows

Requirements: Blender 5.1, running Ollama, an installed instruction model (tested successfully:
`qwen3:4b`). FFmpeg is optional and only needed to turn draft frames into an MP4.
No Python dependencies need installing. The launcher uses Blender's bundled Python.

Start Ollama, open PowerShell in this project, then:

```powershell
# Check available dependencies and models
.\Run-SceneForge.ps1

# Real local AI planning, with three rendered previews
.\Run-SceneForge.ps1 -Prompt 'A blocky explorer walks toward a glowing blue crystal, stops and waves. Two houses behind the path. Warm sunset and a slow camera dolly.'

# Also create a low-cost 6 FPS workbench motion preview
.\Run-SceneForge.ps1 -Prompt 'A blocky explorer waves in a moonlit village' -Preview video

# Organic portrait, planned by the installed local model; 12 FPS lit Eevee preview
.\Run-SceneForge.ps1 -Prompt 'A six-second organic creature portrait with jade skin and long ears. Moonlight, subtle breathing and blinking.' -Preview video

# Full-body greeting with articulated arms and moving forest leaves
.\Run-SceneForge.ps1 -Prompt 'A three-second organic jade forest keeper waving. Full-body camera, planted feet, moonlit trees and wind-moving fern leaves.' -Preview video

# Reproducible organic integration demo, with no AI request
.\Run-SceneForge.ps1 -Demo -Style organic

# Explicit deterministic integration demo: no AI involved
.\Run-SceneForge.ps1 -Demo

# Revise a previous scene specification; creates a NEW project
.\Run-SceneForge.ps1 -Prompt 'Change only the explorer coat to blue and the lighting to moonlight' -Revise 'output\JOB-ID\scene.json'
```

PowerShell execution policy can affect `.ps1` files. The equivalent direct invocation is:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe' -m scene_forge generate --prompt 'A blocky explorer waves beside a glowing crystal'
```

The first successful AI plan took about 200 seconds on this laptop; building the scene,
three stills and a 15-second draft video brought that job to about seven minutes total.
These are observed runs, not a controlled performance benchmark.
Model planning may take several minutes on a small GPU. It unloads the model after each
response to free memory for Blender. If the local model or server is unavailable, the job
fails with an explanation; it never silently substitutes a preset for AI generation.

## Blender panel

Install `dist/scene_forge-0.4.0.zip` using **Edit -> Preferences -> Add-ons -> menu -> Install
from Disk**, then enable Scene Forge. In the 3D View press **N** and select **Scene Forge**.
Enter the instruction, select an output folder, and click **Generate with local AI**.

The panel launches a separate worker and Blender process. Your current project stays open.
Use **Show output folder** or **Open generated project in new window** when it finishes.
`Previous scene JSON` applies the new instruction as a revision to a saved specification.
It does not import hand edits from a `.blend` file. Cancellation during AI planning is
honored after the current network request completes; Blender construction/rendering can
be interrupted during execution. Closing the panel does not stop a running worker.

Build the extension ZIP from source:

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe' scripts/package_extension.py
```

## Outputs

Every request gets a unique folder under `output/` (or the folder you choose).

| File | Meaning |
| --- | --- |
| `scene.blend` | Editable meshes, materials, character armatures, actions, lights and camera |
| `scene.json` | Validated production specification; portable, reproducible, revisable |
| `request.json` / `provenance.json` | Input, planner identity and inference metadata |
| `status.json` | Job state, errors and artifact locations |
| `validation.json` | Structural, trajectory and camera-framing checks |
| `preview_*.png` | Three Cycles renders: organic 960x540, blocky 640x360 |
| `motion_preview.mp4` | Organic: 12 FPS Eevee preview. Blocky: 6 FPS Workbench draft |
| `draft_frames/` | Optional preview image sequence |
| `revision_diff.json` | Differences from the previous scene specification, when revising |
| `blender.log` | Blender's full construction and rendering log |

The saved project uses a 24 or 30 FPS timeline and 960x540 render settings. Preview settings
do not overwrite the saved project. Render the full animation in Blender when ready.

## Supported in 0.3

- One stationary organic creature in a portrait or full-body shot, with connected
  voxel-remeshed skin, a 16-bone weighted skeleton, procedural pigment/pores and eyelid keys.
- Organic idle or a right-arm greeting with independent upper arm, forearm and hand
  deformation. Waving requires the full-body camera. Legs/feet are weighted and editable,
  but this performance keeps them stationary; organic walking is not implemented.
- Finer 0.018 m voxel anatomy, one viewport subdivision level and two at render time.
  Approximately 39,000 base vertices for the default creature; exact counts vary by proportions.
- A deterministic forest set with branching trees, exposed roots, 228 wind-bent leaves,
  fern leaflets, mossy stones, luminous mushrooms and drifting spores. Wind is authored
  deformation, not a physical vegetation simulation.
- Five bounded organic anatomy controls: head width, muzzle length, ear length, cheek
  fullness and brow height. Set them in JSON or ask the local model to change them.
  These are regeneration parameters, not arbitrary brush-based sculpting.
- Organic video uses scene lighting and materials in Eevee. Cycles renders the three stills;
  available CUDA devices are preferred, with CPU fallback when discovery finds no CUDA GPU.
  The saved project retains Cycles settings. Eevee is a faster approximation, not an exact
  match to the Cycles stills.

- One or two blocky characters with editable rigid-weighted meshes and armatures.
- Walk, idle, wave, or walk then wave, on flat ground.
- Houses, pine trees, crystals, rocks, pillars, cubes, spheres.
- Matte, metallic, glass and emissive materials with chosen colors.
- Sunset, moonlight and studio lighting; dolly, orbit and static camera.
- 3-20 second scenes, deterministic build from JSON, revisions into separate jobs.
- Local-only Ollama requests, validated data, bounded scene complexity, no execution of
  model-written Python, and process-level isolation from the user's active Blender scene.
- Captured AI prompt context and an explicit-review dataset exporter. See `TRAINING_DATA.md`.

## Current limitations

- Motion is procedural. Blocky walking can exhibit sliding feet; there is no contact-aware
  IK or collision solver. Organic characters support stationary idle and greeting motions.
- The organic design is one bounded creature family. Its connected voxel topology is
  editable for sculpting but is not production retopology. There is no full facial rig,
  learned anatomy, automatic artistic critique, or unrestricted sculpting tool yet.
- Organic skin weights are anatomical heuristics, not artist-painted production weights.
  Extreme poses and arbitrary motions are unvalidated; fingers have no individual bones.
- `low_poly` currently adjusts character edge rounding; it is not a separate asset model.
- Camera checks test projected centerline bounds at three frames, not occlusion, every
  frame, aesthetic quality or action semantics. There is no automatic visual critic yet.
- Materials are procedural shader values; no image texture synthesis, UV workflow or sculpting.
- No motion foundation model, neural mesh generation, asset downloads, expressive facial animation,
  lip-sync, rain, fluids, cloth, hair, arbitrary VFX or film-level continuity yet.
- Revisions rebuild from the saved scene specification. They do not preserve manual edits
  made later in Blender. Partial updates preserve unspecified fields and merge objects by ID;
  inspect revision_diff.json because a model can still request an unintended change.
- Only Blender 5.1 on Windows is currently being validated. The panel is not a hosted service.
- Generations are not instant. CPU render time and local model latency depend on hardware.
- A generated project is a draft to review, not proof that all aspects of the prompt succeeded.

## Development

```powershell
& 'C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe' -m unittest discover -s tests -v
& 'C:\Program Files\Blender Foundation\Blender 5.1\blender.exe' --background --factory-startup --python-exit-code 1 --python scripts/test_extension_blender.py
```

The planner, validated scene schema, job runner and Blender builder are separate modules.
New model backends must produce the same validated scene representation or a versioned
asset/motion interface; they must not bypass validation and execute arbitrary model output.

See `ROADMAP.md` for the next product milestones and `VALIDATION.md` for actual run evidence.
See `MODEL_PLAN.md` for candidate weights, hardware constraints, data/evaluation gates and
funding milestones. The small shape-network checkpoint is documented in `MODELING.md`;
the Qwen3-0.6B adapter is documented in `QWEN_TRAINING.md`. No motion model has been trained.
