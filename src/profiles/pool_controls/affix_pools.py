from typing import TYPE_CHECKING

from PyQt6.QtCore import QTimer, pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout

from src.profiles import AffixFilterCountModel, AffixFilterModel
from src.profiles.editor import SelectToDeleteDialog
from src.profiles.editor.container import Container
from src.profiles.pool_controls.affix_widget import AffixWidget
from src.profiles.pool_controls.pool_widget import AffixPoolWidget

if TYPE_CHECKING:
    from collections.abc import Iterator


class AffixPoolSection(Container):
    """Collapsible list of "Count N" affix pools backed by ``pools``; pool widgets load on first expansion."""

    pools_removed = pyqtSignal()

    def __init__(
        self, title: str, pools: list[AffixFilterCountModel], default_affix: str, inherent: bool = False
    ) -> None:
        super().__init__(title)
        self._pools = pools
        self._default_affix = default_affix
        self._inherent = inherent
        self._layout = QVBoxLayout(self.content_widget)
        self.first_expansion.connect(self._load_pools)

    def add_pool(self) -> None:
        self.expand()
        pool = AffixFilterCountModel(
            count=[AffixFilterModel(name=self._default_affix, value=None)], min_count=1, max_count=3
        )
        self._pools.append(pool)
        self._add_item(pool)

    def remove_pools(self) -> None:
        """Ask which pools to delete and remove them from the view and the model."""
        self.expand()
        kind = "Inherent Pool" if self._inherent else "Affix Pool"
        containers = self._pool_containers()
        dialog = SelectToDeleteDialog(
            f"Delete {kind}", kind, "Select items to delete:", [(c.header.name, i) for i, c in enumerate(containers)]
        )
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        for index in reversed(dialog.get_value()):
            containers[index].setParent(None)
            self._pools.pop(index)
        for index, container in enumerate(self._pool_containers()):
            container.header.set_name(f"Count {index}")
        self.pools_removed.emit()

    def convert_to_min_percent(self, percent: int) -> None:
        for affix_widget in self._affix_widgets():
            affix_widget.set_min_percent(percent, convert_mode=True)

    def _load_pools(self) -> None:
        for pool in self._pools:
            self._add_item(pool)

    def _add_item(self, pool: AffixFilterCountModel) -> None:
        container = Container(f"Count {self._layout.count()}", color_background=True)
        QVBoxLayout(container.content_widget).addWidget(AffixPoolWidget(pool, self))
        self._layout.addWidget(container)
        QTimer.singleShot(50, container.expand)

    def _pool_containers(self) -> list[Container]:
        items = (self._layout.itemAt(i) for i in range(self._layout.count()))
        return [widget for item in items if item is not None and isinstance(widget := item.widget(), Container)]

    def _affix_widgets(self) -> Iterator[AffixWidget]:
        was_visible = self.content_widget.isVisible()
        self.expand()
        if not was_visible:
            self.collapse()
        for container in self._pool_containers():
            pool_layout = container.content_widget.layout()
            pool_item = pool_layout.itemAt(0) if pool_layout is not None else None
            pool_widget = pool_item.widget() if pool_item is not None else None
            if not isinstance(pool_widget, AffixPoolWidget):
                continue
            for row in range(pool_widget.affix_list.count()):
                affix_widget = pool_widget.affix_list.itemWidget(pool_widget.affix_list.item(row))
                if isinstance(affix_widget, AffixWidget):
                    yield affix_widget
