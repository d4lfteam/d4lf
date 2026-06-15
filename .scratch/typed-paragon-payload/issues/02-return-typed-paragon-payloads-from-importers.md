# Return typed Paragon payloads from importers

Status: complete

## Parent

.scratch/typed-paragon-payload/PRD.md

## What to build

Change Paragon importer payload construction so imported Paragon data becomes a typed Paragon payload before it is assigned to a profile. Maxroll, Mobalytics, and D4Builds imports should still save the same user-facing YAML shape, but malformed extracted payloads should fail at the importer/profile boundary instead of reaching the overlay.

## Acceptance criteria

- [x] Paragon payload construction returns the typed Paragon payload model instead of a raw mapping.
- [x] Maxroll Paragon import preserves board IDs and glyph IDs where present.
- [x] Mobalytics Paragon import still produces valid payloads from existing extracted board and node data.
- [x] D4Builds Paragon import still produces valid payloads from reconstructed board data.
- [x] Importer-generated profiles still serialize with the existing Paragon YAML aliases.
- [x] Tests cover typed payload construction and at least one importer path using the builder.
- [x] Existing importer behavior unrelated to Paragon remains unchanged.

## Blocked by

- .scratch/typed-paragon-payload/issues/01-type-paragon-payload-schema.md

## Comments

- Paragon payload construction now returns `ParagonPayloadModel`, and Maxroll/Mobalytics/D4Builds paths are covered by regression tests.
- Verified with focused tests: `137 passed, 26 skipped`.
