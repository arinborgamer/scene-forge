"""Small CPU training run with fixed splits, saved weights and held-out evaluation."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time

os.environ.setdefault("OPENBLAS_NUM_THREADS", "2")
import numpy as np
from .assets import ASSETS, REVISION, prototypes, teacher_weights, read_obj
from .shape_model import CONTROL_NAMES, forward, gradients, predict_vertices


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def metrics(predicted, reference):
    errors = np.linalg.norm(predicted - reference, axis=-1) * 1000
    return {"mean_vertex_error_mm": float(errors.mean()), "p95_vertex_error_mm": float(np.percentile(errors, 95)),
            "max_vertex_error_mm": float(errors.max())}


def train(output, steps=5000):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    start = time.perf_counter()
    meshes = prototypes()
    flat = meshes.reshape(len(meshes), -1)
    mean = flat.mean(axis=0)
    centered = flat - mean
    eig, vectors = np.linalg.eigh(centered @ centered.T)
    keep = np.flatnonzero(eig > eig.max() * 1e-9)[::-1]
    basis = (vectors[:, keep].T @ centered) / np.sqrt(eig[keep, None])
    prototype_latent = centered @ basis.T
    rng = np.random.default_rng(4627)
    # Fixed non-overlapping random control combinations. All share the same source
    # topology and 36 templates: this is an interpolation test, not unseen-person data.
    controls = rng.uniform(.05, .95, size=(2560, 4))
    train_x, val_x, test_x = controls[:2048], controls[2048:2304], controls[2304:]
    raw_y = teacher_weights(controls) @ prototype_latent
    latent_mean = raw_y[:2048].mean(0)
    latent_scale = raw_y[:2048].std(0)
    latent_scale = np.maximum(latent_scale, latent_scale.max() * .04)
    normalized_y = (raw_y - latent_mean) / latent_scale
    train_y, val_y = normalized_y[:2048], normalized_y[2048:2304]
    np.savez_compressed(output / "dataset.npz", train_controls=train_x, validation_controls=val_x,
                        test_controls=test_x, train_latent=raw_y[:2048], validation_latent=raw_y[2048:2304],
                        test_latent=raw_y[2304:], prototype_controls=np.asarray(__import__("modeling_lab.assets", fromlist=["COMBINATIONS"]).COMBINATIONS))
    n = len(keep)
    params = {"w1": rng.normal(0, np.sqrt(1 / 4), (4, 96)), "b1": np.zeros(96),
              "w2": rng.normal(0, np.sqrt(1 / 96), (96, 96)), "b2": np.zeros(96),
              "w3": rng.normal(0, np.sqrt(1 / 96), (96, n)), "b3": np.zeros(n)}
    initial = {k: v.copy() for k, v in params.items()}
    first = {k: np.zeros_like(v) for k, v in params.items()}
    second = {k: np.zeros_like(v) for k, v in params.items()}
    best, best_step, best_loss = None, 0, float("inf")
    history = []
    for step in range(1, steps + 1):
        batch = rng.integers(0, len(train_x), size=128)
        loss, grad = gradients(train_x[batch] * 2 - 1, train_y[batch], params)
        lr = .002 if step < steps * .75 else .0006
        for key in params:
            first[key] = .9 * first[key] + .1 * grad[key]
            second[key] = .999 * second[key] + .001 * grad[key] ** 2
            params[key] -= lr * (first[key] / (1 - .9 ** step)) / (np.sqrt(second[key] / (1 - .999 ** step)) + 1e-8)
        if step % 250 == 0 or step == 1:
            val_pred, _ = forward(val_x * 2 - 1, params)
            val_loss = float(np.mean((val_pred - val_y) ** 2))
            record = {"step": step, "batch_loss": loss, "validation_loss": val_loss}
            history.append(record)
            print(json.dumps(record), flush=True)
            if val_loss < best_loss:
                best_loss, best_step = val_loss, step
                best = {k: v.copy() for k, v in params.items()}
    decoder = {"format_version": np.array(1), "basis": basis, "mesh_mean": mean,
               "latent_scale": latent_scale, "latent_mean": latent_mean}
    model = {**best, **decoder}
    np.savez_compressed(output / "shape_weights.npz", **model)
    np.savez_compressed(output / "untrained_weights.npz", **initial, **decoder)
    # Evaluate once after model selection. The test values never influence updates
    # or checkpoint selection. Template interpolation remains an exact, free baseline.
    body_faces = read_obj()[4]["body"]
    faces = read_obj()[2]
    body = np.unique([v for f in body_faces for v in faces[f]])
    teacher = (teacher_weights(test_x) @ flat).reshape(-1, meshes.shape[1], 3)[:, body]
    predicted = np.asarray([predict_vertices(model, x)[body] for x in test_x])
    untrained = np.asarray([predict_vertices({**initial, **decoder}, x)[body] for x in test_x])
    constant = np.repeat((mean + latent_mean @ basis).reshape(1, -1, 3)[:, body], len(test_x), axis=0)
    trained_metrics = metrics(predicted, teacher)
    report = {"experiment": "adult humanoid shape interpolation, CPU NumPy MLP plus fitted PCA decoder",
              "source_revision": REVISION, "asset_manifest_sha256": digest(ASSETS / "manifest.json"),
              "source_templates": 36, "source_morph_files": 48, "control_names": CONTROL_NAMES,
              "split_seed": 4627, "training_examples": 2048, "validation_examples": 256, "test_examples": 256,
              "steps": steps, "selected_step": best_step, "latent_dimensions": n,
              "trainable_neural_parameters": sum(v.size for v in best.values()),
              "decoder": "PCA fitted to the 36 shared source templates; not learned anatomy from scans",
              "trained": trained_metrics, "untrained": metrics(untrained, teacher), "constant_mean": metrics(constant, teacher),
              "exact_source_interpolation": {"mean_vertex_error_mm": 0.0, "note": "Teacher by construction; more accurate than learned approximation"},
              "weight_change_l2": float(np.sqrt(sum(np.sum((best[k] - initial[k]) ** 2) for k in best))),
              "dataset_sha256": digest(output / "dataset.npz"), "checkpoint_sha256": digest(output / "shape_weights.npz"),
              "history": history, "elapsed_seconds": time.perf_counter() - start,
              "limitations": ["Same source family in all splits; no evidence of generalizing to unrelated meshes or human scans",
                              "Synthetic interpolation supervision, not artist-rated realism",
                              "No Qwen weights changed; no pretrained geometry foundation model fine-tuned",
                              "Topology, UVs, skeleton and skin weights are borrowed CC0 assets",
                              "No new sculpt detail, hair, clothing, textures or rigging learned",
                              "Neural approximation has no demonstrated advantage over exact source interpolation"],
              "numerical_gate_passed": bool(trained_metrics["mean_vertex_error_mm"] < 5 and trained_metrics["mean_vertex_error_mm"] < metrics(constant, teacher)["mean_vertex_error_mm"])}
    (output / "training_report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({"completed": str(output), "trained": trained_metrics, "numerical_gate_passed": report["numerical_gate_passed"]}), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", required=True)
    parser.add_argument("--steps", type=int, default=5000)
    args = parser.parse_args()
    if args.steps < 1:
        parser.error("steps must be positive")
    train(args.output, args.steps)
