import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PyQt6.QtWidgets import QApplication

from src.desktop.themes import DARK_THEME_TEMPLATE, LIGHT_THEME_TEMPLATE


def test_theme_templates_keep_the_shared_application_selectors() -> None:
    for template in (DARK_THEME_TEMPLATE, LIGHT_THEME_TEMPLATE):
        assert "QWidget" in template
        assert "{{" not in template
        assert "}}" not in template
        assert "QCheckBox::indicator:checked" in template
        assert "QWidget#profile-row" in template
        assert "{accent}" in template


def test_theme_templates_can_be_applied_with_the_runtime_accent() -> None:
    for template in (DARK_THEME_TEMPLATE, LIGHT_THEME_TEMPLATE):
        stylesheet = template.replace("{accent}", "#56B4E9")

        assert "{accent}" not in stylesheet
        assert "#56B4E9" in stylesheet


def test_theme_templates_are_accepted_by_qt(qapp: QApplication) -> None:
    qapp.setStyleSheet(DARK_THEME_TEMPLATE.replace("{accent}", "#56B4E9"))
    qapp.setStyleSheet(LIGHT_THEME_TEMPLATE.replace("{accent}", "#56B4E9"))


@pytest.fixture(scope="module")
def qapp() -> QApplication:
    app = QApplication.instance()
    if isinstance(app, QApplication):
        return app
    return QApplication([])


def test_dark_theme_retains_secondary_button_styling() -> None:
    assert "QPushButton#secondary" in DARK_THEME_TEMPLATE
    assert "QPushButton#secondary" not in LIGHT_THEME_TEMPLATE
