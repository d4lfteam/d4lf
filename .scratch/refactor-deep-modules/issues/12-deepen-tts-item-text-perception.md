# 12 — Deepen TTS and item-text perception

**What to build:** Give filtering modes one perception interface that receives Diablo IV accessibility text and returns equivalent parsed item descriptions on Windows while remaining safely callable on other platforms.

**Blocked by:** 02 — Deepen item models and filtering; 04 — Deepen settings and configuration.

**Status:** complete

- [x] Named-pipe TTS acquisition preserves its Windows runtime behavior.
- [x] Windows and no-op TTS adapters satisfy one real seam without compatibility forwarding modules.
- [x] Equipment, sigil, charm, seal, tribute, rarity, affix, and aspect text parses to equivalent item values.
- [x] Parser errors and incomplete descriptions remain observable through established behavior.
- [x] Every perception source file in this slice is at most 300 physical lines.
- [x] Focused TTS/parser tests and the perception line guard pass.

## Answer

`src.perception` now fronts item-text acquisition and parsing. Its Windows and no-op adapters share
one TTS backend contract, preserving the named pipe, queue, disconnect, connection-state, and
non-Windows behavior. The parser was split into private perception modules, while
`parse_item_text` and latest-item access provide the public typed seam. Item-text helpers moved
with the capability, and production callers no longer import the removed TTS/parser modules.

Parser equivalence coverage now runs on every platform: 40 focused perception/parser tests pass,
and the full non-Selenium suite passes (654 passed, 16 skipped). Every new perception source file
is at most 300 lines, and Ruff, ty, compilation, and diff checks pass. The repository-wide line
hook still reports pre-existing oversized modules outside this slice.

### Structural review correction

The final perception layout exposes `backend` and `parser` as package facades, with sibling
`capture`, `matching`, and `tooltip` seams. Implementations use descriptive names, not
underscore-prefixed privacy markers.
