# Local geometry specialist: CPU-first TripoSR probe

Research checked 28 October 2026 against primary sources. Target: Windows,
i5-9300H, 24 GB RAM and GTX 1650 4 GB. The separate Qwen job remains untouched.

TripoSR is the smallest practical candidate of these three. None has demonstrated
4 GB GPU feasibility on this laptop. Its official default configuration uses about
6 GB VRAM; the application explicitly accepts CPU inference, chunk size, extraction
resolution and OBJ/GLB output. [Pinned README](https://github.com/VAST-AI-Research/TripoSR/blob/107cefdc244c39106fa830359024f6a2f1c78871/README.md),
[inference code](https://github.com/VAST-AI-Research/TripoSR/blob/107cefdc244c39106fa830359024f6a2f1c78871/run.py).

| Candidate | Selected checkpoint | Access and practical constraint |
|---|---|---|
| TripoSR | 1,677,246,742 bytes | Ungated; CPU path; code and weights MIT |
| Stable Fast 3D | 4,024,289,892 bytes | Gated model access; approximately 6 GB default; experimental Windows support; custom commercial terms |
| Hunyuan3D-2mini | 3,819,958,234 bytes for standard mini FP16 file | Ungated metadata; upstream documents 6 GB shape generation; custom license |

These are selected checkpoint sizes, excluding dependencies and caches. First-party
metadata: [TripoSR](https://huggingface.co/api/models/stabilityai/TripoSR?blobs=true),
[SF3D](https://huggingface.co/api/models/stabilityai/stable-fast-3d?blobs=true),
[Hunyuan mini](https://huggingface.co/api/models/tencent/Hunyuan3D-2mini?blobs=true).

## Reproducible candidate

- TripoSR code: `107cefdc244c39106fa830359024f6a2f1c78871`.
- TripoSR model: `5b521936b01fbe1890f6f9baed0254ab6351c04a`.
- DINO config: `facebook/dino-vitb16`, revision
  `f205d5d8e640a89a2b8ef0369670dfc37cc07fc2`.

TripoSR downloads a 987-byte YAML and the checkpoint. Its tokenizer separately loads
only DINO's 454-byte config, creates the architecture, then receives weights from the
complete checkpoint; it does not download another DINO checkpoint. Selected model/config
downloads total 1,677,248,183 bytes. [Loader](https://github.com/VAST-AI-Research/TripoSR/blob/107cefdc244c39106fa830359024f6a2f1c78871/tsr/system.py),
[tokenizer](https://github.com/VAST-AI-Research/TripoSR/blob/107cefdc244c39106fa830359024f6a2f1c78871/tsr/models/tokenizers/image.py).

Use an isolated Python 3.11 environment. The upstream Transformers 4.35.0 pin requires
tokenizers >=0.14,<0.15; those releases lack Windows CPython 3.12 wheels, risking a Rust
source build in the current training environment. [Requirements](https://github.com/VAST-AI-Research/TripoSR/blob/107cefdc244c39106fa830359024f6a2f1c78871/requirements.txt),
[Transformers metadata](https://pypi.org/pypi/transformers/4.35.0/json),
[tokenizers wheel metadata](https://pypi.org/pypi/tokenizers/0.14.1/json).

The first isolated install exposed another real constraint: tokenizers 0.14.1 needs
huggingface-hub <0.18. The initial 0.25.2 pin was rejected by pip before installation.
The corrected environment uses hub 0.17.3 and tokenizers 0.14.1; failed logs remain
preserved. Downloads were prepared separately with the existing hub client, and inference
uses only verified local files. See `geometry_lab/requirements-cpu.txt`.

The native torchmcubes dependency needs a C++20 compiler and CMake >=3.24. Its CPU
backend and Windows CI exist, but a compatible compiler was not found in this shell.
[Build requirements](https://github.com/tatsy/torchmcubes/blob/a9ac95aa329957ba646e7bb057f825f5dfa77f38/README.md).
A small explicit scikit-image CPU marching-cubes adapter can avoid that native build.
Such a probe is an adapted pipeline, not an upstream-tested configuration. Check axes,
surface orientation and extraction on analytical fields before calling it equivalent.

Use an isolated foreground composited onto gray RGB at about 85% occupancy. Upstream's
`--no-remove-bg` converts directly to RGB, discarding alpha; preprocessing must composite
it first. The switch avoids rembg weight downloads, though rembg is still an imported
dependency. Smaller extraction chunks do not reduce transformer-stage memory.
[Exact preprocessing](https://github.com/VAST-AI-Research/TripoSR/blob/107cefdc244c39106fa830359024f6a2f1c78871/run.py).

## Licensing and alternatives

TripoSR explicitly releases both code and pretrained weights under MIT. Dependencies
retain their own terms; preserve notices. Native torchmcubes is MPL-2.0; xatlas is MIT.
[TripoSR license](https://github.com/VAST-AI-Research/TripoSR/blob/107cefdc244c39106fa830359024f6a2f1c78871/LICENSE),
[torchmcubes license](https://github.com/tatsy/torchmcubes/blob/a9ac95aa329957ba646e7bb057f825f5dfa77f38/LICENSE),
[xatlas license](https://pypi.org/project/xatlas/0.0.9/).

SF3D's repository license includes commercial registration, attribution and a revenue
threshold; its gated model license was not independently retrieved. Its code documents
`SF3D_USE_CPU=1`. [Repository](https://github.com/Stability-AI/stable-fast-3d/tree/ff21fc491b4dc5314bf6734c7c0dabd86b5f5bb2),
[license](https://github.com/Stability-AI/stable-fast-3d/blob/ff21fc491b4dc5314bf6734c7c0dabd86b5f5bb2/LICENSE.md).

Hunyuan exposes shape-pipeline CPU offloading, chunks and extraction resolution. Gradio's
`--low_vram_mode` only applies offloading to its texture worker; that flag alone does not
establish shape offloading. Its custom license excludes EU/UK/South Korea and restricts
training other models from outputs. [Pipeline](https://github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/f8db63096c8282cb27354314d896feba5ba6ff8a/hy3dgen/shapegen/pipelines.py),
[Gradio](https://github.com/Tencent-Hunyuan/Hunyuan3D-2/blob/f8db63096c8282cb27354314d896feba5ba6ff8a/gradio_app.py),
[license](https://huggingface.co/tencent/Hunyuan3D-2mini/blob/f90a0f7df7d5e6f71109cf333f6a95a0ae3194a6/LICENSE).

The proposed probe tests new static geometry from pretrained TripoSR weights, not
training our own geometry foundation model. Generated anatomy, topology, rigging and
animation remain unverified. Save raw mesh, input/provenance, editable Blender import,
fresh-process geometry-edit checks and a preview before asking for artistic review.
