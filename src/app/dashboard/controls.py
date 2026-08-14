"""Profile-dashboard controls that coordinate settings and log visibility."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Collection

    from src.app.dashboard.core import ActivityLogWidget


class ActivityLogControlsMixin:
    def _select_all(self: ActivityLogWidget) -> None:
        active = []
        for name, cb in self._checkboxes.items():
            cb.blockSignals(True)  # ruff:ignore[boolean-positional-value-in-call]
            cb.setChecked(True)
            cb.blockSignals(False)  # ruff:ignore[boolean-positional-value-in-call]
            active.append(name)
        self._save_active_list(active)

    def _deselect_all(self: ActivityLogWidget) -> None:
        for cb in self._checkboxes.values():
            cb.blockSignals(True)  # ruff:ignore[boolean-positional-value-in-call]
            cb.setChecked(False)
            cb.blockSignals(False)  # ruff:ignore[boolean-positional-value-in-call]
        self._save_active_list([])

    def _on_toggle(self: ActivityLogWidget) -> None:
        active: list[str] = []
        for i in range(self.profile_layout.count()):
            item = self.profile_layout.itemAt(i)
            if item is None:
                continue
            widget = item.widget()
            if widget:
                name = widget.property("profile_name")
                if name and self._checkboxes.get(name) and self._checkboxes[name].isChecked():
                    active.append(name)
        self._save_active_list(active)

    def _save_active_list(self: ActivityLogWidget, active: list[str]) -> None:
        self._config.save_value("general", "profiles", ",".join(active))

    def _connect_signals(self: ActivityLogWidget) -> None:
        self.splitter.splitterMoved.connect(self._on_splitter_moved)
        self.show_log_btn.clicked.connect(self._on_show_log_clicked)
        if self._main_window:
            self.import_btn.clicked.connect(self._main_window.open_import_dialog)
            self.settings_btn.clicked.connect(self._main_window.open_settings_dialog)

    def _on_config_changed(self: ActivityLogWidget, changed_keys: Collection[str]) -> None:
        """Refresh the hotkey grid if any relevant settings changed."""
        if any(k.startswith("advanced_options") for k in changed_keys):
            self._setup_hotkey_grid()

    def _on_splitter_moved(self: ActivityLogWidget, pos: int, index: int) -> None:
        """Show the 'Show Logs' button if the log viewer height becomes zero."""
        self.show_log_btn.setVisible(self.splitter.sizes()[1] == 0)

    def _on_show_log_clicked(self: ActivityLogWidget) -> None:
        """Expand the log viewer back to a visible size."""
        total_height = sum(self.splitter.sizes())
        self.splitter.setSizes([total_height - 100, 100])
        self.show_log_btn.hide()
