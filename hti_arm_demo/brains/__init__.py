"""Pluggable brain policies for arm control."""

from .base import ArmBrainPolicy
from .arm_p_controller import ArmPControllerBrain
from .arm_aggressive_controller import ArmAggressiveControllerBrain
from .arm_pd_controller import ArmPDControllerBrain, ArmAggressivePDControllerBrain
from .arm_imperfect import ArmImperfectBrain
from .registry import create_arm_brain, list_arm_brains, BRAIN_REGISTRY

__all__ = [
    "ArmBrainPolicy",
    "ArmPControllerBrain",
    "ArmAggressiveControllerBrain",
    "ArmPDControllerBrain",
    "ArmAggressivePDControllerBrain",
    "ArmImperfectBrain",
    "create_arm_brain",
    "list_arm_brains",
    "BRAIN_REGISTRY",
]
