from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QHBoxLayout, QLabel, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from src import __version__
from src.config.loader import IniConfigLoader


class ActivityLogWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(10)

        # === VERSION HEADER ===
        version_label = QLabel(f"D4LF - Diablo 4 Loot Filter v{__version__}")
        version_label.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 5px;")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.main_layout.addWidget(version_label)

        # === LOG VIEWER ===
        self.log_viewer = QPlainTextEdit()
        self.log_viewer.setReadOnly(True)
        self.log_viewer.setMaximumBlockCount(1000)
        self.log_viewer.setPlaceholderText("Waiting for d4lf to start scanning...")

        self.log_viewer.appendPlainText("═" * 80)
        self.log_viewer.appendPlainText("D4LF - Diablo 4 Loot Filter")
        self.log_viewer.appendPlainText("═" * 80)
        self.log_viewer.appendPlainText("")

        self.main_layout.addWidget(self.log_viewer, stretch=1)

        # === HOTKEYS PANEL ===
        hotkeys_label = QLabel("Hotkeys:")
        hotkeys_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        self.main_layout.addWidget(hotkeys_label)

        config = IniConfigLoader()

        hotkey_text = QLabel()
        hotkey_text.setMaximumHeight(65)
        hotkey_text.setWordWrap(True)
        hotkey_text.setTextFormat(Qt.TextFormat.RichText)
        hotkey_text.setStyleSheet("margin-left: 5px;")

        hotkeys_html = "<div style='font-size: 9pt; line-height: 1.5; font-weight: normal;'>"

        if not config.advanced_options.vision_mode_only:
            hotkeys_html += f"<u><b>{config.advanced_options.run_vision_mode.upper()}</b></u>: Run/Stop Vision Mode&nbsp;&nbsp;&nbsp;"
            hotkeys_html += (
                f"<u><b>{config.advanced_options.run_filter.upper()}</b></u>: Run/Stop Auto Filter&nbsp;&nbsp;&nbsp;"
            )
            hotkeys_html += (
                f"<u><b>{config.advanced_options.move_to_inv.upper()}</b></u>: Move Chest → Inventory&nbsp;&nbsp;&nbsp;"
            )
            hotkeys_html += f"<u><b>{config.advanced_options.move_to_chest.upper()}</b></u>: Move Inventory → Chest<br>"
            hotkeys_html += f"<u><b>{config.advanced_options.run_filter_force_refresh.upper()}</b></u>: Force Filter (Reset Item Status)&nbsp;&nbsp;&nbsp;"
            hotkeys_html += f"<u><b>{config.advanced_options.force_refresh_only.upper()}</b></u>: Reset Items (No Filter)&nbsp;&nbsp;&nbsp;"
        else:
            hotkeys_html += f"<u><b>{config.advanced_options.run_vision_mode.upper()}</b></u>: Run/Stop Vision Mode<br>"
            hotkeys_html += "<span style='font-style: italic;'>Vision Mode Only - clicking functionality disabled</span>&nbsp;&nbsp;&nbsp;"

        hotkeys_html += f"<u><b>{config.advanced_options.exit_key.upper()}</b></u>: Exit D4LF"
        hotkeys_html += "</div>"

        hotkey_text.setText(hotkeys_html)
        self.main_layout.addWidget(hotkey_text)

        # === CONTROL BUTTONS ===
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)

        self.import_btn = QPushButton("Import Profile")
        self.import_btn.setMinimumHeight(40)
        button_layout.addWidget(self.import_btn)

        self.settings_btn = QPushButton("Settings")
        self.settings_btn.setMinimumHeight(40)
        button_layout.addWidget(self.settings_btn)

        self.editor_btn = QPushButton("Edit Profile")
        self.editor_btn.setMinimumHeight(40)
        button_layout.addWidget(self.editor_btn)

        # ⭐ STEP 3 — CONNECT BUTTONS TO UnifiedMainWindow ⭐
        self.import_btn.clicked.connect(self.parent().open_import_dialog)
        self.settings_btn.clicked.connect(self.parent().open_settings_dialog)
        self.editor_btn.clicked.connect(self.parent().open_profile_editor)

        self.main_layout.addLayout(button_layout)
