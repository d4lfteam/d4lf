"""Paper doll equipment layout for the profile editor."""

from typing import override

from PyQt6.QtCore import QRect, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QPainter, QPen
from PyQt6.QtWidgets import QFrame, QHBoxLayout, QLabel, QSizePolicy, QVBoxLayout, QWidget

from src.item.data.item_type import ItemType

# Icon mapping for slots using common unicode symbols
SLOT_ICONS = {
    "Helm": "🪖",
    "Chest Armor": "👕",
    "Gloves": "🧤",
    "Pants": "👖",
    "Boots": "👢",
    "Amulet": "📿",
    "Rings": "💍",
    "Main Hand": "⚔️",
    "Off Hand": "🛡️",
    "Bludgeoning": "🔨",
    "Slashing": "🪓",
    "Dual-Wield 1": "🗡️",
    "Dual-Wield 2": "⚔️",
    "Dual Wields": "⚔️",
    "Ranged Weapon": "🏹",
    "Aspect Upgrades": "✨",
    "Sigils": "📜",
    "Tributes": "🏆",
    "Global Rules": "💎",
}

# Base gear slots common to all classes
BASE_GEAR_SLOTS = [
    # Left Column (Gear)
    ("Helm", [ItemType.Helm], QRect(70, 10, 145, 60)),
    ("Chest Armor", [ItemType.ChestArmor], QRect(70, 80, 145, 60)),
    ("Gloves", [ItemType.Gloves], QRect(70, 150, 145, 60)),
    ("Pants", [ItemType.Legs], QRect(70, 220, 145, 60)),
    ("Boots", [ItemType.Boots], QRect(70, 290, 145, 60)),
    # Right Column (Jewelry)
    ("Amulet", [ItemType.Amulet], QRect(525, 10, 145, 60)),
    ("Rings", [ItemType.Ring], QRect(525, 80, 145, 60)),
]


def get_weapon_slots(class_name: str | None = None) -> list[tuple[str, list[ItemType], QRect]]:
    """Return weapon slot definitions based on character class."""
    class_name = (class_name or "").lower()

    # 1H Weapon types for dual wielding
    one_hand_types = [ItemType.Axe, ItemType.Mace, ItemType.Sword, ItemType.Dagger, ItemType.Flail]

    if "barbarian" in class_name:
        return [
            ("Bludgeoning", [ItemType.Mace2H], QRect(525, 150, 145, 60)),
            ("Slashing", [ItemType.Axe2H, ItemType.Sword2H, ItemType.Polearm], QRect(525, 220, 145, 60)),
            ("Dual Wields", one_hand_types, QRect(525, 290, 145, 60)),
        ]

    if "rogue" in class_name or "rog" in class_name:
        return [
            ("Dual Wields", [ItemType.Dagger, ItemType.Sword], QRect(525, 290, 145, 60)),
            ("Ranged Weapon", [ItemType.Bow, ItemType.Crossbow2H], QRect(525, 220, 145, 60)),
        ]

    if "necromancer" in class_name or "necro" in class_name:
        return [
            (
                "Main Hand",
                [
                    ItemType.Scythe,
                    ItemType.Scythe2H,
                    ItemType.Sword,
                    ItemType.Sword2H,
                    ItemType.Dagger,
                    ItemType.Wand,
                    ItemType.Mace,
                ],
                QRect(525, 220, 145, 60),
            ),
            ("Off Hand", [ItemType.Shield, ItemType.Focus], QRect(525, 290, 145, 60)),
        ]

    if "druid" in class_name or "dru" in class_name:
        return [
            (
                "Main Hand",
                [ItemType.Mace, ItemType.Mace2H, ItemType.Axe, ItemType.Axe2H, ItemType.Staff, ItemType.Polearm],
                QRect(525, 220, 145, 60),
            ),
            ("Off Hand", [ItemType.OffHandTotem], QRect(525, 290, 145, 60)),
        ]

    if any(c in class_name for c in ["sorcerer", "sorc", "warlock"]):
        return [
            ("Main Hand", [ItemType.Wand, ItemType.Dagger, ItemType.Staff], QRect(525, 220, 145, 60)),
            ("Off Hand", [ItemType.Focus], QRect(525, 290, 145, 60)),
        ]

    if "spiritborn" in class_name or "spirit" in class_name:
        return [
            ("Main Hand", [ItemType.Glaive, ItemType.Quarterstaff, ItemType.Polearm], QRect(525, 220, 145, 60)),
            # Spiritborn typically uses 2H or Dual 1H (handled in Main/Off logic if needed)
            ("Off Hand", [], QRect(525, 290, 145, 60)),
        ]

    # Default Fallback
    return [
        (
            "Main Hand",
            [
                ItemType.Axe,
                ItemType.Axe2H,
                ItemType.Bow,
                ItemType.Crossbow2H,
                ItemType.Dagger,
                ItemType.Flail,
                ItemType.Glaive,
                ItemType.Mace,
                ItemType.Mace2H,
                ItemType.Polearm,
                ItemType.Quarterstaff,
                ItemType.Scythe,
                ItemType.Scythe2H,
                ItemType.Staff,
                ItemType.Sword,
                ItemType.Sword2H,
                ItemType.Wand,
            ],
            QRect(525, 220, 145, 60),
        ),
        ("Off Hand", [ItemType.Shield, ItemType.Focus, ItemType.OffHandTotem, ItemType.Tome], QRect(525, 290, 145, 60)),
    ]


