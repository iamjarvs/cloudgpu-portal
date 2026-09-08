"""Deterministic fake "compute provisioning" animation.

Step durations are randomized per environment (seeded by its uuid) but,
critically, progress is always *recomputed* from elapsed wall-clock time
against `fake_sim_started_at` rather than replayed via a stored per-step
timer — that's what makes it survive page reloads, extra browser tabs, and
process restarts without visibly resetting or skipping steps.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone

STEPS = [
    "Allocating bare-metal capacity",
    "Provisioning Kubernetes control plane",
    "Bootstrapping worker nodes & GPU drivers",
    "Configuring container runtime & storage",
    "Establishing tenant network fabric",
    "Finalizing",
]

# 6 steps * [3.2, 3.8] always lands the total between 19.2s and 22.8s —
# comfortably inside the requested 19-23s window regardless of per-step draw.
_MIN_STEP_SECONDS = 3.2
_MAX_STEP_SECONDS = 3.8


@dataclass
class ComputeProgress:
    current_step_index: int  # -1 once every step is done
    current_step_label: str | None
    completed_steps: list[str]
    total_duration_seconds: float
    elapsed_seconds: float
    done: bool


def _step_durations(seed: str) -> list[float]:
    rng = random.Random(seed)
    return [rng.uniform(_MIN_STEP_SECONDS, _MAX_STEP_SECONDS) for _ in STEPS]


def total_duration_seconds(seed: str) -> float:
    return sum(_step_durations(seed))


def progress_at(seed: str, started_at: datetime) -> ComputeProgress:
    durations = _step_durations(seed)
    total = sum(durations)
    elapsed = max(0.0, (datetime.now(timezone.utc) - started_at).total_seconds())

    if elapsed >= total:
        return ComputeProgress(-1, None, list(STEPS), total, total, True)

    acc = 0.0
    for i, dur in enumerate(durations):
        if elapsed < acc + dur:
            return ComputeProgress(i, STEPS[i], list(STEPS[:i]), total, elapsed, False)
        acc += dur

    return ComputeProgress(-1, None, list(STEPS), total, total, True)  # pragma: no cover - float rounding guard
