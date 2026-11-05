# Humanoid modeling experiment — separate from animation

Animation development is paused. This experiment is isolated in `modeling_lab/` and
does not replace the Scene Forge animation executor or its 0.4 extension ZIP.

## What was actually trained

A **13,187-parameter neural network** maps four body controls to a 35-dimensional
shape representation. A PCA decoder, fitted to 36 adult source shapes, converts that
representation to vertex coordinates. The learned weights and decoder are saved in
`output/modeling-shape-v1/shape_weights.npz`. Inference loads this checkpoint; it does
not call the training interpolation teacher.

This is a small supervised shape-interpolation experiment trained from scratch using
open 3D asset data. **It is not Qwen fine-tuning, not adaptation of pretrained 3D neural
weights, and not a general sculpting or text-to-3D foundation model.** Qwen remains
unchanged and translates supported prompts into the four shape controls plus height.
The saved decoder and neural weights then produce the mesh. Height scaling, scene
assembly and rig fitting are deterministic Blender operations.

The geometry's anatomical quality comes from the source assets. Training approximates
their variation; it does not invent the topology or improve their anatomical detail.

## Data and permissions

The corpus contains 48 adult morph-target files from **one** source family, MakeHuman
Community MPFB, combined into 36 source body shapes. Three supplied ancestry templates
are averaged equally; ethnicity is not an input or a predicted property. Only the young
adult and older adult categories are included. No child assets, personal photographs,
movie assets or user data are used.

Assets are pinned to MPFB commit `3af0cd5a2ffba072e93a34e5f6f494fdc4813ddf`.
The downloader verifies each file against its Git blob hash and records SHA-256,
source URL, size and license in `modeling_lab/data/<revision>/manifest.json`.
The initial download is approximately 10 MB, not a multi-gigabyte foundation model.

MPFB explicitly releases its graphical data, including meshes, morphs, rigs, weights
and UV data, under CC0. Its software has a separate GPL license; this experiment
downloads the listed assets and license documents, not upstream executable source.
Sources: [pinned asset license explanation](https://github.com/makehumancommunity/mpfb2/blob/3af0cd5a2ffba072e93a34e5f6f494fdc4813ddf/LICENSE.md),
[CC0 statement](https://github.com/makehumancommunity/mpfb2/blob/3af0cd5a2ffba072e93a34e5f6f494fdc4813ddf/LICENSE.ASSETS.md).

Adding unrelated open meshes to this dataset would require compatible licensing and
vertex correspondence/registration or a different model representation. Calling all
internet meshes “training data” would skip that essential work. This first run therefore
does **not** claim training across multiple independent asset libraries or AI models.

## Training and evaluation

All computation is local and free. Training used NumPy on the CPU, not GPU memory.
Architecture: 4 inputs → 96 tanh units → 96 tanh units → 35 shape coefficients; Adam,
5,000 steps, batch size 128. PCA supplies the fitted mesh representation.

Data splits are fixed by seed 4627: **2,048 synthetic training combinations, 256
validation combinations, 256 test combinations**. Checkpoints are selected on validation
loss; test combinations are scored afterward. All splits share the source family,
topology and source templates. This evaluates interpolation of withheld parameters,
not recognition of unseen people, unseen topology, or independently captured scans.

Measured error on body vertices before optional height scaling:

| Predictor | Mean vertex error against synthetic source target |
|---|---:|
| Randomly initialized network | 27.40 mm |
| Constant training-mean shape | 22.70 mm |
| Trained network | **0.352 mm** |
| Exact source interpolation (the teacher) | **0 mm, by construction** |

Trained 95th-percentile error is 0.831 mm; maximum is 7.150 mm. These are geometry
matching measurements, **not realism or animation-quality scores**. The report preserves
the loss history, changed-weight norm, checkpoint/dataset hashes and baseline results.
No advantage over exact source interpolation has been demonstrated. For production,
the source generator remains the stronger baseline until a learned method adds a
capability or quality improvement it cannot provide.

## Editable output and detail levels

The body has **13,380 control vertices and 13,378 quad faces**, inherited UVs and normalized
skin weights. The **163-bone inherited skeleton** includes fingers, toes and face bones.
Bone endpoints are fitted to joint landmarks in the predicted shape. Seven numerical
deformation probes exercise shoulder, elbow, finger, hip, knee, neck and jaw movement.
These probes return the rig to rest; no animation clips or keyframes are added.

The non-destructive subdivision modifier gives a 53,514-vertex mesh at level 1 and
214,050 vertices at level 2, both verified after reopening the saved file. Set it to
zero to use the lighter editable cage.
These are detail levels of the same topology and skeleton. Extra subdivision adds
smoothness, not newly learned anatomy. The current rig is a deformation skeleton,
not a finished animator-facing control rig with IK and corrective poses.

The model is a bald anatomy study. Skin shading and the fitted graphite body-suit
material are procedural, not learned. The suit is a material region, not a separate
garment. Eye components are procedural meshes. There are no photoreal skin maps,
hair groom, corrective blendshapes or guaranteed collision-free poses.

## Reproduce or generate another model

Run from the project folder in PowerShell using Blender's Python, which includes NumPy.
Every output directory must be new: the tools refuse to overwrite an existing run.

```powershell
$py = 'C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe'
$env:OPENBLAS_NUM_THREADS = '2'
$env:PYTHONDONTWRITEBYTECODE = '1'

# Fetch/verify the same CC0 assets (already downloaded for this run).
& $py -B -m modeling_lab.assets

# Train a separate checkpoint; no downloads or paid service is invoked here.
& $py -B -m modeling_lab.train --output output/my-shape-training --steps 5000

# Start your installed Ollama application first. Qwen3:4b must already be installed.
& $py -B -m modeling_lab.generate `
  --prompt 'An adult masculine humanoid anatomy study, athletic and moderately lean, height 1.82 m, with the standard study suit and full skeleton.' `
  --checkpoint output/modeling-shape-v1/shape_weights.npz `
  --output output/my-humanoid-review

# Rebuild a saved control specification without Qwen.
& $py -B -m modeling_lab.generate `
  --spec output/modeling-review-athletic-v1/spec.json `
  --checkpoint output/modeling-shape-v1/shape_weights.npz `
  --output output/my-humanoid-rebuild --no-render
```

The prompt route records the exact prompt, Qwen system instructions, raw Qwen response,
control specification, checkpoint hash, Blender log, validation and editable project.
It fails if the planner reports an unsupported feature; it does not substitute an old
animation demo. Unreported unsupported language can still slip through Qwen: this is
not complete semantic verification. No automatic model-response repair is used here.

## Practical next direction

Review anatomy, silhouette, hands, face and deformation before accepting this asset.
Keep a good master mesh, a clean deformation cage and a consistent skeleton, then derive
lighter versions. A dense mesh and a large bone count alone do not establish quality.

The next useful learning task should beat a strong deterministic baseline—for example,
fitting body/face controls to permitted reference images, learning corrective deformations,
or learning detail from registered high-quality scans. Each needs its own suitable data
and held-out evaluation. Larger pretrained geometry-model fine-tuning remains unstarted;
it needs a selected compatible model, licensed data and verified compute. This small
checkpoint is a concrete local training experiment, not a substitute for that work.
