"""Profile-dashboard controls that coordinate settings and log visibility."""

from typing import Any


class ActivityLogControlsMixin:
    def _select_all(self: Any):
        active = []
        for name, cb in self._checkboxes.items():
            cb.blockSignals(True)  # ruff:ignore[boolean-positional-value-in-call]
            cb.setChecked(True)
            cb.blockSignals(False)  # ruff:ignore[boolean-positional-value-in-call]
            active.append(name)
        self._save_active_list(active)

    def _deselect_all(self: Any):
        for cb in self._checkboxes.values():
            cb.blockSignals(True)  # ruff:ignore[boolean-positional-value-in-call]
            cb.setChecked(False)
            cb.blockSignals(False)  # ruff:ignore[boolean-positional-value-in-call]
        self._save_active_list([])

    def _on_toggle(self: Any):
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

    def _save_active_list(self: Any, active: list[str]):
        self._config.save_value("general", "profiles", ",".join(active))

    def _connect_signals(self: Any):
        self.splitter.splitterMoved.connect(self._on_splitter_moved)
        self.show_log_btn.clicked.connect(self._on_show_log_clicked)
        if self._main_window:
            self.import_btn.clicked.connect(self._main_window.open_import_dialog)
            self.settings_btn.clicked.connect(self._main_window.open_settings_dialog)

    def _on_config_changed(self: Any, changed_keys):
        """Refresh the hotkey grid if any relevant settings changed."""
        if any(k.startswith("advanced_options") for k in changed_keys):
            self._setup_hotkey_grid()

    def _on_splitter_moved(self: Any, pos: int, index: int):
        """Show the 'Show Logs' button if the log viewer height becomes zero."""
        self.show_log_btn.setVisible(self.splitter.sizes()[1] == 0)

    def _on_show_log_clicked(self: Any):
        """Expand the log viewer back to a visible size."""
        total_height = sum(self.splitter.sizes())
        self.splitter.setSizes([total_height - 100, 100])
        self.show_log_btn.hide()
