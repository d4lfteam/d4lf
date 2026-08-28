"""Orchestrate template matching against a supplied or captured image."""

import logging
import time
from concurrent.futures import Executor, ThreadPoolExecutor
from typing import TYPE_CHECKING, cast

from src.perception.capture.core import Cam
from src.perception.matching.matcher import find_image_matches
from src.perception.matching.matcher import get_cv_result as _pure_get_cv_result
from src.perception.matching.resources import process_template_refs, resolve_color_match, resolve_roi
from src.perception.roi import get_center
from src.perception.screenshot import screenshot

from .config import SearchConfig
from .executor import find_matches_for_templates
from .models import ImageMatch, SearchResult, TemplateMatch

if TYPE_CHECKING:
    from collections.abc import Callable, Sequence

    import numpy as np

    from src.settings import Template

    from .config import SearchMode
    from .models import ColorMatch, TemplateReferences

LOGGER = logging.getLogger(__name__)

# These aliases retain narrow seams for callers that used to patch the monolithic implementation.
_process_template_refs = process_template_refs


def _get_cv_result(
    template: Template,
    inp_img: np.ndarray,
    roi: Sequence[int | float] | None = None,
    color_match: list[np.ndarray] | None = None,
    use_grayscale: bool = False,
    take_debug_screenshot: bool = False,
) -> tuple[np.ndarray | None, np.ndarray, list[int]]:
    """Call the pure matcher and keep debug capture at the orchestration boundary."""
    result = _pure_get_cv_result(template, inp_img, roi, color_match, use_grayscale)
    if take_debug_screenshot:
        _, _, resolved_roi = result
        rx, ry, rw, rh = resolved_roi
        screenshot("template_finder", img=inp_img[ry : ry + rh, rx : rx + rw])
    return result


def _find_template_matches(
    template: Template,
    img: np.ndarray,
    roi: list[float] | None,
    color_match: list[np.ndarray] | None,
    use_grayscale: bool,
    threshold: float,
    take_debug_screenshot: bool = False,
) -> list[ImageMatch]:
    """Find all matches for one template without sharing search state between workers."""

    def get_result(
        current_template: Template,
        current_image: np.ndarray,
        current_roi: Sequence[int | float] | None,
        current_color_match: list[np.ndarray] | None,
        grayscale: bool,
    ) -> tuple[np.ndarray | None, np.ndarray, list[int]]:
        return _get_cv_result(
            current_template, current_image, current_roi, current_color_match, grayscale, take_debug_screenshot
        )

    return find_image_matches(template, img, roi, color_match, use_grayscale, threshold, get_result=get_result)


def _to_template_match(template: Template, image_match: ImageMatch) -> TemplateMatch:
    region = image_match.region
    center = get_center(region)
    monitor_region = [*Cam().window_to_monitor((region[0], region[1])), region[2], region[3]]
    monitor_center = Cam().window_to_monitor(center)
    return TemplateMatch(
        region=list(region),
        region_monitor=monitor_region,
        center=center,
        center_monitor=(int(monitor_center[0]), int(monitor_center[1])),
        name=template.name,
        score=image_match.score,
    )


def _find_matches_for_templates(
    templates: list[Template],
    img: np.ndarray,
    config: SearchConfig,
    resolved_roi: list[float] | None,
    resolved_color_match: list[np.ndarray] | None,
    executor: Executor | None,
) -> list[list[ImageMatch]]:
    return find_matches_for_templates(
        templates, img, config, resolved_roi, resolved_color_match, executor, _find_template_matches
    )


def _search_once(
    templates: list[Template],
    img: np.ndarray,
    config: SearchConfig,
    resolved_roi: list[float] | None,
    resolved_color_match: list[np.ndarray] | None,
    executor: Executor | None,
) -> list[TemplateMatch]:
    matches: list[TemplateMatch] = []
    if config.stop_condition is not None and config.stop_condition(matches):
        return matches
    image_matches = _find_matches_for_templates(templates, img, config, resolved_roi, resolved_color_match, executor)
    for template, template_matches in zip(templates, image_matches, strict=True):
        for image_match in template_matches:
            matches.append(_to_template_match(template, image_match))
            if config.mode == "first" or (config.stop_condition is not None and config.stop_condition(matches)):
                return matches
    return matches


