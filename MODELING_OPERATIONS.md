# Qwen modeling operations: baseline before fine-tuning

The baseline described here remains available with unchanged Ollama models. A separate
small Qwen3-0.6B adapter has since been trained for single operations; see
[QWEN_TRAINING.md](QWEN_TRAINING.md) for its measured gains and substantial limitations.

This is a separate experimental route from the four-control humanoid shape predictor.
It uses unchanged local Qwen3:4b to propose actual mesh-building and editing operations.
It does not use that small network, load a humanoid template when starting empty, or
train Qwen during generation. Existing detailed .blend files can be supplied explicitly
for editing. No animations are generated.

## What Qwen controls

Qwen chooses the objects, operation order, explicit vertex/face lists, loft cross
sections, primitive dimensions, locations, materials, modifiers and local deformation
regions. The executor implements those generic Blender operations. It has no bust,
head, character, garment or prop recipes and does not contain the evaluation prompts.

The language currently supports:

- `mesh`: explicit vertex coordinates and polygon index lists.
- `loft`: a sequence of elliptical cross sections, joined into a capped surface.
- `primitive`: a box, ellipsoid or cylinder with full dimensions and orientation.
- `modifier`: bevel, subdivision or solidify; modifiers remain editable.
- `material`: a simple Principled material.
- `duplicate`: an independent mesh copy.
- `transform`: relative whole-object movement, scaling and rotation.
- `deform`: smooth proportional editing within an ellipsoid, in object-local coordinates.

This is genuine **model-selected geometry construction/editing**, but it remains a
bounded tool-use system. The deterministic kernel performs meshing and Blender supplies
the modeling algorithms. It is not neural sculpt-detail synthesis, unrestricted Python,
learned rigging, automatic retopology, or a guarantee of professional anatomy.

The implementation uses Blender's [mesh API](https://docs.blender.org/api/5.1/bpy.types.Mesh.html)
and [BMesh normal recalculation](https://docs.blender.org/api/5.0/bmesh.html). Qwen outputs
data; its response is never executed as Python or passed to a shell.

## Run it

Start the installed Ollama application first. From the project root in PowerShell:

Wait until Ollama responds to `http://127.0.0.1:11434/api/tags` before submitting a
job. Its initial GPU discovery can exceed the CLI's 10-second readiness check.

```powershell
$py = 'C:\Program Files\Blender Foundation\Blender 5.1\5.1\python\bin\python.exe'

# Start empty: Qwen chooses a construction sequence.
& $py -B -m modeling_lab.operate `
  --prompt 'Build a small stylized mechanical object with an asymmetric silhouette.' `
  --output output/my-modeling-request --render

# Edit a saved result; input .blend is never saved over.
& $py -B -m modeling_lab.operate `
  --input output/my-modeling-request/scene/model.blend `
  --prompt 'Make the main body wider while preserving the smaller parts.' `
  --output output/my-modeling-revision --render

# Limit editing access to a specific mesh in a detailed input file.
& $py -B -m modeling_lab.operate `
  --input output/modeling-review-athletic-v2/scene/humanoid.blend `
  --editable Humanoid_Trained_Shape `
  --prompt 'Make a subtle localized upper-chest width edit, preserving the head and legs.' `
  --output output/my-humanoid-edit --render
```

Output folders must be new. Input files are opened in a fresh background Blender process
with automatic script execution disabled. Source file hashes are checked afterward.
The executor does not expose file access, arbitrary code, bone editing or deletion to
the model. An optional `--editable` list limits existing meshes it can target.

Qwen sees object names, bounds, transforms, topology counts and material colors. It does
**not** see the rendered images, understand all of the source scene's semantics, or
receive the full mesh as text. This limits its visual judgment and anatomical precision.
Its unsupported-request reporting is also imperfect; strict schema validation cannot
prove that every part of a natural-language request was understood.

## Evidence saved per job

- `request.json`: actual prompt, input file and its hash.
- `inventory.json`: source scene information supplied to Qwen, when editing.
- `planner_context.json`: exact messages, schema, model metadata and executor source hashes.
- `planner_attempt_N.json`: every raw Qwen response, including failed attempts.
- `plan.json`: the validated operation list, with no manual corrections.
- `scene/execution.json`: operation trace, before/after mesh state and integrity checks.
- `scene/model.blend`: editable result, modifiers, materials and embedded provenance.
- `scene/*.png`: review renders when requested.
- `reopen.json`: fresh-start reload and in-memory vertex-edit check.
- `training_candidate.json`: a **pending, unapproved** training example, not a claim
  that training happened or that the asset passed artistic review.

At most one automatic schema-validation repair is allowed. Runtime execution failures
are retained as failures. No old demo is substituted. A completed job means execution
and reload succeeded; it does not imply request satisfaction or artistic quality.

Inference allows 1,200 seconds per attempt by default (`--model-timeout`, maximum 3,600).
This bounds the request, not its expected duration. Every job records its inference
options, timeout and code hashes. On the tested 4 GB GPU, a long construction plan may
take several minutes. Failed output folders remain intact; retry into a new folder.

Development retests after the first baseline use additional general tool instructions:
one creation operation per object, nondegenerate polygon geometry, explicit materials,
and scale versus translation. These are prompt changes, not trained model weights.
The original failed runs are retained. See `MODELING_OPERATIONS_REVIEW.md`.
The latest snapshot also supplies the full schema in the model's context and rejects
mathematically empty transforms/deformations before Blender runs. No-op plans can use
the same single validation-repair attempt; this adds no runtime or semantic repair loop.

## Evaluation protocol

`examples/modeling-operation-evaluation.json` contains three fixed prompts: a new
mechanical humanoid bust, a precise revision, and a bounded chest edit on an existing
detailed humanoid. These are evaluations, not examples supplied in Qwen's system prompt.
The generic executor was tested separately, then its source and evaluation files were
hashed before the live tests. Any changes after seeing model output must be disclosed.

`modeling_lab.evaluate_operations` checks concrete request properties independently of
the executor's structural success. It tests new-part presence, jaw taper, lens placement
and color, revision dimensions, preservation of unrelated parts, and local-edit boundaries.
Visual quality still requires inspection. Passing these cases does not establish broad
modeling reliability, realistic human creation from scratch or animation-ready anatomy.

## Where fine-tuning starts

This baseline tests what the unchanged model can already do and captures failures worth
addressing. Pending examples must be reviewed for request fidelity, asset rights and
visual/technical quality before use. Related assets and paraphrases must stay in the same
split. Keep an independent test set out of both prompting and training.

The next training run needs a sufficiently varied reviewed corpus, a verified adapter
training configuration that fits available compute, and a before/after comparison on the
same frozen tasks. A few attractive renders are not enough evidence. No Qwen adapter
weights are produced by this baseline; the earlier shape-network checkpoint is unrelated.
