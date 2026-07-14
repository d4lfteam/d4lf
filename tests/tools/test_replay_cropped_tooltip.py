import logging
from pathlib import Path

import cv2
import numpy as np
import pytest

from src.item.data.affix import Affix
from src.item.data.aspect import Aspect
from src.item.descr.geometry_locator import (
    BulletMatchDiagnostics,
    DiagnosticLocatorResult,
    LocatedMarker,
    LocatorDiagnostics,
    LocatorResult,
    TemplateMatchTrace,
)
from src.item.models import Item
from src.tools.replay_cropped_tooltip import (
    ReplayConfig,
    ReplayConfigurationError,
    main,
    run_replay,
    show_result,
    validate_replay_config,
)


def make_item() -> Item:
    return Item(
        inherent=[Affix(name="inherent")],
        affixes=[Affix(name="life"), Affix(name="armor")],
        aspect=Aspect(name="test_aspect"),
    )


def make_replay_config(tmp_path: Path, *, item: Item | None = None, **overrides) -> ReplayConfig:
    image_path = tmp_path / "tooltip.png"
    cv2.imwrite(str(image_path), np.zeros((240, 320, 3), dtype=np.uint8))
    values = {
        "image_path": image_path,
        "game_resolution": "3840x2160",
        "item": item or make_item(),
        "matched_row_indices": [1, 2],
        "aspect_matched": True,
    }
    values.update(overrides)
    return ReplayConfig(**values)


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"image_path": "missing.png"}, "does not exist"),
        ({"game_resolution": "3840"}, "WIDTHxHEIGHT"),
        ({"matched_row_indices": [1, 1]}, "duplicate"),
        ({"matched_row_indices": [3]}, "out of range"),
        ({"aspect_matched": True, "item": Item(affixes=[Affix(name="life")])}, "aspect"),
    ],
)
def test_validate_replay_config_rejects_invalid_inputs(tmp_path, overrides, message):
    with pytest.raises(ReplayConfigurationError, match=message):
        validate_replay_config(make_replay_config(tmp_path, **overrides))


def test_validate_replay_config_rejects_unreadable_image(tmp_path):
    config = make_replay_config(tmp_path)
    config.image_path.write_text("not an image", encoding="utf-8")

    with pytest.raises(ReplayConfigurationError, match="cannot be read"):
        validate_replay_config(config)


def test_run_replay_saves_annotated_output_and_logs_all_stages(tmp_path, monkeypatch, caplog):
    trace = TemplateMatchTrace(name="affix_bullet_point_1", center=(20, 100), region=[16, 96, 8, 8], confidence=0.91)
    separator = TemplateMatchTrace("item_separator", (40, 60), [0, 50, 20, 10], 0.95)
    long_separator = TemplateMatchTrace("item_long_separator", (50, 75), [40, 70, 20, 10], 0.95)
    diagnostics = LocatorDiagnostics(
        separator=separator,
        long_separator=long_separator,
        affix_bullets=BulletMatchDiagnostics(
            raw=[trace],
            rejected_outliers=[TemplateMatchTrace("outlier", (80, 100), [76, 96, 8, 8], 0.82)],
            rejected_duplicates=[TemplateMatchTrace("duplicate", (20, 101), [16, 97, 8, 8], 0.84)],
            accepted=[trace],
        ),
        selected_markers=[LocatedMarker("affix", 1, (20, 100), 0.91)],
    )
    diagnostic_result = DiagnosticLocatorResult(
        LocatorResult([LocatedMarker("affix", 1, (20, 100), 0.91)], reliable=True), diagnostics
    )
    monkeypatch.setattr(
        "src.tools.replay_cropped_tooltip.locate_affix_markers_with_diagnostics", lambda **_: diagnostic_result
    )

    config = make_replay_config(tmp_path, matched_row_indices=[1])
    with caplog.at_level(logging.INFO, logger="d4lf"):
        result = run_replay(config, display=False)

    assert result.reliable
    assert result.output_path == tmp_path / "tooltip_template_matches.png"
    assert result.output_path.exists()
    output = cv2.imread(str(result.output_path))
    assert tuple(output[100, 20]) == (93, 252, 35)
    assert tuple(output[70, 40]) == (255, 255, 0)
    for expected in (
        "Replay inputs",
        "separator",
        "long_separator",
        "affix_bullets.raw",
        "affix_bullets.rejected_outliers",
        "affix_bullets.rejected_duplicates",
        "affix_bullets.accepted",
        "Final marker",
        "reliable=True",
        "tooltip_template_matches.png",
    ):
        assert expected in caplog.text


