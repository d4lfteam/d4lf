# Typed Paragon Payload Profile Schema

Status: complete

## Problem Statement

Paragon payload data in a profile is currently typed as an open-ended mapping or list of mappings. That lets malformed Paragon overlay data pass profile validation and pushes schema assumptions into importer and overlay code. A profile can currently contain arbitrary Paragon data, even though the application expects a specific shape: one Paragon payload with a build name, optional metadata, and one or more Paragon progression steps made of 21x21 board node grids.

This weak typing makes the Paragon overlay fragile. Importers can write incomplete or malformed payloads, profile loading can accept data the overlay cannot render, and future changes do not have a clear schema contract.

## Solution

Make the profile's `Paragon` section a first-class Pydantic model instead of a free-form object.

The profile schema should represent exactly one stored Paragon payload per profile. That payload can contain multiple Paragon progression steps for the same imported build. Legacy single-payload list shapes should still be accepted as migration tolerance, but profile export should write one payload object, not a list.

Paragon import builders should return the typed Paragon payload model so malformed importer output fails before profile save. Profile loading should keep typed Paragon payloads through the filter layer. The Paragon overlay should consume typed model attributes instead of raw dictionary keys.

## User Stories

1. As a profile author, I want invalid Paragon data to fail validation, so that broken profile files do not silently reach the overlay.
1. As a profile author, I want clear validation errors for malformed Paragon data, so that I can fix profile YAML manually when needed.
1. As a profile author, I want a profile to contain at most one Paragon payload, so that the profile schema matches the intended domain model.
1. As a profile author with older data, I want a legacy single-item `Paragon` list to keep loading, so that existing profiles do not break unnecessarily.
1. As a profile author with bad older data, I want a multi-item `Paragon` list to be rejected, so that ambiguous multiple-payload profiles are not treated as supported.
1. As a profile author, I want profile export to write `Paragon` as one object, so that new files follow the canonical schema.
1. As a profile author, I want `ParagonBoardsList` to support multiple Paragon progression steps, so that leveling or progression states remain available.
1. As a profile author with older data, I want a direct board list in `ParagonBoardsList` to normalize into one progression step, so that simple old payloads still load.
1. As a profile author, I want an empty `ParagonBoardsList` to fail validation, so that a stored Paragon payload always contains renderable board data.
1. As a profile author, I want each Paragon board to require a name, so that the overlay can present readable board choices.
1. As a profile author, I want each Paragon board to require exactly 441 node values, so that every board represents the expected 21x21 grid.
1. As a profile author, I want all-false node grids to be valid, so that a board can exist before selected nodes are present.
1. As a profile author, I want board rotation to accept common input forms and normalize to the current stored string format, so that profile YAML stays compatible.
1. As a profile author, I want only supported rotations to validate, so that the overlay never receives impossible board angles.
1. As a profile author, I want unknown Paragon payload keys to be rejected, so that typos and unsupported metadata do not become accidental schema.
1. As a profile author, I want unknown Paragon board keys to be rejected, so that source-specific data must be deliberately modeled.
1. As a Maxroll importer user, I want imported board IDs and glyph IDs to remain supported, so that useful source metadata is not lost.
1. As a Mobalytics importer user, I want imported Paragon data to validate before saving, so that bad source extraction fails early.
1. As a D4Builds importer user, I want reconstructed Paragon data to validate before saving, so that DOM parsing mistakes are caught.
1. As a Paragon overlay user, I want the overlay to read typed Paragon payloads, so that runtime rendering no longer depends on arbitrary dictionaries.
1. As a maintainer, I want the filter layer to expose typed Paragon payloads, so that downstream code has a clear contract.
1. As a maintainer, I want tests around the profile schema, so that future Paragon changes cannot weaken validation accidentally.
1. As a maintainer, I want tests around serialization aliases, so that generated YAML remains compatible with existing profile conventions.
1. As a maintainer, I want legacy normalization covered by tests, so that compatibility behavior is intentional and documented.
1. As a maintainer, I want importer return types to be precise, so that `dict[str, Any]` does not keep spreading through Paragon code.
1. As a maintainer, I want profile model errors to identify the faulty Paragon field, so that support/debugging is faster.
1. As a maintainer, I want the existing overlay UI behavior preserved, so that this schema fix does not become a UI rewrite.
1. As a maintainer, I want no new concept of alternative Paragon builds inside one profile, so that the domain model stays simple.
1. As a maintainer, I want optional payload metadata to remain optional, so that stripped or manually authored profiles can still be valid.
1. As a maintainer, I want generated payload metadata to continue being written by importers, so that saved profiles still show source and generator context.