# Compatibility export for logic that expects a single list
EQUIPMENT_SLOTS = BASE_GEAR_SLOTS + get_weapon_slots()

SPECIAL_TABS = ["Aspect Upgrades", "Sigils", "Tributes", "Global Rules"]


class EquipmentSlotButton(QFrame):
    """A clickable equipment slot button for the paper doll."""

    clicked = pyqtSignal()

    def __init__(self, slot_name: str, item_types: list[ItemType], rect: QRect, parent: QWidget | None = None):
        super().__init__(parent)
        self.slot_name = slot_name
        self.item_types = item_types
        self._slot_rect = rect  # Use _slot_rect to avoid shadowing QWidget.rect property
        self._has_config = False
        self._is_active = False
        self._icon = SLOT_ICONS.get(slot_name, "")

        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "EquipmentSlotButton {"
            "   border: 2px solid #4a5568;"
            "   border-radius: 8px;"
            "   background-color: #1e293b;"
            "   color: #94a3b8;"
            "   font-size: 11px;"
            "   font-weight: bold;"
            "   padding: 4px;"
            "   text-align: center;"
            "}"
            "EquipmentSlotButton:hover {"
            "   border-color: #3b82f6;"
            "   background-color: #2d3748;"
            "}"
            "EquipmentSlotButton.active {"
            "   border: 2px solid #3b82f6;"
            "   background-color: #1e3a5f;"
            "   color: #e2e8f0;"
            "}"
        )

    def set_active(self, active: bool) -> None:
        self._is_active = active
        self.update()

    def has_config(self, has: bool) -> None:
        self._has_config = has
        self.update()

    @override
    def paintEvent(self, event):  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Use local rect (0,0,W,H) instead of geometry (X,Y,W,H) relative to parent
        r = self.rect()

        # Background
        bg_color = QColor(30, 58, 95) if self._is_active else QColor(30, 41, 59)

        painter.fillRect(r, bg_color)

        # Border
        pen_width = max(1, int(2 * (self.width() / 85.0))) if self.width() < 120 else 2
        pen = QPen(QColor(74, 85, 104) if not self._is_active else QColor(59, 130, 246), pen_width)
        painter.setPen(pen)
        painter.drawRoundedRect(r.adjusted(1, 1, -1, -1), 6, 6)

        h = self.height()
        w = self.width()
        # Relative scaling for fonts (reference width is 145px)
        s = w / 145.0
        base_icon, base_text = 18, 10

        # Slot Icon
        painter.setPen(QColor(148, 163, 184) if not self._is_active else QColor(226, 232, 240))
        icon_font = QFont("Segoe UI Emoji", max(6, int(base_icon * s)))
        painter.setFont(icon_font)
        painter.drawText(r.adjusted(0, int(h * 0.05), 0, -int(h * 0.50)), Qt.AlignmentFlag.AlignCenter, self._icon)

        # Slot name
        painter.setPen(QColor(148, 163, 184) if not self._is_active else QColor(226, 232, 240))
        font = QFont("Segoe UI", max(6, int(base_text * s)), QFont.Weight.Medium)
        painter.setFont(font)
        painter.drawText(
            r.adjusted(2, int(h * 0.50), -2, -int(h * 0.05)),
            Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap,
            self.slot_name,
        )

        # Config indicator (dot in corner if has config)
        if self._has_config:
            painter.setPen(QColor(34, 197, 94))
            painter.setBrush(QColor(34, 197, 94))
            painter.drawEllipse(self.width() - 12, 4, 8, 8)

        painter.end()

    @override
    def mousePressEvent(self, event):  # type: ignore[override]
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit()
        super().mousePressEvent(event)

    @override
    def sizeHint(self) -> QSize:
        return QSize(self._slot_rect.width(), self._slot_rect.height())


