import logging
from typing import TYPE_CHECKING

import cv2
import numpy as np
import pytest

if TYPE_CHECKING:
    from pathlib import Path

from src.perception import DescrDetection, TemplateMatch
from src.tools.replay.full_screenshot import ReplayConfig, ReplayConfigurationError, run_replay, validate_replay_config


def make_replay_config(tmp_path: Path, **overrides) -> ReplayConfig:
    image_path = tmp_path / "full_screenshot.png"
    cv2.imwrite(str(image_path), np.zeros((400, 500, 3), dtype=np.uint8))
    values = {"image_path": image_path, "game_resolution": "3840x2160", "item_anchor": (300, 100)}
    values.update(overrides)
    return ReplayConfig(**values)


def _read_output(path: Path) -> np.ndarray:
    output = cv2.imread(str(path))
    if output is None:
        message = f"Missing replay output: {path}"
        raise AssertionError(message)
    return output


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"image_path": "missing.png"}, "does not exist"),
        ({"item_anchor": (300,)}, "pair"),
        ({"item_anchor": (-1, 100)}, "non-negative"),
        ({"game_resolution": "3840"}, "WIDTHxHEIGHT"),
    ],
)
def test_validate_replay_config_rejects_invalid_inputs(tmp_path, overrides, message) -> None:
    with pytest.raises(ReplayConfigurationError, match=message):
        validate_replay_config(make_replay_config(tmp_path, **overrides))


def test_run_replay_saves_crop_and_composes_full_annotation(tmp_path, monkeypatch, caplog) -> None:
    config = make_replay_config(tmp_path)
    top_left_match = TemplateMatch(
        center=(180, 100),
        center_monitor=(180, 100),
        region=[170, 90, 20, 20],
        region_monitor=[170, 90, 20, 20],
        name="item_top_left_legendary",
        score=0.93,
    )
    separator_match = TemplateMatch(
        center=(200, 150),
        center_monitor=(200, 150),
        region=[190, 145, 20, 10],
        region_monitor=[190, 145, 20, 10],
        name="item_seperator_short_legendary",
        score=0.91,
    )
    bottom_match = TemplateMatch(
        center=(200, 350),
        center_monitor=(200, 350),
        region=[190, 345, 20, 10],
        region_monitor=[190, 345, 20, 10],
        name="item_bottom_edge",
        score=0.89,
    )
    detection = DescrDetection(
        found=True,
        cropped_descr=np.zeros((200, 240, 3), dtype=np.uint8),
        crop_roi=[120, 80, 240, 200],
        top_left_match=top_left_match,
        separator_match=separator_match,
        bottom_match=bottom_match,
    )
    monkeypatch.setattr("src.tools.replay.full_screenshot.find_descr_with_diagnostics", lambda *_args: detection)
    with caplog.at_level(logging.INFO, logger="d4lf"):
        result = run_replay(config, display=False)

    assert result.found
    assert result.failure_reason is None
    assert result.crop_path == tmp_path / "full_screenshot_cropped.png"
    assert result.output_path == tmp_path / "full_screenshot_full_template_matches.png"
    crop = cv2.imread(str(result.crop_path))
    np.testing.assert_array_equal(crop, detection.cropped_descr)
    output = _read_output(result.output_path)
    assert tuple(output[90, 170]) == (128, 128, 128)
    assert tuple(output[80, 120]) == (0, 255, 0)
    for expected in (
        "top_left: template=item_top_left_legendary",
        "separator: template=item_seperator_short_legendary",
        "bottom: template=item_bottom_edge",
        "crop: roi=[120, 80, 240, 200]",
        "Full replay detection: found=True",
    ):
        assert expected in caplog.text


def test_run_replay_writes_and_displays_full_failure_annotation(tmp_path, monkeypatch) -> None:
    config = make_replay_config(tmp_path)
    detection = DescrDetection(found=False, failure_reason="missing_top_left_border")
    monkeypatch.setattr("src.tools.replay.full_screenshot.find_descr_with_diagnostics", lambda *_args: detection)
    displayed = []
    monkeypatch.setattr("src.tools.replay.full_screenshot.show_result", displayed.append)

    result = run_replay(config)

    assert not result.found
    assert result.failure_reason == "missing_top_left_border"
    assert len(displayed) == 1
    output = _read_output(result.output_path)
    assert tuple(output[0, 0]) == (0, 0, 255)
