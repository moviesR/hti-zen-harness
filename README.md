# HTI v0.5 – Imperfect Brain Stress Test (2-DOF Arm)

This repo implements the **HTI (Hierarchical Temporal Intelligence)** pattern as a time-banded safety harness for robotic control:

- **Time-banded control**:
  - **Semantics** (10 Hz) – high-level advisor (workspace goals)
  - **Control** (50 Hz) – delegates to pluggable brain policies (IK + PD control)
  - **Reflex** (100 Hz) – fast safety pre-checks
  - **Safety Shield** (100 Hz) – final enforcer before environment

- **Plant-Brain Separation** (v0.4):
  - Fixed plant parameters (realistic low damping)
  - Controllers provide their own stability (PD control)
  - Brain swapping on same physics (ready for RL/VLA)
  - Demonstrates HTI as framework, not just demo

- **Explicit invariants**:
  - Semantics is advisory-only (workspace goals)
  - Shield runs last before `env.step`
  - Actions are bounded by Shield
  - Safety interventions generate logged **event-packs**
  - Brains cannot bypass safety layers (Reflex, Shield)

**What v0.4 proves**:
- HTI harness scales from 1D cart to 2-DOF arm
- Plant-brain separation enables controller diversity
- PD controller stabilizes realistic (low-damping) plants
- Aggressive control is faster, Shield keeps it safe
- Multi-model consensus validation (GPT-5.1 + Gemini-2.5-Pro)

**What v0.5 adds** (NEW):
- **Imperfect brain stress test**: Intentionally mis-tuned PD (Kp=14.0, Kd=0.5)
- **13.2x more Shield interventions** (975 vs 74) - quantifies safety cost
- **100% task completion** - HTI keeps sloppy controllers safe
- **Brain comparison demo**: Side-by-side metrics (interventions, torque, time)
- **Zero harness modifications** - proves brain-agnostic design

For full details, see:
- [`SPEC.md`](./SPEC.md) - Complete technical specification (v0.1 through v0.5)
- [`BRAIN_DEV_GUIDE.md`](./BRAIN_DEV_GUIDE.md) - Guide for implementing custom brains
- [`CHANGELOG.md`](./CHANGELOG.md) - Version history and design decisions

## Quick Start

### v0.5: Brain Comparison Demo (NEW)

```bash
# Compare PD baseline vs Imperfect brain (10 episodes each)
python -m hti_arm_demo.run_v05_demo

# Custom episode count
python -m hti_arm_demo.run_v05_demo --episodes 20

# Output shows:
#   PD Baseline:      74 interventions, 455 ticks
#   Imperfect Brain:  975 interventions, 1613 ticks
#   Ratio:            13.2x more interventions, 100% success both
```

### v0.4: Single Brain Demos

```bash
# Run with nominal PD controller
python -m hti_arm_demo.run_arm_demo --brain pd

# Run with imperfect brain (mis-tuned PD)
python -m hti_arm_demo.run_arm_demo --brain imperfect

# Run with aggressive PD controller (faster, more Shield interventions)
python -m hti_arm_demo.run_arm_demo --brain pd_aggressive

# Custom PD gains
python -m hti_arm_demo.run_arm_demo --brain pd --Kp 10.0 --Kd 3.0

# Legacy P controller (requires high env damping, not recommended)
python -m hti_arm_demo.run_arm_demo --brain p
```

Output:
- Console summary: ticks executed, Shield interventions, waypoint completion
- `event_log.jsonl`: JSONL file with all safety interventions

**Expected results:**
- Nominal PD: ~455 ticks, ~74 interventions ✓ SUCCESS
- Aggressive PD: ~328 ticks, ~158 interventions ✓ SUCCESS (faster but more aggressive)

### v0.3: 1D Cart Demo (Legacy)

```bash
# Run with default P controller
python -m hti_v0_demo.run_demo

# Run with different brains
python -m hti_v0_demo.run_demo --brain noisy_p_controller

# Sensor glitch scenario
python -m hti_v0_demo.run_demo --scenario sensor_glitch
```

### Run Tests

```bash
# v0.4 Arm demo tests (7 tests)
python -m hti_arm_demo.tests.test_pd_controller

# v0.3 1D demo tests (51 tests)
python -m hti_v0_demo.tests.test_invariants
python -m hti_v0_demo.brains.tests.test_brains
python -m hti_v0_demo.tests.test_control_integration
python -m hti_v0_demo.tests.test_v0_2_1_equivalence
python -m hti_v0_demo.tests.test_e2e_scenarios

# Or use pytest (if installed)
pytest hti_arm_demo/ hti_v0_demo/
```

## Project Structure

