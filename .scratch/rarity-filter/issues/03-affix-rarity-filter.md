# Affix rarity filter (model + filter + GUI)

Status: complete

## Parent

`.scratch/rarity-filter/PRD.md`

## What to build

Add a `rarity` constraint to affix filter rules, end-to-end: profile parsing, filter behavior, and the profile editor.

End-to-end behavior: a rule may list rarities; an empty/absent list matches all. The rarity is an item-level gate evaluated once per filter rule (alongside the existing item-type check), not inside the per-affix matching loop. If the rule's rarity list is non-empty and the item's rarity is not in it, the rule does not match. The gate only narrows the affix-matching path — the separate keep paths (legendary aspect/codex upgrade, global uniques, mythic-always-keep) are unchanged and still override. All six `ItemRarity` values are accepted.

GUI: add a "Rarities:" row to the affix group editor immediately after "Item Types:", as a read-only summary line plus a "..." button opening a checkbox rarity picker that mirrors the existing item-type picker, offering all six rarities.

## Acceptance criteria

- [x] `ItemFilterModel` gains the `rarity` constraint (canonical key `rarity`, via the shared normalizer from slice 01).
- [x] A rule with `rarity: [rare]` keeps a matching rare item.
- [x] A legendary with the same affixes is NOT matched by a rule restricted to `rare`.
- [x] A rule with empty/absent rarity matches all rarities (regression).
- [x] Legendary aspect / global unique / mythic keep behavior is unchanged when a rarity constraint is present. (gate lives only in `_check_affixes`; `test_global_uniques`/`test_mythic_always_kept`/`test_uniques_with_affixes` still green)
- [x] Affix editor shows a "Rarities:" row with a checkbox picker offering all six rarities and a summary line. (`RarityPicker` in `dialog.py`)
- [x] Tests: model parsing in `tests/config/models_test.py`; filter behavior in `tests/item/filter/filter_test.py` (prior art: `test_affixes`, `_create_mocked_filter`).
- [x] GUI manually verified.

## Blocked by

- `.scratch/rarity-filter/issues/01-unify-rarity-key-and-normalizer.md`
