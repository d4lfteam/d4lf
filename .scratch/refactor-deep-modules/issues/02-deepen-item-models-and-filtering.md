# 02 — Deepen item models and filtering

**What to build:** Give maintainers one cohesive item interface for item values, item rarity, sigil rules, tribute filters, and keep/junk decisions while preserving every existing profile result.

**Blocked by:** 01 — Lock architecture and line gate.

**Status:** resolved

- [x] Item callers use the package interface rather than cross-package implementation imports.
- [x] Item rarity, rarity filter, sigil rule, tribute filter, Mythic equipment, and always-kept behavior remain unchanged.
- [x] Filtering implementation is split by cohesive behavior, with no Python file over 300 physical lines.
- [x] Duplicated or unused item behavior is removed without adding forwarding modules.
- [ ] Focused item tests and the repository-wide line guard pass.
- [x] Production LOC for the completed slice does not increase without an explicitly documented offset.

## Answer

`src.item` is now the item module's external interface for item values, rarity and type predicates,
sigil rules, and keep/junk evaluation. All production callers use that interface. The former
677-line `src/item/filter.py` was removed and its cohesive implementation now lives privately in
`src/item/filter/` (`engine`, `matching`, `equipment`, and `special`), each below 300 lines.
`MatchedFilter` and `FilterResult` are item values in `src/item/models.py`; no forwarding module
remains.

Focused item and related interface tests pass (101 passed, 1 skipped), as do the full non-Selenium
suite and type checks. After rebasing onto `vision-mode-improvements`, production source is 26,213
lines, exactly at the 26,213 baseline. The target branch contributed eight perception and vision
lines, offsetting the eight-line reduction from this item slice; no new item filtering source
violation was introduced. The repository-wide line guard remains blocked by oversized modules
outside this slice and the deferred test-tree migration.
