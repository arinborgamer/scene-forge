# Local versus whole-object training experiment

Prepared 27 October 2026. The previous CGI adapter made two local/whole-object errors and one target-name error in recorded tests. Those observations motivated this curriculum; older tests must now be described as regression tests, not untouched benchmarks.

`modeling_training/contrast_corpus.py` generates paired requests with the same object, axis and displacement but different scope: local vertices with ellipsoid falloff versus whole-object translation. Names obey the existing operation schema (spaces are not supported). `output/qwen-contrast-corpus-v1` is a preserved empty failed attempt using unsupported names with spaces; it was never trained on.

Frozen corpus: `output/qwen-contrast-corpus-v2`. There are 128 training examples (96 contrast examples and 32 CGI controls), 12 validation examples and 18 test examples. All 158 expected operations passed Blender execution checks. Test wording and names are separate, but the small synthetic test shares operation families and numerical ranges. Original instruction pairs are used; no external teacher outputs or previous failed prompts are copied into training.

Planned run: warm-start `output/qwen-lora-vfx-v1/adapter`, 64 optimizer updates, accumulation 2, learning rate 0.0001. Preserve previous weights and compare unchanged base, previous adapter and new adapter under identical evaluation settings. Do not promote the new weights without checking CGI regression. Only a completed result plus changed saved weights proves training finished.

This experiment concerns structured instructions for existing objects. It does not learn realistic anatomy, new meshes, rigs, animation or cinematic performance.

## Completed evaluation, 28 October 2026

The run completed 64/64 optimizer updates in 861.9 seconds of training. Saved adapter
SHA-256: `54350593d9fe08ad0cf7521cc44c883b7c1a279adcf9404c8e23acd30c418189`.
On the 18-case test: unchanged base 1/18 exact, previous VFX adapter 4/18, new contrast
adapter 15/18. New schema validity is 16/18. All three errors are whole-object moves
with unwanted Z scaling; two violate the scale bounds. Low validation loss did not
prevent these failures.

The older CGI regression completed: unchanged base 6/24, contrast adapter 24/24 exact.
Per-case responses and hashes are in `output/qwen-contrast-regression-v1/`. The earlier
VFX adapter scored 22/24 on these same cases. This improvement does not erase the three
new-suite errors, and the contrast checkpoint has not replaced the app's default model.

The generator's axis/unit/wording correlation motivated the separate balanced experiment
in BALANCED_TRAINING.md. Original frozen files and weights remain in place.
