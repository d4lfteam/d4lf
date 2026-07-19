# Capability-first deep-module architecture

D4LF is being refactored from technical-layer packages into capability-first deep modules. Each
capability owns its behavior and exposes a deliberately small package facade through its
`__init__.py`. A caller in another capability may import only that facade. The final layout uses
descriptive, non-prefixed implementation names; a leading underscore is not the mechanism for
privacy. Privacy is enforced by package ownership and facade imports.

## Decision

The target source layout has these capability packages:

| Capability  | Package facade   | External contract                                                                               |
| ----------- | ---------------- | ----------------------------------------------------------------------------------------------- |
| Item        | `src.item`       | Item values, rules, and keep/junk evaluation.                                                   |
| Profiles    | `src.profiles`   | Profile documents and `ProfileSession` load, save, validation, and result types.                |
| Settings    | `src.settings`   | Typed settings, persistence, reload decisions, coordinates, and hotkey bindings.                |
| Importing   | `src.importing`  | A normalized import request and result, source selection, and filename assembly.                |
| Perception  | `src.perception` | Item-text acquisition and parsing, screenshot capture, tooltip location, and image diagnostics. |
| Paragon     | `src.paragon`    | Paragon payload transformation, selection, and overlay control.                                 |
| Automation  | `src.automation` | Game-window access, hotkeys, pointer movement, and inventory, stash, and vendor actions.        |
| Loot        | `src.loot`       | Filtering-mode lifecycle and orchestration through capability interfaces.                       |
| Overlay     | `src.overlay`    | Session statistics, boss-overlay lifecycle, updates, and positioning.                           |
| Desktop     | `src.desktop`    | Shared Qt/Tk primitives, dialogs, themes, activity logging, and UI-thread dispatch.             |
| Application | `src.app`        | Composition, startup, logging, update checks, and shutdown.                                     |
| Tools       | `src.tools`      | Replay and data-generation entry points.                                                        |

`src.main` remains the executable entry point. It is not a general-purpose public API. Each
capability may contain cohesive public subpackages, and each package or subpackage exposes its
deliberate interface from `__init__.py`. A subpackage may use implementation modules internally,
but callers do not import implementation paths directly. The capability root remains the only
cross-capability import location unless a subpackage is itself an explicitly documented
cross-capability seam. Application composition is the runtime place that wires multiple capability
facades together; cross-capability integration tests may compose those public facades. This rule
applies to production code, package-interface tests, test patches, build configuration, and dynamic
Windows imports. Focused unit tests may import implementation modules only from the capability that
owns the behavior under test.

Profile editor behavior is organized by public subpackage rather than a technical GUI bucket:

| Subpackage                | Responsibility                                                                         | Public interface                   |
| ------------------------- | -------------------------------------------------------------------------------------- | ---------------------------------- |
| `src.profiles.affix`      | Affix pools, item-type/rarity/power/Greater Affix controls, and reusable affix widgets | `src.profiles.affix.__init__`      |
| `src.profiles.aspect`     | Aspect-upgrade and unique-aspect editing                                               | `src.profiles.aspect.__init__`     |
| `src.profiles.unique`     | Global unique editing                                                                  | `src.profiles.unique.__init__`     |
| `src.profiles.charm_seal` | Shared charm and seal editing, dialogs, and tabs                                       | `src.profiles.charm_seal.__init__` |
| `src.profiles.sigil`      | Sigil tabs, widgets, and dialogs                                                       | `src.profiles.sigil.__init__`      |
| `src.profiles.tribute`    | Tribute tabs and dialogs                                                               | `src.profiles.tribute.__init__`    |
| `src.profiles.editor`     | Shared profile-editor primitives and profile editor composition                        | `src.profiles.editor.__init__`     |

These subpackage facades are public within the Profiles capability and do not make Qt widgets part
of the top-level `src.profiles` cross-capability contract.

Capability-root facades export behavior and domain result types, not implementation classes, GUI
widgets, or generic service locators. Capability-owned UI subpackage facades may export their
widgets, dialogs, and editor composition types to callers within that capability; those types do
not become part of the capability-root cross-capability contract. A facade grows only when a second
capability has a concrete use for the new operation. Capability-specific GUI belongs to its
capability; `src.desktop` retains only primitives with multiple real consumers.

