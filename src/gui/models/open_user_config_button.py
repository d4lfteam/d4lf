import os

from PyQt6.QtWidgets import QPushButton

from src.config.loader import IniConfigLoader


class OpenUserConfigButton(QPushButton):
    def __init__(self):
        super().__init__("Open Userconfig Directory")
        self.clicked.connect(self._open_userconfig_directory)

    @staticmethod
    def _open_userconfig_directory():
        os.startfile(IniConfigLoader().user_dir)
