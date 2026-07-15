# 14 — Deepen the Paragon capability

**What to build:** Let users select an imported Paragon build and progression step and use the overlay with unchanged board ordering, rotation, active nodes, settings, placement, and controls through one Paragon interface.

**Blocked by:** 03 — Deepen profile persistence and sessions; 04 — Deepen settings and configuration; 11 — Complete importer UI and Paragon export.

**Status:** ready-for-agent

- [ ] Paragon payload, progression-step, board, glyph, rotation, and active-node semantics remain unchanged.
- [ ] Build discovery, selection, display naming, and persisted overlay settings remain unchanged.
- [ ] Overlay creation, interaction, positioning, rendering, and closure are available through a small interface.
- [ ] Transformation logic remains independently testable without exposing overlay internals to callers.
- [ ] Every Paragon source Python file is at most 300 physical lines.
- [ ] Focused transformation and overlay tests pass.