Desktop's deliberately documented UI subpackage seams are the exceptions for reusable presentation
primitives shared by multiple capabilities:

| Subpackage             | Responsibility                                           | Public interface                              |
| ---------------------- | -------------------------------------------------------- | --------------------------------------------- |
| `src.desktop.widgets`  | Reusable Qt widgets and application accent configuration | `CheckmarkCheckBox`, `set_accent_color`       |
| `src.desktop.activity` | ANSI log presentation and thread-safe Qt log delivery    | `ANSIConsoleWidget`, `QtLogHandler`           |
| `src.desktop.themes`   | Shared dark/light Qt stylesheet templates                | `DARK_THEME_TEMPLATE`, `LIGHT_THEME_TEMPLATE` |

These subpackages are explicit cross-capability seams; their implementation modules remain private.

## Corrected final layout (structural review, 2026-07-19)

The migration inventory below records historical source paths, but the frozen target is the
following package shape. Every listed package (including nested packages) owns its public interface
in `__init__.py`; implementation files use ordinary descriptive names and never a leading
underscore.

| Area        | Final package seams                                                                                                                                                                                                                        |
| ----------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Application | `src.app.dashboard` owns dashboard controls, drag, and profile composition; `src.app` retains shell and lifecycle composition.                                                                                                             |
| Automation  | `src.automation.window` owns the window contract and real Windows/no-op adapters.                                                                                                                                                          |
| Overlay     | `src.overlay.widget` owns widget behavior; lifecycle, statistics, and tracking remain sibling seams.                                                                                                                                       |
| Paragon     | `src.paragon.overlay` owns overlay behavior; transformation and data remain under `src.paragon`.                                                                                                                                           |
| Perception  | `src.perception.backend`, `.matching`, `.capture`, `.parser`, and `.tooltip` are public subpackages with facades.                                                                                                                          |
| Profiles    | `src.profiles.affix.group` owns affix-group behavior; `src.profiles.editor.dialogs` and `.profile` own editor dialogs/profile composition. `src.profiles.validation` consolidates validation and validator behavior into cohesive modules. |
| Settings    | `src.settings.models` is the public model seam; model implementations are beneath that package.                                                                                                                                            |
| Desktop     | `src.desktop.activity`, `.themes`, and `.widgets` are implementation-bearing subpackages, each exposing its interface from `__init__.py`.                                                                                                  |
| Importing   | `src.importing.paragon` contains one common module for normalized Paragon handling. Provider-specific Paragon extraction lives in each provider package (`d4builds`, `infinitybuilds`, `maxroll`, and `mobalytics`).                       |

The mirrored unit-test tree follows this package/module shape exactly: package initializers map to
`init_test.py`, and each implementation module maps to `<module>_test.py`. Tests in one capability
may import its implementation modules; cross-capability tests use only documented facades.

## High-risk seam choices

| Seam       | Rejected design                                                                                                                                           | Chosen design                                                                                                                                                    | Why                                                                                                                                       |
| ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| Importing  | Let source adapters return their current source-specific data and have callers coordinate retries, browser setup, profile conversion, and Paragon export. | An `ImportSource` seam accepts a normalized request and returns one normalized result containing selected variant, profile output, and optional Paragon payload. | It confines source-specific extraction to adapters and preserves one coherent import flow.                                                |
| Perception | One mutable catch-all perception service with mode switches for TTS, screenshots, templates, geometry, and parsing.                                       | Small query-oriented facade operations return typed item-text, tooltip-location, and image-diagnostic results; Windows and no-op backends remain real adapters.  | It preserves useful diagnostics and separates independent acquisition and interpretation behaviors without inventing a giant abstraction. |
| Overlay    | Let callers reach a global Tk overlay and coordinate creation, rendering, update, and close operations.                                                   | An overlay lifecycle port exposes creation, update, visibility, positioning, and close behavior; rendering stays private.                                        | It preserves thread and Windows constraints while making application and loot callers independent of Tk internals.                        |
| Desktop    | Centralize all capability windows in a generic GUI utility package.                                                                                       | Keep capability UI with its owning capability and provide only reusable desktop primitives plus application-shell composition through capability facades.        | It prevents the desktop module from becoming another broad technical bucket and keeps presentation knowledge with behavior ownership.     |

