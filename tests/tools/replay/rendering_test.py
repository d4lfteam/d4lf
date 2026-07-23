import numpy as np

from src.perception import DiagnosticLocatorResult, LocatorDiagnostics, LocatorResult
from src.tools.replay.rendering import _annotate


def test_annotation_preserves_image_shape() -> None:
    image = np.zeros((20, 20, 3), dtype=np.uint8)
    result = DiagnosticLocatorResult(LocatorResult([], reliable=False), LocatorDiagnostics())
    assert _annotate(image, result, 10).shape == image.shape
