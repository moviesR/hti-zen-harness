# HTI v0.1 SPEC – Minimal Demo Harness

## 0. Scope

**Goal:**
Implement the smallest non-bullshit demo of the HTI pattern:

- Time-banded control:
  - Semantics (10 Hz)
  - Control (50 Hz)
  - Reflex (100 Hz)
  - Safety Shield (100 Hz)
- Strict ordering:
  - Semantics → Control → Reflex → Shield → env.step
- Clear invariants with unit tests
- Event-pack logging whenever the Safety Shield intervenes

**v0.1 stops when:**

- The loop runs end-to-end.
- Bands fire at the intended frequencies.
- Shield enforces action bounds and logs interventions as event-packs.
- Basic timing stats per band are collected.

Multi-modal contradictions (vision vs tactile, etc.) are **not** in v0.1.
Here, we treat Shield interventions as the **minimal contradiction**:
> "What Control wanted vs what the safety envelope allows."

---

## 1. Demo Scenario (Toy Environment)

We use a 1D toy "robot" to focus on HTI structure, not physics.

- State:
  - `x` – position on a line, constrained to `[0.0, 1.0]`
  - `x_target` – goal position, e.g. `0.8`
- Action:
  - `u` – delta-position per step (commanded), nominally in `[-0.05, 0.05]`
- Dynamics per base tick (100 Hz, `dt = 0.01 s`):

```python
x_next = clip(x + u, 0.0, 1.0)
```

**Environment API (`env.py`):**

```python
class ToyEnv:
    def reset(self, x0: float = 0.1, x_target: float = 0.8) -> dict:
        """
        Returns initial observation:
        {"x": float, "x_target": float}
        """
        ...

    def step(self, u: float) -> tuple[dict, float, bool, dict]:
        """
        Input:
            u: action actually applied (already safety-checked and bounded)
        Returns:
            obs: {"x": float, "x_target": float}
            reward: e.g. -abs(x - x_target)
            done: True if |x - x_target| < eps or max_steps reached
            info: may include {"safety_clipped": bool}
        """
        ...
```

We intentionally keep this trivial. **Note:** The 1D environment is intentionally simple to isolate the harness pattern mechanics. The demo proves the harness structure, not control performance. Future versions may use multi-step tasks where hierarchy provides clear value.

---

## 1.5 Time Semantics

HTI v0.1 uses a discrete-time simulation with these definitions:

- **tick**: Integer step counter (0, 1, 2, ...). Increments by 1 each loop iteration.
- **t**: Simulated time in seconds. `t = tick * dt` where `dt = 0.01s`.
- **Base rate**: 100 Hz (dt = 0.01s). The scheduler loop runs at this frequency.
- **Band frequencies**: Measured in ticks, not wall-clock time:
  - Semantics: every 10 ticks (10 Hz)
  - Control: every 2 ticks (50 Hz)
  - Reflex: every 1 tick (100 Hz)
  - Shield: every 1 tick (100 Hz)

**Global time authority**: The scheduler owns `tick` and `t`. Bands are stateless functions that receive `state` and must not maintain internal time counters.

---

## 2. Time Bands in v0.1

We simulate a global loop at **100 Hz** (`tick` advances every 0.01 seconds).

### Semantics Band (10 Hz)

* Runs every 10 ticks (`tick % 10 == 0`).
* Role: "brain" stub, high-level advisor.
* **Advisory only**:

  * Can update `state.semantics_advice`.
  * Cannot directly set the final action.
* For v0.1, this can be a simple heuristic, e.g.:

  * Suggest direction sign `+1` or `-1` based on `x_target - x`.

### Control Band (50 Hz)

* Runs every 2 ticks (`tick % 2 == 0`).
* Role: choose an **action proposal**.
* Reads:

  * `state.obs`
  * `state.semantics_advice`
* Writes:

  * `state.action_proposed: float`
* It does **not** apply safety bounds. It may propose an out-of-bounds action.

### Reflex Band (100 Hz)

* Runs every tick.
* Role: **fast pre-check** of the *proposed* action against the current state.
* Reads:

  * `state.obs`
  * `state.action_proposed`
* Writes:

  * `state.reflex_flags: ReflexFlags`
* **Important:** In v0.1, Reflex does **not** modify the action directly.
  It only sets flags that the Safety Shield can use to decide whether to clip / log.

This keeps Shield as the single authority that actually changes `u`, while Reflex is a sensor-side early warning.

### Safety Shield (100 Hz)

