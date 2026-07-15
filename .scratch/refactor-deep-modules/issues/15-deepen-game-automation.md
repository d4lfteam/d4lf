# 15 — Deepen game automation

**What to build:** Give filtering modes one platform-neutral automation interface for locating Diablo IV, handling input, moving the pointer, and acting on inventory, stash, and vendor items without changing user-visible behavior.

**Blocked by:** 04 — Deepen settings and configuration; 13 — Deepen screenshot and tooltip perception.

**Status:** ready-for-agent

- [ ] Windows and no-op window adapters satisfy one real seam.
- [ ] Hotkeys, process discovery, window coordinates, and human-like pointer movement preserve established behavior.
- [ ] Inventory, stash, vendor, and loot-movement actions preserve their ordering and safety checks.
- [ ] Callers no longer coordinate private window, mouse, process, and inventory helpers.
- [ ] Every touched source Python file is at most 300 physical lines.
- [ ] Focused automation tests and the line guard pass.
