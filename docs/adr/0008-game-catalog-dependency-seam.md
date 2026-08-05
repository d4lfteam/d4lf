# Game catalog is an independent dependency seam

D4LF's localized reference data was owned by the Item capability even though Profile validation,
Perception, Importing, and Application code also consume it. That ownership created Item/Profile
cycles which were hidden with function-local imports and lazy package exports. The Game catalog is
now an independent capability: Item and Profiles both depend on its public interface, while the
catalog depends on neither. Runtime adapter selection remains the responsibility of application or
platform composition modules and must not be used to conceal capability cycles.

## Consequences

- This decision amends ADR-0006 by adding `src.game_data` as the Game catalog capability.
- Item values used to interpret catalog entries move with the catalog when sharing them through
  `src.item` would recreate the cycle.
- Capability facades use ordinary imports. Function-local imports are reserved for neither cycle
  breaking nor optional dependency hiding; optional and platform variants are selected explicitly
  by composition modules.
