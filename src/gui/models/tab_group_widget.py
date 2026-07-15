from PyQt6.QtWidgets import QDialog, QPushButton, QTabWidget, QToolBar, QVBoxLayout, QWidget

from src.gui.models.dialog import DeleteItem


class TabGroupWidget[ModelT](QWidget):
    """Shared base for profile editor tabs that show one sub-editor per model in a closable QTabWidget.

    Subclasses must implement create_editor(), tab_label(), and create_model(), and may override the
    other hooks below to customize toolbar buttons, labels, and post-change behavior (e.g. renaming
    tabs).
    """

    def __init__(self, models: list[ModelT], parent=None):
        super().__init__(parent)
        self.models = models
        self.loaded = False

    def load(self):
        if not self.loaded:
            self.setup_ui()
            self.loaded = True

    def setup_ui(self):
        self.prepare_models()

        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 20, 0, 20)

        self.tab_widget = QTabWidget(self)
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.tabCloseRequested.connect(self.close_tab)

        for index, model in enumerate(self.models):
            self.tab_widget.addTab(self.create_editor(model), self.tab_label(model, index))

        corner = self.corner_widget()
        if corner is not None:
            self.tab_widget.setCornerWidget(corner)

        self.toolbar = QToolBar(self.toolbar_name(), self)
        self.toolbar.setMinimumHeight(50)
        self.toolbar.setContentsMargins(10, 10, 10, 10)
        self.toolbar.setMovable(False)
        for button in self.toolbar_buttons():
            self.toolbar.addWidget(button)

        self.main_layout.addWidget(self.toolbar)
        self.main_layout.addWidget(self.tab_widget)

    # --- Hooks for subclasses ---

    def prepare_models(self):
        """Called once, before tabs are built, to normalize/validate self.models in place."""

    def toolbar_name(self) -> str:
        return "TabGroupToolbar"

    def corner_widget(self) -> QWidget | None:
        return None

    def create_editor(self, model: ModelT) -> QWidget:
        msg = "Subclasses must implement create_editor()."
        raise NotImplementedError(msg)

    def tab_label(self, model: ModelT, index: int) -> str:
        msg = "Subclasses must implement tab_label()."
        raise NotImplementedError(msg)

    def create_model(self) -> ModelT | None:
        """Return a new model to add, or None if the user cancelled the creation flow."""
        msg = "Subclasses must implement create_model()."
        raise NotImplementedError(msg)

    def add_button_text(self) -> str:
        return "Add"

    def remove_button_text(self) -> str:
        return "Remove"

    def toolbar_buttons(self) -> list[QPushButton]:
        add_button = QPushButton(self.add_button_text())
        add_button.clicked.connect(self.add_item)
        remove_button = QPushButton(self.remove_button_text())
        remove_button.clicked.connect(self.remove_item)
        return [add_button, remove_button]

    def after_models_changed(self):
        """Called after a tab/model is added or removed. No-op by default."""

    # --- Shared behavior ---

    def add_item(self):
        model = self.create_model()
        if model is None:
            return
        self.models.append(model)
        index = self.tab_widget.count()
        self.tab_widget.addTab(self.create_editor(model), self.tab_label(model, index))
        self.after_models_changed()

    def close_tab(self, index: int):
        self.tab_widget.removeTab(index)
        self.models.pop(index)
        self.after_models_changed()

    def remove_item(self):
        dialog = DeleteItem([self.tab_widget.tabText(i) for i in range(self.tab_widget.count())], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            names_to_delete = set(dialog.get_value())
            indices = [i for i in range(self.tab_widget.count()) if self.tab_widget.tabText(i) in names_to_delete]
            for index in reversed(indices):
                self.tab_widget.removeTab(index)
                self.models.pop(index)
            self.after_models_changed()
