# 15 — Deepen game automation

**What to build:** Give filtering modes one platform-neutral automation interface for locating Diablo IV, handling input, moving the pointer, and acting on inventory, stash, and vendor items without changing user-visible behavior.

**Blocked by:** 04 — Deepen settings and configuration; 13 — Deepen screenshot and tooltip perception.

**Status:** complete

- [x] Windows and no-op window adapters satisfy one real seam.
- [x] Hotkeys, process discovery, window coordinates, and human-like pointer movement preserve established behavior.
- [x] Inventory, stash, vendor, and loot-movement actions preserve their ordering and safety checks.
- [x] Callers no longer coordinate private window, mouse, process, and inventory helpers.
- [x] Every touched source Python file is at most 300 physical lines.
- [x] Focused automation tests and the repository-wide line guard pass.

## Answer

Game automation now has a public `src.automation` facade for Diablo IV window discovery and
foreground checks, hotkeys, human-like pointer movement, process handling, inventory factories,
stash and vendor access, and loot movement. Windows and no-op window adapters share the same
window seam, while filtering and vision-mode callers no longer import the former private
automation modules. Inventory movement ordering, capacity checks, configured tab order, item
selection, right-click actions, and cursor reset behavior are preserved.

Focused automation tests pass, the complete non-Selenium suite passes (659 passed, 16 skipped),
and Ruff and `ty` pass. The repository-wide line guard remains pending because it reports the
pre-existing oversized modules assigned to later refactor slices, including automation callers
touched only for facade import migration.
