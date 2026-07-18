# 17 — Deepen session statistics and boss overlay

**What to build:** Preserve the information overlay experience through cohesive behavior for persisted session statistics, inventory experience tracking, boss timers, positioning, visibility, and lifecycle.

**Blocked by:** 04 — Deepen settings and configuration; 15 — Deepen game automation.

**Status:** complete

- [x] Session statistics calculate, update, reset, and persist equivalent values.
- [x] Inventory experience tracking preserves its existing balance and hover behavior.
- [x] Boss timers preserve configured events, countdown behavior, rendering, positioning, and controls.
- [x] Overlay open, busy, update, and close behavior remains thread-safe and externally controllable.
- [x] Every overlay source Python file is at most 300 physical lines.
- [x] Focused statistics and Windows overlay tests pass.

The overlay implementation now lives behind the `src.overlay` capability facade, with private
modules for settings, statistics, inventory tracking, lifecycle, and Tk rendering. Session totals
persist through `QSettings`, lifecycle cleanup permits reopening after close, and focused coverage
includes statistics persistence, tracking cooldown, facade behavior, and real lifecycle cleanup.

Validation: focused overlay tests pass (6 passed, 1 Windows-only test skipped on macOS); the full
non-Selenium suite passes (674 passed, 16 skipped); Ruff and `ty` pass for the overlay slice. The
repository-wide line gate still reports the pre-existing oversized files documented by ADR 0006.