```text
# Documentation
README.md              # This file
SPEC.md                # Complete technical spec (v0.1 - v0.4)
BRAIN_DEV_GUIDE.md     # Guide for implementing custom brains
CHANGELOG.md           # Version history and design decisions

# v0.4: 2-DOF Planar Arm Demo
hti_arm_demo/
  env.py                 # ToyArmEnv (2-DOF arm dynamics, waypoints)
  shared_state.py        # ArmSharedState, SemanticsAdvice
  event_log.py           # EventPack and EventLogger
  scheduler.py           # Main loop, time-banded orchestration
  run_arm_demo.py        # CLI entry point for arm demo

  # Time bands
  bands/
    semantics.py         # SemanticsBand (10 Hz, workspace goals)
    control.py           # ControlBand (50 Hz, brain delegation)
    reflex.py            # ReflexBand (100 Hz, pre-checks)
    shield.py            # SafetyShield (100 Hz, final enforcer)

  # Pluggable brains
  brains/
    base.py              # ArmBrainPolicy protocol
    registry.py          # Brain factory (create_arm_brain, list_arm_brains)
    arm_p_controller.py  # P controller (legacy, not recommended)
    arm_pd_controller.py # PD controller with IK (canonical v0.4 brain)
                         # - ArmPDControllerBrain (nominal: Kp=8.0, Kd=2.0)
                         # - ArmAggressivePDControllerBrain (Kp=14.0, Kd=3.5)

  # Tests
  tests/
    test_pd_controller.py # 7 behavioral tests for PD control

# v0.3: 1D Cart Demo (Legacy)
hti_v0_demo/
  # (Same structure as before, 51 tests total)
  # See original README section for details
```

## Creating Custom Brains (v0.4 Arm)

### Minimal Arm Brain Example

```python
# hti_arm_demo/brains/my_arm_brain.py
from dataclasses import dataclass
from typing import Tuple, Mapping, Any

@dataclass
class MyArmBrain:
    Kp: float = 5.0

    def step(
        self,
        obs: Mapping[str, float],
        brain_state: dict[str, Any] | None = None,
    ) -> Tuple[Tuple[float, float], dict[str, Any]]:
        """Compute joint torques from observations."""
        if brain_state is None:
            brain_state = {}

        # Read joint state
        theta1 = obs["theta1"]
        theta2 = obs["theta2"]

        # Read workspace goal (from Semantics)
        x_goal = obs["x_goal"]
        y_goal = obs["y_goal"]

        # Your control logic here
        # (This example just applies simple P control in joint space)
        tau1 = self.Kp * (0.0 - theta1)  # Drive to origin
        tau2 = self.Kp * (0.0 - theta2)

        return ((tau1, tau2), brain_state)
```

### Register and Use

```python
# hti_arm_demo/brains/registry.py
from hti_arm_demo.brains.my_arm_brain import MyArmBrain

BRAIN_REGISTRY = {
    "pd": ArmPDControllerBrain,
    "pd_aggressive": ArmAggressivePDControllerBrain,
    "my_arm_brain": MyArmBrain,  # Add here
}
```

```bash
python -m hti_arm_demo.run_arm_demo --brain my_arm_brain
```

**For complete brain development guide**, see:
- [`BRAIN_DEV_GUIDE.md`](./BRAIN_DEV_GUIDE.md) - Covers stateful brains, RL integration, testing
- `hti_arm_demo/brains/arm_pd_controller.py:89` - Reference implementation with IK

## Key Features by Version

### v0.4.0 (2025-11-30) - 2-DOF Planar Arm with Plant-Brain Separation

- **2-DOF planar arm** environment with multi-waypoint task
- **Plant-brain separation**: Fixed plant damping (realistic physics)
- **PD controller with IK**: Workspace goals → joint space control
  - `ArmPDControllerBrain` (nominal: Kp=8.0, Kd=2.0)
  - `ArmAggressivePDControllerBrain` (Kp=14.0, Kd=3.5)
- **Inverse kinematics**: Closed-form solver for 2-link planar arm
- **Demonstrates HTI value**: Aggressive control is faster (328 vs 455 ticks), Shield keeps it safe (158 vs 74 interventions)
- **Framework architecture**: Ready for Phase 2 (MuJoCo), Phase 3 (RL/VLA)
- **7 behavioral tests**: Test what system DOES, not how it's tuned
- **Multi-model consensus**: 2-1 for PD approach (GPT-5.1 + ChatGPT vs Gemini)

### v0.3.0 (2025-11-30) - Brain-Agnostic Architecture (1D Cart)

