# 13 — Deepen screenshot and tooltip perception

**What to build:** Give callers one perception interface for capturing the game, locating an item tooltip, and deriving the image regions and geometry needed by filtering modes.

**Blocked by:** 12 — Deepen TTS and item-text perception.

**Status:** ready-for-agent

- [ ] Screen capture, template matching, image operations, ROI operations, and geometry location are cohesive behind the perception interface.
- [ ] Tooltip discovery returns behaviorally equivalent coordinates and diagnostics.
- [ ] Existing resolution scaling, confidence thresholds, and no-match behavior remain unchanged.
- [ ] Callers no longer coordinate private image and geometry helpers across packages.
- [ ] Every touched source Python file is at most 300 physical lines.
- [ ] Focused perception tests and the line guard pass.
