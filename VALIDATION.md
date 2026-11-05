# Validation evidence — 18 October 2026

## Organic performance update (0.3)

Implemented stationary greetings, a full-body camera, articulated upper arms/forearms/hands,
weighted legs/feet, denser skin, render subdivision and procedural foliage wind.
No model training, paid services or downloaded assets were used.

Verified locally in Blender 5.1 on the existing laptop:

- 24 Python tests passed, including rejection of organic walking, the full-body requirement
  for organic waving, stationary start/end checks and normalized anatomical weights.
- The real Blender performance test produced 39,230 base skin vertices, 39,228 faces and
  16 bones for default proportions. Mean sampled hand travel was 1.42456 m; sampled foot
  drift was exactly zero between the rest and greeting poses.
- Actual evaluated skin samples stayed in frame across 18 sampled frames of the three-second
  greeting. This is stronger than the ordinary centerline job check, but not a full
  collision, occlusion or artistic-quality test.
- 228 wind-deformed leaf meshes were present. Leaf attachment stays fixed; leaf-tip
  deformation and time-varying shape keys were checked.
- The portrait regression passed connected/manifold skin, normalized weights, blinking,
  pupil containment and changed facial proportions. Widening the head changed measured
  half-width from 0.43253 m to 0.51287 m; the widened body had 40,652 vertices.
- Extension registration/unregistration passed. Blender's extension validator accepted
  the 0.3 manifest and archive.

The initial real Qwen generation in `output/20261018-184116-ae08b9e3` took 188.52 seconds,
562 output tokens and one structural-validation attempt. It correctly chose organic wave
and full-body framing but ignored the request for no extra props, adding three primitive
trees. This run was deliberately cancelled during building after plan review. Its raw
plan and provenance remain available; it is not counted as a successful reviewed example.
The explicit model revision in `output/20261018-184521-c0c76ab7` succeeded in 119.31 seconds,
293 output tokens and one attempt. The diff contains only removal of those props and
replacement of the limitations; actor proportions, motion, camera, seed and timing were
preserved. The revised plan is saved as `examples/organic-greeting.json`.

Visual QA caught issues that the initial numeric checks missed: a hard stage horizon,
visible blunt trunk ends and stretched arm skin. Two render attempts were deliberately
cancelled (`20261018-184521-c0c76ab7`, `20261018-184931-65081cdd`). The builder now uses a
continuous rising forest backdrop, taller tapering trunks and height-dependent arm-weight
boundaries. The initial boundary adjustment also exposed thigh coupling in a diagnostic
pose; the final lower-arm boundary excludes the pelvis and legs. Regression checks now
cover stationary leg vertices and inner-arm weighting in addition to feet.
The diagnostic pose also exposed fingertip vertices partially anchored to the root by
an old height cutoff. That cutoff was removed; tests now explicitly cover thumb and
fingertip weights and inspect actual hand vertices, not just average hand displacement.
All 24 Python tests pass after these corrections.
The final real Blender performance test also passes, including actual fingertip vertices,
stationary legs/feet and sampled full-body framing. The corrected middle pose was rendered
and visually inspected before starting the final animation.
Cancelled and diagnostic renders are not final deliverables or approved training examples.

The final scene completed in `output/20261018-185603-da074bec` using the exact
AI-revised plan. `lineage.json` records the original and revised AI jobs and matching
plan hash; this rebuild is correctly attributed as `scene_file`, not a new model call.
Read-only inspection of its saved `.blend` confirms 38,826 base vertices, 38,824 base
skin faces, 621,184 evaluated skin faces at two subdivision levels, 16 bones and 228
wind leaf meshes. The project retains Cycles, 960x540, 24 FPS and 72 timeline frames.
The recorded render device is the local GTX 1650 through CUDA. All 15 job scene checks
passed. Three Cycles stills were rendered; the middle greeting pose was visually checked.
The 36-frame Eevee sequence encoded successfully. FFprobe confirms H.264, 640x360,
12 FPS and exactly 3.000 seconds. The job ended with no warnings; saved project size is
2,885,502 bytes and preview video size is 116,409 bytes. The final rebuild and rendering
took approximately 9 minutes 52 seconds on this laptop; this is an observed run, not a
controlled benchmark. The video is a grainier draft than the Cycles stills.
Beginning, raised-arm, closed-eye and final-rest frames were inspected. This is manual
spot checking, not proof of production-quality deformation in every possible pose.
The final 0.3 ZIP is 35,197 bytes and passes Blender's official extension validation.
All rendering processes exited. No user project was overwritten and no paid resource
or trained-weight checkpoint was created.

