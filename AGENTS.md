# AGENTS.md — D4LF (Diablo 4 Loot Filter)

## Project Overview

D4LF is a Windows desktop application that filters items, sigils, and tributes in Diablo 4 based on user-defined profiles. It reads the game screen via screenshots and receives item data through a custom TTS DLL that intercepts Diablo 4's accessibility text-to-speech pipeline. The app provides a PyQt6 GUI for configuration, profile importing, and a manual profile editor, plus tkinter-based overlays rendered on top of the game.

## Tech Stack

- **Language**: Python 3.14 (primary), C++ (TTS DLL in `tts/`)
- **Package manager**: [uv](https://docs.astral.sh/uv/)
- **Build system**: Hatchling (`pyproject.toml`)
- **GUI**: PyQt6 (main window, settings, importers, profile editor)
- **Overlays**: tkinter (screen overlays for loot filter results, info panels)
- **Screen capture**: mss, OpenCV, NumPy
- **Config/models**: Pydantic, PyYAML, configparser
- **Testing**: pytest (with pytest-xdist for parallel, pytest-mock, pytest-cov)
- **Browser importers**: Selenium/SeleniumBase for site importers; prefer existing SeleniumBase patterns for anti-bot-sensitive flows
- **Linting/formatting**: Ruff (all rules enabled, see `pyproject.toml` for ignores)
- **Pre-commit**: prek/pre-commit hooks with ruff, clang-format, mdformat, TOML/YAML formatters
- **CI**: GitHub Actions on `windows-latest`
- **Distribution**: PyInstaller → single `.exe`

## Repository Structure

```
src/                          # Main application source
├── main.py                   # Entry point
├── __init__.py               # Version (__version__)
├── cam.py                    # Screen capture singleton (mss)
├── tts.py                    # TTS named-pipe listener (win32pipe)
├── overlay.py                # tkinter overlay base
├── paragon_overlay.py        # Paragon board overlay
├── loot_mover.py             # Stash/inventory item transfer automation
├── template_finder.py        # Template matching via OpenCV
├── dataloader.py             # Game data loading
├── logger.py                 # Logging setup (rotating file + colored console)
├── autoupdater.py            # Self-update mechanism
├── startup_messages.py       # Startup validation messages
├── config/                   # Configuration layer
│   ├── loader.py             # IniConfigLoader singleton (params.ini)
│   ├── settings_models.py    # Pydantic settings models
│   ├── profile_models.py     # Pydantic profile/filter models
│   ├── data.py               # UI coordinate data (based on 3840x2160)
│   ├── helper.py             # Config utilities
│   └── ui.py                 # Resolution manager
├── item/                     # Item parsing and filtering
│   ├── models.py             # Item dataclass
│   ├── filter.py             # Filter engine (matches items against profiles)
│   ├── find_descr.py         # Locate item descriptions on screen
│   ├── descr/                # Item description parsers
│   │   ├── read_descr_tts.py # Parse TTS text into Item objects
│   │   ├── text.py           # OCR text-based parsing
│   │   └── texture.py        # Texture-based parsing
│   └── data/                 # Item data enums and types
│       ├── affix.py
│       ├── aspect.py
│       ├── item_type.py
│       ├── rarity.py
│       └── seasonal_attribute.py
├── scripts/                  # Runtime script modes
│   ├── handler.py            # ScriptHandler — hotkey binding and mode dispatch
│   ├── loot_filter_tts.py    # TTS-based loot filter script
│   ├── vision_mode_fast.py   # Fast vision mode (overlay-only)
│   ├── vision_mode_with_highlighting.py  # Vision mode with on-screen highlights
│   ├── info_overlay.py       # Info panel overlay (boss timers, session stats)
│   └── common.py             # Shared script constants
├── gui/                      # PyQt6 GUI
│   ├── unified_window.py     # Main application window
│   ├── settings_window.py    # Settings editor
│   ├── settings_tab.py       # Settings tab widget
│   ├── profile_tab.py        # Profile manager tab
│   ├── importer_window.py    # Profile importer window
│   ├── profile_editor_window.py  # Manual profile editor
│   ├── themes.py             # Dark/light theme support
│   ├── importer/             # Build site importers
│   │   ├── maxroll.py
│   │   ├── mobalytics.py
│   │   ├── d4builds.py
│   │   ├── diablo_trade.py
│   │   └── paragon_export.py
│   └── models/               # GUI data models
├── ui/                       # Game UI interaction (screen reading, clicking)
│   ├── char_inventory.py     # Character inventory grid
│   ├── stash.py              # Stash grid
│   ├── vendor.py             # Vendor UI
│   ├── menu.py               # Game menu detection
│   └── inventory_base.py     # Base inventory grid logic
├── utils/                    # Utility modules
│   ├── custom_mouse.py       # Mouse control abstraction
│   ├── image_operations.py   # OpenCV image utilities
│   ├── roi_operations.py     # Region-of-interest helpers
│   ├── process_handler.py    # Windows process management
│   ├── window.py             # Game window detection
│   └── misc.py               # Miscellaneous helpers
└── tools/                    # Offline tooling / code generation
    ├── gen_data.py            # Generate item data from D4Data repo
    └── gen_data_helpers.py    # Constants for data generation

tests/                        # Test suite (mirrors src/ structure)
├── conftest.py               # Shared fixtures (mock_ini_loader)
├── config/                   # Config loader & model tests
├── item/
│   ├── filter/               # Filter engine tests
│   └── descr/                # Description parser tests
│   └── read_descr_*_test.py  # Season-specific TTS parsing tests
├── gui/importer/             # Importer tests
├── ui/                       # UI interaction tests
└── utils/                    # Utility tests

tts/                          # TTS DLL source and installer
├── saapi.cpp / saapi.h       # C++ DLL source (intercepts D4 TTS)
├── saapi64.dll               # Pre-built signed DLL
└── install_dll.cmd           # Installer script for users

build.py                      # PyInstaller build script
pyproject.toml                # Project config, dependencies, ruff settings
pytest.ini                    # Pytest configuration
uv.lock                       # Locked dependency versions
```

## Development Setup

```bash
# Install all dependencies (including dev group)
uv sync --all-groups

# Activate the virtual environment (Windows)
.venv\Scripts\activate
```

## Common Commands

Prefer `uv run ...` locally so Codex and VS Code use the repository environment instead of a globally installed tool. CI may run bare `pytest` after the setup action has prepared the environment.

### Running Tests

```bash
# Run all tests (excluding selenium-based tests), in parallel
uv run pytest . -m "not selenium" -v -n logical

# Run a specific test file
uv run pytest tests/item/filter/filter_test.py -v

# Run tests with coverage
uv run pytest . -m "not selenium" --cov=src -v -n logical
```

### Linting and Formatting

```bash
# Check linting (all ruff rules enabled)
uv run ruff check src/ tests/

# Auto-fix lint issues
uv run ruff check --fix src/ tests/

# Format code
uv run ruff format src/ tests/

# Run all prek/pre-commit hooks
prek run -a
```

### Building

```bash
# Build the distributable exe (PyInstaller, Windows only)
uv run python build.py
```

## Key Architecture Concepts

### Singletons

Several core classes use a `@singleton` decorator or `__new__` pattern:

- `IniConfigLoader` — central config (reads `~/.d4lf/params.ini`)
- `Cam` — screen capture
- `Publisher` (in `tts.py`) — TTS data pub/sub

### Item Pipeline

1. **TTS Data** arrives via named pipe from the injected DLL → parsed by `tts.py` `Publisher`
1. **Item Parsing** (`item/descr/read_descr_tts.py`) converts raw TTS text into `Item` objects
1. **Filtering** (`item/filter.py`) matches `Item` against user profiles (YAML-based `ProfileModel`)
1. **Action** — items are marked keep/junk via screen overlay or mouse automation

### Configuration

- **Settings** stored in `~/.d4lf/params.ini`, loaded by `IniConfigLoader` (Pydantic-validated)
- **Profiles** are YAML files in `~/.d4lf/profiles/`, validated by `ProfileModel`
- Config changes broadcast to listeners via `IniConfigLoader._change_listeners`

### Screen Coordinates

All UI coordinates in `src/config/data.py` are defined at **3840×2160** (UHD) and scaled at runtime via `ResManager` for the user's actual resolution.

## Testing Notes

- Tests run on **Windows only** in CI (`windows-latest`). Some test modules are skipped on macOS via `conftest.py`.
- Pytest markers: `requests` (tests using HTTP), `selenium` (browser-based tests — currently disabled in CI).
- Season-specific TTS parsing tests exist per-season (`read_descr_season*_test.py`) to handle game data changes. Check the newest season test file before editing parser behavior.
- The filter tests in `tests/item/filter/` use YAML fixture data in `tests/item/filter/data/`.

## CI/CD

- **CI** (`.github/workflows/ci.yml`): Runs on PRs and pushes to `main`. Sets up uv + Python 3.14, runs prek hooks, then `pytest . -m "not selenium" -v -n logical`.
- **Release** (`.github/workflows/release.yml`): Triggered on merged PRs with `release` label or manual dispatch. Builds exe via `build.py`, creates a GitHub release with the zip.

## Code Style

- **Ruff** with `select = ["ALL"]` — nearly all rules enabled. See `pyproject.toml [tool.ruff.lint]` for the ignore list.
- Line length: **120**
- Quote style: **double**
- Indent: **4 spaces**
- Import sorting: isort via ruff, no trailing comma splits
- Docstring convention: **Google style**
- C++ files (TTS DLL): formatted with **clang-format**
- TOML/YAML: auto-formatted via prek/pre-commit hooks
- Prefer direct inline logic over private one-line helper functions when the logic is used only once.
- Do not introduce tiny helper methods only to satisfy linting or style preferences. Add a helper only when it is reused, hides meaningful domain logic, or makes a complex block easier to read.
- Before adding a new helper, check whether an existing helper or model validator already covers the same path.

## Codex Edit Rules

- Make the smallest safe change that fixes the issue and preserves existing behavior.
- Avoid new abstractions for single-use logic; keep one-line checks inline at the call site.
- Reuse existing validators, helpers, constants, and data models before adding new ones.
- Do not move logic across files unless there is a clear cross-file benefit.
- Keep existing comments unless the code they explain is removed.
- When touching profile models, importer parsing, or season data, run targeted model/importer tests when available.

## Important Conventions

- The project targets **Windows only** at runtime (uses win32 APIs, PyInstaller exe builds, and mss/OpenCV-based screen capture). Tests for Windows-only modules are gated in `conftest.py`.
- User data directory: `~/.d4lf/` (profiles, params.ini, logs).
- Version is defined in `src/__init__.py` as `__version__`.
- Existing comments should be kept in place unless the code they relate to is removed
