"""Execute template matching workers with an optional shared executor."""

from collections.abc import Callable
from concurrent.futures import FIRST_COMPLETED, Executor, ThreadPoolExecutor, wait
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np

    from src.settings import Template

    from .config import SearchConfig
    from .models import ImageMatch

type MatchWorker = Callable[
    [Template, np.ndarray, list[float] | None, list[np.ndarray] | None, bool, float, bool], list[ImageMatch]
]


def _run_parallel(
    templates: list[Template],
    img: np.ndarray,
    roi: list[float] | None,
    color_match: list[np.ndarray] | None,
    use_grayscale: bool,
    threshold: float,
    take_debug_screenshot: bool,
    executor: Executor,
    worker: MatchWorker,
) -> list[list[ImageMatch]]:
    futures = [
        executor.submit(worker, template, img, roi, color_match, use_grayscale, threshold, take_debug_screenshot)
        for template in templates
    ]
    # Reading futures in template order makes stop conditions deterministic even when workers finish out of order.
    return [future.result() for future in futures]


def _run_parallel_first(
    templates: list[Template],
    img: np.ndarray,
    roi: list[float] | None,
    color_match: list[np.ndarray] | None,
    use_grayscale: bool,
    threshold: float,
    take_debug_screenshot: bool,
    executor: Executor,
    worker: MatchWorker,
) -> list[list[ImageMatch]]:
    futures = {
        executor.submit(worker, template, img, roi, color_match, use_grayscale, threshold, take_debug_screenshot): index
        for index, template in enumerate(templates)
    }
    pending = set(futures)
    while pending:
        done, pending = wait(pending, return_when=FIRST_COMPLETED)
        # A simultaneous completion has no meaningful completion order. Use template order for that tie.
        for future, template_index in futures.items():
            if future not in done:
                continue
            template_matches = future.result()
            if template_matches:
                for pending_future in pending:
                    pending_future.cancel()
                return [template_matches if index == template_index else [] for index in range(len(templates))]
    return [[] for _ in templates]


def find_matches_for_templates(
    templates: list[Template],
    img: np.ndarray,
    config: SearchConfig,
    resolved_roi: list[float] | None,
    resolved_color_match: list[np.ndarray] | None,
    executor: Executor | None,
    worker: MatchWorker,
) -> list[list[ImageMatch]]:
    """Find matches for templates, reusing an injected executor when available."""
    if not templates:
        return []
    if not config.use_parallel or len(templates) == 1:
        return [
            worker(
                template,
                img,
                resolved_roi,
                resolved_color_match,
                config.use_grayscale,
                config.threshold,
                config.take_debug_screenshot,
            )
            for template in templates
        ]
    if executor is not None:
        return _run_parallel_for_config(templates, img, config, resolved_roi, resolved_color_match, executor, worker)
    owned_executor = ThreadPoolExecutor(max_workers=min(32, len(templates)))
    try:
        return _run_parallel_for_config(
            templates, img, config, resolved_roi, resolved_color_match, owned_executor, worker
        )
    finally:
        owned_executor.shutdown(wait=False, cancel_futures=True)


def _run_parallel_for_config(
    templates: list[Template],
    img: np.ndarray,
    config: SearchConfig,
    resolved_roi: list[float] | None,
    resolved_color_match: list[np.ndarray] | None,
    executor: Executor,
    worker: MatchWorker,
) -> list[list[ImageMatch]]:
    if config.mode == "first" and config.stop_condition is None:
        return _run_parallel_first(
            templates,
            img,
            resolved_roi,
            resolved_color_match,
            config.use_grayscale,
            config.threshold,
            config.take_debug_screenshot,
            executor,
            worker,
        )
    return _run_parallel(
        templates,
        img,
        resolved_roi,
        resolved_color_match,
        config.use_grayscale,
        config.threshold,
        config.take_debug_screenshot,
        executor,
        worker,
    )