## Organic workflow update (0.2)

The local model produced an organic portrait specification in
`output/20261018-171112-2477a7ac/`: one attempt, 320 output tokens, approximately 125.52
seconds reported inference duration. It preserved the requested head width (0.95), muzzle
length (1.0), ear length (1.15), cheek fullness (0.85) and brow height (0.025). Its exact
initial prompt context is captured in provenance. This is a successful planning example,
not a measure of general prompt-following accuracy.

That job built an editable project and three Cycles stills. Its first full-Cycles video
attempt was deliberately cancelled after frame times of roughly 22 seconds made the
preview impractical. The scene specification was retained. The corrected builder is
finished rebuilding the identical AI-generated specification in
`output/20261018-171857-eb92e915/`, using Cycles stills and a 12 FPS Eevee motion preview.
The saved project retains Cycles settings; Eevee is an approximation of those materials
and lighting, not an exact image match. This rebuild's provenance is `scene_file`; its
source AI provenance remains in the earlier job. Do not describe the rebuild as a new
model inference or omit the cancelled attempt.

The rebuild completed in approximately 13 minutes 44 seconds, including three stills and
the motion preview. This was not a controlled benchmark; auxiliary inspection work ran
concurrently for part of it. `ffprobe` verified H.264 video at 640x360, 12 FPS, 72 frames,
exactly six seconds. All 15 structural scene checks passed. `lineage.json` records that
the original AI plan and rebuilt specification are identical. The auxiliary parallel
inspection render did not produce images and was stopped; inspection was retried serially.
Verified front, profile and blink renders are in `inspection_views_verified/` inside the
completed rebuild. They were visually inspected after clearing camera animation in the
diagnostic script (the original project was not overwritten). The actual character base
mesh has 21,734 vertices and 21,732 faces. The side view confirms the intentionally bulging
creature eyes and rounded cranium; it also exposes the simple background stage. These are
inspection artifacts, not proof of film-quality anatomy or an environment ready for all angles.

Verified implementation checks:

- **22 unit tests pass**, including bounds on organic capabilities, partial anatomy edits,
  implicit defaults, reviewed-example filtering, stale approval hashes, and overwrite prevention.
- The real Blender organic test confirms one connected, manifold skin component, normalized
  weights, four animated eyelid shape keys, head motion and a genuine geometry response to
  head-width changes. The widened test mesh has 22,760 base vertices; its measured head
  half-width increased from approximately 0.432 to 0.512 scene units.
- A closed-eye render revealed pupil geometry protruding through the lids. Pupils were
  changed to conform to the eye surface. A regression check verifies their rest geometry
  fits inside the closed-lid ellipsoid, and the corrected blink frame was visually inspected.
- The extension registers/unregisters in Blender, and the ZIP passes official manifest
  validation. Extracted-package tests validate an organic plan and confirm that the current
  unreviewed jobs export zero training examples.
- No production examples have been approved for training. No custom weights were trained,
  downloaded or uploaded. The fine-tuning path is documented in MODEL_PLAN.md and TRAINING_DATA.md.

Visual scope: this is a stylized creature with bounded procedural anatomy, skin shading,
eyes, sensory ears, crest, ornament and idle performance. The foliage and anatomy remain
stylized; eyelids and facial motion are simple. It does not meet the user's Avatar-level
quality reference. No expressive facial rig, independently weighted limb performance,
neural geometry, freeform sculpting, retopology or production animation is claimed.

## Earlier blocky workflow (0.1)