class CharacterCanvas(QFrame):
    """Canvas for drawing the character silhouette and slot buttons."""

    resized = pyqtSignal()
    REF_WIDTH = 740
    REF_HEIGHT = 510

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setStyleSheet("QFrame {   background-color: #0f172a;   border: none;}")

    @override
    def sizeHint(self) -> QSize:
        return QSize(self.REF_WIDTH, self.REF_HEIGHT)

    @override
    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.resized.emit()

    @override
    def paintEvent(self, event):  # type: ignore[override]
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw a simple character silhouette outline
        center_x = self.width() / 2
        sx = self.width() / self.REF_WIDTH
        sy = self.height() / self.REF_HEIGHT

        # Use a slightly lighter, more muted color for the silhouette
        # and thicker lines for better visibility without being too stark.
        pen = QPen(QColor(100, 116, 139), max(1, int(2 * min(sx, sy))))
        painter.setPen(pen)

        # Head circle
        painter.drawEllipse(int(center_x - 25 * sx), int(10 * sy), int(50 * sx), int(50 * sy))

        # Torso (more of a rectangle now)
        painter.drawRect(int(center_x - 20 * sx), int(60 * sy), int(40 * sx), int(100 * sy))

        # Pelvis/Hips (a wider, shorter rectangle)
        painter.drawRect(int(center_x - 30 * sx), int(160 * sy), int(60 * sx), int(20 * sy))

        # Arms
        painter.drawLine(int(center_x - 20 * sx), int(80 * sy), int(center_x - 80 * sx), int(150 * sy))
        painter.drawLine(int(center_x + 20 * sx), int(80 * sy), int(center_x + 80 * sx), int(150 * sy))

        # Legs
        painter.drawLine(int(center_x - 20 * sx), int(180 * sy), int(center_x - 40 * sx), int(370 * sy))
        painter.drawLine(int(center_x + 20 * sx), int(180 * sy), int(center_x + 40 * sx), int(370 * sy))

        painter.end()


