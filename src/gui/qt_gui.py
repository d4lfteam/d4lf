import logging
import os
import sys
import threading

from PyQt6.QtCore import QObject, QPoint, QRegularExpression, QRunnable, QSettings, QSize, QThreadPool, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QColor, QIcon, QRegularExpressionValidator
from PyQt6.QtWidgets import (
    QApplication,
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
from src.gui import config_tab
from src.gui.importer.d4builds import import_d4builds
from src.gui.importer.diablo_trade import import_diablo_trade
from src.gui.importer.maxroll import import_maxroll
from src.gui.importer.mobalytics import import_mobalytics
from src.gui.open_user_config_button import OpenUserConfigButton

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
        self._diablo_trade_tab()
        self.tab_widget.addTab(config_tab.ConfigTab(), config_tab.CONFIG_TABNAME)

        LOGGER.root.addHandler(self.maxroll_log_handler)
        self.tab_widget.currentChanged.connect(self._handle_tab_changed)
        self._toggle_dark_mode()

    def closeEvent(self, e):
        # Write window size, position, and maximized status to config
        if not self.isMaximized():  # Don't want to save the maximized positioning
            self.settings.setValue("size", self.size())
            self.settings.setValue("pos", self.pos())
        self.settings.setValue("maximized", self.isMaximized())

        e.accept()

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
            worker = _Worker(name="diablo.trade", fn=import_diablo_trade, url=input_box.text(), max_listings=int(input_box2.text()))
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
            f"It will then create a file based on the listings in: {IniConfigLoader().user_dir / "profiles"}\n\n"
            "NOTE: You must have Chrome installed on your computer to use this feature."
        )
        instructions_text.setReadOnly(True)
        font_metrics = instructions_text.fontMetrics()
        text_height = font_metrics.height() * (instructions_text.document().lineCount() + 2)
        instructions_text.setFixedHeight(text_height)
        layout.addWidget(instructions_text)

        tab_diablo_trade.setLayout(layout)

    def _handle_tab_changed(self, index):
        if self.tab_widget.tabText(index) == MAXROLL_D4B_MOBALYTICS_TABNAME:
            LOGGER.root.addHandler(self.maxroll_log_handler)
            LOGGER.root.removeHandler(self.diablo_trade_log_handler)
        elif self.tab_widget.tabText(index) == D4TRADE_TABNAME:
            LOGGER.root.addHandler(self.diablo_trade_log_handler)
            LOGGER.root.removeHandler(self.maxroll_log_handler)

    def _maxroll_or_d4builds_tab(self):
        tab_maxroll = QWidget(self)
        self.tab_widget.addTab(tab_maxroll, MAXROLL_D4B_MOBALYTICS_TABNAME)

        layout = QVBoxLayout(tab_maxroll)

        def handle_text_changed(text):
            generate_button.setEnabled(bool(text.strip()))

        hbox = QHBoxLayout()
        url_label = QLabel("url")
        hbox.addWidget(url_label)
        input_box = QLineEdit()
        input_box.textChanged.connect(handle_text_changed)
        hbox.addWidget(input_box)
        layout.addLayout(hbox)

        def generate_button_click():
            url = input_box.text().strip()
            if "maxroll" in url:
                worker = _Worker(name="maxroll", fn=import_maxroll, url=url)
            elif "d4builds" in url:
                worker = _Worker(name="d4builds", fn=import_d4builds, url=url)
            else:
                worker = _Worker(name="mobalytics", fn=import_mobalytics, url=url)
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
            f"It will create a file based on the label of the build in the planer in: {IniConfigLoader().user_dir / "profiles"}\n\n"
            "For d4builds you need to specify your browser in the params.ini file"
        )
        instructions_text.setReadOnly(True)
        font_metrics = instructions_text.fontMetrics()
        text_height = font_metrics.height() * (instructions_text.document().lineCount() + 2)
        instructions_text.setFixedHeight(text_height)
        layout.addWidget(instructions_text)

        tab_maxroll.setLayout(layout)

    def _toggle_dark_mode(self):
        if QApplication.instance().styleSheet():
            QApplication.instance().setStyleSheet("")
        else:
            QApplication.instance().setStyleSheet("""
                QWidget {
                    background-color: #121212;
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
                QPushButton:pressed {
                    background-color: #3c3c3c;
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
                QToolTip {
                    background-color: #1f1f1f;
                    color: #e0e0e0;
                    border: 1px solid #3c3c3c;
                    padding: 3px;
                    border-radius: 5px;
                }
            """)


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