- **Pluggable brain policies** via `BrainPolicy` protocol
- **Anti-corruption layer**: `BrainObservation` decouples brains from harness
- **Reference brains**: `p_controller` (baseline), `noisy_p_controller` (test)
- **100% backward compatibility** (default brain = v0.2.1 behavior)
- **51 comprehensive tests** (unit, integration, equivalence, E2E, regression)
- **Multi-model consensus review** (9/10 from GPT-5.1 + Gemini-2.5-Pro)
- **CLI flag**: `--brain <name>` to swap control policies
- **Future-ready**: RL/RNN integration with NO harness changes

### v0.2.1 (2025-11-29) - Critical Boundary Fix

- **CRITICAL FIX**: Sensor glitch detection now works near boundaries
- **New field**: `x_meas_raw` (unclipped) for mismatch detection
- **Invariant #12**: Boundary glitch detection test
- **Multi-model review**: Found by GPT-5.1-Codex, missed by Gemini-2.5-Pro

### v0.2.0 (2025-11-29) - Sensor Contradictions

- **Sensor glitch simulation** in ToyEnv
- **Sensor mismatch detection** (ReflexBand compares `x_true` vs `x_meas`)
- **Shield STOP** on sensor mismatch (precedence: mismatch > clipping)
- **Automatic recovery** (stateless flags)
- **3 new invariants** (#9, #10, #11)

### v0.1.1 (2025-11-29) - Contract Hardening

- **Explicit validation** for SafetyShield bounds and ToyEnv inputs
- **Fail-fast** on invalid configuration
- **Educational comparison mode** (`--gain` flag)

### v0.1.0 (2025-11-29) - Initial Release

- **Time-banded scheduler** (Semantics 10Hz, Control 50Hz, Reflex 100Hz, Shield 100Hz)
- **Safety Shield** with event-pack logging
- **7 core invariants** with pytest tests

## Documentation

- **[SPEC.md](./SPEC.md)**: Complete technical specification
  - Section 0-9: v0.1 through v0.2.1
  - Section 10: v0.3 brain-agnostic architecture
  - All 16 invariants with test references

- **[BRAIN_DEV_GUIDE.md](./BRAIN_DEV_GUIDE.md)**: Developer guide for custom brains
  - BrainPolicy protocol
  - Stateless vs stateful brains
  - Testing strategies
  - Examples (P, PI, bang-bang, RL template)

- **[CHANGELOG.md](./CHANGELOG.md)**: Version history
  - Design decisions with rationale
  - Multi-model consensus review findings
  - Migration guides

## Production Readiness

### v0.4: 2-DOF Arm Demo

✅ **All 7 behavioral tests passing**
- PD controller waypoint completion
- Aggressive vs nominal comparison
- Safety preservation under aggressive control
- Custom gain tuning
- Brain-agnostic harness verification

✅ **Plant-brain separation established**
- Fixed plant parameters (DAMPING_COEFF=0.1)
- Controllers provide own stability
- Ready for brain swapping (RL, VLA, etc.)

✅ **Multi-model validation**
- Zen MCP code review: No critical issues
- Multi-model consensus: 2-1 for PD approach
- Architecture validated for HTI roadmap

### v0.3: 1D Cart Demo (Legacy)

✅ **All 51 tests passing** (unit, integration, E2E, regression)
✅ **Multi-model consensus** (GPT-5.1 + Gemini: 9/10 confidence)
✅ **Zero safety regressions**
✅ **100% backward compatibility**

## Roadmap

### Phase 1: Toy Demos ✅ COMPLETE
- v0.1-v0.3: 1D cart with brain-agnostic architecture
- v0.4: 2-DOF arm with PD control and plant-brain separation

### Phase 2: MuJoCo Port (Next)
- Port HTI harness to MuJoCo physics
- Same plant-brain separation principle
- Realistic arm dynamics (inertia matrix, Coriolis, gravity)

### Phase 3: Learned Policies
- Plug in RL brains (PPO, SAC, DQN)
- Plug in VLA policies (vision-language-action)
- Same plant, same harness, different brains

### Phase 4+: Stress Testing
- Adversarial scenarios
- Safety boundary exploration
- Real-time guarantees
- Process separation (IPC-based safety isolation)

## Contributing

For custom brain development:
1. Read [`BRAIN_DEV_GUIDE.md`](./BRAIN_DEV_GUIDE.md)
2. Implement `BrainPolicy` protocol
3. Add to `BRAIN_REGISTRY`
4. Write unit tests
5. Run E2E tests

For harness modifications:
1. Read [`SPEC.md`](./SPEC.md) Section 0-10
2. Ensure all 16 invariants preserved
3. Add tests for new behavior
4. Run full test suite (51 tests)

## License

MIT (see LICENSE file)

## Credits

- **Architecture**: Multi-model consensus (GPT-5.1 + Gemini-2.5-Pro)
- **Implementation**: Claude Code (Anthropic)
- **Review**: Zen MCP (multi-model consensus tool)