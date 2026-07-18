import numpy as np

from src.perception._matching_core import process_template_refs
from src.settings import Template


def test_process_template_refs_builds_a_template_from_an_image() -> None:
    image = np.full((4, 4, 4), 255, dtype=np.uint8)
    image[0, 0, 3] = 0

    templates = process_template_refs(image)

    assert len(templates) == 1
    assert isinstance(templates[0], Template)
    assert templates[0].alpha_mask is not None
    assert templates[0].alpha_mask[0, 0] == 0
