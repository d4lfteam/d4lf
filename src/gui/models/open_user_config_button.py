import os

from PyQt6.QtWidgets import QPushButton

from src.settings import get_settings


class OpenUserConfigButton(QPushButton):
    def __init__(self):
        super().__init__("Open Userconfig Directory")
        self.clicked.connect(self._open_userconfig_directory)

    @staticmethod
    def _open_userconfig_directory():
        os.startfile(get_settings().user_dir)
