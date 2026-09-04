import logging
from contextlib import suppress
from typing import TYPE_CHECKING, cast

from src.paragon.data import _save_overlay_settings
from src.paragon.overlay import state as overlay_state
from src.paragon.overlay.contracts import OverlayContract

LOGGER = logging.getLogger(__name__)

if TYPE_CHECKING:
    from src.paragon.overlay.controller import ParagonOverlay


class OverlayLifecycleMixin(OverlayContract):
    def close(self) -> None:
        """Persist state, destroy the window, and clear the global overlay handle."""
        try:
            with suppress(Exception):
                self._config_loader.unregister_change_listener(self._config_listener)
            self._close_build_dropdown()
            self._close_settings_dropdown()
            self._persist_state()
            self.destroy()
        finally:
            if self._on_close:
                self._on_close()
            overlay_state.clear_overlay(cast("ParagonOverlay", self))

    def _persist_state(self) -> None:
        """Write the overlay's current user-facing state back to params.ini."""
        try:
            _save_overlay_settings({
                "cell_size": int(self._cfg.cell_size),
                # Persist both the stable build identity and numeric index so old
                # settings continue to restore sensibly.
                "profile": str(self.builds[self.current_build_idx].get("profile") or "") if self.builds else "",
                "build_name": str(self.builds[self.current_build_idx].get("name") or "") if self.builds else "",
                "build_idx": int(self.current_build_idx),
                "board_idx": int(self.selected_board_idx),
                "grid_x": int(self.grid_x),
                "grid_y": int(self.grid_y),
                "is_collapsed": bool(self._cfg.is_collapsed),
                "cell_size_collapsed": int(self._cfg.cell_size_collapsed),
                "grid_x_collapsed": int(self.grid_x_collapsed),
                "grid_y_collapsed": int(self.grid_y_collapsed),
                "grid_locked": bool(self._cfg.grid_locked),
                "gold_frames": bool(getattr(self._cfg, "gold_frames", False)),
            })
        except Exception:
            LOGGER.debug("Failed to persist overlay state", exc_info=True)