def test_run_replay_saves_failure_annotation_without_display(tmp_path, monkeypatch):
    diagnostic_result = DiagnosticLocatorResult(
        LocatorResult([], reliable=False), LocatorDiagnostics(failure_reason="missing_separator")
    )
    monkeypatch.setattr(
        "src.tools.replay_cropped_tooltip.locate_affix_markers_with_diagnostics", lambda **_: diagnostic_result
    )

    result = run_replay(make_replay_config(tmp_path, matched_row_indices=[1]), display=False)

    assert not result.reliable
    output = cv2.imread(str(result.output_path))
    assert tuple(output[0, 0]) == (0, 0, 255)


def test_run_replay_annotates_all_match_stages_and_resolution_sized_marker(tmp_path, monkeypatch):
    config = make_replay_config(tmp_path, matched_row_indices=[1], aspect_matched=False, game_resolution="1920x1080")
    cv2.imwrite(str(config.image_path), np.zeros((1000, 1000, 3), dtype=np.uint8))
    diagnostic_result = DiagnosticLocatorResult(
        LocatorResult([LocatedMarker("affix", 0, (500, 500), 0.9)], reliable=True),
        LocatorDiagnostics(
            affix_bullets=BulletMatchDiagnostics(
                raw=[TemplateMatchTrace("raw", (100, 100), [96, 96, 8, 8], 0.81)],
                rejected_outliers=[TemplateMatchTrace("outlier", (200, 100), [196, 96, 8, 8], 0.82)],
                accepted=[TemplateMatchTrace("accepted", (300, 100), [296, 96, 8, 8], 0.91)],
            )
        ),
    )
    monkeypatch.setattr(
        "src.tools.replay_cropped_tooltip.locate_affix_markers_with_diagnostics", lambda **_: diagnostic_result
    )

    result = run_replay(config, display=False)
    output = cv2.imread(str(result.output_path))

    assert tuple(output[96, 100]) == (128, 128, 128)
    assert tuple(output[96, 200]) == (0, 165, 255)
    assert tuple(output[96, 300]) == (255, 255, 0)
    assert tuple(output[500, 500]) == (93, 252, 35)
    assert tuple(output[500, 493]) == (93, 252, 35)
    assert tuple(output[500, 492]) != (93, 252, 35)


def test_show_result_uses_blocking_window(monkeypatch):
    calls = []
    monkeypatch.setattr("src.tools.replay_cropped_tooltip.cv2.imshow", lambda *args: calls.append(("show", args)))
    monkeypatch.setattr("src.tools.replay_cropped_tooltip.cv2.waitKey", lambda *args: calls.append(("wait", args)))
    monkeypatch.setattr(
        "src.tools.replay_cropped_tooltip.cv2.destroyWindow", lambda *args: calls.append(("destroy", args))
    )

    show_result(np.zeros((4, 4, 3), dtype=np.uint8))

    assert [call[0] for call in calls] == ["show", "wait", "destroy"]


@pytest.mark.parametrize(("reliable", "expected_status"), [(True, 0), (False, 1)])
def test_main_returns_reliability_status_without_requiring_window(monkeypatch, reliable, expected_status):
    config = ReplayConfig(Path("tooltip.png"), "3840x2160", Item(), [], False)
    result = type("ReplayResult", (), {"reliable": reliable})()
    monkeypatch.setattr("src.tools.replay_cropped_tooltip.REPLAY_CONFIG", config)
    monkeypatch.setattr("src.tools.replay_cropped_tooltip.setup", lambda **_kwargs: None)
    monkeypatch.setattr("src.tools.replay_cropped_tooltip.run_replay", lambda *_args, **_kwargs: result)
    monkeypatch.setattr("src.tools.replay_cropped_tooltip.show_result", lambda *_args: None)

    assert main() == expected_status
