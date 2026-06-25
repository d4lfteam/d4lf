# Domain Context

## Glossary

### Profile

A user-defined loot filtering configuration for one Diablo 4 build. A profile may include at most one stored Paragon payload for the Paragon overlay.

### Paragon payload

The stored Paragon overlay data attached to a profile. It represents one imported Paragon build, not a collection of alternative builds. A payload may contain multiple progression steps for that build.

### Paragon progression step

One board-state snapshot within a Paragon payload. Each step contains the boards and active nodes for a point in the imported build's progression.

### Item rarity

The quality tier of a droppable object: common, magic, rare, legendary, unique, or mythic. The canonical values are lowercase. For sigils the rarity is not provided by the game and is instead derived from the object's affixes.

### Rarity filter

A filter constraint listing the rarities a rule should match. An empty list matches all rarities. Spelled `rarity` (singular) in profiles; `rarities` is accepted only as a back-compat alias on tributes.
_Avoid_: `rarities` as the canonical key.

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
