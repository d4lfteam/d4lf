# D4LF Codex Notes

This file is a quick codebase map for future work in this repository.
It focuses on:

- which files matter most
- what each area appears to own
- where the code is currently weak or high-risk
- what would most improve maintainability and reliability

These notes are based on the current repository structure and a read-through of the main runtime paths. They are intentionally practical rather than exhaustive.

## Top-Level Structure

- `src/main.py`
  Main application entrypoint. Starts logging, loads filters, detects the Diablo IV window, verifies TTS setup, starts script handlers, and runs the overlay loop. Also launches the Qt GUI when not in console-only mode.

- `src/gui/`
  Desktop UI layer. Contains the main window, settings UI, importer UI, activity log, themes, and profile editor tabs.

- `src/config/`
  Typed config models and INI loading/saving. This is the bridge between user settings and runtime behavior.

- `src/item/`
  Core item/filtering domain. Holds item models, affix/aspect data, description parsing, and the keep/junk decision logic.

- `src/scripts/`
  Runtime automation behaviors. Owns hotkeys, loot filtering, vision mode, and item handling workflows.

- `src/ui/`
  In-game UI abstractions like inventory, stash, vendor, and menu detection.

- `src/utils/`
  Lower-level helpers for image operations, ROI logic, process handling, mouse behavior, and window access.

- `src/paragon_overlay.py`
  Large standalone subsystem for the paragon overlay.

- `src/tts.py`
  TTS connection management.

- `tts/`
  Native DLL/signing assets for Diablo IV third-party screen reader integration.

- `tests/`
  Test suite. Coverage is strongest around filters, config, importer parsing, and some image/UI behavior.

- `build.py`
  Packaging script for generating the release folder and Windows launcher scripts.

## Key Files And Responsibilities

### Runtime entry and app boot

- `src/main.py`
  The operational heart of the app. If startup, autoupdate, overlay boot, TTS validation, or GUI launch breaks, this file is part of the path.

- `src/logger.py`
  Logging setup and formatters. Important because this project is very runtime-heavy and logs are a key debugging tool.

- `src/autoupdater.py`
  Release/update path.

### Settings and live reload

- `src/config/loader.py`
  Singleton config loader. Reads `~/.d4lf/params.ini`, validates with models, persists changes, and notifies listeners when settings change.

- `src/config/models.py`
  Very important file. Defines the shape of settings and many enums/behavior options used throughout the app.

- `src/config/ui.py`
  Resolution/UI resource support.

### Filtering and item parsing

- `src/item/filter.py`
  Core business logic for deciding whether items should be kept, junked, or matched to a profile.

- `src/item/models.py`
  Main item data structures.

- `src/item/descr/read_descr_tts.py`
  Converts TTS output into structured item data. This is one of the highest-risk pieces because it depends on game output format and parsing heuristics.

- `src/item/descr/texture.py`
  Screen-template and bullet-detection helpers used by parsing.

- `src/dataloader.py`
  Loads game/language data used by the parser and filter logic.

### Automation and in-game behavior

- `src/scripts/handler.py`
  Global hotkeys, runtime orchestration, config-change reactions, and launching/stopping automation modes.

- `src/scripts/loot_filter_tts.py`
  Filtering workflow using item TTS reads.

- `src/scripts/vision_mode_fast.py`
  Faster overlay/vision mode.

- `src/scripts/vision_mode_with_highlighting.py`
  Richer but likely more fragile/slower vision mode.

- `src/loot_mover.py`
  Inventory/stash movement behavior.

### GUI and profile authoring

- `src/gui/unified_window.py`
  Main Qt application window and embedded runtime/log display.

- `src/gui/config_tab.py`
  Settings UI. Large and central to user-facing configuration.

- `src/gui/importer_window.py`
  Build import entrypoint.

- `src/gui/importer/`
  Scrapers/importers for Maxroll, Mobalytics, D4Builds, Diablo Trade, and paragon export support.

- `src/gui/profile_editor/`
  Manual editor tabs for Affixes, Uniques, Sigils, Tributes, and Aspect Upgrades.

### Game-window and image interaction

- `src/cam.py`
  Window offsets/screen capture coordination.

- `src/template_finder.py`
  Template matching utilities.

- `src/ui/inventory_base.py`
  Base logic for inventory-like screens.

- `src/ui/char_inventory.py`
  Character inventory detection/open behavior.

