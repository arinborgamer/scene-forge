# Learned human-character and auto-rigging alternatives

Checked 28 October 2026 against primary sources. None of these reviewed learned
replacements currently provides a verified, free, commercially reusable, 4 GB Windows
route to the required character. Keep the supplied MPFB character and its inherited
163-bone rig while testing specialists. TripoSR's completed editable reconstructions
failed the face/hand quality target; denser extraction did not solve it. See
GEOMETRY_PROBE.md and MODELING.md. No models below were downloaded or run here.

## UniRig: strongest later rigging comparison

UniRig predicts a skeleton hierarchy and per-vertex skinning weights from an input
mesh. Its workflow exports FBX and merges the skinned result with the original mesh
into GLB. It supports variable joint count J, rather than guaranteeing the existing
163-bone human layout. The authors recommend editing inaccurate skeletons before
skinning. It cannot reconstruct missing facial or hand anatomy.
[Workflow and representation](https://github.com/VAST-AI-Research/UniRig/blob/6793c6640ff01c8fb389f3993434124bb43d2933/README.md).

Code is MIT; the official weights separately declare MIT. No SMPL/SMPL-X prerequisite
is documented. Articulation-XL skeleton weights are 1,439,617,174 bytes and skin weights
4,375,464,854 bytes: 5,815,082,028 combined, excluding dependencies. Both are public.
The smaller RigNet skeleton does not replace the complete two-stage model.
[Code license](https://github.com/VAST-AI-Research/UniRig/blob/6793c6640ff01c8fb389f3993434124bb43d2933/LICENSE),
[weight declaration](https://huggingface.co/VAST-AI/UniRig/blob/36842e2b5947e9e60f89275b83208c8e74071c63/README.md),
[checkpoint metadata](https://huggingface.co/api/models/VAST-AI/UniRig?blobs=true).

The repository requires at least 8 GB CUDA VRAM; the model card says more than 8 GB.
Inference configurations select GPU acceleration and BF16. Dependencies include
FlashAttention, spconv, PyG extensions and Blender's Python package. No supported CPU
or verified native-Windows/4 GB recipe was established.
[Inference configuration](https://github.com/VAST-AI-Research/UniRig/blob/6793c6640ff01c8fb389f3993434124bb43d2933/configs/task/quick_inference_unirig_skin.yaml),
[dependencies](https://github.com/VAST-AI-Research/UniRig/blob/6793c6640ff01c8fb389f3993434124bb43d2933/requirements.txt).

## RigAnything: editable output, incompatible commercial terms

RigAnything accepts OBJ/GLB and exports a rigged GLB containing geometry, skeleton and
skinning. Its default configuration has 64 joint slots, which is not equivalent to the
current 163-bone rig.
[Output documentation](https://github.com/Isabella98Liu/RigAnything/blob/d03cdb21dd134fa81df6b0947522469db3f78bd2/README.md),
[configuration](https://github.com/Isabella98Liu/RigAnything/blob/d03cdb21dd134fa81df6b0947522469db3f78bd2/config.yaml).

Both code and weights use Adobe's noncommercial research license, explicitly excluding
development of commercial products. Its public checkpoint is 2,344,595,770 bytes. No
SMPL prerequisite is documented; that does not remove the Adobe restriction.
[Code license](https://github.com/Isabella98Liu/RigAnything/blob/d03cdb21dd134fa81df6b0947522469db3f78bd2/LICENSE.md),
[weight license](https://huggingface.co/Isabellaliu/RigAnything/blob/30df7c0c390db1d5453c5af12da8d227c5025db6/LICENSE.md),
[file metadata](https://huggingface.co/api/models/Isabellaliu/RigAnything?blobs=true).

The inference entry point hardcodes cuda:0 and selects BF16. No numeric minimum VRAM
or demonstrated CPU/4 GB Windows path is supplied. Mesh simplification is neither a
memory guarantee nor an anatomy improvement.
[Inference source](https://github.com/Isabella98Liu/RigAnything/blob/d03cdb21dd134fa81df6b0947522469db3f78bd2/inference.py).

## LHM++: Gaussian representation and separately restricted assets

LHM++ is the current LHM successor. Its advertised PLY export contains 3D Gaussian
splats, not a textured triangle mesh with an ordinary Blender armature. The export
script supports PixelShuffle and SMPLX-FREE variants; their advertised Hugging Face
IDs returned anonymous-access errors, and the README says PixelShuffle weights are
pending. Their public availability was not verified.
[Release/export documentation](https://github.com/aigc3d/LHM-plusplus/blob/906b5d9fb967ab42efb92f6fa55bf22cac86b653/README.md),
[model registry](https://github.com/aigc3d/LHM-plusplus/blob/906b5d9fb967ab42efb92f6fa55bf22cac86b653/core/utils/model_card.py).

Root code is Apache-2.0, but weights have separate CC-BY-NC-4.0 terms; bundled SMPL-X
software and NVIDIA-derived components retain their own restrictions. SMPLX-FREE still
selects smplx_diffused_voxel and its renderer instantiates SMPL-X skinning. The variant
name does not establish absence of SMPL-X dependencies or unrestricted licensing.
[Weight license](https://github.com/aigc3d/LHM-plusplus/blob/906b5d9fb967ab42efb92f6fa55bf22cac86b653/LICENSE_WEIGHT),
[variant configuration](https://github.com/aigc3d/LHM-plusplus/blob/906b5d9fb967ab42efb92f6fa55bf22cac86b653/configs/train/LHMPP-anyview-SMPLX-FREE.yaml),
[renderer](https://github.com/aigc3d/LHM-plusplus/blob/906b5d9fb967ab42efb92f6fa55bf22cac86b653/core/models/rendering/base_gs_render.py).

The accessible standard checkpoint is 4,527,981,124 bytes. The prior repository totals
7,669,138,548 bytes and includes SMPL/SMPL-X/MANO/FLAME assets. Public mirror access does
not grant commercial rights. Official SMPL-X downloads require registration and its
license separately restricts commercial products/services/artifacts. The body model
documents 10,475 vertices and 54 articulated joints.
[Checkpoint metadata](https://huggingface.co/api/models/3DAIGC/LHMPP-700M?blobs=true),
[prior metadata](https://huggingface.co/api/models/3DAIGC/LHMPP-Prior?blobs=true),
[SMPL-X documentation](https://github.com/vchoutas/smplx),
[official license](https://smpl-x.is.tue.mpg.de/modellicense.html).

LHM++ documents an 8 GB application requirement and Python3.10/Torch2.3/CUDA12.1 with
compiled CUDA dependencies. CPU and 4 GB compatibility remain unverified.

The smallest practical character step is improving and testing an original variant
from existing licensed assets, preserving the rig and measuring face/finger/shoulder/hip
deformation. Reserve UniRig for a later comparison on verified suitable compute. Neither
auto-rigging nor increased polygon count substitutes for correct source anatomy.
