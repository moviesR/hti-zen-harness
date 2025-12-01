"""
Safety Shield - Final enforcer before environment (100 Hz)

Responsibilities:
- Enforce hard torque limits
- Scale torques near joint limits or high velocities
- Log all safety interventions as event packs

Reads: state.action_proposed, state.reflex_flags, state.obs
Writes: state.action_final
Logs: ArmEventPack on intervention
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from hti_arm_demo.shared_state import ArmSharedState, ArmEventPack
from hti_arm_demo.env import TAU_MAX


@dataclass
class SafetyShield:
    """
    Final safety check before env.step().

    Runs at 100 Hz (every tick), after all other bands.
    """

    u_min: float = -TAU_MAX
    u_max: float = TAU_MAX
    near_limit_scale: float = 0.5  # scale torques when joints near limit

    def _clip(self, value: float) -> float:
        """Clip value to [u_min, u_max]."""
        return max(self.u_min, min(self.u_max, value))

    def apply(
        self,
        state: ArmSharedState,
        events: List[ArmEventPack]
    ) -> None:
        """
        Enforce safety bounds on proposed action.

        Reads:
            - state.action_proposed: torques from Control
            - state.reflex_flags: safety flags from Reflex
            - state.obs: current state snapshot

        Writes:
            - state.action_final: safe torques for env.step()

        Logs:
            - Appends ArmEventPack to events list on intervention
        """
        # Default to zero torques if no proposal
        if state.action_proposed is None:
            proposed = (0.0, 0.0)
        else:
            proposed = state.action_proposed

        tau1, tau2 = proposed

        # Scale down near limits or high velocities
        scale = 1.0
        if state.reflex_flags is not None:
            if (state.reflex_flags.joint1_near_limit or
                state.reflex_flags.joint2_near_limit):
                scale *= self.near_limit_scale

            if state.reflex_flags.joints_too_fast:
                scale *= self.near_limit_scale

        tau1_scaled = tau1 * scale
        tau2_scaled = tau2 * scale

        # Hard bounds
        tau1_final = self._clip(tau1_scaled)
        tau2_final = self._clip(tau2_scaled)
        final = (tau1_final, tau2_final)

        # Write final action
        state.action_final = final

        # Log intervention if action changed
        if final != proposed:
            state.shield_interventions += 1
            pack = ArmEventPack(
                timestamp=state.t,
                tick=state.tick,
                band="SafetyShield",
                obs_before=dict(state.obs),
                action_proposed=proposed,
                action_final=final,
                reason="clip_or_scale",
                metadata={
                    "scaled": scale != 1.0,
                    "scale_factor": scale,
                    "brain_name": state.brain_name,  # v0.5: track which brain
                },
            )
            events.append(pack)
