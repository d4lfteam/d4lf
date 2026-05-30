"""Configuration loading, validation, persistence, and live change notifications."""

from __future__ import annotations

import configparser
import logging
import pathlib
import threading
from collections.abc import Callable
from pathlib import Path

from src.config.helper import singleton
from src.config.settings_models import AdvancedOptionsModel, CharModel, GeneralModel

type SectionModel = AdvancedOptionsModel | CharModel | GeneralModel

LOGGER = logging.getLogger(__name__)
PARAMS_INI = "params.ini"
MANUAL_RESTART_SETTING_KEYS = {"general.vision_mode_type"}
ConfigChangeListener = Callable[[frozenset[str]], None]


@singleton
class IniConfigLoader:
    """Load, validate, persist, and broadcast config changes."""

    def __init__(self) -> None:
        self._advanced_options = AdvancedOptionsModel()
        self._char = CharModel()
        self._general = GeneralModel()
        self._parser: configparser.ConfigParser | None = None
        self._user_dir = pathlib.Path.home() / ".d4lf"
        self._user_dir.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._change_listeners: list[ConfigChangeListener] = []
        self._last_config_signature: tuple[int, int] | None = None
        self._config_revision = 0
        self._state_snapshot: dict[str, object] = {}
        self._deferred_cleanup_log_records: list[logging.LogRecord] = []
        self._defer_cleanup_log_records = True
        self.load(notify=False)

    def _config_path(self) -> Path:
        return self.user_dir / PARAMS_INI

    def _get_config_signature(self) -> tuple[int, int] | None:
        config_path = self._config_path()
        if not config_path.exists():
            return None

        stat_result = config_path.stat()
        return stat_result.st_mtime_ns, stat_result.st_size

    def _section_models(self) -> dict[str, SectionModel]:
        return {"advanced_options": self._advanced_options, "char": self._char, "general": self._general}

    def _model_for_section(self, section: str) -> SectionModel | None:
        return self._section_models().get(section)

    def _capture_state_snapshot(self) -> dict[str, object]:
        snapshot: dict[str, object] = {}
        for section_name, model in self._section_models().items():
            for key, value in model.model_dump(mode="python").items():
                snapshot[f"{section_name}.{key}"] = value
        return snapshot

    def _changed_keys(self, previous_snapshot: dict[str, object], current_snapshot: dict[str, object]) -> set[str]:
        return {
            key
            for key in previous_snapshot.keys() | current_snapshot.keys()
            if previous_snapshot.get(key) != current_snapshot.get(key)
        }

    def _write_parser(self) -> None:
        if self._parser is None:
            msg = "Config parser has not been initialized"
            raise RuntimeError(msg)

        with self._config_path().open("w", encoding="utf-8") as config_file:
            self._parser.write(config_file)

    def _remove_defunct_model_keys(self) -> bool:
        if self._parser is None:
            msg = "Config parser has not been initialized"
            raise RuntimeError(msg)

        removed_key = False
        for section, model in self._section_models().items():
            if section not in self._parser:
                continue

            valid_keys = type(model).model_fields
            for key in list(self._parser[section]):
                if key in valid_keys:
                    continue

                self._log_defunct_model_key(section, key)
                self._parser.remove_option(section, key)
                removed_key = True

        return removed_key

    def _log_defunct_model_key(self, section: str, key: str) -> None:
        path_name, line_number, _, _ = LOGGER.findCaller(stacklevel=2)
        record = LOGGER.makeRecord(
            LOGGER.name,
            logging.WARNING,
            path_name,
            line_number,
            "Deprecated key=%s found in [%s]. Removing it from %s.",
            (key, section, PARAMS_INI),
            None,
        )
        if self._defer_cleanup_log_records:
            self._deferred_cleanup_log_records.append(record)
        if LOGGER.isEnabledFor(logging.WARNING):
            LOGGER.handle(record)

    def _remove_defunct_values(self) -> bool:
        if self._parser is None:
            return False

        removed = False
        # Move items "everything" migration: if found, remove the key so it defaults to the full list
        if "general" in self._parser:
            for key in ["move_to_inv_item_type", "move_to_stash_item_type"]:
                if self._parser.has_option("general", key):
                    val = self._parser.get("general", key)
                    if "everything" in val.lower():
                        new_val = "favorites,junk,unmarked"
                        self._log_defunct_value("general", key, val, new_val)
                        self._parser.set("general", key, new_val)
                        removed = True
        return removed

    def _log_defunct_value(self, section: str, key: str, old_value: str, new_value: str) -> None:
        path_name, line_number, _, _ = LOGGER.findCaller(stacklevel=2)
        record = LOGGER.makeRecord(
            LOGGER.name,
            logging.WARNING,
            path_name,
            line_number,
            "Deprecated value=%s found in [%s] %s. Migrating it to %s in %s.",
            (old_value, section, key, new_value, PARAMS_INI),
            None,
        )
        if self._defer_cleanup_log_records:
            self._deferred_cleanup_log_records.append(record)
        if LOGGER.isEnabledFor(logging.WARNING):
            LOGGER.handle(record)

    def consume_deferred_cleanup_log_records(self) -> list[logging.LogRecord]:
        with self._lock:
            records = self._deferred_cleanup_log_records.copy()
            self._deferred_cleanup_log_records.clear()
            self._defer_cleanup_log_records = False
            return records

    def _format_value_for_log(self, value: object) -> str:
        if isinstance(value, bool):
            return "on" if value else "off"
        return str(value)

    def _log_changed_values(self, changed_keys: set[str]) -> None:
        if not changed_keys:
            return

        snapshot = self._state_snapshot.copy()
        formatted_entries = [f"{key}={self._format_value_for_log(snapshot.get(key))}" for key in sorted(changed_keys)]
        noun = "change" if len(formatted_entries) == 1 else "changes"
        LOGGER.info("Applied setting %s: %s", noun, ", ".join(formatted_entries))

        if any(key in MANUAL_RESTART_SETTING_KEYS for key in changed_keys):
            LOGGER.warning("Please restart d4lf manually to apply vision mode changes.")

    def _notify_listeners(self, changed_keys: set[str]) -> None:
        if not changed_keys:
            return

        listeners = list(self._change_listeners)
        frozen_keys = frozenset(changed_keys)
        for listener in listeners:
            try:
                listener(frozen_keys)
            except Exception:
                LOGGER.exception("Failed to notify config listener")

    def register_change_listener(self, listener: ConfigChangeListener) -> None:
        with self._lock:
            if listener not in self._change_listeners:
                self._change_listeners.append(listener)

    def unregister_change_listener(self, listener: ConfigChangeListener) -> None:
        with self._lock:
            self._change_listeners = [existing for existing in self._change_listeners if existing != listener]

    def register_listener(self, listener: ConfigChangeListener) -> None:
        """Backward-compatible alias for older call sites."""
        self.register_change_listener(listener)

    def unregister_listener(self, listener: ConfigChangeListener) -> None:
        """Backward-compatible alias for older call sites."""
        self.unregister_change_listener(listener)

    def load(self, clear: bool = False, notify: bool = True) -> None:
        with self._lock:
            previous_snapshot = self._state_snapshot.copy()
            config_path = self._config_path()
            if not config_path.exists() or clear:
                config_path.write_text("", encoding="utf-8")

            self._parser = configparser.ConfigParser()
            self._parser.read(config_path, encoding="utf-8")

            defunct_keys_removed = self._remove_defunct_model_keys()
            defunct_values_removed = self._remove_defunct_values()
            if defunct_keys_removed or defunct_values_removed:
                self._write_parser()

            if "advanced_options" in self._parser:
                self._advanced_options = AdvancedOptionsModel(**self._parser["advanced_options"])
            else:
                self._advanced_options = AdvancedOptionsModel()

            if "char" in self._parser:
                self._char = CharModel(**self._parser["char"])
            else:
                self._char = CharModel()

            if "general" in self._parser:
                self._general = GeneralModel(**self._parser["general"])
            else:
                self._general = GeneralModel()

            self._last_config_signature = self._get_config_signature()
            self._config_revision += 1
            self._state_snapshot = self._capture_state_snapshot()
            changed_keys = self._changed_keys(previous_snapshot, self._state_snapshot)

        if notify:
            self._log_changed_values(changed_keys)
            self._notify_listeners(changed_keys)

    def reload_if_changed(self) -> bool:
        with self._lock:
            current_signature = self._get_config_signature()
            if current_signature == self._last_config_signature:
                return False

        LOGGER.debug("Detected external params.ini change. Reloading configuration.")
        self.load(notify=True)
        return True

    @property
    def advanced_options(self) -> AdvancedOptionsModel:
        self.reload_if_changed()
        return self._advanced_options

    @property
    def char(self) -> CharModel:
        self.reload_if_changed()
        return self._char

    @property
    def general(self) -> GeneralModel:
        self.reload_if_changed()
        return self._general

    @property
    def user_dir(self) -> Path:
        return self._user_dir

    @property
    def config_revision(self) -> int:
        with self._lock:
            return self._config_revision

    def save_value(self, section: str, key: str, value: object) -> None:
        changed_keys: set[str] = set()

        with self._lock:
            if self._parser is None:
                self.load(notify=False)

            previous_snapshot = self._state_snapshot.copy()
            model = self._model_for_section(section)
            if model is not None:
                setattr(model, key, value)

            if section not in self._parser.sections():
                self._parser.add_section(section)

            new_serialized_value = str(value)
            old_serialized_value = self._parser.get(section, key, fallback=None)
            if old_serialized_value == new_serialized_value:
                return

            self._parser.set(section, key, new_serialized_value)
            self._write_parser()
            self._last_config_signature = self._get_config_signature()
            self._config_revision += 1
            self._state_snapshot = self._capture_state_snapshot()
            changed_keys = self._changed_keys(previous_snapshot, self._state_snapshot)

        self._log_changed_values(changed_keys)
        self._notify_listeners(changed_keys)


if __name__ == "__main__":
    loader = IniConfigLoader()
    loader.load()
