# Mythic equipment is imported and filtered exactly like Unique equipment

Mythics used to be a completely separate class of item, so every build-guide importer (maxroll, d4builds, mobalytics, infinitybuilds) special-cased them: a mythic equipment item's affixes were discarded, its name was stashed in a `mythic_names` list, and the pipeline lumped all of them into one catch-all `"Mythics"` `ItemFilterModel` with an empty `item_type` and no `affix_pool` — matching by name only, across all item types at once. In the current game, a Mythic is mechanically a Unique with a different (purple) rarity value: same one unique aspect, same handful of normal affixes. The filter engine (`_check_unique_aspects_for_item`, `_check_affixes`) already treated `ItemRarity.Mythic` and `ItemRarity.Unique` identically, so the lumping was purely an importer-side artifact, and it produced strictly worse profiles than treating mythics as uniques: no `item_type`, no affix matching, just a name.

## Decision

For equipment, every importer now treats `rarity in (unique, mythic)` as one case: assign `unique_aspect` from the item's name, resolve `item_type` normally, and build `affix_pool`/`inherent_pool` from parsed affixes with `minCount=1` (same as uniques). The `mythic_names` list, the `Variant.mythic_names` field, and `add_mythics_to_filters`/the `"Mythics"` bucket are removed entirely. If no affixes could be parsed for a named unique/mythic item, the item is still kept (matched by `unique_aspect` alone) rather than silently dropped — this already applied to seal/charm imports and now applies uniformly to equipment too.

This equivalence is scoped to **equipment only**. Seals, charms, tributes, and sigils keep their existing, separate mythic handling (e.g. `filter.py`'s "always keep a mythic seal/charm/tribute regardless of match" fallback), which is untouched by this change. The pre-existing "always keep every mythic" fallback in `should_keep()` for equipment is also untouched: it now only matters as a safety net if the imported (or hand-written) affix filter genuinely doesn't match, since normal affix matching is tried first.

## Consequences

- Profiles generated from build guides now filter mythic equipment on its actual stats, not just its name, matching how uniques already work.
- infinitybuilds.py required a small reordering: it resolves gear and seal/charm items in one shared loop, so the mythic branch had to move to run alongside (not before) the existing unique-vs-non-unique logic rather than short-circuiting earlier.
- Old profiles that already contain a `"Mythics"` section from a previous import continue to load and function unchanged — `ProfileModel` doesn't care about section names, only content.
