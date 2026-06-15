# Type the Paragon payload schema

Status: complete

## Parent

.scratch/typed-paragon-payload/PRD.md

## What to build

Make the profile's `Paragon` section a first-class typed schema. A profile should contain at most one Paragon payload, and that payload should contain one or more Paragon progression steps made of boards with valid 21x21 node grids.

The schema should reject arbitrary payload and board keys, preserve current YAML aliases, validate rotations and node counts, and normalize the tolerated legacy shapes into the canonical one-payload format.

## Acceptance criteria

- [x] Profile validation accepts one canonical Paragon payload with one or more Paragon progression steps.
- [x] Profile validation rejects multiple Paragon payloads in one profile.
- [x] Empty `Paragon` legacy list input normalizes to no Paragon payload.
- [x] Single-item `Paragon` legacy list input normalizes to one Paragon payload.
- [x] Direct board-list `ParagonBoardsList` input normalizes to one Paragon progression step.
- [x] Empty `ParagonBoardsList` fails validation.
- [x] Boards require a non-empty name.
- [x] Boards require exactly 441 node values.
- [x] All-false node grids are valid.
- [x] Rotation accepts supported values and normalizes to the canonical stored string.
- [x] Unsupported rotation values fail validation.
- [x] Unknown payload fields fail validation.
- [x] Unknown board fields fail validation, except deliberately modeled optional source IDs.
- [x] Serialized profile output keeps existing public aliases such as `Paragon`, `ParagonBoardsList`, `Name`, `Glyph`, `Rotation`, and `Nodes`.
- [x] Focused profile model tests cover valid, invalid, normalization, and serialization behavior.

## Blocked by

None - can start immediately.

## Comments

- Implemented the typed Paragon board/payload schema, legacy normalization, alias-preserving serialization, and validation coverage.
- Verified with focused tests: `137 passed, 26 skipped`.
