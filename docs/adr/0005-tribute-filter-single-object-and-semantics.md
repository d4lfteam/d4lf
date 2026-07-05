# Tribute filter as a single object with AND semantics, breaking on old shape

Tributes previously stored `Tributes:` as a list of independent rules, each specifying either a
`name` or a `rarity` (never both), combined with OR semantics. This was inconsistent with Affixes
and Sigils, where a single rule ANDs all of its fields together (rarity is a gate, not an
alternative) and OR-style alternatives come from defining multiple named rules in the profile. We
changed `tributes` to a single `TributeFilterModel` object (`name` list + `rarity` list, ANDed
together, each empty list meaning "unconstrained"), matching the Sigils shape and the
Affixes/Sigils AND convention.

We chose to make this a breaking change rather than auto-migrating old list-shaped `Tributes:`
profiles, with a custom validation-error guidance message (mirroring the existing
`minGreaterAffixCount` legacy guidance) pointing users at the old/new YAML shapes. Auto-migration
was rejected: it would need to guess how independent OR'd name-only/rarity-only rules collapse into
one ANDed rule, and that guess could silently change which items a filter keeps.

## Considered Options

- **Auto-migrate old list shape into the new object** — rejected: the old OR semantics has no
  faithful, unsurprising translation into the new AND semantics; a silent migration could change
  filter behavior without the user noticing.
- **Keep OR semantics for names/rarities on the new object** — rejected: would leave Tributes as
  the only filter type where fields alternate instead of gate, defeating the purpose of the
  consistency fix the issue asked for.

## Consequences

- Existing profiles using the old `Tributes:` list format will fail validation and must be
  hand-edited to the new shape; the error message includes before/after YAML samples.
- Users who relied on OR semantics (e.g. "keep this tribute at any rarity, OR keep any legendary
  tribute") must now express that as two separate named profile rules, same as Affixes/Sigils
  users already do.
