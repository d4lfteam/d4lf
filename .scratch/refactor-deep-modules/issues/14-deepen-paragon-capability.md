# 14 — Deepen the Paragon capability

**What to build:** Let users select an imported Paragon build and progression step and use the overlay with unchanged board ordering, rotation, active nodes, settings, placement, and controls through one Paragon interface.

**Blocked by:** 03 — Deepen profile persistence and sessions; 04 — Deepen settings and configuration; 11 — Complete importer UI and Paragon export.

**Status:** resolved

- [x] Paragon payload, progression-step, board, glyph, rotation, and active-node semantics remain unchanged.
- [x] Build discovery, selection, display naming, and persisted overlay settings remain unchanged.
- [x] Overlay creation, interaction, positioning, rendering, and closure are available through a small interface.
- [x] Transformation logic remains independently testable without exposing overlay internals to callers.
- [x] Every Paragon source Python file is at most 300 physical lines.
- [x] Focused transformation and overlay tests pass.

## Answer

Paragon now has a public `src.paragon` capability facade for transformations, build discovery,
display naming, and overlay lifecycle operations. The former root transformation and overlay modules
were removed; overlay rendering, interaction, placement, persisted settings, and closure behavior
were split into private capability modules, each below 300 lines. Importing, profile, script, and
test callers use the facade while payload and profile value ownership remains in `src.profiles`.

Focused Paragon/import/profile/filter coverage passes (298 passed, 7 skipped), and the complete
non-Selenium suite passes (654 passed, 16 skipped). Ruff, `ty`, compilation, and focused lifecycle
dispatch checks pass. The repository-wide line hook still reports oversized modules assigned to
later refactor slices; every new Paragon source file passes the 300-line limit.

### Structural review correction

The final Paragon layout exposes `src.paragon.overlay` as a package facade. Importing uses one
common `src.importing.paragon` module; provider-specific extraction remains in each provider
package.
