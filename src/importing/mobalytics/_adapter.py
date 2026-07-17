import json
import logging
from typing import TYPE_CHECKING

import lxml.html
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from src.importing._conversion import as_string_keyed_mapping as _as_mapping
from src.importing._conversion import as_string_keyed_mapping_list as _as_mapping_list
from src.importing._conversion import as_text as _as_text
from src.importing._web import retry_importer
from src.importing.config import ImportConfig
from src.importing.pipeline import ExtractedBuild, ImportPipeline, StaticBuildGuideAdapter

from ._extraction import (
    _extract_mobalytics_season_number,
    _first_jsonpath_result,
    _fix_input_url,
    _log_mobalytics_page_diagnostics,
)
from ._filters import build_variant

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

    from src.importing import ImportRequest, ImportResult

LOGGER = logging.getLogger(__name__)
LOGGER.propagate = True
BUILD_GUIDE_BASE_URL = "https://mobalytics.gg/diablo-4/"
BUILD_SCRIPT_PREFIX = "window.__PRELOADED_STATE__="
PROFILE_GUIDE_BASE_URL = f"{BUILD_GUIDE_BASE_URL}profile"
SCRIPT_XPATH = "//script"
type _JsonPathValue = str | int | float | bool | list[object] | dict[str, object] | None


class MobalyticsError(Exception):
    """Raised when Mobalytics page data cannot be extracted."""


def import_mobalytics(request: ImportRequest, driver: WebDriver | None = None) -> ImportResult | None:
    options = request.options
    config = ImportConfig(
        url=request.url,
        import_aspect_upgrades=options.import_aspect_upgrades,
        add_to_profiles=options.add_to_profiles,
        import_greater_affixes=options.import_greater_affixes,
        require_greater_affixes=options.require_greater_affixes,
        export_paragon=options.export_paragon,
        custom_file_name=options.custom_file_name,
        filename_parts=request.filename_parts,
    )
    return _import_mobalytics(config, driver)


@retry_importer(inject_webdriver=True)
def _import_mobalytics(config: ImportConfig, driver: WebDriver | None = None) -> ImportResult | None:
    if driver is None:
        msg = "A Selenium WebDriver is required for Mobalytics imports"
        raise RuntimeError(msg)
    url = config.url.strip().replace("\n", "")
    if BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use a mobalytics build guide")
        return None
    if PROFILE_GUIDE_BASE_URL in url:
        LOGGER.error("Builds from user profiles are not supported at this time.")
        return None
    url = _fix_input_url(url=url)
    LOGGER.info("Loading %s", url)
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(ec.presence_of_element_located((By.XPATH, SCRIPT_XPATH)))
    variant_id = url.split(",")[1].split("#")[0] if "activeVariantId" in url else None
    page_source = driver.page_source
    raw_html_data = lxml.html.fromstring(page_source)
    scripts = raw_html_data.xpath(SCRIPT_XPATH)
    state = _load_preloaded_state(scripts)
    if not state:
        _log_mobalytics_page_diagnostics(driver=driver, page_source=page_source, script_count=len(scripts))
        msg = "No script containing build data was found. This means Mobalytics has changed how they present data, please submit a bug."
        raise MobalyticsError(msg)
    build_data = _as_mapping(_first_jsonpath_result("$..userGeneratedDocumentBySlug.data.data", state))
    if not build_data:
        raise MobalyticsError(msg := "No build data found")
    build_header = _as_text(build_data.get("name"))
    class_name = _as_text(
        _first_jsonpath_result("$..userGeneratedDocumentBySlug.data.tags.data[?@.groupSlug=='class'].name", state)
    ).lower()
    if not build_header:
        raise MobalyticsError(msg := "No build name found")
    if not class_name:
        raise MobalyticsError(msg := "No class name found")
    if variant_id:
        items = _first_jsonpath_result(
            f"$..buildVariants.values[?@.id=='{variant_id}'].genericBuilder.slots", build_data
        )
    else:
        items = _first_jsonpath_result("$..buildVariants.values[0].genericBuilder.slots", build_data)
        variant_id = _first_jsonpath_result("$..buildVariants.values[0].id", build_data)
        if not isinstance(variant_id, str):
            raise MobalyticsError(msg := "No variant id found")
    items = _as_mapping_list(items)
    paragon_value = _first_jsonpath_result(f"$..buildVariants.values[?@.id=='{variant_id}'].paragon", build_data)
    if paragon_value is None:
        raise MobalyticsError(msg := "No paragon data found")
    paragon_data = _as_mapping(paragon_value)
    variant_name = _as_text(_first_jsonpath_result(f"$..childrenVariants[?@.id=='{variant_id}'].title", state))
    if not items:
        raise MobalyticsError(msg := "No items found")
    variant = build_variant(
        items=items,
        class_name=class_name,
        config=config,
        driver=driver,
        variant_name=variant_name,
        build_name=f"{build_header} {variant_name}".strip() if variant_name else build_header,
        paragon_data=paragon_data,
        error_type=MobalyticsError,
    )
    return ImportPipeline.run_result(
        adapter=StaticBuildGuideAdapter(
            url=url,
            build=ExtractedBuild(
                source_name="mobalytics",
                class_name=class_name,
                build_header=build_header,
                season_number=_extract_mobalytics_season_number(_as_mapping(state)),
                variants=[variant],
            ),
        ),
        config=config,
    )


def _load_preloaded_state(scripts: list[object]) -> _JsonPathValue:
    for script in scripts:
        script_text = getattr(script, "text", None)
        if script_text and script_text.strip().startswith(BUILD_SCRIPT_PREFIX):
            try:
                return json.loads(script_text.strip().replace(BUILD_SCRIPT_PREFIX, "")[:-1])
            except json.JSONDecodeError as exc:
                message = "Mobalytics build data was not valid JSON"
                raise MobalyticsError(message) from exc
    return None
