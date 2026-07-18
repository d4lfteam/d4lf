import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import cv2  # ruff:ignore[unused-import]

from src.item import Affix, Item, ItemType
from src.logger import setup
from src.perception import locate_affix_markers_with_diagnostics
from src.settings import get_ui_coordinates
from src.tools.replay.common import ReplayConfigurationError, load_replay_image, show_replay_result
from src.tools.replay.common import parse_resolution as _parse_resolution
from src.tools.replay.common import raise_configuration_error as _raise_configuration_error
from src.tools.replay.common import write_image as _write_image
from src.tools.replay.diagnostics import _log_diagnostics
from src.tools.replay.rendering import _annotate

if TYPE_CHECKING:
    import numpy as np

LOGGER = logging.getLogger("d4lf")

_MARKER_THICKNESS_RATIO = 0.0047


@dataclass
class ReplayConfig:
    aspect_matched: bool
    game_resolution: str
    image_path: Path | str
    item: Item
    matched_row_indices: list[int]


@dataclass(frozen=True)
class ReplayResult:
    failure_reason: str | None
    output_path: Path
    reliable: bool


# BEGIN EDITABLE REPLAY CONFIGURATION
# Replace these values with the cropped tooltip and the Item captured from production.
REPLAY_CONFIG = ReplayConfig(
    image_path=Path(r"E:\Downloads\test5.png"),
    game_resolution="3840x2160",
    item=Item(
        inherent=[Affix(name="charm_slot")],
        affixes=[
            Affix(name="barrier_generation"),
            Affix(name="sescherons_fury_fury_generation"),
            Affix(name="berserkers_crucible_lucky_hit_up_to_a_chance_to_become_berserking"),
        ],
        item_type=ItemType.HoradricSeal,
    ),
    matched_row_indices=[2],
    aspect_matched=False,
)
# END EDITABLE REPLAY CONFIGURATION


def validate_replay_config(config: ReplayConfig) -> tuple[Path, np.ndarray]:
    """Validate replay inputs and return the normalized image path and decoded image."""
    image_path, image = load_replay_image(config.image_path, label="Tooltip image")

    _parse_resolution(config.game_resolution)
    if not isinstance(config.item, Item):
        _raise_configuration_error("Replay item must be an Item.")
    if not isinstance(config.aspect_matched, bool):
        _raise_configuration_error("Aspect-matched flag must be true or false.")
    if config.aspect_matched and config.item.aspect is None:
        _raise_configuration_error("Aspect-matched was requested, but the item has no aspect.")

    row_count = len(config.item.inherent) + len(config.item.affixes)
    indices = config.matched_row_indices
    if not isinstance(indices, list):
        _raise_configuration_error("Matched row indices must be provided as a list.")
    if any(not isinstance(index, int) or isinstance(index, bool) for index in indices):
        _raise_configuration_error("Matched row indices must be integers.")
    if len(indices) != len(set(indices)):
        _raise_configuration_error("Matched row indices contain a duplicate.")
    if any(index < 0 or index >= row_count for index in indices):
        _raise_configuration_error(f"Matched row index is out of range; item has {row_count} inherent and affix rows.")
    return image_path, image


def show_result(image: np.ndarray) -> None:
    """Display the replay result until the user closes the blocking window."""
    show_replay_result(image, "D4LF cropped tooltip replay")


def run_replay(config: ReplayConfig, *, display: bool = True) -> ReplayResult:
    """Run production matching against a cropped tooltip and save its explanation."""
    image_path, image = validate_replay_config(config)
    output_path = image_path.with_name(f"{image_path.stem}_template_matches.png")
    rows = config.item.inherent + config.item.affixes
    matched_affixes = [rows[index] for index in config.matched_row_indices]
    width, height = _parse_resolution(config.game_resolution)
    LOGGER.info(
        "Replay inputs: image=%s resolution=%sx%s matched_row_indices=%s aspect_matched=%s item=%s",
        image_path,
        width,
        height,
        config.matched_row_indices,
        config.aspect_matched,
        config.item,
    )

    resolution_manager = get_ui_coordinates()
    previous_resolution = "x".join(str(value) for value in resolution_manager.resolution)
    try:
        resolution_manager.set_resolution(config.game_resolution)
        diagnostic_result = locate_affix_markers_with_diagnostics(
            tooltip_image=image, item=config.item, matched_affixes=matched_affixes, aspect_matched=config.aspect_matched
        )
    finally:
        resolution_manager.set_resolution(previous_resolution)

    _log_diagnostics(diagnostic_result)
    LOGGER.info(
        "Replay reliability: reliable=%s failure_reason=%s",
        diagnostic_result.result.reliable,
        diagnostic_result.diagnostics.failure_reason,
    )
    marker_size = int(int(height * _MARKER_THICKNESS_RATIO) * 3)
    annotated = _annotate(image, diagnostic_result, marker_size)
    _write_image(output_path, annotated)
    LOGGER.info("Replay output: %s", output_path)
    if display:
        show_result(annotated)
    return ReplayResult(
        output_path=output_path,
        reliable=diagnostic_result.result.reliable,
        failure_reason=diagnostic_result.diagnostics.failure_reason,
    )


def main() -> int:
    setup(enable_stdout=True)
    try:
        result = run_replay(REPLAY_CONFIG)
    except ReplayConfigurationError as error:
        LOGGER.error("Replay configuration error: %s", error)
        return 2
    return 0 if result.reliable else 1
