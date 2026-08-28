from src.loot import highlighting_pipeline


def test_highlighting_pipeline_public_interface() -> None:
    expected = [
        "CodexUpgradeCommand",
        "EmptyOutlineCommand",
        "FilterEvaluation",
        "FilterOutcome",
        "ItemRoi",
        "MarkerLocationResult",
        "MatchCommand",
        "NoMatchCommand",
        "Point",
        "RenderingCommand",
        "TargetCenterSelection",
        "TooltipConfirmation",
        "TooltipConfirmationStatus",
        "as_item_roi",
        "classify_filter_outcome",
        "confirm_stable_tooltip",
        "locate_markers_with_retry",
        "select_rendering_command",
        "select_target_center",
    ]

    assert highlighting_pipeline.__all__ == expected
    assert all(hasattr(highlighting_pipeline, name) for name in expected)