* Runs every tick, **always last before `env.step`**.
* Reads:

  * `state.obs`
  * `state.action_proposed`
  * `state.reflex_flags`
* Writes:

  * `state.action_final: float` (the action passed to the environment)
* Responsibilities:

  * Clamp `state.action_proposed` into a safe interval `[-0.05, 0.05]`.
  * Optionally be more conservative when `reflex_flags.near_boundary` is True.
  * If it changes the action (i.e. `action_final != action_proposed`), it emits an **EventPack** describing this intervention.

---

## 3. Invariants for HTI v0.1

These are the explicit rules we want tests for.

1. **No inter-band locks**

   * Bands are called sequentially in the scheduler.
   * No band blocks waiting on another; state sharing is via `SharedState` only.

2. **Ordering per tick**

   * Within a tick, the call order is:

     ```text
     Semantics (if due) → Control (if due) → Reflex → Safety Shield → env.step
     ```

3. **Semantics is advisory-only**

   * SemanticsBand may write to `state.semantics_advice`.
   * It must **never** write directly to `state.action_proposed` or `state.action_final`.

4. **Bounded final commands**

   * `state.action_final` passed to `env.step` is always within `[-0.05, 0.05]`.

5. **Event-pack logging on Shield intervention**

   * Whenever `action_final != action_proposed`, Safety Shield:

     * creates an `EventPack`
     * passes it to the logger
   * This is treated as the minimal **contradiction**: "Control wanted X, Shield allowed Y."

6. **Latency measurement**

   * Each band and the Shield record their own execution times (wall-clock, per tick).
   * At the end of an episode, we print or return basic stats (mean / max) per band.
   * v0.1 doesn't need real-time guarantees, just instrumentation.

7. **Tick-boundary causality**

   * Band outputs at tick T depend only on state from tick T-1 or earlier, **EXCEPT** for reading outputs from bands that executed earlier in the same tick within the strict ordering (Semantics → Control → Reflex → Shield).
   * Example: Control at tick T may read `semantics_advice` written at tick T (because Semantics runs before Control), but Semantics at tick T+10 must read obs from tick T+10, not tick T+11.

---

## 3.1 Error Handling and Edge Cases (v0.1 Scope)

v0.1 does not implement robust error handling. The following assumptions hold:

- Environment always produces valid observations
- Bands always produce valid outputs (no None, NaN, or exceptions)
- Episodes run to natural completion (done=True) or max_ticks
- Initial state (tick 0): `semantics_advice` and `reflex_flags` are initialized with default values

Implementations should use assertions to fail-fast on invalid states rather than attempting recovery.

---

## 4. Data Structures

### 4.1 SemanticsAdvice

`shared_state.py`:

```python
from dataclasses import dataclass

@dataclass
class SemanticsAdvice:
    direction_hint: int = 0    # -1, 0, or +1
    confidence: float = 0.0     # 0.0 to 1.0
```

### 4.2 ReflexFlags

`shared_state.py`:

```python
@dataclass
class ReflexFlags:
    near_boundary: bool = False
    too_fast: bool = False
    distance_to_boundary: float = 0.0
```

### 4.3 SharedState

`shared_state.py`:

```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class SharedState:
    t: float = 0.0
    tick: int = 0
    obs: dict[str, float] = field(default_factory=dict)

    # Control → Shield action flow
    action_proposed: Optional[float] = None
    action_final: Optional[float] = None

    # Semantics output
    semantics_advice: SemanticsAdvice = field(default_factory=SemanticsAdvice)

    # Reflex flags
    reflex_flags: ReflexFlags = field(default_factory=ReflexFlags)
```

### 4.4 EventPack

`event_log.py`:

```python
from dataclasses import dataclass, asdict
from typing import Any

@dataclass
class EventPack:
    timestamp: float
    tick: int
    band: str              # e.g. "SafetyShield"
    obs_before: dict[str, float]
    action_proposed: float
    action_final: float
    reason: str            # e.g. "clip_out_of_bounds", "clip_near_boundary"
    metadata: dict[str, Any]
```

### 4.5 Band Interfaces

`bands/reflex.py`:

```python
class ReflexBand:
    def step(self, state: SharedState) -> None:
        """
        Reads: state.obs, state.action_proposed
        Writes: state.reflex_flags
        MUST NOT write: state.action_proposed, state.action_final
        """
        ...
```

`bands/control.py`:

```python
class ControlBand:
    def step(self, state: SharedState) -> None:
        """
        Reads: state.obs, state.semantics_advice
        Writes: state.action_proposed
        MUST NOT write: state.action_final
        """
        ...
```

