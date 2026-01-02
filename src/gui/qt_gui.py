import logging
import os
import sys
import threading

from PyQt6.QtCore import (
    QObject,
    QPoint,
    QRegularExpression,
    QRunnable,
    QSettings,
    QSize,
    QThreadPool,
    pyqtSignal,
    pyqtSlot,
)
from PyQt6.QtGui import QColor, QIcon, QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QApplication,
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QTabBar,
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

import src.logger
from src import __version__
from src.config import BASE_DIR
from src.config.helper import singleton
from src.config.loader import IniConfigLoader
from src.gui import config_tab, profile_tab
from src.gui.importer.d4builds import import_d4builds
from src.gui.importer.diablo_trade import import_diablo_trade
from src.gui.importer.importer_config import ImportConfig
from src.gui.importer.maxroll import import_maxroll
from src.gui.importer.mobalytics import import_mobalytics
from src.gui.open_user_config_button import OpenUserConfigButton
from src.gui.themes import DARK_THEME, LIGHT_THEME

LOGGER = logging.getLogger(__name__)

THREADPOOL = QThreadPool()
D4TRADE_TABNAME = "diablo.trade"
MAXROLL_D4B_MOBALYTICS_TABNAME = "maxroll / d4builds / mobalytics"


def start_gui():
    os.environ["QT_LOGGING_RULES"] = "qt.qpa.window=false"
    app = QApplication([])

    app.setWindowIcon(QIcon(str(BASE_DIR / "assets/logo.png")))
    window = Gui()
    window.show()
    sys.exit(app.exec())


