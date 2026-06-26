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

### Sigil rule

A profile rule that matches sigils through a blacklist or whitelist.

### Sigil rule target

The dungeon or affix named by a sigil rule. A dungeon target scopes the rule to one sigil dungeon; an affix target applies across sigils that carry that affix.
_Avoid_: sigil kind.
