"""Meaningful checks for the isolated shape learner; no assets or Blender required."""
import tempfile
from pathlib import Path
import unittest
import numpy as np
from modeling_lab.assets import teacher_weights
from modeling_lab.shape_model import forward, gradients, validate_controls, predict_vertices
from modeling_lab.generate import validate_spec


class ShapeLearningTests(unittest.TestCase):
    def test_teacher_is_convex_and_matches_exact_corners(self):
        x = np.array([[0, 0, 0, 0], [1, 1, 1, 1], [.2, .7, .4, .9]])
        w = teacher_weights(x)
        np.testing.assert_allclose(w.sum(1), 1)
        self.assertTrue((w >= 0).all())
        self.assertEqual(w[0, 0], 1)
        self.assertEqual(w[1, -1], 1)

    def test_invalid_controls_rejected(self):
        for controls in ([0, 0, 0], [0, 0, 0, float('nan')], [0, 0, 0, 1.01]):
            with self.assertRaises(ValueError):
                validate_controls(controls)

    def test_backprop_agrees_with_finite_differences(self):
        rng = np.random.default_rng(9)
        p = {'w1': rng.normal(size=(4, 3)) * .2, 'b1': np.zeros(3),
             'w2': rng.normal(size=(3, 2)) * .2, 'b2': np.zeros(2),
             'w3': rng.normal(size=(2, 2)) * .2, 'b3': np.zeros(2)}
        x, y = rng.normal(size=(5, 4)), rng.normal(size=(5, 2))
        _, grad = gradients(x, y, p)
        for key in p:
            index = tuple(0 for _ in p[key].shape)
            value = p[key][index]
            p[key][index] = value + 1e-6
            high = np.mean((forward(x, p)[0] - y) ** 2)
            p[key][index] = value - 1e-6
            low = np.mean((forward(x, p)[0] - y) ** 2)
            p[key][index] = value
            self.assertAlmostEqual(grad[key][index], (high - low) / 2e-6, places=7)

    def test_checkpoint_inference_roundtrip_and_weight_dependence(self):
        p = {'format_version': np.array(1), 'w1': np.ones((4, 2)) * .1, 'b1': np.zeros(2),
             'w2': np.eye(2), 'b2': np.zeros(2), 'w3': np.eye(2), 'b3': np.zeros(2),
             'basis': np.arange(12).reshape(2, 6) * .01, 'mesh_mean': np.zeros(6),
             'latent_scale': np.ones(2), 'latent_mean': np.zeros(2)}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'model.npz'
            np.savez(path, **p)
            a = predict_vertices(path, [.8] * 4)
            np.testing.assert_allclose(a, predict_vertices(p, [.8] * 4))
            p['w3'] *= 0
            self.assertGreater(np.max(np.abs(a - predict_vertices(p, [.8] * 4))), .001)

    def test_unsupported_model_request_cannot_build(self):
        spec = dict(masculine=.5, adult_age=.3, muscle=.5, mass=.5, height_m=1.8,
                    unsupported_requests=['wings'])
        with self.assertRaisesRegex(ValueError, 'wings'):
            validate_spec(spec)
        spec['unsupported_requests'] = []
        self.assertEqual(validate_spec(spec), spec)
        spec['muscle'] = True
        with self.assertRaises(ValueError):
            validate_spec(spec)


if __name__ == '__main__':
    unittest.main()