- `src/ui/stash.py`
  Stash detection and interaction.

- `src/utils/window.py`
  Window discovery and screenshot helpers.

- `src/utils/image_operations.py`
  Low-level image utilities.

- `src/utils/roi_operations.py`
  Region-of-interest math.

## Where The Code Looks Weak

These are not “bad code” judgments. They are the areas most likely to cause maintenance cost, regressions, or debugging pain.

### 1. Oversized, mixed-responsibility modules

High-risk examples:

- `src/paragon_overlay.py`
- `src/item/filter.py`
- `src/config/models.py`
- `src/gui/config_tab.py`
- `src/item/descr/read_descr_tts.py`
- `src/scripts/handler.py`

Why this is weak:

- Large files usually mix domain logic, state management, and UI/runtime wiring.
- They are harder to test in isolation.
- Small changes are more likely to create accidental regressions.
- Onboarding is slower because behavior is spread across long procedural flows.

### 2. Runtime orchestration is tightly coupled

Most of the startup path flows through `src/main.py`, `src/gui/unified_window.py`, and `src/scripts/handler.py`.

Why this is weak:

- Boot behavior, hotkeys, config reload, TTS startup, overlay startup, and GUI lifecycle are all close together.
- There is not a clearly separate “application service layer” that can be tested without Qt, keyboard hooks, or the Diablo window.
- Runtime bugs may require full end-to-end reproduction rather than unit-level diagnosis.

### 3. TTS/item parsing depends on fragile heuristics

The parser path in `src/item/descr/read_descr_tts.py` is doing a lot of inference from text order, item rarity, bullet positions, and string patterns.

Why this is weak:

- A Diablo patch, font/rendering difference, language edge case, or accessibility output change can silently break parsing.
- There are many special cases by item type and season behavior.
- Regex-heavy and index-heavy parsing tends to fail in ways that are hard to reason about quickly.

### 4. UI automation and vision logic are environment-sensitive

Files involved:

- `src/cam.py`
- `src/template_finder.py`
- `src/ui/*`
- `src/scripts/vision_mode_with_highlighting.py`
- `src/utils/window.py`

Why this is weak:

- Behavior depends on resolution, screen brightness, game settings, window mode, font scale, and live pixels.
- These systems are naturally brittle and usually need very disciplined test fixtures and diagnostics.
- There are explicit TODOs in this area already, like monitor clipping in `src/cam.py` and template fallback work in `src/item/descr/texture.py`.

### 5. Config model complexity is growing

`src/config/models.py` is large and central.

Why this is weak:

- It appears to be carrying both data definitions and compatibility/workaround behavior.
- One existing inline note says part of the design was added “to not have to change much of the other code,” which is usually a sign of accumulated technical debt.
- Changes to settings can ripple into many unrelated runtime behaviors.

### 6. GUI code appears feature-rich but not strongly separated

Files like `src/gui/config_tab.py`, `src/gui/dialog.py`, and several importer/profile editor modules are fairly large.

Why this is weak:

- UI widgets may be carrying business logic, validation logic, and data transformation logic in the same place.
- That makes non-UI testing harder and increases the chance of duplicated rules between GUI and backend.

### 7. Test coverage seems lighter around app lifecycle and runtime integration

The current test layout is strongest in:

- `tests/item/`
- `tests/config/`
- `tests/gui/importer/`
- `tests/utils/`

Likely weaker coverage areas:

- full startup flow from `src/main.py`
- hotkey orchestration in `src/scripts/handler.py`
- overlay lifecycle
- live config reload interactions
- TTS connection lifecycle
- failure-mode handling around native/Windows-specific integration

Why this is weak:

- The riskiest code is often the least unit-testable, which means regressions can slip in unless higher-level tests or smoke checks exist.

## What Needs Improvement First

If the goal is to make this repo easier to extend without breaking runtime behavior, these are the highest-value improvements.

### 1. Break large files into narrower services

Priority targets:

- `src/item/filter.py`
- `src/item/descr/read_descr_tts.py`
- `src/scripts/handler.py`
- `src/gui/config_tab.py`
- `src/paragon_overlay.py`

Suggested direction:

- separate pure decision logic from side effects
- move parsing helpers into smaller modules by item type or parsing stage
- extract hotkey registration, config-reload handling, and overlay control into separate classes
- split big Qt tabs into view widgets plus plain-Python logic/helpers

