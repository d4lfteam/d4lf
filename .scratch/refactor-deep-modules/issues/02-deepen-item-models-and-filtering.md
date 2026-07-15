# 02 — Deepen item models and filtering

**What to build:** Give maintainers one cohesive item interface for item values, item rarity, sigil rules, tribute filters, and keep/junk decisions while preserving every existing profile result.

**Blocked by:** 01 — Lock architecture and line gate.

**Status:** ready-for-agent

- [ ] Item callers use the package interface rather than cross-package implementation imports.
- [ ] Item rarity, rarity filter, sigil rule, tribute filter, Mythic equipment, and always-kept behavior remain unchanged.
- [ ] Filtering implementation is split by cohesive behavior, with no Python file over 300 physical lines.
- [ ] Duplicated or unused item behavior is removed without adding forwarding modules.
- [ ] Focused item tests and the line guard pass.
- [ ] Production LOC for the completed slice does not increase without an explicitly documented offset.
