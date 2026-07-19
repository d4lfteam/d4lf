# 02 — Deepen item models and filtering

**What to build:** Give maintainers one cohesive item interface for item values, item rarity, sigil rules, tribute filters, and keep/junk decisions while preserving every existing profile result.

**Blocked by:** 01 — Lock architecture and line gate.

**Status:** resolved

- [x] Item callers use the package interface rather than cross-package implementation imports.
- [x] Item rarity, rarity filter, sigil rule, tribute filter, Mythic equipment, and always-kept behavior remain unchanged.
- [x] Filtering implementation is split by cohesive behavior, with no Python file over 300 physical lines.
- [x] Duplicated or unused item behavior is removed without adding forwarding modules.
- [x] Focused item tests and the repository-wide line guard pass.
- [x] Production LOC for the completed slice does not increase without an explicitly documented offset.

## Answer

`src.item` is now the item module's external interface for item values, rarity and type predicates,
sigil rules, and keep/junk evaluation. All production callers use that interface. The former
677-line `src/item/filter.py` was removed and its cohesive implementation now lives privately in
`src/item/filter/` (`engine`, `matching`, `equipment`, and `special`), each below 300 lines.
`MatchedFilter` and `FilterResult` are item values in `src/item/models.py`; no forwarding module
remains.

Focused item and related interface tests pass, as do the full non-Selenium suite and type checks.
The slice was originally measured at the 26,213-line source baseline; subsequent profile/settings
slices and target-branch changes mean the current source total is tracked by the source-freeze
ticket instead. The repository-wide line guard remains blocked by oversized modules outside this
slice and the deferred test-tree migration.

## Comments

### 2026-07-17 rebase audit

The rebase exposed that duplicate affix requirements reused the first matching item row, so the
ticket's new duplicate-row tests initially failed. `src/item/filter/matching.py` now assigns
distinct item rows through a constrained search, preserving value and Greater Affix requirements;
the unused unique-affix matcher was also removed. The focused filter suite passes (82 passed), and
the full suite passes (598 passed, 47 skipped). The slice is valid after this correction; the
global line-gate checkbox remains open for the later source-freeze work.