The chosen seams are deliberately narrow, typed ports around demonstrated variation. They do not
authorize speculative interfaces, compatibility forwarding modules, or a registry/service-locator
layer.

## Source migration inventory

`P` is a future package facade, `X` is a narrow explicit seam re-exported by that facade, `I` is a
implementation module, and `E` is an executable entry point. Implementation modules are
package-owned rather than name-mangled. `Keep` retains a cohesive
module in its eventual capability, `Move` relocates it intact, `Split` divides it by cohesive
behavior before or while relocating it, and `Delete` requires repository-wide, PyInstaller,
dynamic-import, and Windows reachability checks before removal.

| Current module                                     | Capability owner | Role | Disposition |
| -------------------------------------------------- | ---------------- | ---- | ----------- |
| `src/__init__.py`                                  | Application      | P    | Keep        |
| `src/autoupdater.py`                               | Application      | I    | Keep        |
| `src/cam.py`                                       | Perception       | I    | Move        |
| `src/config/__init__.py`                           | Settings         | P    | Move        |
| `src/config/data.py`                               | Perception       | I    | Split       |
| `src/config/helper.py`                             | Settings         | I    | Split       |
| `src/config/loader.py`                             | Settings         | I    | Split       |
| `src/config/profile_document.py`                   | Profiles         | I    | Keep        |
| `src/config/profile_models.py`                     | Profiles         | I    | Split       |
| `src/config/profile_session.py`                    | Profiles         | X    | Keep        |
| `src/config/reload_groups.py`                      | Settings         | I    | Keep        |
| `src/config/settings_models.py`                    | Settings         | I    | Split       |
| `src/config/ui.py`                                 | Perception       | I    | Split       |
| `src/dataloader.py`                                | Item             | I    | Move        |
| `src/gui/__init__.py`                              | Desktop          | P    | Move        |
| `src/gui/importer_window.py`                       | Importing        | I    | Split       |
| `src/gui/importer/__init__.py`                     | Importing        | P    | Move        |
| `src/gui/importer/d4builds.py`                     | Importing        | I    | Split       |
| `src/gui/importer/gui_common.py`                   | Importing        | I    | Split       |
| `src/gui/importer/import_pipeline.py`              | Importing        | X    | Split       |
| `src/gui/importer/importer_config.py`              | Importing        | X    | Keep        |
| `src/gui/importer/infinitybuilds.py`               | Importing        | I    | Split       |
| `src/gui/importer/maxroll.py`                      | Importing        | I    | Split       |
| `src/gui/importer/mobalytics.py`                   | Importing        | I    | Split       |
| `src/gui/importer/paragon_export.py`               | Importing        | I    | Move        |
| `src/gui/models/__init__.py`                       | Desktop          | P    | Move        |
| `src/gui/models/activity_log_widget.py`            | Desktop          | I    | Split       |
| `src/gui/models/checkmark_checkbox.py`             | Desktop          | I    | Move        |
| `src/gui/models/collapsible_widget.py`             | Profiles         | I    | Move        |
| `src/gui/models/dialog.py`                         | Desktop          | I    | Split       |
| `src/gui/models/open_user_config_button.py`        | Desktop          | I    | Delete      |
| `src/gui/models/rule_list_tab.py`                  | Profiles         | I    | Move        |
| `src/gui/models/tab_group_widget.py`               | Profiles         | I    | Move        |
| `src/gui/open_user_config_button.py`               | Desktop          | I    | Delete      |
| `src/gui/profile_editor_window.py`                 | Profiles         | I    | Move        |
| `src/gui/profile_editor/__init__.py`               | Profiles         | P    | Move        |
| `src/gui/profile_editor/affixes_tab.py`            | Profiles         | I    | Split       |
| `src/gui/profile_editor/aspect_upgrades_tab.py`    | Profiles         | I    | Move        |
| `src/gui/profile_editor/charms_seals_group_tab.py` | Profiles         | I    | Split       |
| `src/gui/profile_editor/global_uniques_tab.py`     | Profiles         | I    | Move        |
| `src/gui/profile_editor/profile_editor.py`         | Profiles         | I    | Move        |
| `src/gui/profile_editor/sigils_tab.py`             | Profiles         | I    | Split       |
| `src/gui/profile_editor/tributes_tab.py`           | Profiles         | I    | Move        |
| `src/gui/profile_tab.py`                           | Profiles         | I    | Split       |
| `src/gui/settings_store.py`                        | Settings         | I    | Move        |
| `src/gui/settings_tab.py`                          | Settings         | I    | Split       |
| `src/gui/settings_window.py`                       | Settings         | I    | Move        |
| `src/gui/themes.py`                                | Desktop          | I    | Split       |
| `src/gui/unified_window.py`                        | Application      | I    | Split       |
| `src/item/__init__.py`                             | Item             | P    | Keep        |
| `src/item/data/__init__.py`                        | Item             | P    | Keep        |
| `src/item/data/affix.py`                           | Item             | I    | Keep        |
| `src/item/data/aspect.py`                          | Item             | I    | Keep        |
| `src/item/data/item_type.py`                       | Item             | I    | Keep        |
| `src/item/data/rarity.py`                          | Item             | I    | Keep        |
| `src/item/data/seasonal_attribute.py`              | Item             | I    | Keep        |
| `src/item/descr/__init__.py`                       | Perception       | P    | Move        |
| `src/item/descr/geometry_locator.py`               | Perception       | I    | Split       |
| `src/item/descr/read_descr_tts.py`                 | Perception       | I    | Split       |
| `src/item/descr/text.py`                           | Perception       | I    | Move        |
| `src/item/descr/texture.py`                        | Perception       | I    | Move        |
| `src/item/filter.py`                               | Item             | I    | Split       |
| `src/item/find_descr.py`                           | Perception       | I    | Move        |
| `src/item/models.py`                               | Item             | I    | Keep        |
| `src/item/sigil_rules.py`                          | Item             | X    | Keep        |
| `src/logger.py`                                    | Application      | I    | Keep        |
| `src/loot_mover.py`                                | Automation       | I    | Move        |
| `src/main.py`                                      | Application      | E    | Keep        |
| `src/overlay.py`                                   | Overlay          | X    | Move        |
| `src/paragon_overlay.py`                           | Paragon          | I    | Split       |
| `src/paragon_transform.py`                         | Paragon          | I    | Keep        |
| `src/scripts/__init__.py`                          | Loot             | P    | Move        |
| `src/scripts/common.py`                            | Loot             | I    | Split       |
| `src/scripts/handler.py`                           | Application      | X    | Split       |
| `src/scripts/info_overlay.py`                      | Overlay          | I    | Split       |
| `src/scripts/loot_filter_tts.py`                   | Loot             | I    | Move        |
| `src/scripts/vision_mode_fast.py`                  | Loot             | I    | Move        |
| `src/scripts/vision_mode_with_highlighting.py`     | Loot             | I    | Split       |
| `src/startup_messages.py`                          | Application      | I    | Keep        |
| `src/template_finder.py`                           | Perception       | I    | Split       |
| `src/tools/__init__.py`                            | Tools            | P    | Keep        |
| `src/tools/gen_data_helpers.py`                    | Tools            | I    | Keep        |
| `src/tools/gen_data.py`                            | Tools            | I    | Split       |
| `src/tools/replay_common.py`                       | Tools            | I    | Keep        |
| `src/tools/replay_cropped_tooltip.py`              | Tools            | I    | Split       |
| `src/tools/replay_full_screenshot.py`              | Tools            | I    | Move        |
| `src/tools/replay_template_matching.py`            | Tools            | I    | Move        |
| `src/tts_backend_noop.py`                          | Perception       | I    | Move        |
| `src/tts_backend_windows.py`                       | Perception       | I    | Move        |
| `src/tts.py`                                       | Perception       | X    | Split       |
| `src/ui_thread.py`                                 | Desktop          | I    | Move        |
| `src/ui/__init__.py`                               | Automation       | P    | Move        |
| `src/ui/char_inventory.py`                         | Automation       | I    | Move        |
| `src/ui/inventory_base.py`                         | Automation       | I    | Move        |
| `src/ui/menu.py`                                   | Automation       | I    | Move        |
| `src/ui/stash.py`                                  | Automation       | I    | Move        |
| `src/ui/vendor.py`                                 | Automation       | I    | Move        |
| `src/utils/__init__.py`                            | Automation       | P    | Move        |
| `src/utils/custom_mouse.py`                        | Automation       | I    | Move        |
| `src/utils/hotkeys.py`                             | Automation       | I    | Move        |
| `src/utils/image_operations.py`                    | Perception       | I    | Move        |
| `src/utils/misc.py`                                | Perception       | I    | Split       |
| `src/utils/process_handler.py`                     | Automation       | I    | Move        |
| `src/utils/roi_operations.py`                      | Perception       | I    | Move        |
| `src/utils/window_backend_noop.py`                 | Automation       | I    | Move        |
| `src/utils/window_backend_windows.py`              | Automation       | I    | Move        |
| `src/utils/window_backend.py`                      | Automation       | X    | Move        |
| `src/utils/window.py`                              | Automation       | X    | Split       |

