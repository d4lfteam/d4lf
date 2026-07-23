import numpy as np

from src.settings.types import Template


def test_template_defaults_are_empty_and_optional() -> None:
    template = Template()
    assert not template.name
    assert template.img_bgra is None
    assert template.img_gray is None


def test_template_keeps_image_arrays() -> None:
    image = np.zeros((2, 2, 4), dtype=np.uint8)
    assert Template(name="stash", img_bgra=image).img_bgra is image
