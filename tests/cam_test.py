import numpy as np
import pytest

from src.cam import Cam


@pytest.fixture
def camera():
    cam = Cam()
    cam.window_offset_set = False
    cam.window_roi = {"top": 0, "left": 0, "width": 0, "height": 0}
    cam.monitor_x_range = None
    cam.monitor_y_range = None
    cam.res_key = ""
    cam.res_p = ""
    cam.last_grab = None
    cam.cached_img = None
    yield cam
    cam.reset_window_position()


def test_grab_discards_frame_captured_before_window_restart(camera, mocker):
    old_frame = np.zeros((1, 1, 4), dtype=np.uint8)
    new_frame = np.full((1, 1, 4), 255, dtype=np.uint8)
    camera.update_window_pos(10, 20, 1000, 800)

    def grab(roi):
        if roi["left"] == 10:
            camera.reset_window_position()
            camera.update_window_pos(100, 200, 1000, 800)
            return old_frame
        return new_frame

    screen_capture = mocker.Mock()
    screen_capture.grab.side_effect = grab
    mss_factory = mocker.patch("src.cam.mss.mss")
    mss_factory.return_value.__enter__.return_value = screen_capture

    image = camera.grab()

    np.testing.assert_array_equal(image, new_frame[:, :, :3])
