# Timed actions — Scene Forge 0.4

This milestone expands the reusable executor. Qwen selects an ordered, timed motion
program and scene settings. Blender computes the joint curves. No training, learned
motion synthesis, new character modeling, sitting, or production VFX is claimed.

## Use it

Start Ollama with the existing qwen3:4b model installed. Use the launcher or the new
0.4 extension package. The old 0.3 ZIP and all existing outputs remain available.
Generating creates a new output folder and never edits a previously saved project.

```powershell
.\Run-SceneForge.ps1 -Prompt 'A six-second blocky character shot. Walk two metres for three seconds, stand still for one second, then turn the head toward the camera for two seconds. Static camera, no props.' -Preview none
```

Open the generated scene.blend. Select the character armature to edit pose curves;
timeline markers label the action boundaries. The scene specification is also embedded
in a Blender text block. Motion remains editable after reopening without Ollama running.
An unsupported request produces an unsupported job state and an explanation, not a
substitute animation. Known English unsupported requests are checked before dependencies
or inference; the model additionally emits unsupported_requests for capabilities it
cannot represent. Each model-reported unmet feature must include a request_quote found
in the actual prompt; invented request quotations trigger a repair attempt. This check
does not prove that a quoted request really is unsupported. Planner responses are
retained even if validation fails.

## Motion program

Version-1 recipes keep the original action/walk_until behavior. Version 2 additionally
supports actor action=sequence with 1–8 ordered steps. All step durations must sum to
the scene duration. The old walk_until field remains required for compatibility but is
ignored for a sequence. Only walk steps have target coordinates.

```json
{
  "id": "performer", "color": "#228899",
  "start": [-2, 0, 0], "end": [0, 0, 0],
  "action": "sequence", "walk_until": 0.6,
  "sequence": [
    {"action": "walk", "duration_seconds": 3, "target": [0, 0, 0]},
    {"action": "hold", "duration_seconds": 1},
    {"action": "look_at_camera", "duration_seconds": 2}
  ]
}
```

This actor belongs in a schema_version=2, duration_seconds=6 blocky/low_poly scene.
Walk paths stay on the ground and their peak procedural travel speed is bounded at
2 metres/second. A hold preserves body position and head pose. A camera look turns the
head smoothly toward the current scene camera, reaching its direction at the step end.
Later holds preserve that head orientation; they do not continuously track a moving camera.
Wave raises and lowers the right arm while the body stays in place. Multiple walking
segments can change direction. Two simple actors may have independent timelines.

## Verification and limitations

Scene checks measure step start/end positions, stationary drift throughout nonwalking
steps, intermediate walking progress, and head/camera angular error at look endpoints.
They do not establish contact quality, collision avoidance, full natural-language
understanding, correct action assignment across actors, or artistic quality.

The preflight is a bounded English phrase/negation heuristic, not universal intent
recognition. Unknown requests still rely on Qwen reporting unmet requirements, and that
can fail. Known motion-presence checks catch omitted walking, waving, pauses and camera
looks, but do not prove every timing or negative instruction in the prompt was obeyed.

The fixed seven-bone character still has no knees or elbows, contact-aware IK, anatomical
head limits, arbitrary rig import or retargeting. Organic characters retain the previous
stationary idle/greeting workflow and do not yet support sequences. The environment
and geometry libraries remain procedural and bounded. JSON revisions rebuild a new
project; manual .blend edits are not imported into revisions.

Run unit tests with Blender's bundled Python and run scripts/test_sequences_blender.py
using background Blender. The latter checks three distinct sequence arrangements and
deliberately deletes head animation to verify that the checker detects the defect.
Existing scene, organic performance, and extension tests remain regression checks.

See [SEQUENCE_VALIDATION.md](SEQUENCE_VALIDATION.md) for actual live-run evidence,
including failures. Successful structural validation alone is not a prompt-fidelity score.
