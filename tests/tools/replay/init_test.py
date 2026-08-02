from src.tools.replay import CroppedTooltipConfig, FullScreenshotConfig, TemplateMatchingConfig


def test_replay_facade_eagerly_exports_config_types() -> None:
    assert CroppedTooltipConfig is not FullScreenshotConfig
    assert TemplateMatchingConfig is not FullScreenshotConfig
