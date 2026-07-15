# 06 — Refactor sigil, tribute, charm, and seal profile editing

**What to build:** Preserve complete editing for sigil rules, tribute filters, charms, and seals while placing their behavior behind the profile capability interface.

**Blocked by:** 02 — Deepen item models and filtering; 03 — Deepen profile persistence and sessions; 04 — Deepen settings and configuration.

**Status:** ready-for-agent

- [ ] Sigil dungeon and affix targets remain distinct and preserve blacklist and whitelist behavior.
- [ ] Tribute name and rarity remain independent OR gates, and legacy list input still migrates correctly.
- [ ] Charm and seal editing preserves set-aware affixes, rarity handling, and mutual-exclusion behavior.
- [ ] Create, remove, and selection dialogs remain behaviorally unchanged.
- [ ] Every touched source Python file is at most 300 physical lines.
- [ ] Focused editor tests and the line guard pass.