@singleton
class Gui(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings = QSettings("d4lf", "gui")

        self.setWindowTitle(f"D4LF v{__version__}")

        self.resize(self.settings.value("size", QSize(650, 800)))
        self.move(self.settings.value("pos", QPoint(0, 0)))

        if self.settings.value("maximized", "true") == "true":
            self.showMaximized()

        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabBar(_CustomTabBar())
        self.setCentralWidget(self.tab_widget)

        self._maxroll_or_d4builds_tab()
        # diablo trade changed search to be login only, so this no longer works
        # self._diablo_trade_tab()
        self.config_tab = config_tab.ConfigTab(theme_changed_callback=self._apply_theme)
        self.tab_widget.addTab(self.config_tab, config_tab.CONFIG_TABNAME)
        self.profile_tab_widget = profile_tab.ProfileTab()
        self.tab_widget.addTab(self.profile_tab_widget, profile_tab.PROFILE_TABNAME)
        LOGGER.root.addHandler(self.maxroll_log_handler)
        self.tab_widget.currentChanged.connect(self._handle_tab_changed)

        # Apply theme on startup
        self._apply_theme()

    def closeEvent(self, e):
        # Write window size, position, and maximized status to config
        if not self.isMaximized():  # Don't want to save the maximized positioning
            self.settings.setValue("size", self.size())
            self.settings.setValue("pos", self.pos())
        self.settings.setValue("maximized", self.isMaximized())
        if self.profile_tab_widget.check_close_save():
            e.accept()
        else:
            e.ignore()

    def _diablo_trade_tab(self):
        tab_diablo_trade = QWidget(self)
        self.tab_widget.addTab(tab_diablo_trade, "diablo.trade")

        layout = QVBoxLayout(tab_diablo_trade)

        def handle_text_changed(text):
            generate_button.setEnabled(bool(input_box.text().strip()) and bool(input_box2.text().strip()))

        hbox = QHBoxLayout()
        url_label = QLabel("url")
        hbox.addWidget(url_label)
        input_box = QLineEdit()
        input_box.textChanged.connect(handle_text_changed)
        hbox.addWidget(input_box)
        maxsize_label = QLabel("max listings")
        hbox.addWidget(maxsize_label)
        input_box2 = QLineEdit()
        input_box2.setText("2000")
        metrics = input_box2.fontMetrics()
        width = metrics.horizontalAdvance("0") * 10
        input_box2.setFixedWidth(width)
        input_box2.textChanged.connect(handle_text_changed)
        reg_ex = QRegularExpression("\\d*")
        input_validator = QRegularExpressionValidator(reg_ex, input_box2)
        input_box2.setValidator(input_validator)
        hbox.addWidget(input_box2)
        layout.addLayout(hbox)

        def generate_button_click():
            worker = _Worker(
                name="diablo.trade", fn=import_diablo_trade, url=input_box.text(), max_listings=int(input_box2.text())
            )
            worker.signals.finished.connect(on_worker_finished)
            generate_button.setEnabled(False)
            generate_button.setText("Generating...")
            self.tab_widget.tabBar().enableTabSwitching(False)
            THREADPOOL.start(worker)

        def on_worker_finished():
            generate_button.setEnabled(True)
            generate_button.setText("Generate")
            self.tab_widget.tabBar().enableTabSwitching(True)

        hbox2 = QHBoxLayout()
        generate_button = QPushButton("Generate")
        generate_button.setEnabled(False)
        generate_button.clicked.connect(generate_button_click)
        hbox2.addWidget(generate_button)
        profiles_button = OpenUserConfigButton()
        hbox2.addWidget(profiles_button)
        layout.addLayout(hbox2)

        log_label = QLabel("Log")
        layout.addWidget(log_label)

        log_output = QTextEdit()
        log_output.setReadOnly(True)
        layout.addWidget(log_output)

        self.diablo_trade_log_handler = _GuiLogHandler(log_output)

        instructions_label = QLabel("Instructions")
        layout.addWidget(instructions_label)

        instructions_text = QTextEdit()
        instructions_text.setText(
            "You can link any valid filter created by diablo.trade.\n\n"
            "https://diablo.trade/listings/items?exactPrice=true&itemType=equipment&price=50000000,999999999999&rarity=legendary&sold=true&sort=newest\n\n"
            "Please note that only legendary items are supported at the moment. The listing must also have an exact price.\n"
            "You can create such a filter by using the one above as a base and then add your custom data to it.\n"
            f"It will then create a file based on the listings in: {IniConfigLoader().user_dir / 'profiles'}"
        )
        instructions_text.setReadOnly(True)
        font_metrics = instructions_text.fontMetrics()
        text_height = font_metrics.height() * (instructions_text.document().lineCount() + 2)
        instructions_text.setFixedHeight(text_height)
        layout.addWidget(instructions_text)

        tab_diablo_trade.setLayout(layout)

    def _handle_tab_changed(self, index):
        # Apply theme whenever tab changes (in case it was changed in config)
        self._apply_theme()

        if self.tab_widget.tabText(index) == MAXROLL_D4B_MOBALYTICS_TABNAME:
            LOGGER.root.addHandler(self.maxroll_log_handler)
        elif self.tab_widget.tabText(index) == D4TRADE_TABNAME:
            LOGGER.root.removeHandler(self.maxroll_log_handler)
        elif self.tab_widget.tabText(index) == config_tab.CONFIG_TABNAME:
        elif self.tab_widget.tabText(index) == profile_tab.PROFILE_TABNAME:
            self.profile_tab_widget.show_tab()

    def _maxroll_or_d4builds_tab(self):
        tab_maxroll = QWidget(self)
        self.tab_widget.addTab(tab_maxroll, MAXROLL_D4B_MOBALYTICS_TABNAME)

        layout = QVBoxLayout(tab_maxroll)

        def handle_text_changed(text):
            generate_button.setEnabled(bool(text.strip()))

        def generate_checkbox(name, settings_value, desc) -> QCheckBox:
            def save_setting_change(settings_value, value):
                self.settings.setValue(settings_value, value)

            checkbox = QCheckBox(name)
            checkbox.setChecked(self.settings.value(settings_value, "true") == "true")
            checkbox.setToolTip(desc)
            checkbox.stateChanged.connect(lambda: save_setting_change(settings_value, checkbox.isChecked()))
            return checkbox

        hbox = QHBoxLayout()
        url_label = QLabel("url")
        hbox.addWidget(url_label)
        input_box = QLineEdit()
        input_box.textChanged.connect(handle_text_changed)
        hbox.addWidget(input_box)
        layout.addLayout(hbox)

        filename_hbox = QHBoxLayout()
        filename_label = QLabel("Custom file name")
        filename_hbox.addWidget(filename_label)
        filename_input_box = QLineEdit()
        filename_input_box.setPlaceholderText("Leave blank for default filename")
        filename_hbox.addWidget(filename_input_box)
        layout.addLayout(filename_hbox)

        checkbox_hbox = QHBoxLayout()
        import_uniques_checkbox = generate_checkbox(
            "Import Uniques",
            "import_uniques",
            "Should uniques be included in the profile if they exist on the build page?",
        )
        import_aspect_upgrades_checkbox = generate_checkbox(
            "Import Aspect Upgrades",
            "import_aspect_upgrades",
            "If legendary aspects are in the build, do you want an aspect upgrades section generated for them?",
        )
        add_to_profiles_checkbox = generate_checkbox(
            "Auto-add To Profiles",
            "import_add_to_profiles",
            "After import, should the imported file be automatically added to your active profiles?",
        )
        checkbox_hbox.addWidget(import_uniques_checkbox)
        checkbox_hbox.addWidget(import_aspect_upgrades_checkbox)
        checkbox_hbox.addWidget(add_to_profiles_checkbox)
        layout.addLayout(checkbox_hbox)

        def generate_button_click():
            url = input_box.text().strip()
            custom_filename = filename_input_box.text()
            if custom_filename:
                custom_filename = custom_filename.split(".")[0]
                custom_filename = custom_filename.strip()

            importer_config = ImportConfig(
                url,
                import_uniques_checkbox.isChecked(),
                import_aspect_upgrades_checkbox.isChecked(),
                add_to_profiles_checkbox.isChecked(),
                custom_filename,
            )

            if "maxroll" in url:
                worker = _Worker(name="maxroll", fn=import_maxroll, config=importer_config)
            elif "d4builds" in url:
                worker = _Worker(name="d4builds", fn=import_d4builds, config=importer_config)
            else:
                worker = _Worker(name="mobalytics", fn=import_mobalytics, config=importer_config)
            worker.signals.finished.connect(on_worker_finished)
            generate_button.setEnabled(False)
            generate_button.setText("Generating...")
            self.tab_widget.tabBar().enableTabSwitching(False)
            THREADPOOL.start(worker)

        def on_worker_finished():
            generate_button.setEnabled(True)
            generate_button.setText("Generate")
            self.tab_widget.tabBar().enableTabSwitching(True)
            filename_input_box.clear()

        hbox2 = QHBoxLayout()
        generate_button = QPushButton("Generate")
        generate_button.setEnabled(False)
        generate_button.clicked.connect(generate_button_click)
        hbox2.addWidget(generate_button)
        profiles_button = OpenUserConfigButton()
        hbox2.addWidget(profiles_button)
        layout.addLayout(hbox2)

        log_label = QLabel("Log")
        layout.addWidget(log_label)

        log_output = QTextEdit()
        log_output.setReadOnly(True)
        layout.addWidget(log_output)

        self.maxroll_log_handler = _GuiLogHandler(log_output)

        instructions_label = QLabel("Instructions")
        layout.addWidget(instructions_label)

        instructions_text = QTextEdit()
        instructions_text.setText(
            "You can link either the build guide or a direct link to the specific planner.\n\n"
            "https://maxroll.gg/d4/build-guides/tornado-druid-guide\n"
            "or\n"
            "https://maxroll.gg/d4/planner/cm6pf0xa#5\n"
            "or\n"
            "https://d4builds.gg/builds/ef414fbd-81cd-49d1-9c8d-4938b278e2ee\n"
            "or\n"
            "https://mobalytics.gg/diablo-4/builds/barbarian/bash\n\n"
            f"It will create a file based on the label of the build in the planner in: {IniConfigLoader().user_dir / 'profiles'}\n\n"
            "For d4builds you need to specify your browser in the config tab"
        )
        instructions_text.setReadOnly(True)
        font_metrics = instructions_text.fontMetrics()
        text_height = font_metrics.height() * (instructions_text.document().lineCount() + 2)
        instructions_text.setFixedHeight(text_height)
        layout.addWidget(instructions_text)

        tab_maxroll.setLayout(layout)

    def _apply_theme(self):
        """Apply the theme from config settings"""
        # Force reload the config to get latest theme value
        config = IniConfigLoader()
        config.load()  # Reload from disk

        theme = config.general.theme.value
        if theme == "dark":
            self.setStyleSheet(DARK_THEME)
        else:
            self.setStyleSheet(LIGHT_THEME)


class _CustomTabBar(QTabBar):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.tab_switching_enabled = True
        self.currentChanged.connect(self.updateTabColors)

    def mousePressEvent(self, event):
        if self.tab_switching_enabled:
            super().mousePressEvent(event)

    def keyPressEvent(self, event):
        if self.tab_switching_enabled:
            super().keyPressEvent(event)

    def enableTabSwitching(self, enable):
        self.tab_switching_enabled = enable
        self.updateTabColors()

    def updateTabColors(self):
        for index in range(self.count()):
            color = "grey" if not self.tab_switching_enabled and index != self.currentIndex() else "black"
            self.setTabTextColor(index, QColor(color))


class _GuiLogHandler(logging.Handler):
    def __init__(self, text_widget: QTextEdit):
        super().__init__()
        self.text_widget = text_widget

    def emit(self, record):
        log_entry = self.format(record)
        self.text_widget.append(log_entry)
        # Ensures log is scrolled to the bottom as it writes
        self.text_widget.ensureCursorVisible()


class _Worker(QRunnable):
    def __init__(self, name, fn, *args, **kwargs):
        super().__init__()
        self.name = name
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = _WorkerSignals()

    @pyqtSlot()
    def run(self):
        threading.current_thread().name = self.name
        self.fn(*self.args, **self.kwargs)
        self.signals.finished.emit()


class _WorkerSignals(QObject):
    finished = pyqtSignal()


if __name__ == "__main__":
    src.logger.setup()
    start_gui()
