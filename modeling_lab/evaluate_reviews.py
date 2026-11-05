"""Record numerical limits of the prompted review specimens, without retraining."""
import hashlib
import json
from pathlib import Path
import numpy as np
from modeling_lab.assets import prototypes, read_obj, teacher_weights
from modeling_lab.shape_model import CONTROL_NAMES, predict_vertices
from modeling_lab.train import metrics


def main():
    root = Path(__file__).resolve().parents[1]
    checkpoint = root / 'output/modeling-shape-v1/shape_weights.npz'
    before = hashlib.sha256(checkpoint.read_bytes()).hexdigest()
    templates = prototypes()
    _, _, faces, _, groups = read_obj()
    indices = np.unique([v for fi in groups['body'] for v in faces[fi]])
    reports = []
    for name in ('modeling-review-athletic-v2', 'modeling-review-older-v1'):
        job = root / 'output' / name
        spec = json.loads((job / 'spec.json').read_text())
        x = np.array([spec[k] for k in CONTROL_NAMES])
        predicted = predict_vertices(checkpoint, x)
        expected = (teacher_weights(x[None, :]) @ templates.reshape(36, -1)).reshape(-1, 3)
        measured = metrics(predicted[None, indices], expected[None, indices])
        reports.append({'job': name, 'controls': dict(zip(CONTROL_NAMES, x.tolist())),
                        'error_before_height_scaling': measured,
                        'outside_sampled_training_interval': bool(np.any((x < .05) | (x > .95))),
                        'note': 'Qwen selected endpoint controls; these extend beyond the sampled .05-.95 training interval. These figures are post-training probes, not part of the 256-case holdout.'})
    report = {'checkpoint_unchanged': hashlib.sha256(checkpoint.read_bytes()).hexdigest() == before,
              'checkpoint_sha256': before, 'specimens': reports}
    path = root / 'output/modeling-shape-v1/review_specimen_metrics.json'
    with path.open('x', encoding='utf-8') as file:
        json.dump(report, file, indent=2)
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
