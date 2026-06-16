# Unify rarity key and shared normalizer

Status: complete

## Parent

`.scratch/rarity-filter/PRD.md`

## What to build

Make `rarity` the single canonical rarity key across all rarity-bearing filters, and route all rarity parsing through one shared normalizer.

End-to-end: a profile may specify rarities as a single string or a list; input is case-insensitive (`Rare` == `rare`); invalid values are rejected with a clear error; the absent/empty case means "all rarities". Tributes — the only filter that already shipped rarity — keep loading profiles written with the old plural `rarities` key, but `rarity` becomes the canonical serialized key.

Per ADR-0001: the Pydantic field stays named `rarities` internally (so filter code keeps reading `model.rarities`); only the aliases change. `rarity` is the serialization alias and a validation alias; on tributes, `rarities` is also a validation alias for back-compat. This slice introduces the shared normalize-then-strict-validate helper and rewires the tribute model onto it.

## Acceptance criteria

- [x] A tribute profile written with `rarity` loads and round-trips with `rarity` as the serialized key.
- [x] A tribute profile written with the legacy `rarities` key still loads (back-compat alias).
- [x] Rarity accepts a bare string and a list; both normalize to a lowercase list.
- [x] Rarity input is case-insensitive (`Rare`, `rare` both valid).
- [x] An invalid rarity value raises a validation error.
- [x] Empty/absent rarity normalizes to an empty list (match-all).
- [x] All rarity parsing goes through one shared helper (no tribute-specific duplicate).
- [x] Tests added in `tests/config/models_test.py` (prior art: `test_parse_from_string`, `test_camelcase_input`, existing `TributeFilterModel` parse tests).

## Blocked by

- None - can start immediately
