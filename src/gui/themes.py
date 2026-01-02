"""Original simple gray theme with dynamic asset paths"""

from src.config import BASE_DIR

# Convert paths to use forward slashes for Qt
CHECKMARK_DARK = str(BASE_DIR / "assets" / "checkmark_dark.svg").replace("\\", "/")
CHECKMARK_LIGHT = str(BASE_DIR / "assets" / "checkmark_light.svg").replace("\\", "/")


DARK_THEME = f"""
QWidget {{
    background-color: #121212;
    color: #e0e0e0;
}}
QPushButton {{
    background-color: #1f1f1f;
    border: 1px solid #3c3c3c;
    border-radius: 5px;
    padding: 3px 8px;
    font-size: 14px;
}}
QPushButton:hover {{
    background-color: #2c2c2c;
    border: 1px solid #5c5c5c;
}}
QPushButton:pressed {{
    background-color: #3c3c3c;
}}
QTextEdit {{
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
    border-radius: 5px;
    padding: 8px;
}}
QLineEdit {{
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
    border-radius: 5px;
    padding: 3px;
}}
QTabBar::tab {{
    background-color: #1f1f1f;
    color: #e0e0e0;
    padding: 5px 15px;
    margin: 2px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    min-width: 80px;
}}
QTabBar::tab:selected {{
    background-color: #3c3c3c;
    border: 1px solid #5c5c5c;
    border-bottom: none;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
}}
QTabBar::tab:hover {{
    background-color: #2c2c2c;
    border: 1px solid #5c5c5c;
}}
QTabBar::tab:!selected {{
    margin-top: 3px;
}}
QCheckBox {{
    color: #e0e0e0;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 1px solid #5c5c5c;
    background-color: #1e1e1e;
    border-radius: 2px;
}}
QCheckBox::indicator:hover {{
    border: 1px solid #7c7c7c;
}}
QCheckBox::indicator:checked {{
    background-color: #5c5c5c;
    border: 1px solid #5c5c5c;
    image: url({CHECKMARK_DARK});
}}
QScrollBar:vertical {{
    background-color: #1f1f1f;
    width: 16px;
    margin: 16px 0 16px 0;
    border: 1px solid #3c3c3c;
}}
QScrollBar::handle:vertical {{
    background-color: #3c3c3c;
    min-height: 20px;
    border-radius: 4px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    background-color: #1f1f1f;
    height: 16px;
    subcontrol-origin: margin;
    border: 1px solid #3c3c3c;
}}
QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover {{
    background-color: #3c3c3c;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
QComboBox {{
    background-color: #1f1f1f;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
    border-radius: 5px;
    padding: 3px;
}}
QComboBox QAbstractItemView {{
    background-color: #1f1f1f;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
    selection-background-color: #3c3c3c;
}}
QListWidget {{
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
}}
QListWidget::item:selected {{
    background-color: #3c3c3c;
}}
QToolTip {{
    background-color: #1f1f1f;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
    padding: 3px;
    border-radius: 5px;
}}

/* Affix editor / GA helper styling */
QLabel[greaterCountLabel="true"] {{
    color: gray;
    font-style: italic;
}}

QSpinBox[autoSyncSpin="true"] {{
    background-color: #3c3c3c;
    color: #888888;
}}

QLabel[affixHeaderLabel="true"] {{
    color: #e0e0e0;
}}

QCheckBox[greaterCheckbox="true"] {{
    background-color: transparent;
}}

/* Hotkey button styling */
QPushButton[hotkeyButton="true"] {{
    text-align: left;
    padding-left: 5px;
}}
"""


LIGHT_THEME = f"""
QWidget {{
    background-color: #ededed;
    color: #1f1f1f;
}}
QPushButton {{
    background-color: #e0e0e0;
    border: 1px solid #c3c3c3;
    border-radius: 5px;
    padding: 3px 8px;
    font-size: 14px;
}}
QPushButton:hover {{
    background-color: #d3d3d3;
    border: 1px solid #a3a3a3;
}}
QPushButton:pressed {{
    background-color: #c3c3c3;
}}
QTextEdit {{
    background-color: #e1e1e1;
    color: #1f1f1f;
    border: 1px solid #c3c3c3;
    border-radius: 5px;
    padding: 8px;
}}
QLineEdit {{
    background-color: #e1e1e1;
    color: #1f1f1f;
    border: 1px solid #c3c3c3;
    border-radius: 5px;
    padding: 3px;
}}
QTabBar::tab {{
    background-color: #e0e0e0;
    color: #1f1f1f;
    padding: 5px 15px;
    margin: 2px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    min-width: 80px;
}}
QTabBar::tab:selected {{
    background-color: #c3c3c3;
    border: 1px solid #a3a3a3;
    border-bottom: none;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
}}
QTabBar::tab:hover {{
    background-color: #d3d3d3;
    border: 1px solid #a3a3a3;
}}
QTabBar::tab:!selected {{
    margin-top: 3px;
}}
QCheckBox {{
    color: #1f1f1f;
    spacing: 8px;
}}
QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border: 2px solid #5c5c5c;
    background-color: #ffffff;
    border-radius: 2px;
}}
QCheckBox::indicator:hover {{
    border: 2px solid #3c3c3c;
}}
QCheckBox::indicator:checked {{
    background-color: #3c3c3c;
    border: 2px solid #1f1f1f;
    image: url({CHECKMARK_LIGHT});
}}
QScrollBar:vertical {{
    background-color: #e0e0e0;
    width: 16px;
    margin: 16px 0 16px 0;
    border: 1px solid #c3c3c3;
}}
QScrollBar::handle:vertical {{
    background-color: #c3c3c3;
    min-height: 20px;
    border-radius: 4px;
}}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    background-color: #e0e0e0;
    height: 16px;
    subcontrol-origin: margin;
    border: 1px solid #c3c3c3;
}}
QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover {{
    background-color: #c3c3c3;
}}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}
QComboBox {{
    background-color: #e0e0e0;
    color: #1f1f1f;
    border: 1px solid #c3c3c3;
    border-radius: 5px;
    padding: 3px;
}}
QComboBox QAbstractItemView {{
    background-color: #e0e0e0;
    color: #1f1f1f;
    border: 1px solid #c3c3c3;
    selection-background-color: #c3c3c3;
}}
QListWidget {{
    background-color: #e1e1e1;
    color: #1f1f1f;
    border: 1px solid #c3c3c3;
}}
QListWidget::item:selected {{
    background-color: #c3c3c3;
}}
QToolTip {{
    background-color: #e0e0e0;
    color: #1f1f1f;
    border: 1px solid #c3c3c3;
    padding: 3px;
    border-radius: 5px;
}}

/* Affix editor / GA helper styling */
QLabel[greaterCountLabel="true"] {{
    color: gray;
    font-style: italic;
}}

QSpinBox[autoSyncSpin="true"] {{
    background-color: #d3d3d3;
    color: #555555;
}}

QLabel[affixHeaderLabel="true"] {{
    color: #1f1f1f;
}}

QCheckBox[greaterCheckbox="true"] {{
    background-color: transparent;
}}

/* Hotkey button styling */
QPushButton[hotkeyButton="true"] {{
    text-align: left;
    padding-left: 5px;
}}
"""
