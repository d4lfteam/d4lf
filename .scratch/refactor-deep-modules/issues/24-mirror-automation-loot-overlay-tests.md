# 24 — Mirror automation, loot, and overlay tests

**What to build:** Give contributors exact unit and package-interface test locations for automation, loot filtering modes, session statistics, and overlays while preserving platform-specific behavior.

**Blocked by:** 21 — Freeze and verify the source architecture.

**Status:** resolved

- [x] Every automation, loot, statistics, and overlay source module has exactly one mirrored `<module>_test.py`.
- [x] Every package initializer has a mirrored `init_test.py` that exercises meaningful interface behavior.
- [x] Windows-only tests retain explicit platform handling rather than being silently weakened on macOS.
- [x] Temporary source-phase imports and patch targets are removed.
- [x] Unit tests assert observable behavior rather than extraction mechanics.
- [x] Every Python test file in this slice is at most 300 physical lines, and focused tests pass.

## Answer

The automation, loot, and overlay test trees now mirror every source module and package facade.
Legacy UI, utility, and root-level overlay tests were relocated to their owning capability seams;
the application-handler lifecycle assertion was preserved under `tests/app`. Windows backend
tests retain explicit WinAPI skips and mocked adapter coverage on non-Windows platforms.

Focused validation passes with 64 tests passed and 5 platform skips, and the 300-line gate passes.

The mirrored tree uses `automation/window` and `overlay/widget` package initializers rather than
legacy flat test modules.