`bands/semantics.py`:

```python
class SemanticsBand:
    def step(self, state: SharedState) -> None:
        """
        Reads: state.obs
        Writes: state.semantics_advice
        MUST NOT write: state.action_proposed, state.action_final
        """
        ...
```

### 4.6 Safety Shield

`shield.py`:

```python
from typing import Optional, Tuple

class SafetyShield:
    def __init__(self, u_min: float = -0.05, u_max: float = 0.05):
        self.u_min = u_min
        self.u_max = u_max

    def apply(self, state: SharedState) -> Tuple[float, Optional[EventPack]]:
        """
        Reads: state.action_proposed, state.obs, state.reflex_flags
        Produces:
          - safe action_final (bounded)
          - optional EventPack if clipping / override occurred
        Writes: state.action_final
        """
        ...
```

---

## 5. Scheduler Logic

`scheduler.py` owns the main loop.

```python
import time

def run_episode(env: ToyEnv, max_ticks: int = 2000):
    state = SharedState()
    bands = {
        "semantics": SemanticsBand(),
        "control": ControlBand(),
        "reflex": ReflexBand(),
    }
    shield = SafetyShield()
    logger = EventLogger()
    timing_stats = TimingStats()  # simple helper for per-band timing

    obs = env.reset()
    state.obs = obs

    for tick in range(max_ticks):
        state.tick = tick
        state.t = tick * 0.01  # 100 Hz base rate

        # Semantics band (10 Hz)
        if tick % 10 == 0:
            t0 = time.perf_counter()
            bands["semantics"].step(state)
            timing_stats.record("semantics", time.perf_counter() - t0)

        # Control band (50 Hz)
        if tick % 2 == 0:
            t0 = time.perf_counter()
            bands["control"].step(state)
            timing_stats.record("control", time.perf_counter() - t0)

        # Reflex band (100 Hz)
        t0 = time.perf_counter()
        bands["reflex"].step(state)
        timing_stats.record("reflex", time.perf_counter() - t0)

        # Safety Shield (always last before env.step)
        t0 = time.perf_counter()
        safe_u, event = shield.apply(state)
        timing_stats.record("shield", time.perf_counter() - t0)

        if event is not None:
            logger.log(event)

        # Env step
        obs, reward, done, info = env.step(safe_u)
        state.obs = obs
        state.action_final = safe_u

        if done:
            break

    logger.dump()         # write event-packs to disk or stdout
    timing_stats.report() # print band timing summary
```

---

## 6. Tests (`tests/test_invariants.py`)

Unit tests should cover all invariants with concrete, runnable examples:

### Test 1: Semantics is advisory-only

```python
def test_semantics_advisory_only():
    """Invariant #3: Semantics may not write action_proposed or action_final"""
    state = SharedState(obs={"x": 0.5, "x_target": 0.8})
    state.action_proposed = 0.03  # Set by prior band

    sem = SemanticsBand()
    sem.step(state)

    # Assert semantics didn't touch action
    assert state.action_proposed == 0.03
    assert state.action_final is None
    # But did write advice
    assert state.semantics_advice.direction_hint in [-1, 0, 1]
```

### Test 2: Shield bounds actions

```python
def test_shield_bounds_actions():
    """Invariant #4: action_final is always within bounds"""
    state = SharedState(obs={"x": 0.5, "x_target": 0.8})
    shield = SafetyShield(u_min=-0.05, u_max=0.05)

    # Test out-of-bounds proposals
    test_cases = [0.10, -0.10, 0.03, -0.02, 0.0]

    for proposed in test_cases:
        state.action_proposed = proposed
        safe_u, event = shield.apply(state)

        assert -0.05 <= safe_u <= 0.05, f"Action {safe_u} out of bounds for proposal {proposed}"
        assert state.action_final == safe_u
```

### Test 3: Event-pack on clipping

```python
def test_event_pack_on_clipping():
    """Invariant #5: EventPack generated when Shield intervenes"""
    state = SharedState(obs={"x": 0.5, "x_target": 0.8}, tick=42, t=0.42)
    shield = SafetyShield(u_min=-0.05, u_max=0.05)

    # Propose out-of-bounds action
    state.action_proposed = 0.10
    safe_u, event = shield.apply(state)

    # Should have clipped and logged
    assert safe_u == 0.05
    assert event is not None
    assert event.action_proposed == 0.10
    assert event.action_final == 0.05
    assert event.band == "SafetyShield"
    assert event.tick == 42

    # Propose in-bounds action
    state.action_proposed = 0.03
    safe_u, event = shield.apply(state)

    # Should NOT log
    assert safe_u == 0.03
    assert event is None
```

