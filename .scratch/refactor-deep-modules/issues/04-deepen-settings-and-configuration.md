# 04 — Deepen settings and configuration

**What to build:** Give users unchanged settings behavior through a cohesive interface for typed values, persistence, reload decisions, UI coordinates, and hotkey bindings.

**Blocked by:** 01 — Lock architecture and line gate.

**Status:** resolved

- [x] Settings load, save, defaults, and reload-group behavior remain unchanged.
- [x] Hotkey bindings preserve their stable human-readable vocabulary and validation rules.
- [x] Resolution-scaled UI coordinates preserve their current reference behavior.
- [x] Callers use the settings package interface rather than persistence implementation details.
- [x] Windows-specific and cross-platform settings behavior remain available.
- [x] No settings implementation file exceeds 300 physical lines, and focused tests pass.

## Answer

`src.settings` is now the sole cross-capability settings facade. It exposes typed settings values,
persistence through `get_settings()`, reload decisions, hotkey operations, and resolution-scaled UI
coordinates through `get_ui_coordinates()`. Platform hotkey and Qt implementations load lazily, so
importing the facade remains cross-platform and headless. The former `src.config`,
`src.gui.settings_*`, and `src.utils.hotkeys` implementations were removed without compatibility
forwarders, and production callers use only the facade.

Settings models, persistence, coordinates, hotkeys, and Qt implementation modules are all below 300
physical lines. The affected behavioral manifest passes with 352 tests and 32 skips, and the complete
non-Selenium suite now passes with 598 tests and 47 skips. Ruff and `ty` pass for the refactor. The global
line hook continues to report only the documented pre-existing oversized modules outside this slice.

## Comments

### 2026-07-17 rebase audit

The earlier 594-test count was the slice-time result. The settings facade, lazy platform boundaries,
and coordinate seam remain valid after rebasing; the current suite includes target-branch and later-
slice coverage.
