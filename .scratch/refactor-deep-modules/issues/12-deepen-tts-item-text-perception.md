# 12 — Deepen TTS and item-text perception

**What to build:** Give filtering modes one perception interface that receives Diablo IV accessibility text and returns equivalent parsed item descriptions on Windows while remaining safely callable on other platforms.

**Blocked by:** 02 — Deepen item models and filtering; 04 — Deepen settings and configuration.

**Status:** ready-for-agent

- [ ] Named-pipe TTS acquisition preserves its Windows runtime behavior.
- [ ] Windows and no-op TTS adapters satisfy one real seam without compatibility forwarding modules.
- [ ] Equipment, sigil, charm, seal, tribute, rarity, affix, and aspect text parses to equivalent item values.
- [ ] Parser errors and incomplete descriptions remain observable through established behavior.
- [ ] Every perception source file in this slice is at most 300 physical lines.
- [ ] Focused TTS/parser tests and the line guard pass.
