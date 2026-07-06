# Tribute filter supports single-rule and list-of-rules shapes

Tributes can now be configured as either:

- a single `TributeFilterModel` object
- or a list of `TributeFilterModel` objects

Rule semantics are:

- **Within one rule:** `name` and `rarity` are ANDed together.
- **Across multiple rules (list):** rules are ORed together.
- Empty `name`/`rarity` lists in a rule mean that dimension is unconstrained.

This restores support for list-shaped `Tributes:` while keeping field-level semantics consistent
with Affixes and Sigils (fields inside a rule are gates, not alternatives).

## Considered Options

- **Keep only a single object shape** — rejected: users need a concise way to express OR between
  tribute conditions without splitting into separate profiles.
- **Auto-migrate list shape into one combined object** — rejected: combining independent rules into
  one object changes behavior (OR becomes AND) and can silently drop wanted matches.

## Consequences

- Existing profiles using list-shaped `Tributes:` are valid again.
- Existing single-object `Tributes:` profiles continue to work unchanged.
- Tribute matching now evaluates list entries as OR branches while preserving AND checks inside each
  entry.
