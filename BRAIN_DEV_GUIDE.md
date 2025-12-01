# HTI Brain Development Guide

**Version**: v0.3.0
**Audience**: Developers implementing custom control policies for HTI harness

This guide explains how to create custom brain policies for the HTI (Hierarchical Temporal Intelligence) harness. The v0.3 architecture enables pluggable control policies without modifying the safety-critical harness code.

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [BrainPolicy Protocol](#brainpolicy-protocol)
3. [Stateless vs Stateful Brains](#stateless-vs-stateful-brains)
4. [BrainObservation: What Brains Can See](#brainobservation-what-brains-can-see)
5. [Registering Your Brain](#registering-your-brain)
6. [Testing Your Brain](#testing-your-brain)
7. [Examples](#examples)
8. [Common Pitfalls](#common-pitfalls)
9. [Safety Contract](#safety-contract)

---

## Quick Start

**Minimal stateless brain**:

```python
# hti_v0_demo/brains/my_brain.py
from dataclasses import dataclass
from typing import Tuple, Any
from hti_v0_demo.brains.observation import BrainObservation

@dataclass
class MyBrain:
    """My custom brain policy."""

    def reset(self) -> None:
        """Stateless brain returns None."""
        return None

    def step(self, obs: BrainObservation, brain_state: Any) -> Tuple[float, None]:
        """Compute action based on observation."""
        # Your control logic here
        action = 0.5 * (obs.x_target - obs.x_meas)
        return (action, None)
```

**Register it**:

```python
# hti_v0_demo/brains/registry.py
from hti_v0_demo.brains.my_brain import MyBrain

BRAIN_REGISTRY: Dict[str, Type[BrainPolicy]] = {
    "p_controller": PControllerBrain,
    "noisy_p_controller": NoisyPControllerBrain,
    "my_brain": MyBrain,  # Add your brain here
}
```

**Use it**:

```bash
python -m hti_v0_demo.run_demo --brain my_brain
```

---

## BrainPolicy Protocol

All brains must implement the `BrainPolicy` protocol (Python 3.10+ structural typing):

```python
from typing import Protocol, Any, Tuple
from hti_v0_demo.brains.observation import BrainObservation

class BrainPolicy(Protocol):
    """Structural interface for pluggable control policies."""

    def reset(self) -> Any:
        """Initialize brain state for new episode.

        Returns:
            Initial brain_state (Any type).
            - Return None for stateless brains.
            - Return dict/tuple/custom object for stateful brains.

        Called once per episode after env.reset().
        """
        ...

    def step(self, obs: BrainObservation, brain_state: Any) -> Tuple[float, Any]:
        """Compute action based on observation and internal state.

        Args:
            obs: BrainObservation with x_meas and x_target
            brain_state: Your brain's state (from reset() or previous step())

        Returns:
            (action, new_brain_state) tuple:
            - action: float, proposed action (will be validated by harness)
            - new_brain_state: Updated state (or None for stateless)

        CRITICAL: This must be a PURE FUNCTION.
        - No side effects (file I/O, network, etc.)
        - All state flows through brain_state return value
        - Do NOT mutate instance variables
        """
        ...
```

**Why Protocol instead of ABC?**
- **No inheritance required**: Your class doesn't need to inherit from anything
- **Structural typing**: If it has the right methods, it's valid
- **External integration**: Easy to wrap external libraries

**Example (no inheritance needed)**:

```python
# This works! No 'class MyBrain(BrainPolicy)' needed
@dataclass
class MyBrain:
    gain: float = 0.5

    def reset(self) -> None:
        return None

    def step(self, obs: BrainObservation, brain_state: Any) -> Tuple[float, None]:
        return (self.gain * (obs.x_target - obs.x_meas), None)
```

---

## Stateless vs Stateful Brains

### Stateless Brains (Simpler)

**When to use**: Reactive policies, P/PD controllers, lookup tables

**Signature**:
```python
def reset(self) -> None:
    return None

def step(self, obs: BrainObservation, brain_state: Any) -> Tuple[float, None]:
    action = compute_action(obs)  # Pure function of observation
    return (action, None)
```

**Example: P Controller**

```python
@dataclass
class PControllerBrain:
    gain: float = 0.3

    def reset(self) -> None:
        return None

    def step(self, obs: BrainObservation, brain_state: Any) -> Tuple[float, None]:
        error = obs.x_target - obs.x_meas
        action = self.gain * error
        return (action, None)
```

### Stateful Brains (Advanced)

**When to use**: Filters, integrators, RNNs, RL policies with internal state

**Signature**:
```python
def reset(self) -> Dict:
    return {"integral": 0.0, "prev_error": 0.0}  # Your state structure

def step(self, obs: BrainObservation, brain_state: Dict) -> Tuple[float, Dict]:
    # Update state based on observation
    new_state = update_state(brain_state, obs)
    action = compute_action(obs, new_state)
    return (action, new_state)
```

**Example: PI Controller (Stateful)**

```python
@dataclass
class PIControllerBrain:
    kp: float = 0.3
    ki: float = 0.1

    def reset(self) -> Dict:
        """Initialize integrator state."""
        return {"integral": 0.0}

    def step(self, obs: BrainObservation, brain_state: Dict) -> Tuple[float, Dict]:
        error = obs.x_target - obs.x_meas

        # Update integrator (state mutation happens via return value)
        new_integral = brain_state["integral"] + error * 0.01  # dt=0.01

        # PI control law
        action = self.kp * error + self.ki * new_integral

        # Return action and updated state
        new_state = {"integral": new_integral}
        return (action, new_state)
```

**CRITICAL**: State must flow through return values. Do NOT do this:

```python
# ❌ WRONG - Don't mutate instance variables
class BadBrain:
    def __init__(self):
        self.integral = 0.0  # Instance variable

    def step(self, obs, brain_state):
        self.integral += error  # ❌ Mutating self - BREAKS HARNESS
        return (action, brain_state)

# ✅ CORRECT - State flows through return values
class GoodBrain:
    def reset(self):
        return {"integral": 0.0}

    def step(self, obs, brain_state):
        new_integral = brain_state["integral"] + error
        return (action, {"integral": new_integral})
```

---

## BrainObservation: What Brains Can See

Brains receive a **simplified observation** via the `BrainObservation` dataclass:

```python
from dataclasses import dataclass

@dataclass
class BrainObservation:
    """What brains can observe."""
    x_meas: float      # Measured position (potentially corrupted by sensor glitches)
    x_target: float    # Goal position
```

**What you CAN'T see** (by design):
- `x_true`: Ground truth position (only for safety checks in Reflex)
- `x_meas_raw`: Unclipped measurement (only for Reflex mismatch detection)
- `reflex_flags`: Safety layer outputs
- `semantics_advice`: High-level advisor outputs
- `action_proposed`, `action_final`: Other bands' outputs

**Why this restriction?**
- **Security**: Brains can't bypass safety layers (Reflex, Shield)
- **Decoupling**: Brains don't depend on harness internals
- **Forward compatibility**: Can extend observation without breaking brains

**Anti-Corruption Layer**: `ControlBand` translates `SharedState` → `BrainObservation` before calling your brain. You never touch `SharedState` directly.

---

## Registering Your Brain

**Step 1**: Implement your brain in `hti_v0_demo/brains/my_brain.py`

**Step 2**: Add import to `hti_v0_demo/brains/registry.py`:

```python
from hti_v0_demo.brains.my_brain import MyBrain
```

**Step 3**: Add to `BRAIN_REGISTRY`:

```python
BRAIN_REGISTRY: Dict[str, Type[BrainPolicy]] = {
    "p_controller": PControllerBrain,
    "noisy_p_controller": NoisyPControllerBrain,
    "my_brain": MyBrain,  # Your brain
}
```

**Step 4**: Test it:

```bash
python -m hti_v0_demo.run_demo --brain my_brain
```

**No harness modifications required!** The registry is the only touchpoint.

---

## Testing Your Brain

### Unit Testing (Computation Correctness)

```python
# hti_v0_demo/brains/tests/test_my_brain.py
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from hti_v0_demo.brains.my_brain import MyBrain
from hti_v0_demo.brains.observation import BrainObservation

def test_my_brain_computation():
    """Test action computation is correct."""
    brain = MyBrain(gain=0.5)
    obs = BrainObservation(x_meas=0.2, x_target=0.8)

    # Stateless brain: reset() returns None
    brain_state = brain.reset()
    assert brain_state is None

    # Compute action
    action, new_state = brain.step(obs, brain_state)

    # Verify math
    expected = 0.5 * (0.8 - 0.2)  # 0.3
    assert abs(action - expected) < 1e-9
    assert new_state is None  # Stateless

if __name__ == "__main__":
    test_my_brain_computation()
    print("✓ test_my_brain_computation")
```

### Integration Testing (with ControlBand)

```python
def test_my_brain_with_control_band():
    """Test brain works in ControlBand harness."""
    from hti_v0_demo.bands.control import ControlBand
    from hti_v0_demo.shared_state import SharedState

    brain = MyBrain(gain=0.5)
    band = ControlBand(brain)
    band.reset_episode()

    state = SharedState()
    state.obs = {"x_meas": 0.3, "x_target": 0.7, "x_true": 0.3, "x": 0.3}
    state.semantics_advice.confidence = 0.8  # High confidence (no scaling)

    band.step(state)

    # Verify action was proposed
    expected = 0.5 * (0.7 - 0.3)  # 0.2
    assert abs(state.action_proposed - expected) < 1e-9
```

### E2E Testing (Full Episode)

```python
def test_my_brain_full_episode():
    """Test brain completes a full episode."""
    from hti_v0_demo.env import ToyEnv
    from hti_v0_demo.scheduler import run_episode

    env = ToyEnv(enable_glitches=False)
    summary = run_episode(
        env=env,
        brain_name="my_brain",
        control_gain=0.5,
        verbose=False
    )

    # Verify episode completed
    assert summary["ticks"] >= 1
    assert "success" in summary
    assert summary["interventions"] >= 0  # Shield may intervene
```

---

## Examples

### Example 1: Bang-Bang Controller (Stateless)

```python
@dataclass
class BangBangBrain:
    """On-off controller (bang-bang control)."""
    max_action: float = 0.05

    def reset(self) -> None:
        return None

    def step(self, obs: BrainObservation, brain_state: Any) -> Tuple[float, None]:
        error = obs.x_target - obs.x_meas

        if abs(error) < 0.01:
            action = 0.0  # Within tolerance
        elif error > 0:
            action = self.max_action  # Move forward
        else:
            action = -self.max_action  # Move backward

        return (action, None)
```

### Example 2: Exponential Moving Average Filter (Stateful)

```python
@dataclass
class EMAFilterBrain:
    """Brain with exponential moving average of error."""
    alpha: float = 0.1  # Smoothing factor
    gain: float = 0.3

    def reset(self) -> Dict:
        return {"ema_error": 0.0}

    def step(self, obs: BrainObservation, brain_state: Dict) -> Tuple[float, Dict]:
        error = obs.x_target - obs.x_meas

        # Update EMA
        ema_error = self.alpha * error + (1 - self.alpha) * brain_state["ema_error"]

        # Control based on smoothed error
        action = self.gain * ema_error

        new_state = {"ema_error": ema_error}
        return (action, new_state)
```

### Example 3: RL Brain Template (Stateful)

```python
from typing import Dict
import torch

@dataclass
class RLBrain:
    """Reinforcement learning brain template.

    NOTE: This is a template. Replace with your actual RL model.
    """
    model: torch.nn.Module

    def reset(self) -> Dict:
        """Initialize episode buffer for training."""
        return {
            "episode_buffer": [],
            "hidden_state": None  # For RNN models
        }

    def step(self, obs: BrainObservation, brain_state: Dict) -> Tuple[float, Dict]:
        # Convert observation to tensor
        obs_tensor = torch.tensor([obs.x_meas, obs.x_target], dtype=torch.float32)

        # Forward pass (with hidden state for RNN)
        with torch.no_grad():
            if brain_state["hidden_state"] is None:
                action_dist, hidden = self.model(obs_tensor)
            else:
                action_dist, hidden = self.model(obs_tensor, brain_state["hidden_state"])

        # Sample action
        action = action_dist.sample().item()

        # Store transition for training (optional)
        brain_state["episode_buffer"].append((obs, action))

        # Update state
        new_state = {
            "episode_buffer": brain_state["episode_buffer"],
            "hidden_state": hidden
        }

        return (action, new_state)
```

---

## Common Pitfalls

### ❌ Pitfall 1: Mutating Instance Variables

```python
# WRONG
class BadBrain:
    def __init__(self):
        self.counter = 0  # Instance variable

    def step(self, obs, brain_state):
        self.counter += 1  # ❌ Mutating self
        return (action, brain_state)
```

**Why it fails**: ControlBand creates brain once. If you mutate `self`, state persists across episodes incorrectly.

**Fix**: Use `brain_state` return value.

```python
# CORRECT
class GoodBrain:
    def reset(self):
        return {"counter": 0}

    def step(self, obs, brain_state):
        new_counter = brain_state["counter"] + 1
        return (action, {"counter": new_counter})
```

### ❌ Pitfall 2: Accessing SharedState Directly

```python
# WRONG
def step(self, obs, brain_state):
    # obs is BrainObservation, NOT SharedState
    x_true = obs.x_true  # ❌ AttributeError - x_true not in BrainObservation
    return (action, brain_state)
```

**Fix**: Only use `obs.x_meas` and `obs.x_target`.

### ❌ Pitfall 3: Forgetting to Return New State

```python
# WRONG (for stateful brains)
def step(self, obs, brain_state):
    brain_state["integral"] += error  # Mutating dict (works but fragile)
    return (action, brain_state)  # Returns SAME dict
```

**Why it's fragile**: While Python dicts are mutable, this violates pure function contract.

**Fix**: Create new dict.

```python
# CORRECT
def step(self, obs, brain_state):
    new_integral = brain_state["integral"] + error
    new_state = {"integral": new_integral}
    return (action, new_state)
```

### ❌ Pitfall 4: Non-Float Actions

```python
# WRONG
def step(self, obs, brain_state):
    action = np.array([0.5])  # ❌ NumPy array, not float
    return (action, brain_state)
```

**Fix**: Return Python float.

```python
# CORRECT
def step(self, obs, brain_state):
    action = 0.5  # Python float
    # OR
    action = float(np_array[0])  # Convert NumPy to float
    return (action, brain_state)
```

---

## Safety Contract

### What Brains Are Responsible For

1. **Computing actions**: Based on `x_meas` and `x_target`
2. **Managing internal state**: Via `brain_state` return value
3. **Returning valid floats**: Actions must be Python `float` type

### What the Harness Guarantees

1. **Observation validity**: `obs.x_meas` and `obs.x_target` are always valid floats
2. **State threading**: Your `brain_state` is preserved between calls
3. **reset_episode() call**: Called exactly once per episode after `env.reset()`
4. **Safety validation**: Your actions will be validated/clipped by Shield

### What the Harness Does (You Don't Need To)

1. **Confidence scaling**: Applied in ControlBand after your brain.step()
2. **Action bounding**: Shield clips to `[-0.05, 0.05]`
3. **Sensor mismatch detection**: ReflexBand checks `x_true` vs `x_meas_raw`
4. **Safety logging**: EventPacks generated automatically on interventions

**Key Principle**: Brains are **untrusted computations**. The harness validates and constrains your outputs. You focus on control logic, not safety.

### Confidence Scaling Example

Your brain computes:
```python
action = 1.0 * (x_target - x_meas)  # Aggressive gain
```

ControlBand applies confidence scaling:
```python
if confidence < 0.3:
    action = action * 0.5  # Scale down if low confidence
```

Shield enforces bounds:
```python
if action > 0.05:
    action = 0.05  # Clip to safe range
```

You don't implement scaling or clipping—harness handles it.

---

## Advanced: Wrapping External Libraries

You can wrap external control libraries:

```python
import control  # python-control library

@dataclass
class LQRBrain:
    """LQR controller via python-control."""

    def __init__(self):
        # Design LQR controller
        A = [[0, 1], [0, 0]]  # State dynamics
        B = [[0], [1]]        # Control input
        Q = [[1, 0], [0, 1]]  # State cost
        R = [[1]]             # Control cost
        self.K, _, _ = control.lqr(A, B, Q, R)

    def reset(self) -> None:
        return None

    def step(self, obs: BrainObservation, brain_state: Any) -> Tuple[float, None]:
        # State: [position error, velocity (approx)]
        error = obs.x_target - obs.x_meas
        velocity = 0.0  # Approximate (need state history for real velocity)
        state = [error, velocity]

        # LQR control law: u = -K*x
        action = float(-self.K @ state)
        return (action, None)
```

---

## Testing Checklist

Before submitting your brain:

- [ ] Implements `BrainPolicy` protocol (`reset()` and `step()`)
- [ ] Returns `(float, Any)` from `step()` (not NumPy array, tensor, etc.)
- [ ] Stateless brains return `None` from `reset()` and `step()`
- [ ] Stateful brains return new state dict (don't mutate instance variables)
- [ ] Registered in `BRAIN_REGISTRY`
- [ ] Unit tests verify computation correctness
- [ ] Integration test with `ControlBand`
- [ ] E2E test completes episode without crashes
- [ ] Works with both clean sensors and sensor glitch scenarios

---

## Questions?

See `SPEC.md` Section 10 for full v0.3 specification.

For examples, see:
- `hti_v0_demo/brains/p_controller.py` - Stateless baseline
- `hti_v0_demo/brains/noisy_p_controller.py` - Stateless with randomness
- `hti_v0_demo/brains/tests/test_brains.py` - Unit test examples
- `hti_v0_demo/tests/test_control_integration.py` - Integration test examples
