"""
Empirically-optimized PD controller brain for HTI damping validation experiment.

VALIDATION OUTCOME: Deep analysis prediction REVISED by empirical findings

Original Hypothesis (Investigation 2):
- Critical damping (ζ=1.0) would yield 2-3x speedup
- Formula: Kd_optimal = 2√Kp - b_plant ≈ 5.56 for Kp=8.0

Empirical Grid Search Results:
- Tested Kd range: [0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.5, 5.0, 5.56, 6.0, 7.0]
- Empirical optimum: Kd=3.50 (ζ≈0.636) → 302 ticks (1.51x speedup)
- Critical damping: Kd=5.56 (ζ=1.0) → 486 ticks (0.94x slowdown!)
- Baseline nominal: Kd=2.0 (ζ≈0.37) → 455 ticks

KEY INSIGHT: Under-damping (ζ≈0.636) beats critical damping (ζ=1.0) for this task
- Under-damped: faster response, acceptable overshoot (Shield clips excess)
- Critical damped: slower response, no overshoot (unnecessary constraint)
- Over-damped: even slower

This validates the investigation methodology while refining the specific findings.
"""

from __future__ import annotations

from dataclasses import dataclass
from .arm_pd_controller import ArmPDControllerBrain


@dataclass
class ArmOptimalPDBrain(ArmPDControllerBrain):
    """
    Empirically-optimized PD controller (ζ≈0.636) from validation experiment.

    Tuned via grid search over Kd ∈ [0.5, 7.0] with Kp=8.0 fixed:
    - Damping ratio formula: ζ = (Kd + b_plant) / (2 * √Kp)
    - Empirical optimum: Kd=3.50 → ζ≈0.636
    - Baseline nominal: Kd=2.0 → ζ≈0.37
    - Originally predicted: Kd=5.56 → ζ=1.0 (critical damping)

    Measured behavior vs nominal PD (Kp=8.0, Kd=2.0):
    - Faster convergence: 302 vs 455 ticks (1.51x speedup)
    - Moderate under-damping: faster response, acceptable overshoot
    - Shield clips overshoot torques (validates brain-agnostic safety)

    This empirically validates that moderate under-damping (ζ≈0.636) outperforms
    both the nominal (ζ≈0.37) and critical damping (ζ=1.0) for this task,
    refining the deep analysis prediction with real-world data.
    """

    Kp: float = 8.0   # Same as nominal (isolates Kd effect)
    Kd: float = 3.5   # Empirically optimal (vs 2.0 nominal, 5.56 predicted)
    # L1, L2 inherited from parent (0.6, 0.4)
