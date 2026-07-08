# Tribute filter uses single-object semantics with OR between name and rarity

`Tributes:` accepts one object with a `name` list and a `rarity` list. A tribute is kept when
its name is in the `name` list **or** its rarity is in the `rarity` list. Omitting a key means
that dimension is not evaluated. `Tributes: {}` (both lists empty) keeps nothing.

Only the absence of the `Tributes:` key entirely means "keep all tributes".

If a profile uses the old list-shaped `Tributes:`, all names and rarities across every list entry
are merged into one object on load (migration is silent).

## Considered Options

- **OR between name and rarity** — chosen: matches user expectation that `name: [harmony], rarity: [legendary]`
  keeps tribute_of_harmony of any rarity **and** all legendary tributes of any name. Consistent with
  how sigil blacklists/whitelists work (OR within each list, separate lists are independent gates).
- **AND between name and rarity** — rejected: `name: [harmony], rarity: [legendary]` would keep
  only harmony tributes that are also legendary, silently dropping non-legendary harmonies and
  non-harmony legendaries, which is surprising and hard to reason about.
- **Support both single object and list of objects** — rejected: adds permanent schema complexity
  for an OR pattern already covered by the single-object OR semantics.

## Consequences

- `ProfileModel.tributes` is `TributeFilterModel | None`.
- Existing profiles with list-shaped `Tributes:` are silently migrated; no manual edits required.
- The profile editor only needs to handle one flat name + rarity model.
- `Tributes: {}` (empty) keeps nothing; only the absent key keeps everything.
