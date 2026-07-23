import cv2
import numpy as np

from src.perception.screenshot import screenshot


def test_screenshot_writes_the_supplied_image_without_a_timestamp(tmp_path) -> None:
    image = np.zeros((3, 4, 3), dtype=np.uint8)

    screenshot(name="tooltip", path=str(tmp_path), img=image, timestamp=False)

    saved = cv2.imread(str(tmp_path / "tooltip.png"))
    assert saved is not None
    assert saved.shape == image.shape
