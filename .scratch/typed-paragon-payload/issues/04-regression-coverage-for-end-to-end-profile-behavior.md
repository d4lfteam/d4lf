# Regression coverage for end-to-end profile behavior

Status: complete

## Parent

.scratch/typed-paragon-payload/PRD.md

## What to build

Add final regression coverage across the profile, importer, filter, and overlay seams so the typed Paragon payload contract stays intact end to end. This issue should remove or update any remaining tests or assumptions that treat Paragon data as arbitrary dictionaries or lists.

## Acceptance criteria

- [x] Tests verify a profile with canonical Paragon data can be validated, serialized, loaded, and exposed for overlay use.
- [x] Tests verify legacy tolerated Paragon shapes become canonical typed payloads before overlay use.
- [x] Tests verify invalid Paragon payloads fail before overlay use.
- [x] Tests verify importer-generated Paragon data remains compatible with profile serialization.
- [x] Any stale test expectations around `dict[str, object] | list[dict[str, object]]` are removed or updated.
- [x] Targeted tests for config models, importer payload construction, filter loading, and overlay build-row creation pass.

## Blocked by

- .scratch/typed-paragon-payload/issues/01-type-paragon-payload-schema.md
- .scratch/typed-paragon-payload/issues/02-return-typed-paragon-payloads-from-importers.md
- .scratch/typed-paragon-payload/issues/03-carry-typed-paragon-payloads-through-filter-and-overlay.md

## Comments

- Added regression coverage across schema, serialization, importer, filter, and overlay seams.
- Verified with focused tests: `137 passed, 26 skipped`.
