# AGENTS.md - D4LF

## Project

D4LF is a Windows desktop app for filtering Diablo 4 items, sigils, and tributes from user-defined
profiles. It reads the game screen with screenshots and receives item text from a custom TTS DLL that
intercepts Diablo 4's accessibility text-to-speech pipeline.

The main UI is PyQt6. Game overlays are tkinter windows rendered above the game.

## Stack

Python 3.14 via uv; C++ for the TTS DLL in `tts/`; PyQt6/tkinter; mss, OpenCV, NumPy; Pydantic,
PyYAML, configparser; pytest; Ruff; PyInstaller.

## Key paths

- `src/main.py` - app entry point
- `src/__init__.py` - version
- `src/config/` - settings/profile models, config loader, UI coordinate scaling
- `src/item/` - item models, TTS/OCR parsing, filter engine, item data
- `src/scripts/` - hotkey-driven runtime modes
- `src/gui/` - PyQt6 windows, tabs, importers, profile editor
- `src/ui/` - game UI interaction for inventory, stash, vendors, menus
- `src/utils/` - image, process, window, mouse, and misc helpers
- `tests/` - pytest suite, mostly mirroring `src/`
- `tts/` - TTS DLL source, prebuilt DLL, installer

## Commands

Run these just before finishing work and and make sure it passes.

```bash
uv run pytest . -m "not selenium" -v -n logical
uv run prek run -a
```

For Windows release builds.

```bash
uv run python build.py
```

## Architecture

Item flow:

1. TTS DLL sends named-pipe text to `src/tts.py`.
1. `src/item/descr/read_descr_tts.py` parses text into `Item` objects.
1. `src/item/filter.py` matches items against YAML profiles.
1. Scripts show keep/junk overlays or automate mouse actions.

Core singletons include `IniConfigLoader`, `Cam`, and `Publisher`.

## Conventions

- Runtime target is Windows. Some tests are skipped outside Windows.
- User data lives under `~/.d4lf/` including profiles, params, and logs.
- Profile YAML files live under `~/.d4lf/profiles/` and validate through `ProfileModel`.
- UI coordinates in `src/config/data.py` are defined at 3840x2160 and scaled by `ResManager`.
- Ruff config in `pyproject.toml` is the style source of truth.
- Keep existing comments unless the related code is removed.

## Agent docs

Issue tracking, triage labels, and domain docs live in `docs/agents/`.
