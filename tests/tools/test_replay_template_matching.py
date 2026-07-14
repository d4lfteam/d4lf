import logging
from typing import TYPE_CHECKING

import cv2
import numpy as np
import pytest

from src.template_finder import SearchResult, TemplateMatch
from src.tools.replay_template_matching import (
    REROLLED_BULLET_POINT_TEMPLATES,
    ReplayConfig,
    ReplayConfigurationError,
    run_replay,
    validate_replay_config,
)

if TYPE_CHECKING:
    from pathlib import Path


def make_replay_config(tmp_path: Path, **overrides) -> ReplayConfig:
    image_path = tmp_path / "screen.png"
    cv2.imwrite(str(image_path), np.zeros((200, 300, 3), dtype=np.uint8))
    values = {"image_path": image_path, "templates": REROLLED_BULLET_POINT_TEMPLATES.copy(), "threshold": 0.8}
    values.update(overrides)
    return ReplayConfig(**values)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"image_path": "missing.png"}, "does not exist"),
        ({"templates": []}, "non-empty list"),
        ({"templates": ["rerolled_bullet_point_1", 3]}, "non-empty string"),
        ({"threshold": -0.1}, "between 0 and 1"),
        ({"threshold": 1.1}, "between 0 and 1"),
    ],
)
def test_validate_replay_config_rejects_invalid_inputs(tmp_path, overrides, message):
    with pytest.raises(ReplayConfigurationError, match=message):
        validate_replay_config(make_replay_config(tmp_path, **overrides))


def test_run_replay_matches_all_templates_logs_confidence_and_saves_annotation(tmp_path, monkeypatch, caplog):
    config = make_replay_config(tmp_path, templates=["rerolled_bullet_point_1", "rerolled_bullet_point_2"])
    matches = [
        TemplateMatch(center=(40, 50), region=[30, 40, 20, 20], name="rerolled_bullet_point_1", score=0.93),
        TemplateMatch(center=(100, 120), region=[90, 110, 20, 20], name="rerolled_bullet_point_2", score=0.87),
    ]
    search_calls = []

    def fake_search(*args, **kwargs):
        search_calls.append((args, kwargs))
        return SearchResult(matches=matches, success=True)

    monkeypatch.setattr("src.tools.replay_template_matching.search", fake_search)
    with caplog.at_level(logging.INFO, logger="d4lf"):
        result = run_replay(config, display=False)

    assert result.found
    assert result.matches == matches
    assert result.output_path == tmp_path / "screen_all_template_matches.png"
    assert len(search_calls) == 1
    args, kwargs = search_calls[0]
    assert args == (config.templates,)
    assert kwargs["inp_img"].shape == (200, 300, 3)
    assert kwargs["threshold"] == pytest.approx(0.8)
    assert kwargs["use_grayscale"] is True
    assert kwargs["mode"] == "all"
    assert kwargs["do_multi_process"] is False
    output = cv2.imread(str(result.output_path))
    assert tuple(output[40, 30]) == (0, 255, 255)
    assert "Template matching: count=2" in caplog.text
    assert "template=rerolled_bullet_point_1" in caplog.text
    assert "confidence=0.9300" in caplog.text
    assert "template=rerolled_bullet_point_2" in caplog.text
    assert "confidence=0.8700" in caplog.text
