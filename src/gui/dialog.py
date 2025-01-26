from PyQt6.QtWidgets import QDialog, QVBoxLayout, QLabel, QSpinBox, QPushButton, QHBoxLayout, QGridLayout, QTextBrowser
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidgetItem, QPushButton, QScrollArea, QFileDialog, QVBoxLayout, QWidget, QComboBox, QLineEdit, QLabel, QFormLayout, QHBoxLayout, QMessageBox, QMenuBar, QStatusBar, QSpinBox, QSizePolicy
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QFont, QIcon
import pywinstyles

class MinPowerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Min Power")
        self.setFixedSize(250, 150)
        pywinstyles.apply_style(self, "dark")
        self.layout = QVBoxLayout()

        self.label = QLabel("Min Power:")
        self.layout.addWidget(self.label)

        self.spinBox = QSpinBox()
        self.spinBox.setRange(0, 800)
        self.spinBox.setValue(800)
        self.layout.addWidget(self.spinBox)

        self.buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)
        self.buttonLayout.addWidget(self.okButton)
        self.buttonLayout.addWidget(self.cancelButton)

        self.layout.addLayout(self.buttonLayout)
        self.setLayout(self.layout)

    def get_value(self):
        return self.spinBox.value()

class MinGreaterDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Min Greater Affix")
        self.setFixedSize(250, 150)
        pywinstyles.apply_style(self, "dark")
        self.layout = QVBoxLayout()

        self.label = QLabel("Min Greater Affix:")
        self.layout.addWidget(self.label)

        self.spinBox = QSpinBox()
        self.spinBox.setRange(0, 3)
        self.spinBox.setValue(0)
        self.layout.addWidget(self.spinBox)

        self.buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)
        self.buttonLayout.addWidget(self.okButton)
        self.buttonLayout.addWidget(self.cancelButton)

        self.layout.addLayout(self.buttonLayout)
        self.setLayout(self.layout)

    def get_value(self):
        return self.spinBox.value()

class MinCountDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Set Min Count")
        self.setFixedSize(250, 150)
        pywinstyles.apply_style(self, "dark")
        self.layout = QVBoxLayout()

        self.label = QLabel("Min Count:")
        self.layout.addWidget(self.label)

        self.spinBox = QSpinBox()
        self.spinBox.setRange(0, 3)
        self.spinBox.setValue(0)
        self.layout.addWidget(self.spinBox)

        self.buttonLayout = QHBoxLayout()
        self.okButton = QPushButton("OK")
        self.okButton.clicked.connect(self.accept)
        self.cancelButton = QPushButton("Cancel")
        self.cancelButton.clicked.connect(self.reject)
        self.buttonLayout.addWidget(self.okButton)
        self.buttonLayout.addWidget(self.cancelButton)

        self.layout.addLayout(self.buttonLayout)
        self.setLayout(self.layout)

    def get_value(self):
        return self.spinBox.value()