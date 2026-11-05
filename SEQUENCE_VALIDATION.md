# Scene Forge 0.4 — verified milestone

Verified locally on 19 October 2026 using installed Qwen3:4b and Blender 5.1.
No paid services, model downloads, fine-tuning or custom neural weights were used.

## What changed

The executor now accepts timed lists of walk, hold, wave and look_at_camera actions for
the existing blocky/low-poly rig. Action orders, durations and destinations are data,
not per-prompt source edits. Each list is baked to editable rig keyframes and timeline
markers. Existing version-1 recipes and the organic greeting remain supported.

Known unsupported English requests are rejected before inference. The model must also
report any unmet request with an exact excerpt from the user prompt. Unknown requests
still depend on model judgment; the heuristic and quotation check are not universal
semantic verification. Model descriptions in limitations remain unverified notes.

## Live inference evidence

### Walk, hold, look

Job: [first successful sequence](output/20261019-102638-15137fc1/scene.blend).
The new prompt requested six seconds, a two-metre walk over three seconds, one second
stationary, then a two-second head turn to a static camera. Qwen returned these timings
and targets in one response. The job completed in approximately 144 seconds without a
manually corrected plan. Blender verified the movement, stationary intervals and head
direction. This run preceded the later pause-recognition and typed-action schema changes.

The requested teal was interpreted as cyan (#00ffff), so this is not a perfect
prompt-fidelity result. The character and environment remain the existing procedural assets.
Reopening confirmed 4,680 rig keyframe points and a working in-memory keyframe edit.

### Wave, walk, hold, look

Job: [successful development retest](output/20261019-201849-71c325ea/scene.blend).
The prompt requested a stationary wave for 1.5 seconds, a one-metre walk over two seconds,
a half-second pause, and a one-second head turn, with an orbit camera and moonlight.
The final implementation produced this sequence from one live Qwen response, without
editing its output. Total job time was approximately 140 seconds. The resulting project
has 150 frames at 30 FPS and 3,900 rig keyframe points. Reopening and editing a keyframe
in memory passed; the input .blend was not saved over. Saved verification reports include
measured leg/arm motion, stationary body checks and head/camera endpoint alignment.

These two development jobs retain request.json, planner_attempt_1.json, provenance.json,
scene.json, validation.json, reopen_validation.json and the editable project. Their
sequence_preview.mp4 files are six-FPS Workbench drafts, not final cinematic renders.

### New action order after freezing the implementation

Job: [held-out sequence](output/20261019-202433-6b497509/scene.blend).
After freezing the implementation and package, a new prompt requested a five-second,
24-FPS low-poly shot: turn the head toward the camera for one second, hold for half a
second, wave for 1.5 seconds, then walk from [0, 0, 0] to [1.5, 0, 0] over two seconds.
It specified a red (#cc3322) explorer, static camera, golden-hour lighting and no props.

One live Qwen response produced the requested action order, durations, destination,
frame rate, character color, camera and lighting settings. The job completed in
approximately 144 seconds. No source, planner instructions or generated plan were
changed after seeing this result. Blender motion checks passed, and a fresh Blender
process reopened the saved project and verified an in-memory keyframe edit. The project
contains 3,120 rig keyframe points. Request, raw response, provenance, scene and validation
reports are retained alongside the editable project; no preview was rendered for this run.
This single held-out success supports reusable composition of the implemented actions;
it does not establish general animation understanding or a broad success rate.

### Failures retained, not counted as successes

- output/20261019-102945-4978503a: the second prompt initially failed because Qwen added
  a destination to a stationary wave and repeated the mistake after validation feedback.
  The schema was changed to separate walking and stationary action variants.
- output/20261019-201340-3ad72a7b: the same prompt was then falsely rejected by Qwen,
  citing unrequested organic/facial features. The unmet-request contract was clarified
  and request quotations were added before the successful final run above.
- output/20261019-201537-46186cc6: the original chair-and-sitting challenge now returns
  unsupported with chair asset and sitting listed, before any model or Blender call.
  This demonstrates honest rejection, not successful sitting animation.

The first two successful sequences and their failures are iterative development
observations; the additional held-out sequence is still not a statistically meaningful
benchmark. The successful retry does not erase earlier planner failures. Qwen
still writes inaccurate general notes (including speed descriptions); checks use actual
scene data rather than those notes.

## Automated and packaging checks

- 36 Python unit tests passed, covering legacy behavior, timing/ground/speed constraints,
  revisions, omitted known motions, unsupported requests and invented request quotations.
- Real Blender sequence tests passed for walk-hold-look, wave-walk-look-walk and two actors.
  Deliberately deleting head curves caused the camera-look check to fail as intended.
- Existing alternate-scene, organic performance/weights/foliage, and extension registration
  regression scripts passed.
- The final 0.4 ZIP passed Blender extension manifest validation. Its archived files match
  current source bytes; its packaged CLI validated the final live-generated scene.
- All 333 pre-existing output/example/older-package files checked against the earlier audit
  retained their content hashes. Original .blend files and older ZIPs were preserved.

The packaged extension is ready to install; no installed extension or user preferences
were changed. The full interactive panel click-through has not been verified. Runtime
testing used the same underlying CLI/job pipeline with separate Blender processes and
an isolated local Ollama server, including fresh server starts. That test server was
stopped afterward.

## Remaining limits

This is an expanded AI-controlled procedural animation engine, not a trained motion model.
It still lacks sitting/contact IK, arbitrary rigs/retargeting, organic locomotion, realistic
facial acting and production VFX. Head turns have no anatomical limits. Prompt coverage
checks recognize only selected English features and do not prove every timing, negative
instruction, actor assignment or visual property. Further work should improve measured
planner reliability and rig/motion quality, rather than treat these clips as Avatar-level
results. See [SEQUENCES.md](SEQUENCES.md) for usage and format.
