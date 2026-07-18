"""Shared Qt theme templates used by the application and capability windows."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _Palette:
    window: str
    text: str
    button: str
    hover: str
    border: str
    hover_border: str
    editor: str
    selected: str
    checkbox_checked: str
    checkbox_bg: str
    checkbox_checked_bg: str
    checkbox_border: str
    checkbox_hover_border: str
    switch_border: str
    switch_unchecked: str
    scroll_handle: str
    combo: str
    list_bg: str
    nav_bg: str
    tooltip: str
    auto_sync: str
    auto_sync_text: str
    label: str
    badge_bg: str
    badge_text: str
    badge_border: str
    log_bg: str
    log_border: str
    segment_container: str
    segment_button: str
    segment_border: str
    segment_selected: str
    segment_selected_text: str
    row_bg: str
    row_alt: str
    row_border: str
    description: str
    action_bg: str
    action_button: str
    action_border: str
    action_text: str
    delete_text: str
    profile_help: str


_DARK = _Palette(
    window="#1a1a1a",
    text="#e0e0e0",
    button="#1f1f1f",
    hover="#2c2c2c",
    border="#3c3c3c",
    hover_border="#5c5c5c",
    editor="#1e1e1e",
    selected="#3c3c3c",
    checkbox_checked="@accent@",
    checkbox_bg="#1a1a1a",
    checkbox_checked_bg="#2c2c2c",
    checkbox_border="#5c5c5c",
    checkbox_hover_border="#7c7c7c",
    switch_border="#5c5c5c",
    switch_unchecked="#444",
    scroll_handle="#3c3c3c",
    combo="#1f1f1f",
    list_bg="#1e1e1e",
    nav_bg="#1a1a1a",
    tooltip="#1f1f1f",
    auto_sync="#3c3c3c",
    auto_sync_text="#888888",
    label="#e0e0e0",
    badge_bg="#333333",
    badge_text="#ffffff",
    badge_border="#555555",
    log_bg="#121212",
    log_border="#333",
    segment_container="#121212",
    segment_button="#1f1f1f",
    segment_border="#3c3c3c",
    segment_selected="#2c2c2c",
    segment_selected_text="@accent@",
    row_bg="#1c1c1c",
    row_alt="#242424",
    row_border="#252525",
    description="#999",
    action_bg="#161616",
    action_button="#2c2c2c",
    action_border="#444444",
    action_text="#ffffff",
    delete_text="#ff4d4d",
    profile_help="#888",
)
_LIGHT = _Palette(
    window="#ededed",
    text="#1f1f1f",
    button="#e0e0e0",
    hover="#d3d3d3",
    border="#c3c3c3",
    hover_border="#a3a3a3",
    editor="#e1e1e1",
    selected="#c3c3c3",
    checkbox_checked="#000000",
    checkbox_bg="#ffffff",
    checkbox_checked_bg="#a0a0a0",
    checkbox_border="#c3c3c3",
    checkbox_hover_border="#a3a3a3",
    switch_border="#c3c3c3",
    switch_unchecked="#d3d3d3",
    scroll_handle="#c3c3c3",
    combo="#e0e0e0",
    list_bg="#e1e1e1",
    nav_bg="#ededed",
    tooltip="#e0e0e0",
    auto_sync="#d3d3d3",
    auto_sync_text="#555555",
    label="#1f1f1f",
    badge_bg="#e0e0e0",
    badge_text="#1f1f1f",
    badge_border="#a3a3a3",
    log_bg="#ffffff",
    log_border="#c3c3c3",
    segment_container="#dcdcdc",
    segment_button="#ededed",
    segment_border="#a3a3a3",
    segment_selected="#a0a0a0",
    segment_selected_text="#000000",
    row_bg="#f0f0f0",
    row_alt="#e5e5e5",
    row_border="#dcdcdc",
    description="#666",
    action_bg="#e0e0e0",
    action_button="#f5f5f0",
    action_border="#b0b0b0",
    action_text="#1f1f1f",
    delete_text="#cc0000",
    profile_help="#666",
)

_TEMPLATE = """
QWidget {{ background-color: @window@; color: @text@; }}
QPushButton {{ background-color: @button@; border: 1px solid @border@; border-radius: 5px; padding: 3px 8px; font-size: 14px; }}
QPushButton:hover {{ background-color: @hover@; border: 1px solid @hover_border@; }}
QPushButton#primary {{ background-color: #721c24; border: 1px solid #f5c6cb; color: #f8d7da; font-weight: bold; }}
QPushButton:pressed {{ background-color: @border@; }}
QGroupBox {{ font-weight: bold; font-size: 15px; border: 1px solid @border@; margin-top: 20px; padding-top: 20px; }}
QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 10px; }}
QTextEdit {{ background-color: @editor@; color: @text@; border: 1px solid @border@; border-radius: 5px; padding: 8px; }}
QLineEdit {{ background-color: @editor@; color: @text@; border: 1px solid @border@; border-radius: 5px; padding: 3px; }}
QTabBar::tab {{ background-color: @button@; color: @text@; padding: 5px 15px; margin: 2px; border-top-left-radius: 5px; border-top-right-radius: 5px; min-width: 80px; }}
QTabBar::tab:selected {{ background-color: @selected@; border: 1px solid @hover_border@; border-bottom: none; border-top-left-radius: 5px; border-top-right-radius: 5px; }}
QTabBar::tab:hover {{ background-color: @hover@; border: 1px solid @hover_border@; }}
QTabBar::tab:!selected {{ margin-top: 3px; }}
QCheckBox {{ color: @text@; spacing: 8px; }}
QCheckBox:checked {{ color: @checkbox_checked@; font-weight: bold; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid @checkbox_border@; background-color: @checkbox_bg@; border-radius: 3px; }}
QCheckBox::indicator:hover {{ border: 1px solid @checkbox_hover_border@; }}
QCheckBox::indicator:checked {{ background-color: @checkbox_checked_bg@; border: 1px solid @accent@; }}
QCheckBox#switch::indicator {{ width: 36px; height: 18px; border-radius: 9px; border: 1px solid @switch_border@; background-color: @checkbox_bg@; }}
QCheckBox#switch::indicator:checked {{ background-color: @checkbox_checked_bg@; border: 1px solid @accent@; }}
QCheckBox#switch::indicator:unchecked {{ background-color: @switch_unchecked@; }}
QCheckBox:disabled {{ color: gray; }}
QCheckBox::indicator:disabled {{ background-color: #555; border: 1px solid #444; }}
QScrollBar:vertical {{ background-color: @button@; width: 16px; margin: 16px 0 16px 0; border: 1px solid @border@; }}
QScrollBar::handle:vertical {{ background-color: @scroll_handle@; min-height: 20px; border-radius: 4px; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ background-color: @button@; height: 16px; subcontrol-origin: margin; border: 1px solid @border@; }}
QScrollBar::add-line:vertical:hover, QScrollBar::sub-line:vertical:hover {{ background-color: @scroll_handle@; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: none; }}
QComboBox {{ background-color: @combo@; color: @text@; border: 1px solid @border@; border-radius: 5px; padding: 3px; }}
QComboBox QAbstractItemView {{ background-color: @combo@; color: @text@; border: 1px solid @border@; selection-background-color: @selected@; }}
QListWidget {{ background-color: @list_bg@; color: @text@; border: 1px solid @border@; }}
QListWidget::item:selected {{ background-color: @selected@; }}
QListWidget#nav-list {{ border: none; padding: 0px; background-color: @nav_bg@; border-right: 1px solid @border@; outline: none; }}
QListWidget#nav-list::item {{ height: 48px; padding-left: 15px; border-left: 4px solid transparent; border-bottom: 1px solid @row_border@; }}
QListWidget#nav-list::item:selected {{ background-color: @selected@; color: @checkbox_checked@; border-left: 4px solid @accent@; }}
QToolTip {{ background-color: @tooltip@; color: @text@; border: 1px solid @border@; padding: 3px; border-radius: 5px; }}
QLabel[greaterCountLabel="true"] {{ color: gray; font-style: italic; }}
QSpinBox[autoSyncSpin="true"] {{ background-color: @auto_sync@; color: @auto_sync_text@; }}
QLabel[affixHeaderLabel="true"] {{ color: @label@; }}
QCheckBox[greaterCheckbox="true"] {{ background-color: transparent; }}
QPushButton[hotkeyButton="true"] {{ text-align: left; padding-left: 5px; }}
QLabel#key-badge {{ background-color: @badge_bg@; color: @badge_text@; border: 1px solid @badge_border@; border-radius: 4px; padding: 2px 6px; font-family: 'Consolas', 'Monospace'; }}
QPlainTextEdit#log-viewer, QTextEdit#log-viewer {{ background-color: @log_bg@; color: @text@; border: 1px solid @log_border@; }}
QWidget#segmented-container {{ background-color: @segment_container@; border: 1px solid @border@; border-radius: 6px; }}
QPushButton#segment-btn {{ background-color: @segment_button@; border: 1px solid @segment_border@; border-radius: 4px; padding: 4px 12px; font-size: 13px; font-weight: normal; }}
QPushButton#segment-btn:checked {{ background-color: @segment_selected@; border: 1px solid @accent@; color: @segment_selected_text@; font-weight: bold; }}
QPushButton#row-action-btn, QPushButton#delete-profile-btn {{ background-color: transparent; border: none; font-weight: normal; padding: 3px 8px; font-size: 13px; }}
QPushButton#row-action-btn:hover, QPushButton#delete-profile-btn:hover {{ background-color: @hover@; border-radius: 4px; }}
QPushButton#delete-profile-btn {{ color: @delete_text@; }}
QWidget#profile-row {{ background-color: @row_bg@; border-bottom: 1px solid @row_border@; }}
QWidget#profile-row[alt="true"] {{ background-color: @row_alt@; }}
QLabel#description-label {{ color: @description@; font-size: 11px; }}
QLabel#setting-title {{ font-weight: bold; font-size: 13px; }}
QWidget#action-bar {{ background-color: @action_bg@; border-top: 1px solid @border@; }}
QWidget#action-bar QPushButton {{ background-color: @action_button@; border: 1px solid @action_border@; color: @action_text@; }}
QWidget#action-bar QPushButton:hover {{ border: 1px solid @accent@; }}
QLabel#profile-help {{ color: @profile_help@; font-size: 11px; font-style: italic; border-left: 2px solid @accent@; padding-left: 8px; margin-bottom: 5px; }}
QFrame#drop-indicator {{ background-color: @accent@; }}
"""


def _render(palette: _Palette, *, dark: bool) -> str:
    stylesheet = _TEMPLATE.replace("{{", "{").replace("}}", "}")
    for field in palette.__dataclass_fields__:
        stylesheet = stylesheet.replace(f"@{field}@", getattr(palette, field))
    if dark:
        stylesheet = (
            "QPushButton#secondary { background-color: transparent; border: 1px solid #3c3c3c; }\n" + stylesheet
        )
    return stylesheet.replace("@accent@", "{accent}")


DARK_THEME_TEMPLATE = _render(_DARK, dark=True)
LIGHT_THEME_TEMPLATE = _render(_LIGHT, dark=False)
