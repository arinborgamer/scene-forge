"""Bounded mixed-precision updates. A skipped optimizer call never spends a step."""
import math
import random
import time

import torch


def require_finite_weights(parameters):
    if any(not torch.isfinite(p).all().item() for p in parameters):
        raise RuntimeError('Nonfinite trainable weights; refusing to save adapter')


def train_updates(*, parameters, optimizer, scaler, batches, loss_for_batch,
                  updates, accumulate, max_skipped=16, seed=22104,
                  record=None, checkpoint=None, peak_memory=None):
    """Retry the same microbatch indices after overflow, with fresh stochastic forwards.

    The optimizer's public post-step hook counts actual calls, independently of scale
    growth. Nonfinite losses/weights fail immediately. AMP gradient overflow consumes
    the explicit skip budget; no unbounded retry or silent data advance is allowed.
    """
    if (type(updates) is not int or not 1 <= updates <= 1000
            or type(accumulate) is not int or not 1 <= accumulate <= 8
            or type(max_skipped) is not int or not 0 <= max_skipped <= 64
            or not batches):
        raise ValueError('Training budget or batches out of bounds')
    parameters = list(parameters)
    if not parameters:
        raise ValueError('No trainable parameters')
    require_finite_weights(parameters)
    rng = random.Random(seed)
    order = list(range(len(batches)))
    rng.shuffle(order)
    cursor = successful = attempts = skipped = optimizer_calls = 0
    pending = None
    start = time.perf_counter()
    last = None

    def count_optimizer_call(*_):
        nonlocal optimizer_calls
        optimizer_calls += 1

    hook = optimizer.register_step_post_hook(count_optimizer_call)
    optimizer.zero_grad(set_to_none=True)
    try:
        while successful < updates:
            if pending is None:
                pending = []
                for _ in range(accumulate):
                    if cursor == len(order):
                        rng.shuffle(order)
                        cursor = 0
                    pending.append(order[cursor])
                    cursor += 1
            attempts += 1
            attempt_start = time.perf_counter()
            loss_sum = 0.
            for index in pending:
                loss = loss_for_batch(batches[index])
                if loss.ndim != 0 or not torch.isfinite(loss).item():
                    raise RuntimeError('Nonfinite training loss or nonscalar loss')
                loss_sum += loss.item() / accumulate
                scaler.scale(loss / accumulate).backward()
            scaler.unscale_(optimizer)
            gradients = [p.grad for p in parameters if p.grad is not None]
            if not gradients:
                raise RuntimeError('No gradients for trainable weights')
            finite = all(torch.isfinite(g).all().item() for g in gradients)
            norm = None
            if finite:
                norm = float(torch.nn.utils.clip_grad_norm_(parameters, 1., error_if_nonfinite=True))
            elif not scaler.is_enabled():
                raise RuntimeError('Nonfinite gradients without an enabled AMP scaler')
            old_scale = scaler.get_scale()
            if not math.isfinite(old_scale) or old_scale <= 0:
                raise RuntimeError('Invalid AMP loss scale')
            before_calls = optimizer_calls
            scaler.step(optimizer)
            scaler.update()
            new_scale = scaler.get_scale()
            updated = optimizer_calls == before_calls + 1
            if not math.isfinite(new_scale) or new_scale <= 0:
                raise RuntimeError('Invalid AMP loss scale after update')
            if updated != finite or updated != (new_scale >= old_scale):
                raise RuntimeError('AMP optimizer update accounting mismatch')
            successful += int(updated)
            skipped += int(not updated)
            require_finite_weights(parameters)
            optimizer.zero_grad(set_to_none=True)
            last = dict(step=successful, attempt=attempts, loss=loss_sum,
                        gradient_norm=norm, gradients_finite=finite,
                        optimizer_updated=updated, successful_optimizer_steps=successful,
                        skipped_optimizer_steps=skipped, batch_indices=list(pending),
                        loss_scale_before=old_scale, loss_scale_after=new_scale,
                        step_seconds=time.perf_counter() - attempt_start,
                        elapsed_seconds=time.perf_counter() - start)
            if peak_memory is not None:
                last['peak_allocated_mb'] = peak_memory()
            if record is not None:
                record(last)
            if skipped > max_skipped:
                raise RuntimeError('AMP overflow budget exhausted; training incomplete')
            if updated:
                if checkpoint is not None:
                    checkpoint(last)
                pending = None
    finally:
        optimizer.zero_grad(set_to_none=True)
        hook.remove()
    return dict(successful_optimizer_steps=successful, optimizer_attempts=attempts,
                skipped_optimizer_steps=skipped, training_seconds=last['elapsed_seconds'])
