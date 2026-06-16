# Sigil rarity derived from the sigils.json rarities map

Diablo 4 does not expose a rarity on sigil objects, so a sigil's rarity for filtering is derived: scan the sigil's affixes (`item.affixes + item.inherent`) and the first affix found in `sigils.json["rarities"]` determines the rarity. When no affix resolves to a rarity, the sigil's rarity is unknown.

A non-empty sigil `rarity` filter is applied as an AND gate before the existing blacklist/whitelist logic. An unknown rarity is treated fail-closed: it never matches a non-empty rarity filter, so the sigil is dropped, and the unresolved lookup is logged at debug to surface gaps in the map.

## Consequences

- The `rarities` map in `sigils.json` (previously unused) becomes load-bearing; gaps in it cause otherwise-wanted sigils to be filtered out when a rarity filter is active.
- Fail-closed was chosen over fail-open so a `rarity: [rare]` filter cannot silently leak unknown-rarity sigils; the debug log is the mitigation for incomplete map coverage.
