from typing import TYPE_CHECKING

import src.settings.coordinates as data

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