### Test 4: Scheduler frequencies

```python
def test_scheduler_frequencies():
    """Invariant #2: Bands fire at correct frequencies"""
    from unittest.mock import Mock

    env = Mock()
    env.reset.return_value = {"x": 0.1, "x_target": 0.8}
    env.step.return_value = ({"x": 0.1, "x_target": 0.8}, 0.0, False, {})

    # Track calls
    semantics_ticks = []
    control_ticks = []
    reflex_ticks = []

    class TrackingSemanticsBand(SemanticsBand):
        def step(self, state):
            semantics_ticks.append(state.tick)
            super().step(state)

    class TrackingControlBand(ControlBand):
        def step(self, state):
            control_ticks.append(state.tick)
            super().step(state)

    class TrackingReflexBand(ReflexBand):
        def step(self, state):
            reflex_ticks.append(state.tick)
            super().step(state)

    # Run for 100 ticks
    # ... (scheduler code with tracking bands)

    # Assert frequencies
    assert semantics_ticks == [0, 10, 20, 30, 40, 50, 60, 70, 80, 90]  # every 10
    assert control_ticks == [0, 2, 4, 6, 8, ..., 98]  # every 2
    assert len(reflex_ticks) == 100  # every tick
```

### Test 5: Shield runs last

```python
def test_shield_runs_last():
    """Invariant #2: Shield executes after all bands, before env.step"""
    call_order = []

    class TrackingSemanticsBand(SemanticsBand):
        def step(self, state):
            call_order.append("semantics")
            super().step(state)

    class TrackingControlBand(ControlBand):
        def step(self, state):
            call_order.append("control")
            super().step(state)

    class TrackingReflexBand(ReflexBand):
        def step(self, state):
            call_order.append("reflex")
            super().step(state)

    class TrackingShield(SafetyShield):
        def apply(self, state):
            call_order.append("shield")
            return super().apply(state)

    # Run one tick (tick % 10 == 0 and tick % 2 == 0)
    # ... (single tick execution)

    # At tick 0, order should be: semantics → control → reflex → shield
    assert call_order == ["semantics", "control", "reflex", "shield"]
```

### Test 6: Causality (within-tick visibility)

```python
def test_causality_within_tick():
    """Invariant #7: Bands can read earlier bands' outputs from same tick"""
    state = SharedState(obs={"x": 0.5, "x_target": 0.8}, tick=0)

    # Semantics writes advice at tick 0
    sem = SemanticsBand()
    sem.step(state)

    semantics_hint = state.semantics_advice.direction_hint

    # Control at tick 0 should see that advice
    ctrl = ControlBand()
    ctrl.step(state)

    # Control should have used the hint (implementation-dependent verification)
    # At minimum, verify Control had access to non-default semantics_advice
    assert semantics_hint != 0  # Assuming target is different from current x
```

---

## 7. v0.2+ (Notes Only)

Not for implementation now, just for future:

* Add a second modality (e.g. "noisy sensor" vs "true state") and treat disagreements as a new type of contradiction.
* Use Reflex to process raw sensor streams into flags.
* Extend EventPack with `contradiction_type` (vision_vs_dynamics, slip_vs_force, etc.).
* Introduce a simple learning loop that uses EventPacks as training data.

v0.1 is done as soon as the scheduler, bands, Shield, event logging, and tests exist and pass.

---

## 8. v0.2 - Sensor Contradiction Extension

### 8.1 Motivation

v0.1 demonstrated the minimal HTI pattern with a single contradiction source:
> "What Control wanted vs what the safety envelope allows."

v0.2 extends this to include **sensor contradictions**:
> "What sensors report vs what the true state is."

This demonstrates HTI's value in handling multi-modal information conflicts, a common scenario in robotics (vision vs tactile, encoder vs IMU, GPS vs odometry, etc.).

### 8.2 Environment Features

ToyEnv gains optional sensor glitch simulation:

```python
env = ToyEnv(
    enable_glitches=True,
    glitch_start_tick=5,
    glitch_end_tick=25,
    glitch_magnitude=0.3
)
```

**Behavior**:
- `x_true`: Ground truth position (always accurate)
- `x_meas`: Measured position (corrupted during glitch window)
- During glitch: `x_meas = clip(x_true + glitch_magnitude, 0.0, 1.0)`
- Outside glitch: `x_meas = x_true`

