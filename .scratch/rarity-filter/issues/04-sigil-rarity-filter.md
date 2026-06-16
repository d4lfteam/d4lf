# Sigil rarity filter (model + filter + GUI)

Status: complete (GUI manual verify pending — cannot run GUI on Darwin)

## Parent

`.scratch/rarity-filter/PRD.md`

## What to build

Add a global sigil rarity gate, end-to-end: profile parsing, filter behavior with derived rarity, and the profile editor.

Per ADR-0002: Diablo 4 does not expose a rarity on sigils, so rarity is derived by scanning the sigil's affixes (affixes + inherent); the first affix found in the `sigils.json` `rarities` map yields the rarity. `SigilFilterModel` gains a top-level `rarity` list (sibling of `priority`/blacklist/whitelist); empty = all, and it gates every sigil globally rather than per blacklist/whitelist entry.

Gate semantics: when the rarity list is non-empty, apply it as an AND gate before the existing blacklist/whitelist logic — a sigil whose derived rarity is not in the list is dropped. Unknown rarity is fail-closed: it never matches a non-empty rarity filter (sigil dropped), and the unresolved lookup is logged at debug.

GUI: add a rarity control to the sigil tab, on top of the #502-fixed editor.

## Acceptance criteria

- [x] `SigilFilterModel` gains a top-level `rarity` list (canonical key `rarity`, via the shared normalizer from slice 01).
- [x] Sigil rarity is derived from the `sigils.json` rarities map (first matching affix wins). (`Filter._get_sigil_rarity`)
- [x] A non-empty `rarity` gate keeps only sigils of listed rarities and ANDs with blacklist/whitelist. (`test_sigil_rarity_and_blacklist_*`, `test_sigil_rarity_and_whitelist_drops_whitelisted_wrong_rarity`)
- [x] An empty `rarity` list lets all sigil rarities through (regression).
- [x] A sigil with unresolved rarity is dropped when a rarity filter is active, and the miss is logged at debug. (`test_sigil_rarity_gate_drops_unknown_rarity` asserts the debug log)
- [x] Sigil editor exposes a rarity control. (`SigilsTab` "Rarities:" row reusing `RarityPicker`)
- [x] Tests in `tests/item/filter/filter_test.py` (prior art: `test_sigils`, `test_sigil_empty_lists`, sigil fixtures in `tests/item/filter/data/`).
- [ ] GUI manually verified. (cannot run GUI on Darwin — `mouse` unsupported)

## Blocked by

- `.scratch/rarity-filter/issues/01-unify-rarity-key-and-normalizer.md`
- `.scratch/rarity-filter/issues/02-fix-sigil-editor-global-affix-blacklist.md`
