# 16 — Deepen loot filtering modes

**What to build:** Preserve end-to-end loot evaluation and user feedback through a small loot interface that orchestrates profiles, perception, filtering, automation, vision mode fast, and vision mode with highlighting.

**Blocked by:** 02 — Deepen item models and filtering; 03 — Deepen profile persistence and sessions; 12 — Deepen TTS and item-text perception; 13 — Deepen screenshot and tooltip perception; 15 — Deepen game automation.

**Status:** ready-for-agent

- [ ] Handler lifecycle, busy-state, reload, and mode selection behavior remain unchanged.
- [ ] Vision mode fast continues to display tooltip-level keep or junk results.
- [ ] Vision mode with highlighting continues to place affix markers on matched affix bullets.
- [ ] Keep/junk overlays and automated actions preserve their current triggers and outcomes.
- [ ] Every loot source Python file is at most 300 physical lines.
- [ ] Focused mode and orchestration tests pass.
