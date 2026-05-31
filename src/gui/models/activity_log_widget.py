from __future__ import annotations

import datetime
import logging
from typing import TYPE_CHECKING

import yaml
from PyQt6.QtCore import QMimeData, Qt
from PyQt6.QtGui import QDrag
from PyQt6.QtWidgets import (
    QFrame,
    QGraphicsOpacityEffect,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.config.loader import IniConfigLoader
from src.config.profile_models import ProfileModel
from src.config.settings_models import IS_HOTKEY_KEY, LIVE_RELOAD_GROUP_KEY
from src.gui.models.checkmark_checkbox import CheckmarkCheckBox
from src.item.filter import _UniqueKeyLoader

if TYPE_CHECKING:
    from collections.abc import Set as AbstractSet
    from pathlib import Path

LOGGER = logging.getLogger(__name__)


class ActivityLogWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._main_window = parent
        self._config = IniConfigLoader()
        self._config.register_change_listener(self._on_config_changed)
        self.setAcceptDrops(True)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(20, 20, 20, 20)
        self.main_layout.setSpacing(15)

        # === CENTER CONTENT: PROFILES & HOTKEYS ===
        content_hbox = QHBoxLayout()
        content_hbox.setSpacing(30)

        # -- LEFT: PROFILE LIST --
        profile_section = QVBoxLayout()
        profile_section.setSpacing(10)

        profile_hdr = QLabel("ACTIVE PROFILES")
        profile_hdr.setStyleSheet("font-weight: bold; color: #888; letter-spacing: 1px;")
        profile_section.addWidget(profile_hdr)

        # Inline help text instead of a tooltip for better discovery and clarity
        profile_help = QLabel(
            "Toggle profiles to enable them. Drag <b>⠿</b> to set priority; "
            "the top profile determines affix highlighting."
        )
        profile_help.setWordWrap(True)
        profile_help.setObjectName("profile-help")
        profile_section.addWidget(profile_help)

        # Visual drop indicator for drag-and-drop
        self.drop_indicator = QFrame()
        self.drop_indicator.setObjectName("drop-indicator")
        self.drop_indicator.setFixedHeight(2)
        self.drop_indicator.hide()

        self._checkboxes: dict[str, CheckmarkCheckBox] = {}
        self._rows: dict[str, QWidget] = {}

        self.profile_scroll = QScrollArea()
        self.profile_scroll.setWidgetResizable(True)
        self.profile_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.profile_container = QWidget()
        self.profile_layout = QVBoxLayout(self.profile_container)
        self.profile_layout.setSpacing(0)
        self.profile_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self.profile_scroll.setWidget(self.profile_container)
        profile_section.addWidget(self.profile_scroll)

        # Search bar for profiles
        self.profile_search_input = QLineEdit()
        self.profile_search_input.setPlaceholderText("🔍 Filter profiles...")
        self.profile_search_input.textChanged.connect(self._filter_profiles)

        # Bulk selection buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        self.select_all_btn = QPushButton("Select All")
        self.deselect_all_btn = QPushButton("Deselect All")
        self.select_all_btn.clicked.connect(self._select_all)
        self.deselect_all_btn.clicked.connect(self._deselect_all)
        btn_layout.addWidget(self.select_all_btn)
        btn_layout.addWidget(self.deselect_all_btn)
        btn_layout.addStretch()

        profile_section.addLayout(btn_layout)
        profile_section.addWidget(self.profile_search_input)

        content_hbox.addLayout(profile_section, stretch=6)

        # -- RIGHT: HOTKEY GRID --
        hotkey_section = QVBoxLayout()
        hotkey_hdr = QLabel("KEYBOARD SHORTCUTS")
        hotkey_hdr.setStyleSheet("font-weight: bold; color: #888; letter-spacing: 1px;")
        hotkey_section.addWidget(hotkey_hdr)

        self.hotkey_grid = QGridLayout()
        self.hotkey_grid.setSpacing(10)
        self._setup_hotkey_grid()

        hotkey_section.addLayout(self.hotkey_grid)
        hotkey_section.addStretch()
        content_hbox.addLayout(hotkey_section, stretch=4)

        # Use a splitter for the main dashboard content and the log viewer to allow drag-resizing
        self.splitter = QSplitter(Qt.Orientation.Vertical)
        self.splitter.setObjectName("dashboard-splitter")

        # Container for the dashboard content (Profiles & Hotkeys)
        top_content_container = QWidget()
        top_content_container.setLayout(content_hbox)
        self.splitter.addWidget(top_content_container)

        # === BOTTOM: MINI LOG PREVIEW ===
        self.log_viewer = QPlainTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setObjectName("log-viewer")
        self.splitter.addWidget(self.log_viewer)

        # Set initial distribution (top takes priority, log starts at 100px)
        self.splitter.setStretchFactor(0, 4)
        self.splitter.setStretchFactor(1, 1)
        self.splitter.setSizes([500, 100])

        self.main_layout.addWidget(self.splitter, stretch=1)

        # Hidden button that appears when the log viewer is fully collapsed
        self.show_log_btn = QPushButton("Show Activity Log")
        self.show_log_btn.setObjectName("secondary")
        self.show_log_btn.setVisible(False)
        self.main_layout.addWidget(self.show_log_btn)

        # === ACTION BAR ===
        action_layout = QHBoxLayout()
        self.import_btn = QPushButton("Import Profile")
        self.import_btn.setObjectName("primary")
        self.settings_btn = QPushButton("Settings")

        self.minimize_to_tray_cb = CheckmarkCheckBox("Minimize to Tray")
        self.minimize_to_tray_cb.setObjectName("switch")

        for btn in [self.import_btn, self.settings_btn]:
            btn.setFixedHeight(34)
            btn.setFixedWidth(130)
            action_layout.addWidget(btn)

        action_layout.addStretch()
        action_layout.addWidget(self.minimize_to_tray_cb)

        self.main_layout.addLayout(action_layout)
        self._connect_signals()
        self.refresh_profiles()

    def _setup_hotkey_grid(self):
        """Build the hotkey grid dynamically from AdvancedOptionsModel metadata."""
        while self.hotkey_grid.count():
            item = self.hotkey_grid.takeAt(0)
            if widget := item.widget():
                widget.deleteLater()
            elif layout := item.layout():
                while layout.count():
                    child = layout.takeAt(0)
                    if w := child.widget():
                        w.deleteLater()

        opts = self._config.advanced_options
        schema = opts.model_json_schema()
        properties = schema.get("properties", {})

        hotkey_items = []
        # Filter for keys that control the app (Advanced section) and are tagged as hotkeys
        for key, field in opts.model_fields.items():
            meta = field.json_schema_extra or {}
            if meta.get(IS_HOTKEY_KEY) == "True" or meta.get(LIVE_RELOAD_GROUP_KEY) == "hotkeys":
                val = getattr(opts, key)
                prop_meta = properties.get(key, {})
                label = prop_meta.get("title") or key.replace("_", " ").title()
                hotkey_items.append((str(val), label))

        for i, (key_val, label) in enumerate(hotkey_items):
            row, col = divmod(i, 2)
            item_layout = QHBoxLayout()
            item_layout.setContentsMargins(0, 0, 0, 0)
            badge = QLabel(key_val.upper())
            badge.setObjectName("key-badge")
            item_layout.addWidget(badge)
            item_layout.addWidget(QLabel(label))
            item_layout.addStretch()
            self.hotkey_grid.addLayout(item_layout, row, col)

    def refresh_profiles(self):
        """Scan the profiles folder and update the list."""
        for i in reversed(range(self.profile_layout.count())):
            child = self.profile_layout.takeAt(i)
            if w := child.widget():
                w.deleteLater()

        self._checkboxes.clear()
        self._rows.clear()

        profiles_dir = self._config.user_dir / "profiles"
        active_list = self._config.general.profiles

        if profiles_dir.exists():
            all_files = list(profiles_dir.glob("*.yaml")) + list(profiles_dir.glob("*.yml"))
            file_map = {p.stem: p for p in all_files}

            # Order: Active profiles in their saved order first, then remaining alphabetical
            active_names = [n for n in active_list if n in file_map]
            remaining = sorted([n for n in file_map if n not in active_names], key=lambda x: x.lower())

            for name in active_names + remaining:
                p_path = file_map[name]
                row_widget = QWidget()
                row_widget.setObjectName("profile-row")
                row_widget.setProperty("profile_name", name)
                row_vbox = QVBoxLayout(row_widget)
                row_vbox.setContentsMargins(10, 5, 10, 5)
                row_vbox.setSpacing(0)

                header_container = QWidget()
                header_hbox = QHBoxLayout(header_container)
                header_hbox.setContentsMargins(0, 0, 0, 0)
                header_hbox.setSpacing(5)

                toggle_btn = self._create_row_btn("▶")
                drag_handle = self._create_row_btn("⠿")
                drag_handle.setCursor(Qt.CursorShape.SizeAllCursor)

                cb = CheckmarkCheckBox(name.replace("_", " "))
                cb.blockSignals(True)  # noqa: FBT003
                cb.setChecked(name in active_list)
                cb.blockSignals(False)  # noqa: FBT003
                cb.stateChanged.connect(self._on_toggle)

                header_hbox.addWidget(toggle_btn)
                header_hbox.addWidget(drag_handle)
                header_hbox.addWidget(cb)
                header_hbox.addStretch()

                edit_btn = self._create_row_btn("Edit")
                edit_btn.setToolTip("Edit Profile")
                edit_btn.clicked.connect(lambda _, n=name: self._edit_profile(n))
                header_hbox.addWidget(edit_btn)

                delete_btn = self._create_row_btn("Delete")
                delete_btn.setObjectName("delete-profile-btn")
                delete_btn.setToolTip("Delete Profile")
                delete_btn.clicked.connect(lambda _, n=name: self._delete_profile(n))
                header_hbox.addWidget(delete_btn)

                summary_lbl = QLabel(self._get_profile_summary(p_path))
                summary_lbl.setObjectName("description-label")
                summary_lbl.setContentsMargins(30, 2, 10, 8)
                summary_lbl.setWordWrap(True)
                summary_lbl.setVisible(False)
                toggle_btn.clicked.connect(lambda _, lbl=summary_lbl, btn=toggle_btn: self._toggle_row(lbl, btn))

                # Connect drag handle
                drag_handle.mouseMoveEvent = lambda e, w=row_widget, h=drag_handle: self._start_drag(e, w, h)

                row_vbox.addWidget(header_container)
                row_vbox.addWidget(summary_lbl)
                self.profile_layout.addWidget(row_widget)
                self._checkboxes[name] = cb
                self._rows[name] = row_widget

        if not self._rows:
            empty_lbl = QLabel("No Profiles found. Please import a profile below.")
            empty_lbl.setStyleSheet("color: #888; font-style: italic; padding: 20px;")
            empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.profile_layout.addWidget(empty_lbl)

        if self.profile_search_input.text():
            self._filter_profiles(self.profile_search_input.text())
        else:
            self._update_zebra_striping()

    def _create_row_btn(self, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("row-action-btn")
        btn.setFlat(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Styling is handled by themes.py
        return btn

    def _toggle_row(self, label: QLabel, button: QPushButton):
        is_visible = not label.isVisible()
        label.setVisible(is_visible)
        button.setText("▼" if is_visible else "▶")

    def _edit_profile(self, name: str):
        if self._main_window:
            self._main_window.open_profile_editor(profile_name=name)

    def _delete_profile(self, name: str):
        msg = QMessageBox(self)
        msg.setIcon(QMessageBox.Icon.Warning)
        msg.setWindowTitle("Delete Profile")
        msg.setText(f"Are you sure you want to permanently delete the profile '{name}'?")
        msg.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if msg.exec() == QMessageBox.StandardButton.Yes:
            profiles_dir = self._config.user_dir / "profiles"
            for ext in [".yaml", ".yml"]:
                p_path = profiles_dir / f"{name}{ext}"
                if p_path.exists():
                    try:
                        p_path.unlink()
                        # Also remove from active config if it was selected
                        current_active = list(self._config.general.profiles)
                        if name in current_active:
                            current_active.remove(name)
                            self._save_active_list(current_active)
                        self.refresh_profiles()
                    except Exception:
                        LOGGER.exception(f"Failed to delete profile {name}")

    def _get_profile_summary(self, path: Path) -> str:
        """Peeks into the YAML using ProfileModel to build a summary tooltip."""
        try:
            stat = path.stat()
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime, tz=datetime.UTC).strftime("%Y-%m-%d %H:%M")
            with path.open(encoding="utf-8") as f:
                config = yaml.load(stream=f, Loader=_UniqueKeyLoader)
            if not config or not isinstance(config, dict):
                return f"Last Modified: {mtime}\n(Empty or invalid profile)"

            # Convert to ProfileModel for robust, future-proof access
            model = ProfileModel(name=path.stem, **config)
            summary = [f"Last Modified: {mtime}"]

            if model.affixes:
                types = set()
                for filter_dict in model.affixes:
                    for item_filter in filter_dict.root.values():
                        if it := getattr(item_filter, "item_type", None):
                            if isinstance(it, list):
                                types.update([str(t) for t in it])
                            else:
                                types.add(str(it))
                if types:
                    summary.append(f"📦 Items: {', '.join(sorted(types))}")
                summary.append(f"🔍 Affix Filters: {len(model.affixes)}")

            if model.aspect_upgrades:
                summary.append(f"✨ Aspect Upgrades: {len(model.aspect_upgrades)}")
            if model.global_uniques:
                summary.append(f"💎 Global Uniques: {len(model.global_uniques)}")
            if model.sigils:
                summary.append("📜 Sigils: Included")
            if model.tributes:
                summary.append("🏆 Tributes: Included")
            if model.paragon:
                summary.append("🔱 Paragon Overlay: Data Found")

            return "\n".join(summary)
        except Exception:  # noqa: BLE001
            return f"Path: {path}\n(Could not parse profile details)"

    def _start_drag(self, event, row_widget: QWidget, handle: QWidget):
        if event.buttons() != Qt.MouseButton.LeftButton:
            return
        click_pos = handle.mapTo(row_widget, event.position().toPoint())
        drag = QDrag(row_widget)
        mime = QMimeData()
        mime.setText(str(id(row_widget)))
        drag.setMimeData(mime)
        pixmap = row_widget.grab()
        drag.setPixmap(pixmap)
        drag.setHotSpot(click_pos)
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.3)
        row_widget.setGraphicsEffect(opacity_effect)
        idx = self.profile_layout.indexOf(row_widget)
        self.profile_layout.insertWidget(idx, self.drop_indicator)
        self.drop_indicator.show()
        drag.exec(Qt.DropAction.MoveAction)
        row_widget.setGraphicsEffect(None)
        self.drop_indicator.hide()

    def dragEnterEvent(self, event):  # noqa: N802
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragMoveEvent(self, event):  # noqa: N802
        source_id = event.mimeData().text()

        # Auto-scroll the list if dragging near the top or bottom edges
        global_pos = self.mapToGlobal(event.position().toPoint())
        viewport_pos = self.profile_scroll.viewport().mapFromGlobal(global_pos)
        margin = 40
        if viewport_pos.y() < margin:
            sb = self.profile_scroll.verticalScrollBar()
            sb.setValue(sb.value() - 10)
        elif viewport_pos.y() > self.profile_scroll.viewport().height() - margin:
            sb = self.profile_scroll.verticalScrollBar()
            sb.setValue(sb.value() + 10)

        pos = self.profile_container.mapFrom(self, event.position().toPoint())
        dragged_row = None
        current_idx = -1
        for i in range(self.profile_layout.count()):
            w = self.profile_layout.itemAt(i).widget()
            if w and str(id(w)) == source_id:
                dragged_row = w
                current_idx = i
                break
        if not dragged_row:
            return
        for i in range(self.profile_layout.count()):
            target_row = self.profile_layout.itemAt(i).widget()
            if not target_row or target_row in (dragged_row, self.drop_indicator):
                continue
            rect = target_row.geometry()
            mid_y = rect.center().y()
            if (i > current_idx and pos.y() > mid_y) or (i < current_idx and pos.y() < mid_y):
                self.profile_layout.insertWidget(i, self.drop_indicator)
                self.profile_layout.insertWidget(i, dragged_row)
                break
        event.acceptProposedAction()

    def dropEvent(self, event):  # noqa: N802
        self._on_toggle()
        self._update_zebra_striping()
        event.acceptProposedAction()

    def _update_zebra_striping(self):
        """Update alternating background colors for currently visible rows."""
        visible_count = 0
        for i in range(self.profile_layout.count()):
            widget = self.profile_layout.itemAt(i).widget()
            if widget and widget.objectName() == "profile-row" and not widget.isHidden():
                widget.setProperty("alt", visible_count % 2 == 0)
                widget.style().polish(widget)
                visible_count += 1

    def _filter_profiles(self, text: str):
        query = text.lower()
        for name, row in self._rows.items():
            row.setVisible(query in name.lower())
        self._update_zebra_striping()

    def _select_all(self):
        active = []
        for name, cb in self._checkboxes.items():
            cb.blockSignals(True)  # noqa: FBT003
            cb.setChecked(True)
            cb.blockSignals(False)  # noqa: FBT003
            active.append(name)
        self._save_active_list(active)

    def _deselect_all(self):
        for cb in self._checkboxes.values():
            cb.blockSignals(True)  # noqa: FBT003
            cb.setChecked(False)
            cb.blockSignals(False)  # noqa: FBT003
        self._save_active_list([])

    def _on_toggle(self):
        active: list[str] = []
        for i in range(self.profile_layout.count()):
            widget = self.profile_layout.itemAt(i).widget()
            if widget:
                name = widget.property("profile_name")
                if name and self._checkboxes.get(name) and self._checkboxes[name].isChecked():
                    active.append(name)
        self._save_active_list(active)

    def _save_active_list(self, active: list[str]):
        self._config.save_value("general", "profiles", ",".join(active))

    def _connect_signals(self):
        self.splitter.splitterMoved.connect(self._on_splitter_moved)
        self.show_log_btn.clicked.connect(self._on_show_log_clicked)
        if self._main_window:
            self.import_btn.clicked.connect(self._main_window.open_import_dialog)
            self.settings_btn.clicked.connect(self._main_window.open_settings_dialog)

    def _on_config_changed(self, changed_keys: AbstractSet[str]):
        """Refresh the hotkey grid if any relevant settings changed."""
        if any(k.startswith("advanced_options") for k in changed_keys):
            self._setup_hotkey_grid()

    def _on_splitter_moved(self, pos: int, index: int):
        """Show the 'Show Logs' button if the log viewer height becomes zero."""
        self.show_log_btn.setVisible(self.splitter.sizes()[1] == 0)

    def _on_show_log_clicked(self):
        """Expand the log viewer back to a visible size."""
        total_height = sum(self.splitter.sizes())
        self.splitter.setSizes([total_height - 100, 100])
        self.show_log_btn.hide()
