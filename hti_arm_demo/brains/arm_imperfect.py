"""
Imperfect PD controller brain with mis-tuned gains for HTI v0.5.

This brain demonstrates HTI's value by intentionally using poor gain tuning:
- Kp too high (over-aggressive)
- Kd too low (under-damped)

The result: more Shield interventions and slower convergence,
but still safe and successful under HTI protection.
"""

from __future__ import annotations

from dataclasses import dataclass

from .arm_pd_controller import ArmPDControllerBrain


@dataclass
class ArmImperfectBrain(ArmPDControllerBrain):
    """
    Intentionally mis-tuned PD controller for HTI v0.5.

    Demonstrates HTI's value by creating a "bad" brain that:
    - Uses IK correctly (same as nominal PD)
    - Has poor gain tuning (over-aggressive Kp, under-damped Kd)
    - Still completes task under Shield protection

    User-specified gains chosen to stress Shield without causing failure:
    - Kp=12.0-14.0 (vs 8.0 nominal) - Too aggressive → over-torques
    - Kd=0.5-1.0 (vs 2.0 nominal) - Under-damped → oscillatory

    Expected behavior vs nominal PD:
    - More Shield interventions (clips excessive torques)
    - Slower convergence (oscillations near targets)
    - Still safe and successful (100% task completion)

    This is HTI v0.5's stress test: proving the safety system works
    even with sloppy control, at the cost of more interventions.
    """

    Kp: float = 14.0  # Over-tuned proportional gain (vs 8.0 nominal)
    Kd: float = 0.5   # Under-tuned derivative gain (vs 2.0 nominal)
    # L1=0.6, L2=0.4 inherited from parent
