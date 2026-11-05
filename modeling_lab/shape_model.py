"""Trained neural controls-to-shape predictor with a fitted PCA mesh decoder.

Inference uses the checkpoint only, never the synthetic interpolation teacher.
Four controls: masculine-template blend, adult-age blend, muscularity, body mass.
The range describes this source asset family, not real-world measurements.
"""
from pathlib import Path
import numpy as np

CONTROL_NAMES = ("masculine", "adult_age", "muscle", "mass")


def validate_controls(controls):
    x = np.asarray(controls, dtype=np.float64)
    if x.shape != (4,) or not np.isfinite(x).all() or np.any((x < 0) | (x > 1)):
        raise ValueError("Four finite controls between 0 and 1 are required")
    return x


def forward(x, params):
    h1 = np.tanh(x @ params["w1"] + params["b1"])
    h2 = np.tanh(h1 @ params["w2"] + params["b2"])
    y = h2 @ params["w3"] + params["b3"]
    return y, (x, h1, h2)


def gradients(x, target, params):
    predicted, (_, h1, h2) = forward(x, params)
    error = predicted - target
    dy = 2 * error / error.size
    dh2 = (dy @ params["w3"].T) * (1 - h2 * h2)
    dh1 = (dh2 @ params["w2"].T) * (1 - h1 * h1)
    grads = {"w3": h2.T @ dy, "b3": dy.sum(0),
             "w2": h1.T @ dh2, "b2": dh2.sum(0),
             "w1": x.T @ dh1, "b1": dh1.sum(0)}
    return float(np.mean(error * error)), grads


def load_model(checkpoint):
    with np.load(Path(checkpoint), allow_pickle=False) as data:
        result = {k: data[k] for k in data.files}
    if int(result["format_version"]) != 1:
        raise ValueError("Unknown shape checkpoint version")
    return result


def predict_vertices(checkpoint, controls):
    model = load_model(checkpoint) if not isinstance(checkpoint, dict) else checkpoint
    x = validate_controls(controls)
    latent, _ = forward(x[None, :] * 2 - 1, model)
    coeff = latent[0] * model["latent_scale"] + model["latent_mean"]
    result = (model["mesh_mean"] + coeff @ model["basis"]).reshape(-1, 3)
    if not np.isfinite(result).all():
        raise ValueError("Non-finite mesh prediction")
    return result
