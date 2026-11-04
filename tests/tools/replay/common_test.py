import numpy as np
import pytest

from src.tools.replay.common import (
    ReplayConfigurationError,
    font_scale,
    parse_resolution,
    run_replay_main,
    save_replay_output,
)


def test_parse_resolution_and_font_scale() -> None:
    assert parse_resolution("1920x1080") == (1920, 1080)
    small = font_scale(np.zeros((400, 800, 3), dtype=np.uint8))
    large = font_scale(np.zeros((800, 1600, 3), dtype=np.uint8))

    assert large > small


def test_save_replay_output_writes_and_shows_blocking_window(tmp_path, monkeypatch) -> None:
    calls = []
    monkeypatch.setattr("src.tools.replay.common.cv2.imshow", lambda *args: calls.append(("show", args[0])))
    monkeypatch.setattr("src.tools.replay.common.cv2.waitKey", lambda *_args: calls.append(("wait", None)))
    monkeypatch.setattr("src.tools.replay.common.cv2.destroyWindow", lambda *args: calls.append(("destroy", args[0])))
    path = tmp_path / "out.png"

    save_replay_output(path, np.zeros((4, 4, 3), dtype=np.uint8), window_name="title", display=True)

    assert path.is_file()
    assert calls == [("show", "title"), ("wait", None), ("destroy", "title")]


def test_save_replay_output_skips_window_without_display(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("src.tools.replay.common.cv2.imshow", lambda *_args: pytest.fail("window shown"))

    save_replay_output(tmp_path / "out.png", np.zeros((4, 4, 3), dtype=np.uint8), window_name="title", display=False)

    assert (tmp_path / "out.png").is_file()


def _raise_configuration_error() -> bool:
    message = "bad"
    raise ReplayConfigurationError(message)


@pytest.mark.parametrize(
    ("replay", "expected"), [(lambda: True, 0), (lambda: False, 1), (_raise_configuration_error, 2)]
)
def test_run_replay_main_maps_outcome_to_exit_status(monkeypatch, replay, expected) -> None:
    monkeypatch.setattr("src.tools.replay.common.setup", lambda **_kwargs: None)

    assert run_replay_main(replay) == expected
