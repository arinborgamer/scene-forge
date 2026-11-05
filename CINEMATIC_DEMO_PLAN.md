# Original alien-forest demo: two-month milestone

Prepared 28 October 2026. Target review: 28 December 2026, subject to the gates below.
This is a development milestone, not a scheduled background job or a promise of film-studio quality.

## Deliverable and ownership

Aim for an original 10–15 second sequence: an adult explorer in a luminous forest notices
a floating light, turns toward it and reaches out. One reusable character, one environment,
at most three shots. Deliver an editable `.blend`, preview MP4, source/configuration,
raw model instructions, model/data versions and a failure report. Avatar is the visual
reference for rich organic worlds; use original assets and no movie footage as training data.

Each component must say where it came from: trained model output, pretrained model output,
supplied asset, procedural construction, or manual artist work. An authored demonstration
does not count as evidence that a model learned anatomy or motion.

## Starting evidence

- The later typed-intent v2 run scored 48/56 exact (base 21/56) and 44/56 on older
  combined regressions. It failed the declared gate, including refusals/reduction wording
  and 127 rather than 128 actual updates. The corrective refinement01 run is active;
  its new scores are pending. See INTENT_REFINEMENT.md. No default changed.

- A small shape network predicts variations of supplied CC0 adult humanoid assets. The
  13,380-vertex control mesh and 163-bone skeleton are inherited; subdivision does not
  create learned detail. Source family and licenses are recorded in MODELING.md.
- Qwen3-0.6B adapters learn one structured Blender edit at a time. The 64-update contrast
  run scored 15/18 exact versus 4/18 for the previous adapter on its small synthetic suite.
  Three whole-object requests incorrectly changed scale; older CGI regression scored 24/24.
- The unchanged Qwen3:4b scene planner coordinates authored tools. Motion generation,
  reliable retargeting to the detailed humanoid, facial acting and general scene editing
  have not been established by those adapter scores.
- The balanced follow-up completed 64 updates: 23/32 exact versus 16/32 for its starting
  adapter, but 19/24 on older regression versus 22/24. It failed the declared gate and
  did not change the app default. Two precise fresh detailed-mesh edits passed; this
  does not resolve the nine differently phrased local edits that failed the new suite.
- A versioned explicit rig profile now exports observed bones/rest transforms and canonical
  joint mappings. Both supplied characters plus a renamed same-family fixture passed
  42 static deformation probes in total. This is preparation for retargeting, not a
  retargeting or motion-generation result; see RIG_PROFILES.md.
- Local budget is zero external spend: GTX 1650 4 GB, approximately 24 GB system RAM.
  Do not assume free remote GPUs will be available.

## Measurable work sequence

| Window | Work | Gate before moving on |
|---|---|---|
| Weeks 1–2 | Finish modeling adapter comparisons; cross axes, units and wording; retain prior scaling/CGI tasks; apply uncorrected predictions to supplied detailed meshes. | At least 90% exact on the frozen 32-case balanced suite, all outputs schema-valid, and at least 22/24 on existing CGI regression. Target mesh, rig, skin weights and the mesh's unrequested properties preserved in Blender. Report every failure. |
| Weeks 3–4 | Asset review and reusable rig interface: units, rest pose, joint mapping, mesh/rig IDs and dependencies. Establish an original character look and forest asset kit. | At least two supplied characters survive fresh import/edit/reopen and the shoulder, elbow, wrist, hip, knee, neck and jaw deformation probes. Human approval of front/profile/three-quarter anatomy and materials. |
| Weeks 5–6 | Resume animation work explicitly for this demo. Implement/validate reusable turn, reach and locomotion support on the selected detailed rig; preserve contacts and editable curves. | Three unseen action arrangements execute after restarting the app/Blender, with no source edits or manual scene repair. Frame-sampled checks and visual review identify foot sliding, self-intersection and framing failures. Missing capabilities produce clear failures. |
| Weeks 7–8 and final review | Integrate the accepted character, forest, camera, lighting and small effects. Render short previews and verify scene provenance and repeatability. | Generate the agreed short sequence plus two variations, save editable keyframes/rigs/materials, reopen in a clean Blender process, and complete artistic review. Keep preview/render costs measured. |

These are proposed gates, not current accomplishments. If the quality gate fails, reduce
shot count or action complexity with an explicit scope note; do not lower evaluation
thresholds to declare success. A 10-second accepted shot is more useful than a longer
sequence that needs undocumented repairs.

## Training protocol

Train in bounded experiments, not continuously for two months. Each run requires a
specific failure hypothesis, immutable data hashes, independent numerical checks,
Blender target verification, a saved baseline, changed-weight evidence and evaluation.
Retain the last accepted adapter. Never silently replace a model response with a corrected
operation. Test prompts must not enter the training split; older tests used to design a
curriculum become regression cases rather than untouched benchmarks.

The balanced curriculum addresses a discovered axis/unit/wording correlation and retains
24 local-scale plus 32 CGI examples. It teaches existing-element tool instructions; it
does not train high-resolution geometry, anatomy, motion, fluids or facial performance.
New capabilities require a representation/tool interface and licensed data before training.

## Work ownership and limits

Codex can perform bounded local work while a task is active. This file does not keep Codex
or the laptop training unattended until December. Long jobs need explicit launch, saved
logs and restart/recovery handling. No paid service, cloud account or recurring automation
is configured by this plan. Human visual review is required before calling the demo accepted.
