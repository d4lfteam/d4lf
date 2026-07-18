"""Profile rows and summaries for the application dashboard."""

import datetime
import logging
from typing import TYPE_CHECKING, Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QMessageBox, QPushButton, QVBoxLayout, QWidget

from src.desktop.widgets import CheckmarkCheckBox
from src.profiles import ProfileDocumentError, ProfileDocumentStore

from .dashboard_drag import DragHandleButton

if TYPE_CHECKING:
    from pathlib import Path

LOGGER = logging.getLogger(__name__)


class ActivityProfileRowsMixin:
    def refresh_profiles(self: Any):
        """Scan the profiles folder and update the list."""
        for i in reversed(range(self.profile_layout.count())):
            child = self.profile_layout.takeAt(i)
            if child is not None and (w := child.widget()):
                w.deleteLater()

        self._checkboxes.clear()
        self._rows.clear()

        profiles_dir = self._config.user_dir / "profiles"
        active_list = self._config.general.profiles

        if profiles_dir.exists():
            all_files = list(profiles_dir.glob("*.yaml")) + list(profiles_dir.glob("*.yml"))
            file_map = {p.stem: p for p in all_files}

            # Order: Active profiles in their saved order first, then remaining alphabetical.
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
                drag_handle = DragHandleButton(row_widget, self._start_drag)
                drag_handle.setCursor(Qt.CursorShape.SizeAllCursor)

                cb = CheckmarkCheckBox(name.replace("_", " "))
                cb.blockSignals(True)  # ruff:ignore[boolean-positional-value-in-call]
                cb.setChecked(name in active_list)
                cb.blockSignals(False)  # ruff:ignore[boolean-positional-value-in-call]
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

    def _create_row_btn(self: Any, text: str) -> QPushButton:
        btn = QPushButton(text)
        btn.setObjectName("row-action-btn")
        btn.setFlat(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        # Styling is handled by the shared theme.
        return btn

    def _toggle_row(self: Any, label: QLabel, button: QPushButton):
        is_visible = not label.isVisible()
        label.setVisible(is_visible)
        button.setText("▼" if is_visible else "▶")

    def _edit_profile(self: Any, name: str):
        if self._main_window:
            self._main_window.open_profile_editor(profile_name=name)

    def _delete_profile(self: Any, name: str):
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
                        current_active = list(self._config.general.profiles)
                        if name in current_active:
                            current_active.remove(name)
                            self._save_active_list(current_active)
                        self.refresh_profiles()
                    except Exception:
                        LOGGER.exception("Failed to delete profile %s", name)

    def _get_profile_summary(self: Any, path: Path) -> str:
        """Build a summary tooltip from the profile document."""
        try:
            stat = path.stat()
            mtime = datetime.datetime.fromtimestamp(stat.st_mtime, tz=datetime.UTC).strftime("%Y-%m-%d %H:%M")
            model = ProfileDocumentStore.default().load(path).profile
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
        except OSError, ProfileDocumentError:
            return f"Path: {path}\n(Could not parse profile details)"
