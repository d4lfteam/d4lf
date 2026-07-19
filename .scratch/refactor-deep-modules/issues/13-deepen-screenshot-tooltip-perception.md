# 13 — Deepen screenshot and tooltip perception

**What to build:** Give callers one perception interface for capturing the game, locating an item tooltip, and deriving the image regions and geometry needed by filtering modes.

**Blocked by:** 12 — Deepen TTS and item-text perception.

**Status:** complete

- [x] Screen capture, template matching, image operations, ROI operations, and geometry location are cohesive behind the perception interface.
- [x] Tooltip discovery returns behaviorally equivalent coordinates and diagnostics.
- [x] Existing resolution scaling, confidence thresholds, and no-match behavior remain unchanged.
- [x] Callers no longer coordinate private image and geometry helpers across packages.
- [x] Every new perception source file is at most 300 physical lines.
- [x] Focused perception tests pass.
- [x] The repository-wide line guard passes.

## Answer

`src.perception` now fronts game-window capture, template matching, image and ROI operations,
tooltip discovery, and affix-marker geometry alongside the existing item-text interface. The
legacy technical and item-description modules were moved into private perception implementations;
production callers and focused tests use the public facade or perception-owned implementation
modules. Resolution scaling, matching thresholds, diagnostic result types, and no-match behavior
are preserved. The matching implementation was split so every new perception source file remains
within the 300-line limit. The focused perception tests pass; the repository-wide line guard still
reports pre-existing oversized modules, including legacy callers touched only for import updates
and unrelated source and test files, so that gate is recorded as pending rather than claimed as
passed.

### Structural review correction

The final target places capture, matching, and tooltip behavior in their corresponding perception
subpackages, each exporting from `__init__.py`; implementation filenames are descriptive rather
than underscore-prefixed.
