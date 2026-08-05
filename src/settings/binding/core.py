"""Pure parsing and validation for the persisted hotkey vocabulary."""

_VALID_KEY_NAMES = frozenset({
    "alt",
    "alt_gr",
    "backspace",
    "caps_lock",
    "cmd",
    "delete",
    "down",
    "end",
    "enter",
    "esc",
    "f1",
    "f2",
    "f3",
    "f4",
    "f5",
    "f6",
    "f7",
    "f8",
    "f9",
    "f10",
    "f11",
    "f12",
    "f13",
    "f14",
    "f15",
    "f16",
    "f17",
    "f18",
    "f19",
    "f20",
    "home",
    "left",
    "media_eject",
    "media_next",
    "media_play_pause",
    "media_previous",
    "media_volume_down",
    "media_volume_mute",
    "media_volume_up",
    "page_down",
    "page_up",
    "right",
    "shift",
    "space",
    "tab",
    "up",
})
_MODIFIER_KEYS = frozenset({"ctrl", "shift", "alt", "cmd"})
_MODIFIER_ORDER = {modifier: index for index, modifier in enumerate(("ctrl", "shift", "alt", "cmd"))}
_KEY_ALIASES = {
    "control": "ctrl",
    "control_l": "ctrl",
    "control_r": "ctrl",
    "ctrl_l": "ctrl",
    "ctrl_r": "ctrl",
    "option": "alt",
    "option_l": "alt",
    "option_r": "alt",
    "alt_l": "alt",
    "alt_r": "alt",
    "command": "cmd",
    "command_l": "cmd",
    "command_r": "cmd",
    "cmd_l": "cmd",
    "cmd_r": "cmd",
}


def _split_hotkey_tokens(hotkey: str) -> list[str]:
    return [token.strip().lower() for token in hotkey.split("+") if token.strip()]


def _canonicalize_token(token: str) -> str:
    raw_token = token.strip().lower()
    if not raw_token:
        msg = "Hotkey cannot be empty."
        raise ValueError(msg)

    is_bracketed = raw_token.startswith("<") or raw_token.endswith(">")
    if is_bracketed and not (raw_token.startswith("<") and raw_token.endswith(">")):
        msg = f"Key '{raw_token}' is not mapped to any known key."
        raise ValueError(msg)

    key_name = raw_token[1:-1].strip() if raw_token.startswith("<") and raw_token.endswith(">") else raw_token
    key_name = _KEY_ALIASES.get(key_name, key_name)
    if len(key_name) == 1 and not is_bracketed:
        return key_name
    if key_name in _VALID_KEY_NAMES or key_name in _MODIFIER_KEYS:
        return key_name

    msg = f"Key '{key_name}' is not mapped to any known key."
    raise ValueError(msg)


def canonicalize_hotkey(hotkey: str) -> str:
    tokens = _split_hotkey_tokens(hotkey)
    if not tokens:
        msg = "Hotkey cannot be empty."
        raise ValueError(msg)

    canonical_tokens = [_canonicalize_token(token) for token in tokens]
    if len(set(canonical_tokens)) != len(canonical_tokens):
        msg = "Hotkey contains duplicate keys."
        raise ValueError(msg)
    if all(token in _MODIFIER_KEYS for token in canonical_tokens):
        msg = "Hotkey must include at least one non-modifier key."
        raise ValueError(msg)

    modifiers = sorted(
        (token for token in canonical_tokens if token in _MODIFIER_KEYS), key=lambda token: _MODIFIER_ORDER[token]
    )
    keys = [token for token in canonical_tokens if token not in _MODIFIER_KEYS]
    return "+".join([*modifiers, *keys])


def _to_backend_token(token: str) -> str:
    if len(token) == 1:
        return token
    return f"<{token}>"


def normalize_hotkey(hotkey: str) -> str:
    return "+".join(_to_backend_token(token) for token in _split_hotkey_tokens(canonicalize_hotkey(hotkey)))


def validate_hotkey(hotkey: str) -> str:
    return canonicalize_hotkey(hotkey)


__all__ = ["canonicalize_hotkey", "normalize_hotkey", "validate_hotkey"]
