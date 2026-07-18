# 16 — Deepen loot filtering modes

**What to build:** Preserve end-to-end loot evaluation and user feedback through a small loot interface that orchestrates profiles, perception, filtering, automation, vision mode fast, and vision mode with highlighting.

**Blocked by:** 02 — Deepen item models and filtering; 03 — Deepen profile persistence and sessions; 12 — Deepen TTS and item-text perception; 13 — Deepen screenshot and tooltip perception; 15 — Deepen game automation.

**Status:** resolved

- [x] Handler lifecycle, busy-state, reload, and mode selection behavior remain unchanged.
- [x] Vision mode fast continues to display tooltip-level keep or junk results.
- [x] Vision mode with highlighting continues to place affix markers on matched affix bullets.
- [x] Keep/junk overlays and automated actions preserve their current triggers and outcomes.
- [x] Every loot source Python file is at most 300 physical lines.
- [x] Focused mode and orchestration tests pass.

## Answer

Loot filtering and both vision modes now live behind the `src.loot` capability facade. The former
script implementations were moved into cohesive private modules, highlighting was split into
rendering and tooltip-worker behavior, and the shared Tk implementation moved under `src.desktop`.
The application handler selects modes and runs inventory/stash filtering through typed public
operations while preserving its locking, cancellation, restart, and reload behavior.

Fast mode reports keep and junk results immediately; highlighting preserves tooltip confirmation,
marker retry, and overlay lifecycle behavior. Focused Loot tests cover facade mode selection, stash
orchestration, fast feedback, and reliable affix-marker rendering. All new Loot and Desktop source
files remain within the 300-line limit.
