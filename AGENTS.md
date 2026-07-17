# AGENTS.md - D4LF

## Project

D4LF is a Windows desktop app for filtering Diablo 4 items, sigils, and tributes from user-defined
profiles. It reads the game screen with screenshots and receives item text from a custom TTS DLL that
intercepts Diablo 4's accessibility text-to-speech pipeline.

The main UI is PyQt6. Game overlays are tkinter windows rendered above the game.

## Stack

Python 3.14 via uv; C++ for the TTS DLL in `tts/`; PyQt6/tkinter; mss, OpenCV, NumPy; Pydantic,
PyYAML, configparser; pytest; Ruff; PyInstaller.

## Commands

Run these when you think you are finished and make sure these pass.

```bash
uv run prek run -a
uv run pytest . -m "not selenium" -v -n logical
```

## Architecture

Item flow:

1. TTS DLL sends named-pipe text to `src/tts.py`.
1. `src/item/descr/read_descr_tts.py` parses text into `Item` objects.
1. `src/item/filter.py` matches items against YAML profiles.
1. Scripts show keep/junk overlays or automate mouse actions.

## Conventions

- Runtime target is Windows. Some tests are skipped outside Windows.
- No more than 300 lines of code in Python files in `src` and `tests`.
- User data lives under `~/.d4lf/` including profiles, params, and logs.
- Profile YAML files live under `~/.d4lf/profiles/` and validate through `ProfileModel`.
- UI coordinates in `src/config/data.py` are defined at 3840x2160 and scaled by `ResManager`.
- Keep existing comments unless the related code is removed.
- Capability subdomains use public subpackages with deliberate `__init__.py` facades (for example,
  `src.profiles.affix` and `src.profiles.aspect`). Callers import from those facades rather than
  prefixed implementation modules; implementation modules remain internal to their subpackage.

### Python 3.14

- from __future__ import annotations aren't needed

## Agent skills

### Issue tracker

Issues are tracked as local markdown files under `.scratch/` in this repository. See `docs/agents/issue-tracker.md`.

### Triage labels

Using the default triage vocabulary: `needs-triage`, `needs-info`, `ready-for-agent`, `ready-for-human`, `wontfix`. See `docs/agents/triage-labels.md`.

### Domain docs

Single-context layout: `CONTEXT.md` at the repository root and `docs/adr/` for ADRs. See `docs/agents/domain.md`.
