from typing import TYPE_CHECKING, cast

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from src.app.dashboard.controls import ActivityLogControlsMixin
from src.app.dashboard.drag import ActivityProfileDragMixin, DragHandleButton
from src.app.dashboard.profiles import ActivityProfileRowsMixin
from src.desktop.activity import ANSIConsoleWidget
from src.desktop.widgets import CheckmarkCheckBox
from src.settings import IS_HOTKEY_KEY, get_settings

if TYPE_CHECKING:
    from src.app.shell import UnifiedMainWindow

__all__ = ["ActivityLogWidget", "DragHandleButton"]


class ActivityLogWidget(ActivityProfileRowsMixin, ActivityProfileDragMixin, ActivityLogControlsMixin, QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._main_window = cast("UnifiedMainWindow | None", parent)
        self._config = get_settings()
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
        self.enable_all_btn = QPushButton("Enable All")
        self.disable_all_btn = QPushButton("Disable All")
        self.enable_all_btn.clicked.connect(self._select_all)
        self.disable_all_btn.clicked.connect(self._deselect_all)
        btn_layout.addWidget(self.enable_all_btn)
        btn_layout.addWidget(self.disable_all_btn)
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
        self.log_viewer = ANSIConsoleWidget()
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

    def _setup_hotkey_grid(self) -> None:
        """Build the hotkey grid dynamically from AdvancedOptionsModel metadata."""
        while self.hotkey_grid.count():
            item = self.hotkey_grid.takeAt(0)
            if item is None:
                continue
            if widget := item.widget():
                widget.deleteLater()
            elif layout := item.layout():
                while layout.count():
                    child = layout.takeAt(0)
                    if child is not None and (w := child.widget()):
                        w.deleteLater()

        opts = self._config.advanced_options
        schema = opts.model_json_schema()
        properties = schema.get("properties", {})

        hotkey_items = []
        # Filter for keys that control the app (Advanced section) and are tagged as hotkeys
        for key, field in opts.model_fields.items():
            meta = field.json_schema_extra or {}
            if meta.get(IS_HOTKEY_KEY) == "True":
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
