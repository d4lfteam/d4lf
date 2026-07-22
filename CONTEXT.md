# Domain Context

## Glossary

### Profile

A user-defined loot filtering configuration for one Diablo 4 build. A profile may include at most one stored Paragon payload for the Paragon overlay.

### Paragon payload

The stored Paragon overlay data attached to a profile. It represents one imported Paragon build, not a collection of alternative builds. A payload may contain multiple progression steps for that build.

### Paragon progression step

One board-state snapshot within a Paragon payload. Each step contains the boards and active nodes for a point in the imported build's progression.

### Paragon board

One node grid within a Paragon progression step, identified by a name and an optional glyph, with a rotation (0°/90°/180°/270°) applied before its active nodes are recorded.

### Item rarity

The quality tier of a droppable object: common, magic, rare, legendary, unique, or mythic. The canonical values are lowercase. For sigils the rarity is not provided by the game and is instead derived from the object's affixes. For equipment, Mythic is functionally identical to Unique — same affix pool shape (one unique aspect plus a handful of normal affixes) — differing only in the rarity value itself; filters and importers must not special-case Mythic separately from Unique for equipment. Mythic seals, charms, tributes, and sigils keep their own separate handling (e.g. always-kept-regardless-of-match rules) and are unaffected by this equivalence.

### Ancestral Mythic Unique

The visual presentation of an existing Mythic/Unique equipment item with an animated tooltip border. It is not a separate item type or rarity in D4LF.

### Rarity filter

A filter constraint listing the rarities a rule should match. An empty list matches all rarities. Spelled `rarity` (singular) in profiles; `rarities` is accepted only as a back-compat alias on tributes.
_Avoid_: `rarities` as the canonical key.

### Charm filter

A profile rule that matches charms through their affixes, rarity, unique aspect, or set.

### Seal filter

A profile rule that matches Horadric Seals through their affixes, rarity, or unique aspect.

### Profile filename

The name used when saving an imported profile file. Its default form is assembled from selectable filename parts.
_Avoid_: Build name, importer name.

### Custom profile filename

A manually entered profile filename for an import. When present, it replaces the generated profile filename rather than modifying its filename parts.
_Avoid_: Custom default.

### Filename part

One selectable component of an imported profile filename: source, season, class, build title, or variant. Selected parts are assembled in that fixed order.
_Avoid_: Build name object, filename object.

### Filename part selector

A profile importer control that chooses which filename parts appear in the generated profile filename.
_Avoid_: Filename box, build name selector.

### Variant

A named alternative within an imported build. Use this term for source-specific labels such as subbuilds.
_Avoid_: Subbuild.

### Sigil rule

A profile rule that matches sigils through a blacklist or whitelist.

### Sigil rule target

The dungeon or affix named by a sigil rule. A dungeon target scopes the rule to one sigil dungeon; an affix target applies across sigils that carry that affix.
_Avoid_: sigil kind.

### Tribute filter

A profile's tribute-matching configuration, spelled `Tributes` (plural key for historical reasons) in profiles. It is a single object with a `name` list (tribute names to keep) and a `rarity` list (rarities to keep).
A tribute is kept if its name is in the `name` list **or** its rarity is in the `rarity` list — the two fields are independent OR gates, not AND constraints. Omitting a field means that dimension is not checked. An empty object keeps nothing.
Legacy profiles that used a list of objects are silently migrated on load by merging all names and rarities into one object. A mythic tribute is always kept regardless of the filter.

### Human-like pointer movement

Automated cursor movement that resembles manual user movement through gradual travel rather than instant repositioning.
_Avoid_: Teleporting.

### Hotkey binding

A user-configured keyboard shortcut stored in a stable, human-readable vocabulary such as `ctrl+shift+f11`, independent of the operating system or input backend.
It must include at least one non-modifier key; on macOS, `cmd` and `ctrl` identify distinct physical modifiers.
_Avoid_: Backend key spec.

### Vision mode fast

A vision mode that evaluates the hovered item from TTS and displays a tooltip-level keep or junk result without marking individual affixes.
_Avoid_: full tooltip level mode.

### Vision mode with highlighting

A vision mode that evaluates the hovered item from TTS and marks the matched affixes on the item tooltip.
_Avoid_: highlighting mode, old vision mode.

### Affix marker

The on-screen marker drawn by vision mode with highlighting to indicate one matched affix on the item tooltip. The current marker is a square centered on the affix bullet.
_Avoid_: affix highlight, row highlight.