## Baselines and gate

At this decision point, the architecture-lock commit (`3fbac7b`) contains 108 Python modules and
26,229 physical lines under `src`. The planning note recorded 26,213 lines, an undercount of 16;
26,229 is the reproducible historical source baseline. It is the maximum production-source LOC
for the refactor; any increase requires a documented offset before the source architecture can
freeze. The current 300-line guard reports 29 source and 8 test violations. Those violations are
intentional migration work, not exemptions.

The behavioral baseline on macOS is 586 passed and 47 skipped non-Selenium tests. Existing tests
are preserved while source modules move; test-tree mirroring is deferred until source architecture
is frozen.

The line gate checks every Python file below `src` and `tests` for at most 300 physical lines. It
is part of `uv run prek run -a`, and is available during a focused source slice with:

```bash
uv run --no-project hooks/check_lines.py
```

The gate configuration and hook implementation are user-owned changes already present when this
decision was recorded. This ADR documents their contract without claiming or replacing those
changes.

## Consequences

- Refactor slices move in dependency order and update every repository import, patch target, build
  reference, and dynamic Windows import to the final package path. No old-path compatibility
  module is retained.
- All capability boundaries are explicit before structural moves begin, so later tickets can
  verify placement against this inventory rather than creating new technical buckets.
- The source architecture is not frozen until all source files pass the line gate, source LOC is at
  or below the reproducible 26,229-line historical baseline (or a documented offset is approved),
  and the complete non-Selenium behavioral suite passes.
