from typing import TYPE_CHECKING

import src.settings.coordinates as data
from src.settings.coordinates import COLORS

if TYPE_CHECKING:
    from pathlib import Path


def test_load_templates_skips_unreadable_images(monkeypatch, tmp_path: Path) -> None:
    template_dir = tmp_path / "assets" / "templates"
    template_dir.mkdir(parents=True)
    broken_image = template_dir / "broken.png"
    broken_image.touch()
    monkeypatch.setattr(data, "BASE_DIR", tmp_path)
    imread_calls: list[str] = []

    def imread_unreadable(path: str, *_args: object, **_kwargs: object) -> None:
        imread_calls.append(path)

    monkeypatch.setattr(data.cv2, "imread", imread_unreadable)
    data.load_templates.cache_clear()

    try:
        assert data.load_templates() == {}
        assert imread_calls == [str(broken_image)]
    finally:
        data.load_templates.cache_clear()


def test_coordinates_expose_reference_colors_and_templates(monkeypatch) -> None:
    template = object()
    monkeypatch.setattr(data, "load_templates", lambda: {"stash": template})
    assert COLORS.material_color.h_s_v_min.tolist() == [86, 110, 190]
    assert data.load_templates() == {"stash": template}