This is a working prototype using an existing local language model and procedural Blender
tools. No new model was trained. No paid API, paid compute or model download was used.

## Environment

- Windows; Intel i5-9300H; approximately 24 GB RAM; GTX 1650 with approximately 4 GB VRAM.
- Blender 5.1.0 and its bundled Python 3.13.9.
- Ollama 0.35.1; already installed `qwen3:4b` weights.
- FFmpeg 8.1.2 for draft MP4 encoding.

## Actual AI generation

Job: `output/20261018-164013-c0d6ecbd/`.

Prompt: "Make a 15-second blocky explorer scene. An explorer in an orange coat walks from
left to right, stops beside a glowing turquoise crystal and waves. Put two small houses
and two pine trees behind the path. Use warm sunset light and a slow camera dolly. Keep
the environment uncluttered."

Ollama produced the scene specification in one attempt: 574 output tokens, approximately
200.43 seconds reported generation duration. The complete job took about seven minutes.
This was an observed run, not a controlled performance benchmark; other work was running.

Outputs: an editable `.blend`, validated JSON specification, provenance, three Cycles
preview images, 90 Workbench draft frames, and an H.264 MP4. `ffprobe` confirmed the MP4
is 640x360, 6 FPS, 90 frames, exactly 15 seconds. The saved Blender timeline is 360 frames
at 24 FPS. All 14 scene checks passed: camera, duration, requested entities, seven-bone
rig, start/end positions and sampled actor framing.

The rendered scene and draft frames at the start, middle and end were visually inspected.
They show the explorer moving toward the crystal and raising an arm. This is a basic
procedural gait/wave, not learned character performance. Workbench video uses draft
shading; Cycles stills show the configured lighting and emissive material more faithfully.

## Actual AI revision

Job: `output/20261018-164349-3499ac43/`.

Prompt: "Change only the explorer coat color to blue (#3366ff) and the lighting to
moonlight. Keep every other setting unchanged."

Ollama completed in one attempt, approximately 194.26 seconds reported generation duration.
The resulting specification changed the coat color and lighting. It also updated a
lighting description in the model-generated `limitations` notes. All other scene fields
were preserved, including prop definitions, motion, camera, duration and seed. The
revision was built as a separate project and passed its scene checks. Its final Cycles
still was visually inspected for the blue coat and cool lighting.

Model-generated notes are not verification evidence. For example, claims about exact
prop clearance or camera behavior in those notes have not been independently established.
Use the explicit validation checks and the actual Blender project for those assessments.

## Automated checks

- 14 Python unit tests passed: schema constraints, identifier validation, impossible
  motion, local-only endpoint, invalid-output repair, no silent demo fallback, unique job
  directories, failure reporting, revision preservation/deletion and incomplete new objects.
- Alternate real Blender scene: two actors, wave/idle actions, orbit camera, moonlight,
  low-poly setting, metallic cube, glass sphere and pillar; 19 structural checks passed.
- Blender extension register/unregister smoke test passed, including default model,
  bundled Python discovery and generation operator availability.
- Final extension ZIP passed Blender's official extension manifest validation.
- The packaged CLI was extracted into a temporary directory and successfully validated
  the generated scene specification, confirming that the ZIP includes its Python modules.

The extension's interactive panel has not had a complete manual click-through test.
Registration and generation through the command-line pipeline have been exercised.

## Failure retained

An initial request using installed `qwen3.5:4b` exceeded the earlier 300-second timeout.
The failed job is retained at `output/20261018-163434-52ec45a4/`. The default was changed
to the successfully tested `qwen3:4b`; current requests allow 600 seconds. This does not
establish that the other model can never work on this computer.

## Limits of verification

Framing checks sample three frames and test actor centerline bounds. They do not prove
absence of occlusion, collisions, foot sliding, prompt omissions or artistic defects.
There is no automatic visual critic. Manual Blender edits are not read back into the
revision system. The current implementation does not provide general sculpting, detailed
mesh generation, facial animation, lip-sync, learned body motion, arbitrary VFX or
multi-shot movie production. See README.md and ROADMAP.md for scope and next milestones.
