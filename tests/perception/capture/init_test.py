from src.perception.capture import Cam, WindowROI


def test_capture_interface_exposes_camera_types() -> None:
    assert Cam is not None
    assert WindowROI is not None
