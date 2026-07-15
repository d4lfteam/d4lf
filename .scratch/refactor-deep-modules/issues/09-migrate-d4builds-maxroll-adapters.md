# 09 — Migrate D4Builds and Maxroll adapters

**What to build:** Preserve D4Builds and Maxroll imports end to end through the normalized importing interface, including variants, filters, filenames, and Paragon output where available.

**Blocked by:** 08 — Establish the importing interface and shared pipeline.

**Status:** ready-for-agent

- [ ] Representative D4Builds imports produce behaviorally equivalent profile and Paragon results.
- [ ] Representative Maxroll imports produce behaviorally equivalent profile and Paragon results.
- [ ] Variant and filename-part selection remain unchanged for both sources.
- [ ] Both adapters use shared importing behavior rather than duplicating it.
- [ ] Every adapter source file is at most 300 physical lines.
- [ ] Focused adapter tests and the line guard pass.