def _build_config(
    threshold: float | SearchConfig,
    roi: Sequence[int | float] | str | None,
    use_grayscale: bool,
    color_match: ColorMatch,
    mode: str,
    timeout: int,
    suppress_debug: bool,
    do_multi_process: bool | None,
    take_debug_screenshot: bool,
    stop_condition: Callable[[list[TemplateMatch]], bool] | None,
    config: SearchConfig | None,
    use_parallel: bool | None,
) -> SearchConfig:
    threshold_value: float
    if isinstance(threshold, SearchConfig):
        if config is not None:
            message = "SearchConfig was supplied more than once"
            raise ValueError(message)
        config = threshold
        threshold_value = config.threshold
    else:
        threshold_value = threshold
    if config is not None:
        if use_parallel is not None or do_multi_process is not None:
            message = "SearchConfig cannot be combined with parallel options"
            raise ValueError(message)
        return config
    parallel = use_parallel if use_parallel is not None else do_multi_process
    return SearchConfig(
        threshold=float(threshold_value),
        roi=roi,
        use_grayscale=use_grayscale,
        color_match=color_match,
        mode=cast("SearchMode", mode),
        timeout=timeout,
        suppress_debug=suppress_debug,
        use_parallel=True if parallel is None else parallel,
        take_debug_screenshot=take_debug_screenshot,
        stop_condition=stop_condition,
    )


def search(
    ref: TemplateReferences,
    inp_img: np.ndarray | None = None,
    threshold: float | SearchConfig = 0.7,
    roi: Sequence[int | float] | str | None = None,
    use_grayscale: bool = False,
    color_match: ColorMatch = None,
    mode: str = "first",
    timeout: int = 0,
    suppress_debug: bool = True,
    do_multi_process: bool | None = None,
    take_debug_screenshot: bool = False,
    stop_condition: Callable[[list[TemplateMatch]], bool] | None = None,
    *,
    config: SearchConfig | None = None,
    use_parallel: bool | None = None,
    _executor: Executor | None = None,
) -> SearchResult:
    """Search for templates in an image or the current game window.

    ``use_parallel`` is the clear option name for new callers. ``do_multi_process`` remains accepted
    as a migration bridge for integrations outside the matching package; it controls threads, not processes.
    A :class:`SearchConfig` can be passed as the third positional argument or through ``config=``.
    """
    search_config = _build_config(
        threshold,
        roi,
        use_grayscale,
        color_match,
        mode,
        timeout,
        suppress_debug,
        do_multi_process,
        take_debug_screenshot,
        stop_condition,
        config,
        use_parallel,
    )
    templates = _process_template_refs(ref)
    resolved_roi = resolve_roi(search_config.roi)
    resolved_color_match = resolve_color_match(search_config.color_match)
    matches: list[TemplateMatch] = []
    started = time.monotonic()
    owned_executor: ThreadPoolExecutor | None = None
    executor = _executor
    if executor is None and search_config.use_parallel and len(templates) > 1:
        owned_executor = ThreadPoolExecutor(max_workers=min(32, len(templates)))
        executor = owned_executor
    try:
        while True:
            image = Cam().grab() if inp_img is None else inp_img
            matches = _search_once(templates, image, search_config, resolved_roi, resolved_color_match, executor)
            if matches or search_config.timeout <= 0 or time.monotonic() - started >= search_config.timeout:
                break
    finally:
        if owned_executor is not None:
            owned_executor.shutdown(wait=False, cancel_futures=True)
    result = SearchResult()
    if matches:
        result.success = True
        result.matches = sorted(matches, key=lambda match: match.score, reverse=True)
        if not search_config.suppress_debug and len(matches) > 1 and search_config.mode == "all":
            details = "\n".join(
                f"  {template_match.name} ({template_match.score * 100:.1f}% confidence)" for template_match in matches
            )
            LOGGER.debug(f"Found the following matches:\n{details}")
    elif not search_config.suppress_debug:
        LOGGER.debug(f"Could not find desired templates: {ref}")
    return result
