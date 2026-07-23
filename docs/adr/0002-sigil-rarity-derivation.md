# Sigil rarity derived from the sigils.json rarities map

Diablo 4 does not expose a rarity on sigil objects, so a sigil's rarity for filtering is derived: scan the sigil's affixes (`item.affixes + item.inherent`) and the first affix found in `sigils.json["rarities"]` determines the rarity. When no affix resolves to a rarity, the sigil's rarity is unknown.

A non-empty sigil `rarity` filter is an OR selector with the whitelist: a sigil matches a profile when its derived rarity is listed or a whitelist rule matches it. Blacklist rules remain exclusions, subject to the configured priority. An unknown rarity never matches the rarity selector, but a matching whitelist rule can still keep the sigil. The unresolved lookup is logged at debug to surface gaps in the map.

## Consequences

- The `rarities` map in `sigils.json` (previously unused) becomes load-bearing for the rarity selector; gaps in it do not block explicit whitelist matches.
- A `rarity: [rare]` selector cannot silently leak unknown-rarity sigils by itself; the debug log remains the mitigation for incomplete map coverage.