class PaperDollWidget(QWidget):
    """A paper doll character layout with clickable equipment slots."""

    slot_clicked = pyqtSignal(str)  # Emits slot_name when clicked

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._active_slot: str | None = None
        self._slot_buttons: dict[str, EquipmentSlotButton] = {}
        self._has_config_map: dict[str, bool] = {}

        self.setup_ui()

    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Character silhouette panel (left side) - fill remaining space
        self.character_panel = QFrame()
        self.character_panel.setStyleSheet("QFrame {   background-color: #0f172a;   border-right: 1px solid #1e293b;}")
        self.character_panel.setMaximumWidth(800)
        char_layout = QVBoxLayout(self.character_panel)
        char_layout.setContentsMargins(20, 10, 20, 20)
        char_layout.setSpacing(5)
        char_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Special Navigation Tabs at the Top
        self.special_nav_layout = QHBoxLayout()
        self.special_nav_layout.setSpacing(15)
        self.special_nav_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        for name in SPECIAL_TABS:
            btn = EquipmentSlotButton(name, [], QRect(0, 0, 145, 60))
            btn.clicked.connect(lambda n=name: self._on_slot_clicked(n))
            btn.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
            self._slot_buttons[name] = btn
            self.special_nav_layout.addWidget(btn)
        char_layout.addLayout(self.special_nav_layout)

        title_label = QLabel("Equipment")
        title_label.setProperty("titleLabel", True)  # noqa: FBT003
        title_label.setStyleSheet(
            "QLabel { color: #e2e8f0; font-size: 18px; font-weight: bold; padding: 10px; border-top: 1px solid #334155; border-bottom: 1px solid #334155; border-left: none; border-right: none; }"
        )
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        char_layout.addWidget(title_label)

        # Character silhouette canvas
        self.character_canvas = CharacterCanvas()
        self.character_canvas.resized.connect(self.position_slots)
        char_layout.addWidget(self.character_canvas)

        main_layout.addWidget(self.character_panel, stretch=0)

        # Side panel (right side) - initially shows placeholder
        self.side_panel = QFrame()
        self.side_panel.setStyleSheet("QFrame {   background-color: #1e293b;   border-left: 1px solid #334155;}")
        self.side_panel.setMinimumWidth(650)
        side_layout = QVBoxLayout(self.side_panel)
        side_layout.setContentsMargins(20, 10, 20, 20)

        self.show_message("Select an equipment slot to configure")

        main_layout.addWidget(self.side_panel, stretch=1)
        self.side_panel.hide()

    def show_message(self, text: str) -> None:
        """Clear side panel and show a message label."""
        self._clear_layout()

        placeholder = QLabel(text)
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder.setWordWrap(True)
        placeholder.setStyleSheet("QLabel {   color: #64748b;   font-size: 14px;   padding: 40px;}")
        self.side_panel.layout().addWidget(placeholder)
        self.side_panel.layout().addStretch()

    def set_active_slot(self, slot_name: str | None) -> None:
        """Set the currently active equipment slot."""
        self._active_slot = slot_name
        for name, button in self._slot_buttons.items():
            button.set_active(name == slot_name)
        if slot_name:
            self.slot_clicked.emit(slot_name)

    def update_config_status(self, slot_name: str, has_config: bool) -> None:
        """Update the config indicator for a slot."""
        self._has_config_map[slot_name] = has_config
        if slot_name in self._slot_buttons:
            self._slot_buttons[slot_name].has_config(has_config)

    def add_slot(self, slot_name: str, item_types: list[ItemType], rect: QRect) -> None:
        """Add an equipment slot button."""
        button = EquipmentSlotButton(slot_name, item_types, rect, self.character_canvas)
        button.clicked.connect(lambda: self._on_slot_clicked(slot_name))  # type: ignore[misc]
        self._slot_buttons[slot_name] = button

    def position_slots(self) -> None:
        """Position all slot buttons on the character canvas based on their defined rects and current canvas size."""
        if not self.character_canvas.width() or not self.character_canvas.height():
            return

        sx = self.character_canvas.width() / 740.0
        sy = self.character_canvas.height() / 510.0

        # Scale the layout spacing for the top navigation
        self.special_nav_layout.setSpacing(int(15 * sx))

        for name, button in self._slot_buttons.items():
            if button.parent() == self.character_canvas:
                # Use the rect stored internally during add_slot
                rect = button._slot_rect
                button.setGeometry(
                    int(rect.x() * sx), int(rect.y() * sy), int(rect.width() * sx), int(rect.height() * sy)
                )
            elif name in SPECIAL_TABS:
                # Scale the special buttons to match the canvas items
                button.setFixedSize(int(145 * sx), int(60 * sy))
            button.show()

    def _on_slot_clicked(self, slot_name: str):
        if self._active_slot == slot_name:
            self.set_active_slot(None)
            self.slot_clicked.emit(None)
        else:
            self.set_active_slot(slot_name)
            self.slot_clicked.emit(slot_name)

    def _clear_layout(self) -> None:
        """Remove items from the side panel layout without necessarily deleting widgets."""
        while self.side_panel.layout().count() > 0:
            item = self.side_panel.layout().takeAt(0)
            if item and item.widget():
                item.widget().hide()

    def clear_side_panel(self) -> None:
        """Reset side panel to default placeholder."""
        self.side_panel.hide()

    def restore_side_panel(self, widget: QWidget) -> None:
        """Restore a previously hidden widget to the side panel."""
        self._clear_layout()
        self.side_panel.layout().addWidget(widget)
        widget.show()
        self.side_panel.show()


# Re-export for convenience
__all__ = ["EQUIPMENT_SLOTS", "CharacterCanvas", "EquipmentSlotButton", "PaperDollWidget"]
