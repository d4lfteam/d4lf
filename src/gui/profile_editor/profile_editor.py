"""Profile editor with paper doll layout."""

import logging

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from src.config.profile_models import ProfileModel
from src.gui.importer.gui_common import save_as_profile
from src.gui.profile_editor.affixes_tab import AffixesTab
from src.gui.profile_editor.aspect_upgrades_tab import AspectUpgradesTab
from src.gui.profile_editor.global_uniques_tab import UniquesTab
from src.gui.profile_editor.paper_doll import BASE_GEAR_SLOTS, PaperDollWidget, get_weapon_slots
from src.gui.profile_editor.sigils_tab import SigilsTab
from src.gui.profile_editor.tributes_tab import TributesTab

LOGGER = logging.getLogger(__name__)


class ProfileEditor(QWidget):
    """Profile editor with paper doll layout and side panel for editing."""

    # Signal emitted when profile is saved (passes profile name)
    profile_saved = pyqtSignal(str)

    def __init__(self, profile_model: ProfileModel, parent: QWidget | None = None):
        super().__init__(parent)
        self.profile_model = profile_model

        # Create all tab widgets upfront (lazy-loaded internally)
        self.affixes_tab = AffixesTab(self.profile_model.affixes, self)
        self.aspect_upgrades_tab = AspectUpgradesTab(self.profile_model.aspect_upgrades, self)
        self.sigils_tab = SigilsTab(self.profile_model.sigils, self)
        self.tributes_tab = TributesTab(self.profile_model.tributes, self)
        self.uniques_tab = UniquesTab(self.profile_model.global_uniques, self)

        # Side panel content widget (swaps based on slot selection)
        self.side_content_widget: QWidget | None = None

        self.current_class = self._detect_class()

        # Build the UI
        self.setup_ui()

        # Reset window expansion state on load to prevent accumulation when switching profiles
        QTimer.singleShot(50, lambda: self._adjust_window_size(expanding=False))

    def _detect_class(self) -> str:
        """Return the character class defined in the profile model."""
        return self.profile_model.class_name.lower()

    def setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Paper doll widget (left side with clickable slots)
        self.paper_doll = PaperDollWidget()

        # Add base gear slots
        for slot_name, item_types, rect in BASE_GEAR_SLOTS:
            self.paper_doll.add_slot(slot_name, item_types, rect)

        # Add dynamic weapon slots based on class
        self.weapon_slots = get_weapon_slots(self.current_class)
        for slot_name, item_types, rect in self.weapon_slots:
            self.paper_doll.add_slot(slot_name, item_types, rect)

        # Position all slot buttons on the canvas
        self.paper_doll.position_slots()

        # Add Bulk Actions at bottom of armory
        actions_group = QGroupBox("Profile-Wide Actions")
        actions_layout = QHBoxLayout(actions_group)
        actions_layout.setContentsMargins(10, 15, 10, 10)

        btn_min_ga = QPushButton("Set Min GAs")
        btn_min_ga.setToolTip("Set the Minimum Greater Affix requirement for every legendary filter in this profile.")
        btn_min_ga.clicked.connect(self.affixes_tab.set_all_min_greater_affix)

        btn_min_power = QPushButton("Set minPower")
        btn_min_power.setToolTip(
            "Set the Minimum Power threshold (e.g. 900) for every legendary filter in this profile."
        )
        btn_min_power.clicked.connect(self.affixes_tab.set_all_min_power)

        btn_to_percent = QPushButton("Convert to Min %")
        btn_to_percent.setToolTip(
            "Convert every legendary filter in this profile to use 'Min %' mode instead of fixed values."
        )
        btn_to_percent.clicked.connect(self.affixes_tab.convert_all_to_min_percent_of_affix)

        for btn in [btn_min_ga, btn_min_power, btn_to_percent]:
            btn.setFixedHeight(32)
            actions_layout.addWidget(btn)

        # Insert into the paper doll panel's vertical layout (after the canvas)
        self.paper_doll.character_panel.layout().addWidget(actions_group)

        # Pre-create integrated gear view components to avoid heavy construction on every click
        self.gear_view_scroll = QScrollArea()
        self.gear_view_scroll.setWidgetResizable(True)
        self.gear_view_scroll.setFrameShape(QFrame.Shape.NoFrame)
        self.gear_view_container = QWidget()
        self.gear_view_layout = QVBoxLayout(self.gear_view_container)
        self.gear_view_layout.setContentsMargins(0, 0, 10, 0)

        self.gear_view_header = QLabel()
        self.gear_view_header.setStyleSheet("font-size: 18px; font-weight: bold; color: #3b82f6; margin-bottom: 10px;")
        self.gear_view_layout.addWidget(self.gear_view_header)
        self.gear_view_layout.addWidget(self.affixes_tab)
        self.gear_view_layout.addWidget(self.uniques_tab)
        self.gear_view_scroll.setWidget(self.gear_view_container)

        # Connect slot click signal
        self.paper_doll.slot_clicked.connect(self.on_slot_clicked)

        main_layout.addWidget(self.paper_doll)

    def _update_equilibrium_config_status(self):
        """Update the config status indicators on equipment slots."""
        # TODO: Implement logic to check which items in self.profile_model.affixes match slot types
        has_affix_config = len(self.profile_model.affixes) > 0
        self.paper_doll.update_config_status("Equipment", has_affix_config)

    def on_slot_clicked(self, slot_name: str):
        """Handle equipment slot click - show relevant tab in side panel."""
        self.side_content_widget = None
        item_types = None

        if not slot_name:
            # Hide all content widgets and show placeholder
            for widget in [
                self.affixes_tab,
                self.aspect_upgrades_tab,
                self.sigils_tab,
                self.tributes_tab,
                self.uniques_tab,
            ]:
                widget.hide()
            self.paper_doll.clear_side_panel()
            self._adjust_window_size(expanding=False)
            return

        # Find item types for the clicked slot
        all_equipment = BASE_GEAR_SLOTS + self.weapon_slots
        slot_info = next((s for s in all_equipment if s[0] == slot_name), None)
        item_types = slot_info[1] if slot_info else None

        # Determine if it's a gear/weapon slot (Affixes + Unique Rules)
        is_gear_slot = any(s[0] == slot_name for s in all_equipment)

        if is_gear_slot:
            # Ensure children are loaded before filtering
            self.affixes_tab.load()
            self.uniques_tab.load()
            # Ensure gear view components are visible (they might have been hidden by Global Rules)
            self.affixes_tab.show()
            self.uniques_tab.hide()
            self.gear_view_header.show()

            # Filter both tabs for this specific slot
            self.affixes_tab.filter_by_item_types(item_types, slot_name)

            self.gear_view_header.setText(f"Slot: {slot_name}")
            self.side_content_widget = self.gear_view_scroll
        elif slot_name == "Aspect Upgrades":
            self.aspect_upgrades_tab.load()
            self.aspect_upgrades_tab.show()
            self.side_content_widget = self.aspect_upgrades_tab
        elif slot_name == "Sigils":
            self.sigils_tab.load()
            self.sigils_tab.show()
            self.side_content_widget = self.sigils_tab
        elif slot_name == "Tributes":
            self.tributes_tab.load()
            self.tributes_tab.show()
            self.side_content_widget = self.tributes_tab
        elif slot_name == "Global Rules":
            self.uniques_tab.load()
            # When clicking global tab, show all rules via the integrated view
            # to avoid widget reparenting issues that break the layout.
            self.uniques_tab.filter_by_item_types(None)
            self.uniques_tab.show()

            # Hide the gear-specific parts
            self.affixes_tab.hide()
            self.gear_view_header.hide()

            self.side_content_widget = self.gear_view_scroll
        else:
            self.side_content_widget = None

        if self.side_content_widget is not None:
            self.paper_doll.restore_side_panel(self.side_content_widget)
            self._adjust_window_size(expanding=True)
        else:
            self.paper_doll.show_message(f"Configuration for '{slot_name}' coming soon")

    def _adjust_window_size(self, expanding: bool):
        """Resize the top-level window to accommodate the side panel."""
        win = self.window()
        if not win or win.isMaximized():
            return

        # Use dynamic properties on the main window to track expansion state globally across instances.
        # This prevents the window from getting wider and wider when switching profiles.
        is_already_expanded = win.property("profile_editor_expanded") is True

        if expanding and not is_already_expanded:
            # Store the current width before expanding so we can return to it exactly
            win.setProperty("profile_editor_pre_expansion_width", win.width())
            current_size = win.size()
            win.resize(current_size.width() + 850, current_size.height())
            win.setProperty("profile_editor_expanded", True)  # noqa: FBT003
        elif not expanding and is_already_expanded:
            # Restore the window to the exact width it had before the expansion
            pre_width = win.property("profile_editor_pre_expansion_width")
            current_size = win.size()
            if pre_width is not None:
                win.resize(pre_width, current_size.height())
            else:
                # Fallback if the property is missing
                new_width = max(800, current_size.width() - 850)
                win.resize(new_width, current_size.height())
            win.setProperty("profile_editor_expanded", False)  # noqa: FBT003

    def save_all(self):
        """Save all tabs' configurations."""
        try:
            # Re-validate to catch schema issues
            ProfileModel.model_validate(self.profile_model)

            save_as_profile(
                file_name=self.profile_model.name,
                profile=self.profile_model,
                url="custom",
                exclude={"name"},
                backup_file=True,
            )

            # Emit signal for hot reload
            self.profile_saved.emit(self.profile_model.name)
            QMessageBox.information(self, "Info", f"Profile saved successfully to {self.profile_model.name + '.yaml'}")
        except Exception as e:
            LOGGER.exception("Failed to save profile")
            QMessageBox.critical(self, "Error", f"Failed to save profile: {e}")
