# PRD: Rarity filter for affixes, sigils, and tributes

Status: complete (all four slices code-complete; #502 fix approach signed off — see ADR-0003; GUI manual verification pending — GUI cannot run on Darwin, `mouse` unsupported)

## Problem Statement

As a player using loot filters, I can describe *which affixes* a rule should match, but I cannot constrain a rule to a specific item rarity. With crafting, this matters: I want to keep a common/magic/rare item that matches a rule while NOT keeping a legendary that matches the same rule (because I would craft the lower-rarity item, not the legendary). Today every rarity that matches the affixes is treated the same, so I cannot express "match these affixes, but only on rare items."

Tributes already support a rarity list, but the capability is inconsistent: affixes have no rarity filter at all, sigils have no rarity filter, and the tribute key (`rarities`) differs from what the rest of the tool will use.

## Solution

Every object that has a rarity can be filtered on rarity. A rule may list one or more rarities; an empty/absent list matches all rarities.

- **Affixes**: a filter rule gains a `rarity` constraint that narrows which item rarities the rule matches, alongside the existing item-type/power constraints.
- **Sigils**: a profile gains a global `rarity` gate. Because Diablo 4 does not expose a rarity on sigils, the rarity is derived from the sigil's affixes via the existing `sigils.json` rarities map.
- **Tributes**: keep working exactly as today, but the canonical key becomes `rarity`; `rarities` continues to load as a back-compat alias.

The profile editor lets me set affix rarities through a checkbox picker. Sigil rarity editing arrives together with the fix for the broken sigil editor (#502).

## User Stories

1. As a crafter, I want to match a rule only on rare items, so that I keep craft candidates and not the equivalent legendary.
1. As a crafter, I want to select multiple rarities on one affix rule (e.g. common, magic, rare), so that I keep all viable craft bases in a single rule.
1. As a player, I want an affix rule with no rarity set to match all rarities, so that existing rules keep behaving as before.
1. As a player, I want the affix rarity constraint to be combined with item type and power, so that "rare helms with these affixes" is expressible.
1. As a player, I want a legendary that matches an affix rule restricted to `rare` to NOT be kept by that rule, so that rarity actually narrows the match.
1. As a player, I want legendary aspect / unique / mythic keep behavior to remain unchanged when I add a rarity constraint to an affix rule, so that adding rarity doesn't silently disable unrelated keep logic.
1. As a player, I want to write affix rarities as a single value or a list, so that `rarity: rare` and `rarity: [common, magic]` both work.
1. As a player, I want rarity values to be case-insensitive on input, so that `Rare` and `rare` both load.
1. As a player, I want an invalid rarity value to be rejected with a clear error, so that typos surface instead of silently doing nothing.
1. As a player, I want to set affix rarities in the profile editor via checkboxes, so that I don't have to hand-edit YAML.
1. As a player, I want the affix rarity picker to offer all six rarities (common, magic, rare, legendary, unique, mythic), so that the control is complete.
1. As a player, I want my chosen affix rarities shown as a summary next to the rule, so that I can see the constraint without opening the picker.
1. As a player, I want a global sigil rarity gate, so that I can keep only sigils of chosen rarities regardless of dungeon.
1. As a player, I want the sigil rarity gate to combine with my blacklist/whitelist as an AND, so that a sigil must pass rarity AND survive blacklist/whitelist to be kept.
1. As a player, I want a sigil whose rarity cannot be resolved to be dropped when a sigil rarity filter is active, so that unknown-rarity sigils don't leak through a `rarity: [rare]` gate.
1. As a player, I want unresolved sigil rarities logged at debug, so that gaps in the rarities map can be diagnosed.
1. As a player with an empty sigil rarity list, I want all sigil rarities to pass the gate, so that the gate is opt-in.
1. As an existing tribute user, I want my profile written with `rarities` to keep loading, so that the rename doesn't break me.
1. As a tribute user, I want `rarity` to be the documented key going forward, so that the vocabulary is consistent across the tool.
1. As a player, I want one consistent rarity vocabulary across affixes, sigils, and tributes, so that I don't have to remember per-section spellings.
1. As a player, I want the broken sigil editor (#502) usable so that I can edit sigil rules — including the new rarity gate — in the GUI.
1. As a maintainer, I want the rarity normalization logic in one shared place, so that affixes and tributes parse rarities identically.

## Implementation Decisions

Split into two releases:

- **Release 1 — affix rarity + tribute vocabulary unification.**
- **Release 2 — #502 sigil-editor fix bundled with sigil rarity (model, filter, GUI).**

### Canonical key and parsing (ADR-0001)

- Canonical profile key is singular `rarity`, holding a list. Empty/absent = match all rarities.
- The Pydantic field stays named `rarities` internally so filter code keeps reading `model.rarities`; only the serialization/validation aliases change. `rarity` is the serialization alias and a validation alias on all rarity-bearing models. On tributes, `rarities` is *also* a validation alias for back-compat.
- A single shared normalizer parses rarity input everywhere: bare string → single-element list, case-folded to lowercase, then strictly validated against the `ItemRarity` enum (invalid values raise). This replaces the tribute-specific parsing while preserving its lenient input behavior.

### Affix rarity (Release 1)

- `ItemFilterModel` gains the `rarity` constraint, a sibling of item type and power.
- Filtering: rarity is an item-level gate evaluated once per filter rule (next to the existing item-type check), not inside the per-affix matching loop. If the rule's rarity list is non-empty and the item's rarity is not in it, the rule does not match (skip to next rule).
- The affix rarity gate only narrows the affix-matching path. The separate keep paths in `should_keep` — legendary aspect/codex upgrade, global uniques, mythic-always-keep — are unchanged and still override.
- Allowed values: all six `ItemRarity` members. (Unique/mythic on an affix rule are largely inert because uniques without a matched unique-aspect are already skipped; this is accepted rather than special-cased.)

### Sigil rarity (Release 2, ADR-0002)

- `SigilFilterModel` gains a top-level `rarity` list (sibling of `priority`/blacklist/whitelist). Empty = all. It is a global gate over every sigil, not per blacklist/whitelist entry.
- Rarity derivation: scan the sigil's affixes (item affixes + inherent); the first affix found in the `sigils.json` `rarities` map yields the rarity. No match = unknown.
- Gate semantics: when the rarity list is non-empty, apply it as an AND gate *before* the existing blacklist/whitelist logic. A sigil whose rarity is not in the list is dropped.
- Unknown rarity is fail-closed: it never matches a non-empty rarity filter (sigil dropped), and the unresolved lookup is logged at debug.
- #502 fix (sigil editor cannot blacklist global top-level affixes without a dungeon) is bundled into this release as a prerequisite for adding the sigil rarity GUI control. Fix approach (ADR-0003): the editor derives a `kind` (`affix`/`dungeon`) from the rule name — no schema change. Affix-kind rows render only the affix picker (condition UI hidden) and act as a global blacklist/whitelist; dungeon-kind rows are unchanged. Name validation stays loose (combined affix+dungeon pool).

### GUI

- Affix editor (Release 1): add a "Rarities:" row to the affix group editor, directly after "Item Types:", as a read-only summary line plus a "..." button opening a new checkbox-based rarity picker that mirrors the existing item-type picker. All six rarities offered.
- Sigil editor (Release 2): add a rarity control to the sigil tab on top of the #502-fixed editor.
- Tribute editor: no change required; it reads the `rarities` field which is unaffected by the alias work.

## Testing Decisions

Good tests assert external behavior — what a profile parses into, and what `Filter.should_keep` keeps — not internal helper calls.

### Seam 1 — model parsing (`tests/config/models_test.py`)

Drives `ProfileModel(**data)` / `ItemFilterModel` / `TributeFilterModel`. Cover:

- Affix `rarity` parses from single string, from list, and case-insensitively.
- Invalid rarity value is rejected.
- Empty/absent rarity parses to all-match (empty list).
- Tribute back-compat: `rarities` still loads; `rarity` is the canonical serialized key.

Prior art: `test_camelcase_input`, `test_snake_case_input`, `test_parse_from_string`, and the existing `TributeFilterModel` parse tests in the same file.

### Seam 2 — filter behavior (`tests/item/filter/filter_test.py`)

Drives `Filter.should_keep(item)` and asserts matched profile names. Cover:

- Affix rule with `rarity: [rare]` keeps a matching rare item and does NOT match a legendary with the same affixes.
- Affix rule with empty rarity matches all rarities (regression).
- Sigil rarity gate keeps only listed rarities; AND with blacklist/whitelist.
- Sigil with unresolved rarity is dropped when a sigil rarity filter is active.

Prior art: `test_affixes`, `test_sigils`, `test_sigil_empty_lists`, and the data fixtures in `tests/item/filter/data/` (`items.py`, `filters.py`, `sigils.py`, `tributes.py`). Use `_create_mocked_filter` to reset the singleton.

### GUI

Manually verified by launching the profile editor and exercising the rarity picker. No automated GUI tests (the repo has no profile-editor tests).

## Out of Scope

- Importers: no importer changes; rarity is a user-set filter constraint, not imported build data.
- Populating or auditing the `sigils.json` rarities map. The feature consumes whatever coverage exists; gaps surface via the debug log.
- Per-entry sigil rarity (rarity attached to individual blacklist/whitelist entries). The gate is global.
- Tribute GUI changes and any change to tribute keep behavior.
- The detailed design of the #502 sigil-editor fix is recorded in ADR-0003 (kind derived from name; affix-kind hides condition UI).

## Further Notes

- ADR-0001 records the canonical-`rarity`-with-`rarities`-alias decision; ADR-0002 records the sigil rarity derivation and fail-closed-on-unknown decision; ADR-0003 records the #502 sigil-editor affix/dungeon kind split. All live in `docs/adr/`.
- CONTEXT.md defines "Item rarity" and "Rarity filter"; use that vocabulary (`rarity`, not `rarities`) in implementation and tests.
- Release 2 bundles a bugfix (#502) with a feature; keep the commits separable for review/revert.
