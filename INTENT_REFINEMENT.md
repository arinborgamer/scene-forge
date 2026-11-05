# Corrective intent experiment — 28 October 2026

## Observed result and decision

The completed v2 run improved exact matches from 21/56 to 48/56, with 51/56 valid
outputs. Both local and whole translations passed 18/18. Local scaling was 3/6,
unsupported requests 1/6, and CGI controls 8/8. Older regressions were 22/32 modeling
and 22/24 CGI. One of four look-development requests copied the wrong glare-node
name, so no repaired CGI fixture was rendered. Two detailed-mesh edits and both
post-edit rig checks passed. The combined acceptance result is false.

V2 made 127 successful updates in 128 attempts. Its checkpoint and all responses are
preserved; its strict update gate remains rejected. No application default changed.

## Error categories and hypothesis

- Nine older whole-object prompts copied an imperative verb into the target name.
- Three reduction prompts copied an unsigned magnitude rather than a negative change.
- Five unsupported requests used invalid categories or proposed a partial edit.
- Three older camera requests were incorrectly refused; one glare request lost part
  of its target name.

Hypothesis: explicit sign contrasts, varied imperative/name boundaries, substantially
more refusal examples, and replay of supported controls improve these categories
without losing correct local/whole scope. No compiler prompt heuristics, output repair,
or test-target injection will be used to create that improvement.

## Data and training contract, fixed before the new run

`modeling_training.intent_refinement` selects 80 training-only replay examples from
the frozen v2 corpus and adds 112 original authored examples: 40 refusals, 24 signed
local scales, 24 whole-object names and 24 CGI controls. Total: 192 training examples.
Validation (26) and primary test (56) bytes remain identical to v2. Failed test prompts
are not copied into training; the correction design is informed by their categories.
These are development regressions, not untouched evidence of generalization.

A separate 20-prompt authored challenge is frozen under `output/qwen-intent-challenge-v1/`
before this run. It has different wording/names but shares the schema and author, so
it is still a limited synthetic check. Additional acceptance requires 20/20 valid,
at least 18/20 exact, and all five unsupported requests correctly refused. The same
unchanged base can host both adapters to compare v2 and the candidate on these prompts.
The examples/schema are AI-assisted authored project templates, with executable target
checks in Blender. They have not undergone independent human labeling or customer review.
The frozen challenge manifest's phrase "human-authored" is inaccurate; an additive
provenance note records the correction without altering its frozen cases or source snapshot.

The first corpus-generation attempt under `output/qwen-intent-corpus-v3/` failed while
writing source snapshots, before training. Its partial files are preserved. The fixed
generator writes `output/qwen-intent-corpus-v4/`, with source snapshots and Blender
checks before use. All data is original synthetic text, with no external model outputs
or movie assets. Anatomy and rigs remain supplied, not learned by this adapter.

Planned run: `refinement01`, warm-start v2 adapter, 96 successful optimizer updates,
accumulation 2, learning rate 0.0001, fresh optimizer, seed 22104. This is one pass over
192 shuffled examples plus explicitly recorded overflow retries; dropout is resampled
on retry. Maximum 16 skipped updates; exceeding that budget stops the run. Weight
checksums and actual-call counts must match the saved evidence. No exact optimizer
resume is claimed.

The unchanged gates in `INTENT_TRAINING.md` apply, including 51/56 exact, all outputs
valid, 6/6 refusals, 5/6 scales, 29/32 older modeling and 22/24 older CGI. Mesh, rig,
four-control CGI and fresh-reopen checks remain necessary. No default changes occur
automatically, and passing numeric gates still requires visual review.

## Trainer repair and verification

`optimizer_steps.py` counts actual optimizer post-step calls, retries the same pending
microbatch indices after AMP overflow, bounds skips, rejects nonfinite losses/weights,
and writes strict JSON (nonfinite gradient norms become null). Checkpoints happen only
after a successful finite update. The CPU test suite uses real PyTorch GradScaler and
optimizers to cover skips, scale growth, retry exhaustion, corrupt updated weights,
callback failures and cleanup. CUDA evidence is established only by the next actual run.

Every new run snapshots the training module files and hashes local warm-start weights.
Previous experiments and their source snapshots are unchanged.

`modeling_training.run_audit` independently checks update/skip counters, retry batches,
the exact one-pass exposure, frozen dataset/source hashes, warm-start preservation and
finite saved tensors on CPU. Its integrity result is separate from accuracy/visual gates.

## Completed refinement01 result

Training and every downstream stage completed. Independent audit: 96 successful updates
in 97 attempts, one overflow retried on identical microbatches, all 192 training rows
used once, all 112 tensors finite and changed. Training took 1,276.15 seconds; adapter
SHA-256 `878176f038d1c03cf89bb11e3a0ea7adf28e73a7b8cdacc25effb4bd83bbc790`.

- Primary: **53/56 exact, 56/56 valid**, compared with v2 48/56 and base 21/56.
  Remaining errors are all three worded reductions, emitted as positive scaling.
- Older regression: **23/32 modeling, 24/24 CGI**. Whole-object name extraction on
  differently phrased commands still fails; aggregate improvement is insufficient.
- Newly frozen challenge: **17/20 exact, 19/20 valid**, compared with v2 15/20.
  Two contractions have the wrong sign; one glow request remains invalid.
- Both precise detailed-mesh edits, all post-edit rig checks, four CGI controls and
  the saved CGI fixture's fresh-process editable-file check passed.

Final acceptance is **false**. Scales, old modeling and the fresh challenge fail their
predeclared gates. No defaults changed. This is a measured language/control improvement,
not learned geometry or a production-ready model. Next experiment should expose actual
scene targets in the request and separate increase/decrease from unsigned magnitude;
avoid silently correcting invalid names or signs after generation.

## Reproduce

Prepare a unique corpus, verify it using `scripts/verify_training_corpus_blender.py`,
then run the existing wrapper:

```powershell
.\scripts\run_intent_experiment.ps1 -Name refinement01 -Data output/qwen-intent-corpus-v4 -InitialAdapter output/qwen-lora-intent-v2/adapter -Steps 96 -LearningRate 0.0001 -ChallengeCases output/qwen-intent-challenge-v1/cases.json
```

The wrapper refuses reused output paths and concurrent model jobs. Read its saved
`output/qwen-intent-refinement01-final/result.json` before making any quality claim.
