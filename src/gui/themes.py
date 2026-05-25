"""Original simple gray theme with dynamic asset paths."""

DARK_THEME = """
QWidget {
    background-color: #1a1a1a;
    color: #e0e0e0;
}
QPushButton {
    background-color: #1f1f1f;
    border: 1px solid #3c3c3c;
    border-radius: 5px;
    padding: 3px 8px;
    font-size: 14px;
}
QPushButton:hover {
    background-color: #2c2c2c;
    border: 1px solid #5c5c5c;
}
QPushButton#primary {
    background-color: #721c24;
    border: 1px solid #f5c6cb;
    color: #f8d7da;
    font-weight: bold;
}
QPushButton#secondary {
    background-color: transparent;
    border: 1px solid #3c3c3c;
}
QPushButton:pressed {
    background-color: #3c3c3c;
}
QGroupBox {
    font-weight: bold;
    font-size: 15px;
    border: 1px solid #3c3c3c;
    margin-top: 20px;
    padding-top: 20px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
}
QTextEdit {
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
    border-radius: 5px;
    padding: 8px;
}
QLineEdit {
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
    border-radius: 5px;
    padding: 3px;
}
QTabBar::tab {
    background-color: #1f1f1f;
    color: #e0e0e0;
    padding: 5px 15px;
    margin: 2px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    min-width: 80px;
}
QTabBar::tab:selected {
    background-color: #3c3c3c;
    border: 1px solid #5c5c5c;
    border-bottom: none;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
}
QTabBar::tab:hover {
    background-color: #2c2c2c;
    border: 1px solid #5c5c5c;
}
QTabBar::tab:!selected {
    margin-top: 3px;
}
QCheckBox {
    color: #e0e0e0;
    spacing: 8px;
}
QCheckBox:checked {
    color: #23fc5d;
    font-weight: bold;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #5c5c5c;
    background-color: #1a1a1a;
    border-radius: 3px;
}
QCheckBox::indicator:hover {
    border: 1px solid #7c7c7c;
}
QCheckBox::indicator:checked {
    background-color: #2c2c2c;
    border: 1px solid #23fc5d;
}

/* Action Bar at bottom */
QWidget#action-bar {
    background-color: #161616;
    border-top: 1px solid #3c3c3c;
}
QWidget#action-bar QPushButton {
    background-color: #2c2c2c;
    border: 1px solid #444444;
    color: #ffffff;
}
QWidget#action-bar QPushButton:hover {
    border: 1px solid #23fc5d;
}

/* Switch Toggle Styling */
QCheckBox#switch::indicator {
    width: 36px; height: 18px;
    border-radius: 9px;
    border: 1px solid #5c5c5c;
    background-color: #1a1a1a;
}
QCheckBox#switch::indicator:checked {
    background-color: #2c2c2c;
    border: 1px solid #23fc5d;
}
QCheckBox#switch::indicator:unchecked {
    background-color: #444;
}

/* Disabled checkbox styling */
QCheckBox:disabled {
    color: gray;
}
QCheckBox::indicator:disabled {
    background-color: #555;
    border: 1px solid #444;
}

QScrollBar:vertical {
    background-color: #1f1f1f;
    width: 16px;
    margin: 16px 0 16px 0;
    border: 1px solid #3c3c3c;
}
QScrollBar::handle:vertical {
    background-color: #3c3c3c;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    background-color: #1f1f1f;
    height: 16px;
    subcontrol-origin: margin;
    border: 1px solid #3c3c3c;
}
QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover {
    background-color: #3c3c3c;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
QComboBox {
    background-color: #1f1f1f;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
    border-radius: 5px;
    padding: 3px;
}
QComboBox QAbstractItemView {
    background-color: #1f1f1f;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
    selection-background-color: #3c3c3c;
}
QListWidget {
    background-color: #1e1e1e;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
}
QListWidget::item:selected {
    background-color: #3c3c3c;
}
QToolTip {
    background-color: #1f1f1f;
    color: #e0e0e0;
    border: 1px solid #3c3c3c;
    padding: 3px;
    border-radius: 5px;
}

/* Affix editor / GA helper styling */
QLabel[greaterCountLabel="true"] {
    color: gray;
    font-style: italic;
}

QSpinBox[autoSyncSpin="true"] {
    background-color: #3c3c3c;
    color: #888888;
}

QLabel[affixHeaderLabel="true"] {
    color: #e0e0e0;
}

QCheckBox[greaterCheckbox="true"] {
    background-color: transparent;
}

/* Hotkey button styling */
QPushButton[hotkeyButton="true"] {
    text-align: left;
    padding-left: 5px;
}

QLabel#key-badge {
    background-color: #333333;
    color: #ffffff;
    border: 1px solid #555555;
    border-radius: 4px;
    padding: 2px 6px;
    font-family: 'Consolas', 'Monospace';
}

/* Segmented Control Styling */
QWidget#segmented-container {
    background-color: #121212;
    border: 1px solid #3c3c3c;
    border-radius: 6px;
}
QPushButton#segment-btn {
    background-color: #1f1f1f;
    border: 1px solid #3c3c3c;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 13px;
    font-weight: normal;
}
QPushButton#segment-btn:checked {
    background-color: #2c2c2c;
    border: 1px solid #23fc5d;
    color: #23fc5d;
    font-weight: bold;
}

QLabel#description-label {
    color: #999;
    font-size: 11px;
}
QLabel#setting-title {
    font-weight: bold;
    font-size: 13px;
}
"""


