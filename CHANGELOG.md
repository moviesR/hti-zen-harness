# Changelog

All notable changes to the HTI (Hierarchical Temporal Intelligence) project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [0.2.0] - 2025-11-29

### Added - Sensor Contradiction Demo

#### New Environment Features
- **Sensor glitch simulation** (`env.py`)
  - `enable_glitches` parameter (default: `False` for backward compatibility)
  - `glitch_start_tick`, `glitch_end_tick`, `glitch_magnitude` parameters
  - `current_tick` tracking for glitch window evaluation
  - Observation dict now includes:
    - `x_true`: Ground truth state (always accurate)
    - `x_meas`: Measured state (corrupted during glitch window)
    - `x`: Backward compatibility alias for `x_true`

#### New Band Behaviors
- **ControlBand** (`bands/control.py:38-41`)
  - Now uses `x_meas` (measured state) instead of `x_true`
  - Intentionally naive controller vulnerable to sensor faults
  - Demonstrates how sensor contradictions propagate to action proposals
  - Fallback to `x` for backward compatibility

- **ReflexBand** (`bands/reflex.py`)
  - New `mismatch_threshold` parameter (default: 0.05)
  - Detects sensor contradictions by comparing `x_true` vs `x_meas`
  - Single source of truth for mismatch detection
  - Uses `x_true` for boundary checks (ground truth)

- **SafetyShield** (`shield.py:33-77`)
  - Complete rewrite with precedence hierarchy:
    1. **Sensor mismatch → STOP** (`action_final = 0.0`)
    2. Out of bounds → CLIP
    3. Near boundary → CONSERVATIVE CLIP
  - Trusts ReflexBand flag (no re-checking) - *Zen MCP #1*
  - Generates EventPack even for no-op stops - *Zen MCP #5*

#### New Data Structures
- **ReflexFlags extended** (`shared_state.py`)
  - `sensor_mismatch: bool = False` - Flag for sensor contradiction
  - `mismatch_magnitude: float = 0.0` - Magnitude of contradiction
  - **STATELESS**: Flags reset every tick for automatic recovery - *Zen MCP #2*

- **New EventPack reason** (`event_log.py`)
  - `"stop_sensor_mismatch"` - Shield STOP due to sensor contradiction

#### New Invariant Tests
- **test_sensor_mismatch_triggers_stop()** (`test_invariants.py:204`)
  - Invariant #9: Sensor mismatch → `action_final = 0.0`
  - Verifies Shield STOPS on sensor contradiction
  - Confirms EventPack generation with correct reason

- **test_recovery_after_glitch_window()** (`test_invariants.py:237`)
  - Invariant #10: Automatic recovery (stateless flags)
  - Tests before, during, and after glitch window
  - Verifies mismatch clears when glitch ends - *Zen MCP #3*

- **test_no_op_event_generation()** (`test_invariants.py:282`)
  - Invariant #11: EventPack even if `action_proposed == 0.0`
  - Ensures safety decisions are always logged - *Zen MCP #5*

#### Enhanced Demo Runner
- **New `--scenario` flag** (`run_demo.py:50-54`)
  - `clean`: v0.1.1 behavior (no glitches)
  - `sensor_glitch`: v0.2 demonstration (glitch window)
  - `both`: Side-by-side comparison (default)
  - Educational comparison showing intervention difference

- **Demo Output**:
  - Clean scenario: ~12 interventions (all clipping)
  - Glitch scenario: ~31 interventions (11 clipping + 20 sensor mismatch stops)
  - Clear +19 intervention difference demonstrates v0.2 features

