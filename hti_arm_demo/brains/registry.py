"""
Brain registry for creating arm control policies.

Provides factory function to instantiate brains by name.
"""

from __future__ import annotations

from typing import Dict, Type, Any

from .base import ArmBrainPolicy
from .arm_p_controller import ArmPControllerBrain
from .arm_aggressive_controller import ArmAggressiveControllerBrain
from .arm_pd_controller import ArmPDControllerBrain, ArmAggressivePDControllerBrain
from .arm_imperfect import ArmImperfectBrain
from .arm_optimal_pd import ArmOptimalPDBrain


BRAIN_REGISTRY: Dict[str, Type[ArmBrainPolicy]] = {
    "p": ArmPControllerBrain,
    "aggressive": ArmAggressiveControllerBrain,
    "pd": ArmPDControllerBrain,
    "pd_aggressive": ArmAggressivePDControllerBrain,
    "imperfect": ArmImperfectBrain,  # v0.5: mis-tuned PD for stress testing
    "optimal": ArmOptimalPDBrain,    # Phase 1: critically damped PD (ζ=1.0)
}


def create_arm_brain(brain_name: str, config: Dict[str, Any] | None = None) -> ArmBrainPolicy:
    """
    Factory function for creating arm brains.

    Args:
        brain_name: Name from BRAIN_REGISTRY ("p", "aggressive", "pd", "pd_aggressive", "imperfect", "optimal")
        config: Optional dict of constructor arguments
            - For P brains: {"gain": 7.0}
            - For PD brains: {"Kp": 10.0, "Kd": 2.5}
            - For imperfect brain: {"Kp": 14.0, "Kd": 0.5} (defaults)
            - For optimal brain: {"Kp": 8.0, "Kd": 5.56} (defaults)

    Returns:
        Instantiated brain

    Raises:
        ValueError: If brain_name not in registry
    """
    if brain_name not in BRAIN_REGISTRY:
        available = ", ".join(BRAIN_REGISTRY.keys())
        raise ValueError(
            f"Unknown brain: '{brain_name}'. "
            f"Available: {available}"
        )

    brain_class = BRAIN_REGISTRY[brain_name]

    if config is None:
        config = {}

    return brain_class(**config)


def list_arm_brains() -> list[str]:
    """Get list of available brain names."""
    return list(BRAIN_REGISTRY.keys())
