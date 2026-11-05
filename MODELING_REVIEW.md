# Humanoid shape experiment: review and evidence

Review prepared 20 October 2026. Animation work remains paused.

## Review the actual outputs

| Specimen | Editable Blender project | Front | Side | Face | Actual saved skeleton |
|---|---|---|---|---|---|
| Athletic adult, 1.82 m | [Open project](output/modeling-review-athletic-v2/scene/humanoid.blend) | [Front](output/modeling-review-athletic-v2/scene/front.png) | [Profile](output/modeling-review-athletic-v2/scene/profile.png) | [Face](output/modeling-review-athletic-v2/scene/face.png) | [163-bone diagram](output/modeling-review-athletic-v2/scene/reopen_validation.svg) |
| Older, fuller-build adult, 1.65 m | [Open project](output/modeling-review-older-v1/scene/humanoid.blend) | [Front](output/modeling-review-older-v1/scene/front.png) | [Profile](output/modeling-review-older-v1/scene/profile.png) | [Face](output/modeling-review-older-v1/scene/face.png) | [163-bone diagram](output/modeling-review-older-v1/scene/reopen_validation.svg) |

These are bald humanoid anatomy studies, not finished realistic production characters.
The skin and eyes look mannequin-like. The graphite suit is a material mask on the body,
not learned clothing or a separate garment. There are no eyebrow/eyelash/hair grooms,
high-resolution skin textures, facial corrective shapes or artist-approved proportions.
The profile review also exposes a stage/background edge; these are diagnostic renders.

## What created them

1. Unchanged local **Qwen3:4b** translated each new prompt into body-shape controls.
2. The **trained 13,187-parameter shape network** predicted shape coefficients.
3. Its **fitted PCA decoder** converted those coefficients to mesh vertex coordinates.
4. Our Blender builder attached the inherited **MakeHuman CC0 topology, UVs, weights
   and 163-bone skeleton**, with joints fitted to predicted landmarks.
5. Blender added deterministic eye components, materials, review lighting and cameras.

The network learns variation within the source family. The source assets supply the
anatomy and rig. No Qwen weights or pretrained geometry-foundation-model weights were
fine-tuned, and the experiment does not train across multiple independent asset families.

The athletic v1 job contains the original [prompt](output/modeling-review-athletic-v1/request.json)
and [raw Qwen response](output/modeling-review-athletic-v1/planner_response.json). V2 reuses
that exact specification and checkpoint after fixing the jagged suit-material boundary.
No geometry training was repeated and the model response was not manually edited.
The older specimen has its own [prompt](output/modeling-review-older-v1/request.json) and
[raw response](output/modeling-review-older-v1/planner_response.json), with no repairs.

Qwen interpreted “fuller body build” as maximum mass and “older-adult” as the oldest
template endpoint. This may be stronger than the intended wording; semantic control
calibration remains a limitation. Both prompts selected some values at 0 or 1, outside
the randomly sampled training interval of 0.05–0.95.

## Training evidence and limits

The run used 48 CC0 adult morph files to construct 36 source shapes, then 2,048 synthetic
training combinations. A further 256 validation combinations selected the checkpoint;
256 test combinations were excluded from training and checkpoint selection.

| Comparison against synthetic source targets | Mean body-vertex error |
|---|---:|
| Untrained neural network | 27.40 mm |
| Constant mean shape | 22.70 mm |
| Trained network, withheld interpolation combinations | **0.352 mm** |
| Exact source interpolation | **0 mm by construction** |

The trained holdout maximum error was 7.15 mm. Separate post-training measurements on
the two displayed specimens found 0.446 mm mean / 1.859 mm maximum for the athletic
specimen, and 3.161 mm mean / 10.214 mm maximum for the older specimen. These measurements
precede the height-scaling postprocess. Endpoint accuracy is worse than interior
interpolation. The checkpoint remained unchanged throughout these evaluations.

This demonstrates actual weight training and bounded shape prediction. It does not
demonstrate improved realism, novel anatomical knowledge, generalization to unrelated
assets, or an advantage over the deterministic source generator.

- [Saved trained checkpoint](output/modeling-shape-v1/shape_weights.npz)
- [Training report, baselines, loss history and hashes](output/modeling-shape-v1/training_report.json)
- [Dataset and fixed split controls](output/modeling-shape-v1/dataset.npz)
- [Displayed-specimen error measurements](output/modeling-shape-v1/review_specimen_metrics.json)

## Blender verification

Both saved files were opened in fresh Blender processes. Each has:

- **163 bones** and a **13,380-vertex / 13,378-quad** editable body cage.
- **53,514 vertices at subdivision 1; 214,050 at subdivision 2**, verified on reload.
- Normalized skin weights and no unweighted body vertices.
- Successful construction-time deformation probes for shoulder, elbow, finger, hip,
  knee, neck and jaw. These are numerical probes, not animation clips.
- Successful in-memory finger posing and direct mesh-vertex editing after reopening.
- Embedded provenance and no animation actions. Input file hashes remained unchanged.

The reports are [athletic validation](output/modeling-review-athletic-v2/scene/validation.json),
[athletic reload/edit check](output/modeling-review-athletic-v2/scene/reopen_validation.json),
[older validation](output/modeling-review-older-v1/scene/validation.json), and
[older reload/edit check](output/modeling-review-older-v1/scene/reopen_validation.json).
The full Python suite passed **41 tests**, including backpropagation checked against
finite differences and checkpoint dependence. This does not prove all extreme poses
are good, avoid intersections or preserve anatomy. Artist acceptance is still pending.

## Recommendation

Keep the detailed master, clean deformation cage and common skeleton, with lighter
subdivision levels for interaction. Improve actual anatomy, materials and deformation
before adding more polygons or bones. Use the original source interpolation as a strong
production baseline; further training should earn its place by adding a capability or
quality improvement over that baseline.

The smallest useful next learning experiment is a carefully bounded reference-fitting
or corrective-deformation task with suitable permitted data and an independent test set.
Broader pretrained 3D-model adaptation remains a separate, unstarted undertaking.
See [MODELING.md](MODELING.md) for reproduction commands and the full model scope.