### 2. Create a clearer app service boundary

Suggested direction:

- add a runtime coordinator/service layer between `main.py` and the concrete subsystems
- make startup steps explicit: config, data load, window detection, TTS validation, handler startup, overlay startup
- expose these steps in a way that can be smoke-tested without opening the full GUI

### 3. Harden parsing with more fixture-driven tests

Suggested direction:

- add more tests for TTS parsing edge cases
- group fixtures by season, item class, and failure mode
- capture known-bad examples when parser bugs are found
- test parser behavior on malformed or partially missing TTS sections, not only happy paths

### 4. Improve diagnostics for image/template failures

Suggested direction:

- standardize screenshot dumps and debug metadata when template matching fails
- log which resolution/ROI/template set was used
- make failures easier to compare across machines
- add fixture-based regression tests when bugs are reproduced from screenshots

### 5. Reduce config coupling

Suggested direction:

- keep `src/config/models.py` focused on schema and validation
- move compatibility shims and migration logic into dedicated helpers
- document which settings are live-reload safe vs restart-required in one place

### 6. Centralize domain rules

Suggested direction:

- ensure item/filtering rules live in backend/domain code, not inside multiple GUI forms
- keep importer normalization, manual editor validation, and runtime filtering aligned through shared helper functions or models

### 7. Add lightweight runtime smoke tests

Suggested direction:

- boot-level smoke tests for config load, filter load, and non-GUI service initialization
- tests for config change notifications and hotkey refresh behavior
- tests for startup failure paths where Diablo/TTS/native dependencies are missing

## Concrete Improvement Candidates By Area

### Filtering

Files:

- `src/item/filter.py`
- `src/item/models.py`
- `src/item/data/*`

Needs:

- split matching logic by category: affixes, aspects, sigils, tributes, uniques
- expose smaller pure functions with narrow inputs/outputs
- make file reload behavior easier to test without singleton/global state

### TTS and parsing

Files:

- `src/item/descr/read_descr_tts.py`
- `src/item/descr/texture.py`
- `src/tts.py`

Needs:

- isolate normalization, structural parsing, and value extraction into separate phases
- reduce hidden assumptions based on list positions where possible
- add better failure reporting when parsing falls back or guesses

### Runtime handler

Files:

- `src/scripts/handler.py`
- `src/main.py`
- `src/gui/unified_window.py`

Needs:

- separate hotkey binding, command dispatch, and lifecycle management
- reduce duplication between GUI boot flow and console boot flow
- make subsystem startup/shutdown order more explicit

### GUI

Files:

- `src/gui/config_tab.py`
- `src/gui/dialog.py`
- `src/gui/profile_editor/*`
- `src/gui/importer/*`

Needs:

- move data transformation and validation out of widgets where practical
- define smaller widget responsibilities
- share importer/profile validation logic with backend models

### Vision and window interaction

Files:

- `src/cam.py`
- `src/template_finder.py`
- `src/ui/*`
- `src/utils/window.py`

Needs:

- stronger abstraction around resolution-specific behavior
- clearer fallback behavior when templates do not match
- more deterministic diagnostics around ROI and template selection

## Existing Explicit TODO Signals

Current inline TODOs I noticed:

- `src/cam.py`
  “clip by monitor ranges”

- `src/config/models.py`
  compatibility/workaround note that should be cleaned up later

- `src/item/descr/texture.py`
  “small font template fallback”

These are useful because they point to known weak spots in screen handling, config debt, and parser robustness.

## Suggested Working Priorities

If we want a practical order of attack:

1. Add safety nets first: parser tests, startup smoke tests, and better debug dumps.
2. Refactor `src/scripts/handler.py` and `src/item/filter.py` into smaller units.
3. Split `src/item/descr/read_descr_tts.py` into clearer parsing stages.
4. Reduce GUI/business-logic mixing in the heaviest Qt modules.
5. Tackle `src/paragon_overlay.py` once the core runtime seams are cleaner.

## Bottom Line

The project already has a solid domain shape:

- config
- filter logic
- parsing
- GUI/importers
- automation/runtime
- native TTS bridge

What seems weakest is not the feature set, but the concentration of responsibility inside a handful of large, environment-sensitive modules. The biggest improvements will come from making those modules smaller, more testable, and easier to debug when Diablo or Windows behavior shifts.
