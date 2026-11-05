"""Real CPU optimizers/scalers exercise the same budget loop as CUDA training."""
import json
import unittest

import torch

from modeling_training.optimizer_steps import train_updates


class OptimizerBudgetTests(unittest.TestCase):
    def exercise(self, *, overflow_attempts=(), updates=2, accumulate=2,
                 max_skipped=3, enabled=True, invalid_loss=False):
        parameter = torch.nn.Parameter(torch.tensor(1.0))
        optimizer = torch.optim.SGD([parameter], lr=.1)
        scaler = torch.amp.GradScaler('cpu', init_scale=8., growth_interval=100,
                                     enabled=enabled)
        attempts, checkpoints, seen, handles = [], [], [], []
        calls = 0

        def loss_for_batch(batch):
            nonlocal calls
            attempt = calls // accumulate + 1
            calls += 1
            seen.append(batch)
            if attempt in overflow_attempts:
                # Forward loss is finite; only its derivative overflows.
                handles.append(parameter.register_hook(lambda grad: grad * float('inf')))
            return parameter.square() * (float('nan') if invalid_loss else batch)

        # A one-shot hook is removed after each attempt, so the retry can recover.
        def record(value):
            attempts.append(value)
            for handle in handles:
                handle.remove()
            handles.clear()
            json.dumps(value, allow_nan=False)

        def checkpoint(value):
            checkpoints.append(value['step'])

        return parameter, attempts, checkpoints, seen, lambda: train_updates(
            parameters=[parameter], optimizer=optimizer, scaler=scaler,
            batches=[1., 2., 3.], loss_for_batch=loss_for_batch,
            updates=updates, accumulate=accumulate, max_skipped=max_skipped,
            seed=73, record=record, checkpoint=checkpoint)

    def test_successful_updates_are_the_budget(self):
        parameter, attempts, checkpoints, _, run = self.exercise()
        summary = run()
        self.assertEqual(summary['successful_optimizer_steps'], 2)
        self.assertEqual(summary['optimizer_attempts'], 2)
        self.assertEqual(checkpoints, [1, 2])
        self.assertLess(parameter.item(), 1.)
        self.assertTrue(all(r['optimizer_updated'] for r in attempts))

    def test_overflow_retries_exact_pending_batch_and_does_not_checkpoint(self):
        parameter, attempts, checkpoints, seen, run = self.exercise(overflow_attempts={1})
        summary = run()
        self.assertEqual(summary['successful_optimizer_steps'], 2)
        self.assertEqual(summary['optimizer_attempts'], 3)
        self.assertEqual(summary['skipped_optimizer_steps'], 1)
        self.assertEqual(seen[:2], seen[2:4])
        self.assertEqual(attempts[0]['batch_indices'], attempts[1]['batch_indices'])
        self.assertFalse(attempts[0]['optimizer_updated'])
        self.assertIsNone(attempts[0]['gradient_norm'])
        self.assertLess(attempts[0]['loss_scale_after'], attempts[0]['loss_scale_before'])
        self.assertEqual(checkpoints, [1, 2])
        self.assertTrue(torch.isfinite(parameter))

    def test_overflow_budget_fails_closed(self):
        parameter, attempts, checkpoints, _, run = self.exercise(
            overflow_attempts={1, 2}, max_skipped=1)
        with self.assertRaisesRegex(RuntimeError, 'overflow budget'):
            run()
        self.assertEqual(len(attempts), 2)
        self.assertEqual(checkpoints, [])
        self.assertEqual(parameter.item(), 1.)

    def test_nonfinite_loss_stops_before_optimizer(self):
        parameter, attempts, checkpoints, _, run = self.exercise(invalid_loss=True)
        with self.assertRaisesRegex(RuntimeError, 'Nonfinite training loss'):
            run()
        self.assertEqual(parameter.item(), 1.)
        self.assertEqual(checkpoints, [])

    def test_disabled_scaler_cannot_apply_nonfinite_gradients(self):
        parameter, _, checkpoints, _, run = self.exercise(
            overflow_attempts={1}, enabled=False)
        with self.assertRaisesRegex(RuntimeError, 'Nonfinite gradients'):
            run()
        self.assertEqual(parameter.item(), 1.)
        self.assertEqual(checkpoints, [])

    def test_budget_arguments_and_finite_initial_weights(self):
        parameter = torch.nn.Parameter(torch.tensor(float('nan')))
        optimizer = torch.optim.SGD([parameter], lr=.1)
        kwargs = dict(parameters=[parameter], optimizer=optimizer,
                      scaler=torch.amp.GradScaler('cpu'), batches=[1],
                      loss_for_batch=lambda _: parameter.square(), updates=1,
                      accumulate=1, max_skipped=0)
        with self.assertRaisesRegex(RuntimeError, 'Nonfinite trainable weights'):
            train_updates(**kwargs)
        parameter.data.fill_(1.)
        for key in ('updates', 'accumulate'):
            with self.assertRaises(ValueError):
                train_updates(**{**kwargs, key: 0})
        with self.assertRaises(ValueError):
            train_updates(**{**kwargs, 'max_skipped': -1})

    def test_scale_growth_counts_one_update_per_optimizer_call(self):
        parameter = torch.nn.Parameter(torch.tensor(1.))
        optimizer = torch.optim.SGD([parameter], lr=.1)
        scaler = torch.amp.GradScaler('cpu', init_scale=8., growth_interval=1)
        records = []
        result = train_updates(parameters=[parameter], optimizer=optimizer, scaler=scaler,
                               batches=[1], loss_for_batch=lambda _: parameter.square(),
                               updates=2, accumulate=1, record=records.append)
        self.assertEqual(result['successful_optimizer_steps'], 2)
        self.assertEqual([r['loss_scale_after'] for r in records], [16., 32.])

    def test_nonfinite_updated_weights_are_not_logged_as_success_or_checkpointed(self):
        parameter = torch.nn.Parameter(torch.tensor(1.))
        optimizer = torch.optim.SGD([parameter], lr=.1)
        def corrupt(*_):
            parameter.data.fill_(float('inf'))
        hook = optimizer.register_step_post_hook(corrupt)
        records, checkpoints = [], []
        try:
            with self.assertRaisesRegex(RuntimeError, 'Nonfinite trainable weights'):
                train_updates(parameters=[parameter], optimizer=optimizer,
                              scaler=torch.amp.GradScaler('cpu'), batches=[1],
                              loss_for_batch=lambda _: parameter.square(), updates=1, accumulate=1,
                              record=records.append, checkpoint=checkpoints.append)
        finally:
            hook.remove()
        self.assertEqual(records, [])
        self.assertEqual(checkpoints, [])
        self.assertIsNone(parameter.grad)

    def test_callback_errors_propagate_and_remove_hook_and_gradients(self):
        parameter = torch.nn.Parameter(torch.tensor(1.))
        optimizer = torch.optim.SGD([parameter], lr=.1)
        prior_hooks = len(optimizer._optimizer_step_post_hooks)
        def fail(_):
            raise OSError('Cannot persist training evidence')
        with self.assertRaisesRegex(OSError, 'Cannot persist'):
            train_updates(parameters=[parameter], optimizer=optimizer,
                          scaler=torch.amp.GradScaler('cpu'), batches=[1],
                          loss_for_batch=lambda _: parameter.square(), updates=1, accumulate=1,
                          record=fail)
        self.assertEqual(len(optimizer._optimizer_step_post_hooks), prior_hooks)
        self.assertIsNone(parameter.grad)


if __name__ == '__main__':
    unittest.main()