**Backward Compatibility**:
- `enable_glitches=False` (default): `x = x_true = x_meas` (v0.1.1 behavior)
- obs dict contains `x`, `x_true`, and `x_meas` for compatibility

### 8.3 Band Updates

**ControlBand** (intentionally naive):
- Uses `x_meas` for control decisions
- During glitch, makes decisions based on corrupted measurement
- Demonstrates vulnerability to sensor faults
- Fallback to `obs["x"]` for v0.1.1 compatibility

**ReflexBand** (mismatch detection):
- Compares `x_true` vs `x_meas`
- Sets `sensor_mismatch=True` when `|x_true - x_meas| > threshold` (default 0.05)
- Uses `x_true` for boundary checks (ground truth)
- Fallback to `obs["x"]` for v0.1.1 compatibility

**SafetyShield** (trust and verify):
- Trusts ReflexBand's `sensor_mismatch` flag (no re-checking per Zen MCP #1)
- **Precedence hierarchy**:
  1. Sensor mismatch → STOP (action_final=0.0)
  2. Out of bounds → CLIP
  3. Near boundary → CONSERVATIVE CLIP
- Generates EventPack even for no-op stops (per Zen MCP #5)

### 8.4 New ReflexFlags Fields

```python
@dataclass
class ReflexFlags:
    near_boundary: bool = False
    too_fast: bool = False
    distance_to_boundary: float = 0.0
    sensor_mismatch: bool = False      # v0.2
    mismatch_magnitude: float = 0.0    # v0.2
```

**STATELESS** (Zen MCP #2): Flags are reset/recomputed every tick. Previous flags discarded.

**RECOVERY** (Zen MCP #3): When mismatch clears, sensor_mismatch automatically becomes False.

### 8.5 New EventPack Reason

v0.2 adds one new intervention reason:
- `"stop_sensor_mismatch"`: Shield stopped system due to sensor contradiction

Metadata now includes:
- `sensor_mismatch: bool`
- `mismatch_magnitude: float`

### 8.6 New Invariants (v0.2)

**Invariant #9: Sensor mismatch triggers stop**
- When `reflex_flags.sensor_mismatch=True`, Shield sets `action_final=0.0`
- EventPack generated with reason `"stop_sensor_mismatch"`
- Test: `test_sensor_mismatch_triggers_stop()`

**Invariant #10: Automatic recovery**
- ReflexFlags are stateless: when glitch clears, mismatch flag clears
- Shield resumes normal operation automatically
- No manual reset required
- Test: `test_recovery_after_glitch_window()`

**Invariant #11: No-op event generation**
- EventPack generated even if `action_proposed` was already `0.0`
- Ensures all sensor mismatch stops are logged
- Test: `test_no_op_event_generation()`

### 8.7 Demonstration Scenarios

```bash
# Clean sensors (v0.1.1 behavior)
python -m hti_v0_demo.run_demo --scenario clean

# Sensor glitch (v0.2 demonstration)
python -m hti_v0_demo.run_demo --scenario sensor_glitch

# Both scenarios with comparison (default)
python -m hti_v0_demo.run_demo --scenario both
```

**Expected Behavior**:
- Clean: ~12 interventions (clip_out_of_bounds, clip_near_boundary)
- Glitch: ~31 interventions (11 clipping + 20 stop_sensor_mismatch)
- Difference: +19 interventions during glitch window
- Automatic recovery at tick 25

### 8.8 Design Decisions (Zen MCP Refinements)

1. **Trust ReflexBand** (Zen MCP #1): Shield doesn't re-compute mismatch threshold
   - Rationale: Avoid duplicated logic, single source of truth

2. **Stateless Flags** (Zen MCP #2): ReflexFlags don't carry state between ticks
   - Rationale: Simplifies reasoning, automatic recovery

3. **Explicit Recovery Documentation** (Zen MCP #3): Recovery is automatic, not manual
   - Rationale: Prevents confusion about reset mechanisms

4. **Precedence Clarity** (Zen MCP #4): Sensor mismatch stop > clipping
   - Rationale: Sensor faults are more critical than control aggressiveness

5. **No-op Event Logging** (Zen MCP #5): Generate EventPack even for 0.0 → 0.0
   - Rationale: Audit trail for all safety decisions, not just action changes

### 8.9 Test Coverage

Total tests: 11 (8 from v0.1.1 + 3 new from v0.2)

All v0.1.1 tests pass with `enable_glitches=False`, ensuring backward compatibility.

---
