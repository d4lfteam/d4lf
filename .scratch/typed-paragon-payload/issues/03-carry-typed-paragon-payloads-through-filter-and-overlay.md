# Carry typed Paragon payloads through filter and overlay

Status: complete

## Parent

.scratch/typed-paragon-payload/PRD.md

## What to build

Keep typed Paragon payloads after profile validation and pass them through profile loading into the Paragon overlay. The overlay should build its selectable Paragon build rows from model attributes rather than raw dictionary keys, while preserving current overlay behavior and user-facing labels.

## Acceptance criteria

- [x] Profile loading stores typed Paragon payloads for profiles that contain Paragon data.
- [x] The filter layer exposes typed Paragon payloads to Paragon consumers.
- [x] The Paragon overlay reads payload names, progression steps, boards, rotations, glyphs, and nodes from typed model attributes.
- [x] Existing overlay behavior is preserved, including newest progression step first.
- [x] Legacy shapes accepted by the profile model still reach the overlay as canonical typed payloads.
- [x] No tkinter rendering behavior is intentionally changed.
- [x] Tests cover the overlay-facing build-row seam using typed Paragon payloads.

## Blocked by

- .scratch/typed-paragon-payload/issues/01-type-paragon-payload-schema.md

## Comments

- The filter layer now exposes typed Paragon payloads and the overlay builds rows from model attributes.
- Verified with focused tests: `137 passed, 26 skipped`.