- The two modules classified for deletion remain source until their non-Python, dynamic, Windows,
  and PyInstaller reachability has been verified.

## Source-freeze audit

The source migration audit on 2026-07-18 completed the structural checks that do not require the
later mirrored test tree:

- The remaining oversized source module, importer Paragon export, is split behind the cohesive
  `src.importing.paragon` common module. Provider-specific extraction remains in each provider
  package; generic Paragon transformation and overlay behavior remain owned by `src.paragon`.
- Data loading is owned by `src.item.data.loader` and exposed from `src.item`; text-name
  normalization is owned by `src.perception`; the runtime coordinator is owned by `src.app`; and
  overlay singleton state is owned by `src.overlay`.
- The obsolete `src.dataloader`, `src.scripts`, `src.utils`, and empty parallel GUI packages were
  removed after repository-wide import and entry-point searches. Cross-capability production and
  test callers now use capability or documented subpackage facades.
- Every Python file under `src` is at most 300 physical lines. The complete non-Selenium suite
  passes at 688 passed and 16 skipped, and `ty` passes.

The historical 26,229-line budget is not yet met: the audited source tree measures 27,185 lines,
or 956 lines above the corrected baseline. The additional lines are distributed across the
capability implementations and facades introduced by the source migration; no dead or compatibility
source was found by the repository reference audit, Ruff, or Vulture. This is an explicit budget
reconciliation decision still requiring approval, not an implicit exemption.

The repository-wide `check_lines` hook also continues to report the seven pre-existing oversized
test files owned by the test-mirroring issues. All other prek hooks pass, and the complete
non-Selenium suite passes with 688 tests passed and 16 skipped. Consequently, the source structure
is not declared frozen by this audit; the source-budget decision and test-tree gate remain explicit
follow-up work rather than undocumented exemptions.

## Source-budget reconciliation

On 2026-07-19, the project owner approved the explicit 956-line production-source offset. The
accepted source budget is therefore 27,185 physical Python lines: the corrected 26,229-line
architecture-lock baseline plus the approved offset. Tests are accounted for separately and do not
explain the offset; they decreased from 10,925 to 10,896 physical Python lines over the same period.
