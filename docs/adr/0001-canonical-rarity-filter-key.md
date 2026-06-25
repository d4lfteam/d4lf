# Canonical `rarity` filter key with `rarities` back-compat alias

Rarity filtering now spans affix, sigil, and tribute filters. Tributes already shipped a plural `rarities` key, but we standardize all filters on a singular `rarity` key for one consistent vocabulary. Tributes keep `rarities` as a validation alias so existing profiles still load. Input is normalized (bare string → list, case-folded to lowercase) and then strictly validated against the `ItemRarity` enum, so the canonical stored form is always a lowercase list.

## Considered Options

- **Keep tributes on `rarities`, use `rarity` only for affixes** — rejected: two keys for the same concept across filter types is a lasting vocabulary smell.
- **Rename tributes to `rarity` with no alias** — rejected: breaks existing tribute profiles on load.

## Consequences

- Internally the Pydantic field stays named `rarities` (so filter code reads `model.rarities`); only the serialization/validation aliases differ.
- The shared normalize-then-validate helper is the single place rarity input is parsed.
