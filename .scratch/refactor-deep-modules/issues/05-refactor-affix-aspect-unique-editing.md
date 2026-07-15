# 05 — Refactor affix, aspect, and unique profile editing

**What to build:** Preserve the complete equipment-rule editing experience while localizing affix pools, aspects, uniques, item-type selection, and their dialogs inside the profile capability.

**Blocked by:** 02 — Deepen item models and filtering; 03 — Deepen profile persistence and sessions; 04 — Deepen settings and configuration.

**Status:** ready-for-agent

- [ ] Users can create, edit, summarize, and remove affix pools with unchanged validation and saved output.
- [ ] Aspect upgrade and global unique editing preserve existing mutual-exclusion and rarity behavior.
- [ ] Item type, set, rarity, minimum power, and Greater Affix Count controls preserve existing behavior.
- [ ] Shared editor behavior is cohesive and private to the profile capability rather than a generic GUI bucket.
- [ ] Every touched source Python file is at most 300 physical lines.
- [ ] Focused profile-editor tests and the line guard pass.