## Implementation Decisions

- Add a dedicated Paragon board model to the profile schema. It should model board name, glyph, rotation, node grid, and known optional source IDs.
- Add a dedicated Paragon payload model to the profile schema. It should model payload name, optional source metadata, and the payload's Paragon progression steps.
- The profile's `Paragon` field should become `ParagonPayloadModel | None`.
- A profile may include at most one stored Paragon payload. Multiple Paragon payloads in one profile are not part of the supported domain model.
- A Paragon payload may contain multiple Paragon progression steps. Each step is a list of Paragon boards.
- Legacy `Paragon: [payload]` input should normalize to `Paragon: payload`.
- Legacy `Paragon: []` input should normalize to no Paragon payload.
- Legacy `Paragon: [payload1, payload2]` input should fail validation with a clear error.
- Official `ParagonBoardsList` shape is a list of progression steps.
- Legacy direct board-list input in `ParagonBoardsList` should normalize to one progression step.
- Empty `ParagonBoardsList` should fail validation.
- Board `Nodes` must contain exactly 441 boolean-compatible values.
- Board `Nodes` may be all false.
- Board `Rotation` should export as the current string format: `0°`, `90°`, `180°`, or `270°`.
- Rotation input may accept integer or digit-only string forms, but validation should normalize to the canonical stored string.
- Payload metadata fields such as source URL, generated timestamp, and generator should be optional strings.
- Unknown fields should be forbidden on Paragon payloads and boards.
- Known optional Maxroll metadata such as board ID and glyph ID should stay modeled.
- Paragon import builders should return the typed Paragon payload model, not a raw dictionary.
- The filter layer should store and expose typed Paragon payload models.
- The Paragon overlay should consume typed model attributes rather than dictionary key lookups.
- Profile serialization should keep existing public YAML aliases such as `Paragon`, `ParagonBoardsList`, `Name`, `Glyph`, `Rotation`, and `Nodes`.
- Exported profiles should write the canonical one-payload shape, even when input used a legacy tolerated shape.
- No ADR is needed for this change. The decision is a schema tightening with compatibility rules, not a hard-to-reverse architectural trade-off.

## Testing Decisions

- Tests should assert external behavior: profile validation, normalized model values, serialization output, importer-builder return behavior, and overlay-facing loaded data shape.
- Add profile model tests following the existing config model test style.
- Cover valid Paragon payload construction with canonical aliases.
- Cover snake-case and alias behavior where it matters for existing model conventions.
- Cover rejection of unknown payload fields.
- Cover rejection of unknown board fields.
- Cover missing required payload name.
- Cover missing required board name.
- Cover missing nodes.
- Cover node count shorter than 441.
- Cover node count longer than 441.
- Cover all-false nodes as valid.
- Cover valid rotations for 0, 90, 180, and 270 degrees.
- Cover invalid rotations.
- Cover rotation normalization from integer and string inputs if implemented.
- Cover legacy `Paragon: []` normalization.
- Cover legacy `Paragon: [payload]` normalization.
- Cover legacy multi-payload list rejection.
- Cover canonical `ParagonBoardsList` list-of-steps input.
- Cover legacy direct board-list normalization to one progression step.
- Cover serialization with aliases so saved YAML keeps existing field names.
- Cover importer builder returning a typed Paragon payload model.
- Cover the filter layer returning typed Paragon payloads after profile load where practical with existing filter tests.
- Keep overlay tests focused at the seam where typed models are converted into overlay build rows; avoid testing tkinter rendering internals.
- Prior art exists in the current profile model tests, importer tests, and filter profile-loading tests.

## Out of Scope

- Changing Paragon overlay UI behavior.
- Changing board rendering, node layout, or rotation math.
- Supporting multiple alternative Paragon payloads inside one profile.
- Adding a migration command that rewrites profile files on disk.
- Adding new Paragon importer sources.
- Validating whether a board name, glyph name, board ID, or glyph ID exists in Diablo 4 game data.
- Changing how item, sigil, tribute, or aspect profile sections are modeled.
- Reworking profile editor UI to edit Paragon payloads manually.

## Further Notes

The domain glossary defines a profile as a user-defined loot filtering configuration for one Diablo 4 build. A profile may include at most one stored Paragon payload. A Paragon payload represents one imported Paragon build and may contain multiple Paragon progression steps.

This PRD deliberately preserves current YAML names and the current importer payload concept while replacing the permissive `dict[str, object] | list[dict[str, object]]` schema with a strict model.

Verified with focused tests: `172 passed, 6 skipped`.