#### Documentation Updates
- **SPEC.md Section 8**: Complete v0.2 specification
  - Motivation for sensor contradiction extension
  - Environment features (x_true vs x_meas behavior)
  - Band updates for all three bands
  - New ReflexFlags fields with stateless documentation
  - New EventPack reason `"stop_sensor_mismatch"`
  - All 3 new invariants (#9, #10, #11)
  - Demonstration scenarios with expected output
  - All 5 Zen MCP design decisions with rationale
  - Test coverage summary (11 total tests)

### Changed
- **ReflexFlags**: Now includes sensor mismatch fields (backward compatible)
- **SafetyShield.apply()**: Precedence-based safety logic - *Zen MCP #4*
- **EventPack metadata**: Extended with all ReflexFlags for debugging

### Validated
- ✅ All 11 invariant tests passing (8 from v0.1.1 + 3 new)
- ✅ Backward compatibility: `enable_glitches=False` preserves v0.1.1 behavior
- ✅ All 5 Zen MCP refinements implemented and tested
- ✅ Demo shows clear sensor contradiction behavior

### Design Decisions (Zen MCP Review)

**Zen MCP #1: Trust ReflexBand Flag**
- Shield doesn't re-check sensor mismatch
- Single source of truth (ReflexBand)
- Prevents duplicate logic and potential inconsistencies

**Zen MCP #2: Stateless Flags**
- ReflexFlags replaced entirely every tick
- No persistent mismatch state
- Prevents stale data bugs

**Zen MCP #3: Automatic Recovery**
- When glitch clears, `sensor_mismatch` automatically becomes `False`
- No manual reset logic needed
- Emergent property of stateless flags

**Zen MCP #4: Precedence Hierarchy**
- Sensor mismatch checked FIRST (early return)
- STOP takes precedence over clipping
- Clear, auditable safety logic

**Zen MCP #5: No-Op Event Generation**
- EventPack generated even when `proposed == final == 0.0`
- Preserves audit trail of safety decisions
- Critical for incident reconstruction

### Code Review
- **Reviewed by**: Zen MCP (Gemini-2.5-Pro)
- **Verdict**: APPROVED for release
- **Focus**: Sensor contradiction safety, stateless recovery, audit trail

---

## [0.1.1] - 2025-11-29

### Added
- **Explicit validation for SafetyShield bounds** (`shield.py:28`)
  - Constructor now enforces `u_min <= u_max`
  - Raises `ValueError` for invalid safety bounds
  - Prevents silent agent paralysis from misconfiguration

- **Input validation for ToyEnv.reset()** (`env.py:48-51`)
  - Validates `x0` and `x_target` are within `[0.0, 1.0]`
  - Prevents starting simulation in invalid state
  - Clear error messages for out-of-range values

- **New invariant test**: `test_shield_rejects_invalid_bounds()` (`test_invariants.py:187`)
  - Verifies SafetyShield enforces bound contract
  - Total invariant tests: 7 → 8

- **Educational comparison mode** (`run_demo.py`)
  - `--gain` command-line argument for configurable control gain
  - Default behavior runs both conservative (0.3) and aggressive (1.0) scenarios
  - Shows Shield intervention differences side-by-side
  - Demonstrates Shield behavior under different control policies

- **Future improvement markers** (TODO comments)
  - v0.2: Parameterize env bounds in ReflexBand (`reflex.py:41`)
  - v0.2: Replace `.get()` with direct dict access (`control.py:35`, `semantics.py:25`)

- **VALIDATION.md** - Comprehensive validation report
  - Three validation exercises (log analysis, invariant violation, stress test)
  - Zen MCP code review findings
  - What v0.1.1 proves vs what it doesn't

### Changed
- **Scheduler**: Added `control_gain` parameter to `run_episode()` (`scheduler.py:52`)
- **ControlBand**: Constructor now accepts `gain` parameter (default: 0.3)

### Validated
- ✅ All 8 invariant tests passing
- ✅ Zen MCP code review: NO SLOPPY FALLBACKS
- ✅ Three validation exercises completed (all passed)
  - Log analysis: Verified event-pack integrity
  - Invariant violation: Confirmed tests catch violations
  - Aggressive mode: Demonstrated Shield under load

### Fixed
- Explicit failures now occur at construction time for invalid inputs
- Clear error messages for configuration mistakes

### Code Review
- **Reviewed by**: Zen MCP (Gemini-2.5-Pro)
- **Verdict**: APPROVED for release
- **Findings**: Only intentional, safe defaults (`None → 0.0` action)

---

## [0.1.0] - 2025-11-29

### Added - Initial Release

#### Core Architecture
- **Time-banded scheduler** (`scheduler.py`)
  - Semantics band: 10 Hz (advisory)
  - Control band: 50 Hz (action proposer)
  - Reflex band: 100 Hz (pre-checks)
  - Safety Shield: 100 Hz (final enforcer)
  - Strict execution ordering enforced

- **Shared state management** (`shared_state.py`)
  - `SharedState` dataclass with typed fields
  - `SemanticsAdvice` dataclass (direction_hint, confidence)
  - `ReflexFlags` dataclass (near_boundary, too_fast, distance_to_boundary)

- **Band implementations** (`bands/`)
  - `SemanticsBand`: High-level advisory layer (10 Hz)
  - `ControlBand`: Proportional controller (50 Hz)
  - `ReflexBand`: Fast safety pre-checks (100 Hz)

- **Safety Shield** (`shield.py`)
  - Final enforcer of action bounds (±0.05)
  - Mandatory EventPack logging on intervention
  - Conservative mode near boundaries

- **Event logging** (`event_log.py`)
  - `EventPack` dataclass for structured interventions
  - `EventLogger` with JSONL output
  - Immediate write (no buffering)
  - Summary statistics and console output

- **Toy environment** (`env.py`)
  - 1D position control on [0.0, 1.0]
  - Simple dynamics: `x_next = clip(x + u, 0.0, 1.0)`
  - Success threshold: distance < 0.02

#### Testing
- **7 invariant tests** (`tests/test_invariants.py`)
  1. Semantics is advisory-only
  2. Shield bounds actions
  3. Event-pack on clipping
  4. Scheduler frequencies
  5. Bounded final commands
  6. Shield runs last
  7. Causality within tick

- All tests passing ✅

#### Documentation
- **README.md**: Project overview, quick start, usage
- **SPEC.md**: Complete technical specification with amendments
  - Explicit time semantics (tick, dt, frequency)
  - Concrete type signatures for all band interfaces
  - Typed dataclasses replacing `Dict[str, Any]`
  - Causality invariant explicitly stated
  - Error handling scope defined
  - Concrete pytest examples

- **CLAUDE.md**: Python implementation guidelines
  - Standard library only (Python 3.10+)
  - Type hints throughout
  - Dataclasses for state
  - Clear contracts

#### Demo
- **run_demo.py**: Entry point
  - Runs 1D position control task
  - Displays Shield intervention summary
  - Outputs event_log.jsonl

### Architecture Decisions
- Single-threaded scheduler (intentional simplification for v0.1)
- No error handling (fail-fast with assertions)
- Standard library only (no external dependencies except pytest)
- JSONL for event logging (human-readable, streaming-friendly)

### Known Limitations (By Design)
- 1D problem doesn't showcase hierarchy value
- No real-time guarantees (synchronous loop)
- No multi-threading or process separation
- Simple P controller (no RL/ML integration)

### Implementation Philosophy
- Explicit failures > silent fallbacks
- Fail fast at construction, not during episode
- Clear contracts enforced by types + validation
- Tests as architectural guardrails

---

## [Unreleased] - Future Work

### Planned for v0.3
- Apply to richer problem domain (2-DOF arm, multi-sensor)
- Demonstrate policy swap with RL controller
- Parameterize environment bounds (ReflexBand)
- Replace `.get()` with fail-fast dict access throughout
- Add multi-sensor fusion scenarios

### Planned for v0.4 (Production Path)
- Real-time scheduler integration
- Process separation for safety isolation
- IPC/message passing instead of SharedState
- ROS2 node implementation example
- Formal verification of invariants

---

## Version History

- **v0.2.0** (2025-11-29): Sensor contradiction demo + Zen MCP refinements
- **v0.1.1** (2025-11-29): Contract hardening + educational comparison
- **v0.1.0** (2025-11-29): Initial implementation
- **v0.0.1** (2025-11-27): Project initialization

---

## Contributors

- **Implementation**: Claude Code (Anthropic)
- **Architecture Review**: Zen MCP (Gemini-2.5-Pro, GPT-5.1)
- **Validation Methodology**: ChatGPT
- **Specification**: Multi-model consensus (GPT-5.1, Gemini-2.5-Pro)