LIGHT_THEME = """
QWidget {
    background-color: #ededed;
    color: #1f1f1f;
}
QPushButton {
    background-color: #e0e0e0;
    border: 1px solid #c3c3c3;
    border-radius: 5px;
    padding: 3px 8px;
    font-size: 14px;
}
QPushButton:hover {
    background-color: #d3d3d3;
    border: 1px solid #a3a3a3;
}
QPushButton:pressed {
    background-color: #c3c3c3;
}
QGroupBox {
    font-weight: bold;
    font-size: 15px;
    border: 1px solid #c3c3c3;
    margin-top: 20px;
    padding-top: 20px;
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    left: 10px;
}
QTextEdit {
    background-color: #e1e1e1;
    color: #1f1f1f;
    border: 1px solid #c3c3c3;
    border-radius: 5px;
    padding: 8px;
}
QLineEdit {
    background-color: #e1e1e1;
    color: #1f1f1f;
    border: 1px solid #c3c3c3;
    border-radius: 5px;
    padding: 3px;
}
QTabBar::tab {
    background-color: #e0e0e0;
    color: #1f1f1f;
    padding: 5px 15px;
    margin: 2px;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
    min-width: 80px;
}
QTabBar::tab:selected {
    background-color: #c3c3c3;
    border: 1px solid #a3a3a3;
    border-bottom: none;
    border-top-left-radius: 5px;
    border-top-right-radius: 5px;
}
QTabBar::tab:hover {
    background-color: #d3d3d3;
    border: 1px solid #a3a3a3;
}
QTabBar::tab:!selected {
    margin-top: 3px;
}
QCheckBox {
    color: #1f1f1f;
    spacing: 8px;
}
QCheckBox:checked {
    color: #000000;
    font-weight: bold;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border: 1px solid #c3c3c3;
    background-color: #ffffff;
    border-radius: 3px;
}
QCheckBox::indicator:hover {
    border: 1px solid #a3a3a3;
}
QCheckBox::indicator:checked {
    background-color: #a0a0a0;
    border: 1px solid #23fc5d;
}

/* Switch Toggle Styling */
QCheckBox#switch::indicator {
    width: 36px; height: 18px;
    border-radius: 9px;
    border: 1px solid #c3c3c3;
    background-color: #ffffff;
}
QCheckBox#switch::indicator:checked {
    background-color: #a0a0a0;
    border: 1px solid #23fc5d;
}
QCheckBox#switch::indicator:unchecked {
    background-color: #d3d3d3;
}

/* Disabled checkbox styling */
QCheckBox:disabled {
    color: gray;
}
QCheckBox::indicator:disabled {
    background-color: #555;
    border: 1px solid #444;
}

QScrollBar:vertical {
    background-color: #e0e0e0;
    width: 16px;
    margin: 16px 0 16px 0;
    border: 1px solid #c3c3c3;
}
QScrollBar::handle:vertical {
    background-color: #c3c3c3;
    min-height: 20px;
    border-radius: 4px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    background-color: #e0e0e0;
    height: 16px;
    subcontrol-origin: margin;
    border: 1px solid #c3c3c3;
}
QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover {
    background-color: #c3c3c3;
}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
    background: none;
}
QComboBox {
    background-color: #e0e0e0;
    color: #1f1f1f;
    border: 1px solid #c3c3c3;
    border-radius: 5px;
    padding: 3px;
}
QComboBox QAbstractItemView {
    background-color: #e0e0e0;
    color: #1f1f1f;
    border: 1px solid #c3c3c3;
    selection-background-color: #c3c3c3;
}
QListWidget {
    background-color: #e1e1e1;
    color: #1f1f1f;
    border: 1px solid #c3c3c3;
}
QListWidget::item:selected {
    background-color: #c3c3c3;
}
QToolTip {
    background-color: #e0e0e0;
    color: #1f1f1f;
    border: 1px solid #c3c3c3;
    padding: 3px;
    border-radius: 5px;
}

/* Affix editor / GA helper styling */
QLabel[greaterCountLabel="true"] {
    color: gray;
    font-style: italic;
}

QSpinBox[autoSyncSpin="true"] {
    background-color: #d3d3d3;
    color: #555555;
}

QLabel[affixHeaderLabel="true"] {
    color: #1f1f1f;
}

QCheckBox[greaterCheckbox="true"] {
    background-color: transparent;
}

/* Hotkey button styling */
/* Segmented Control Styling */
QWidget#segmented-container {
    background-color: #dcdcdc;
    border: 1px solid #c3c3c3;
    border-radius: 6px;
}
QPushButton#segment-btn {
    background-color: #ededed;
    border: 1px solid #a3a3a3;
    border-radius: 4px;
    padding: 4px 12px;
    font-size: 13px;
    font-weight: normal;
}
QPushButton#segment-btn:checked {
    background-color: #a0a0a0;
    border: 1px solid #23fc5d;
    color: #000000;
    font-weight: bold;
}

QPushButton[hotkeyButton="true"] {
    text-align: left;
    padding-left: 5px;
}

QLabel#description-label {
    color: #666;
    font-size: 11px;
}
QLabel#setting-title {
    font-weight: bold;
    font-size: 13px;
}

/* Action Bar at bottom */
QWidget#action-bar {
    background-color: #e0e0e0;
    border-top: 1px solid #c3c3c3;
}
QWidget#action-bar QPushButton {
    background-color: #f5f5f0;
    border: 1px solid #b0b0b0;
}
QWidget#action-bar QPushButton:hover {
    border: 1px solid #23fc5d;
}
"""
