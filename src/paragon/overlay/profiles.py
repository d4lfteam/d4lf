from src.paragon import data as _data
from src.paragon.data import _resolve_build_index, load_builds_from_path
from src.paragon.shared import LOGGER, OverlayContract

globals().update({name: getattr(_data, name) for name in _data.__all__})


class OverlayUIMixin(OverlayContract):
    def _reload_profiles(self) -> None:
        """Reload build data from disk and keep the current selection if possible."""
        try:
            if not (new_builds := load_builds_from_path()):
                return
            current_build = self.builds[self.current_build_idx] if self.builds else {}
            self.builds = new_builds
            self.current_build_idx = _resolve_build_index(
                self.builds,
                profile_name=current_build.get("profile"),
                build_name=current_build.get("name"),
                fallback_idx=self.current_build_idx,
            )
            self.boards = self.builds[self.current_build_idx]["boards"] if self.builds else []
            self.selected_board_idx = min(self.selected_board_idx, max(0, len(self.boards) - 1))
            self._refresh_lists()
            self.redraw()
            self._persist_state()
        except Exception:  # ruff:ignore[blind-except] - preserve profile reload fallback
            LOGGER.exception("Failed to reload profiles")
