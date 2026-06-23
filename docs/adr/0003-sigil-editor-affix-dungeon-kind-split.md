# Sigil editor affix/dungeon kind split for global affix blacklist (#502)

The sigil profile editor was dungeon-first: every sigil row rendered a "Dungeon:" picker plus a condition list, so a user could not express "blacklist this affix on every sigil" — a global, dungeon-less rule. The filter already honors such rules (`_match_affixes_sigils` matches when the named affix is present on a sigil regardless of dungeon), but the editor could not author or load them and raised `KeyError` on a top-level affix name.

## Decision

The editor classifies each sigil rule into a `kind` — `affix` or `dungeon` — and renders accordingly. `kind` is **derived from the name**, not stored:

- `derive_sigil_kind(name)` returns `dungeon` if the name is in the `sigils.json` dungeons map, otherwise `affix`. No new profile field; existing profiles load unchanged.
- `sigil_name_dict_for_kind(kind)` selects the name pool per kind (affix = minor+major+positive; dungeon = dungeons).
- An **affix-kind** row is a global blacklist/whitelist of that affix and renders only the "Affix:" picker — the condition list and Add/Remove Condition controls are hidden, because conditions are a dungeon-scoped concept.
- A **dungeon-kind** row keeps the existing "Dungeon:" picker plus condition list, unchanged.
- `CreateSigil` exposes a Kind dropdown (dungeon/affix) that repopulates the name pool.

Name validation stays loose: `SigilConditionModel.name_must_exist` checks the name is in the combined affix+dungeon dict, with no per-kind pool enforcement.

## Consequences

- No schema change and no migration; round-trips through the existing `SigilConditionModel` (`{name, condition}`).
- A name present in both pools is ambiguous and resolves to `dungeon` (dungeons checked first). Accepted: no current overlap in the data.
- Because validation is loose, a misclassified name is not rejected at load; this trades strictness for zero back-compat risk.
- This fix is a prerequisite for the sigil rarity GUI control (ADR-0002), which adds a rarity row to the same tab.
