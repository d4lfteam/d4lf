import json
import logging
from typing import TYPE_CHECKING

import lxml.html
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from src.importing.config import ImportConfig
from src.importing.contracts import VariantMetadata
from src.importing.conversion import as_string_keyed_mapping as _as_mapping
from src.importing.conversion import as_string_keyed_mapping_list as _as_mapping_list
from src.importing.conversion import as_text as _as_text
from src.importing.mobalytics.extraction import (
    _extract_mobalytics_season_number,
    _first_jsonpath_result,
    _fix_input_url,
    _log_mobalytics_page_diagnostics,
)
from src.importing.mobalytics.filters import build_variant
from src.importing.pipeline import ExtractedBuild, ImportPipeline, StaticBuildGuideAdapter
from src.importing.web import retry_importer

if TYPE_CHECKING:
    from selenium.webdriver.remote.webdriver import WebDriver

    from src.importing.contracts import ImportRequest, ImportResult

LOGGER = logging.getLogger(__name__)
LOGGER.propagate = True
BUILD_GUIDE_BASE_URL = "https://mobalytics.gg/diablo-4/"
BUILD_SCRIPT_PREFIX = "window.__PRELOADED_STATE__="
PROFILE_GUIDE_BASE_URL = f"{BUILD_GUIDE_BASE_URL}profile"
SCRIPT_XPATH = "//script"
type _JsonPathValue = str | int | float | bool | list[object] | dict[str, object] | None


class MobalyticsError(Exception):
    """Raised when Mobalytics page data cannot be extracted."""


@retry_importer(inject_webdriver=True)
def fetch_variants_mobalytics(request: ImportRequest, driver: WebDriver | None = None) -> list[VariantMetadata]:
    if driver is None:
        msg = "A Selenium WebDriver is required for Mobalytics imports"
        raise RuntimeError(msg)
    url = request.url.strip().replace("\n", "")
    if BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use a mobalytics build guide")
        return []
    url = _fix_input_url(url=url)
    LOGGER.info("Loading %s for variants", url)
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(ec.presence_of_element_located((By.XPATH, SCRIPT_XPATH)))
    page_source = driver.page_source
    raw_html_data = lxml.html.fromstring(page_source)
    scripts = raw_html_data.xpath(SCRIPT_XPATH)
    state = _load_preloaded_state(scripts)
    if not state:
        return []

    import jsonpath  # ruff:ignore[import-outside-top-level]

    variant_titles: dict[str, str] = {}
    for cv_list in jsonpath.findall("$..childrenVariants", state) or []:
        if isinstance(cv_list, list):
            for cv in cv_list:
                if isinstance(cv, dict):
                    v_id = _as_text(cv.get("id"))
                    title = _as_text(cv.get("title"))
                    if v_id and title:
                        variant_titles[v_id] = title

    build_data = _as_mapping(_first_jsonpath_result("$..userGeneratedDocumentBySlug.data.data", state))
    if not build_data:
        return []
    variants = []
    for val in _as_mapping_list(_as_mapping(_as_mapping(build_data).get("buildVariants")).get("values", [])):
        v_id = _first_jsonpath_result("id", val)
        if isinstance(v_id, str):
            name = variant_titles.get(v_id) or _as_text(val.get("name")) or f"Variant {v_id}"
            variants.append(VariantMetadata(id=v_id, name=name))
    return variants


def import_mobalytics(
    request: ImportRequest, driver: WebDriver | None = None, selected_variant_ids: list[str] | None = None
) -> ImportResult | None:
    return _import_mobalytics(ImportConfig.from_request(request), driver, selected_variant_ids)


@retry_importer(inject_webdriver=True)
def _import_mobalytics(
    config: ImportConfig, driver: WebDriver | None = None, selected_variant_ids: list[str] | None = None
) -> ImportResult | None:
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
    variant_id_from_url = url.split("?variant=")[1].split("&")[0] if "?variant=" in url else None
    page_source = driver.page_source
    raw_html_data = lxml.html.fromstring(page_source)
    scripts = raw_html_data.xpath(SCRIPT_XPATH)
    state = _load_preloaded_state(scripts)
    if not state:
        _log_mobalytics_page_diagnostics(driver=driver, page_source=page_source, script_count=len(scripts))
        msg = "No script containing build data was found. This means Mobalytics has changed how they present data, please submit a bug."
        raise MobalyticsError(msg)

    variant_id = variant_id_from_url or _as_text(_first_jsonpath_result("$..childrenVariants[0].id", state))
    build_data = _as_mapping(_first_jsonpath_result("$..userGeneratedDocumentBySlug.data.data", state))
    if not build_data:
        if "page you are looking for is archived" in page_source.casefold():
            LOGGER.warning("Mobalytics build is archived: %s", url)
            return None
        raise MobalyticsError(msg := "No build data found")
    build_header = _as_text(build_data.get("name"))
    class_name = _as_text(
        _first_jsonpath_result("$..userGeneratedDocumentBySlug.data.tags.data[?@.groupSlug=='class'].name", state)
    ).lower()
    if not build_header:
        raise MobalyticsError(msg := "No build name found")
    if not class_name:
        raise MobalyticsError(msg := "No class name found")
    variants_to_extract = []
    if config.multi_build:
        for val in _as_mapping_list(_as_mapping(_as_mapping(build_data).get("buildVariants")).get("values", [])):
            v_id = _first_jsonpath_result("id", val)
            if isinstance(v_id, str) and (selected_variant_ids is None or v_id in selected_variant_ids):
                variants_to_extract.append(v_id)
        if (
            not variants_to_extract
            and variant_id
            and (selected_variant_ids is None or variant_id in selected_variant_ids)
        ):
            variants_to_extract.append(variant_id)
    else:
        if not variant_id:
            variant_id = _as_text(_first_jsonpath_result("$..buildVariants.values[0].id", build_data)) or None
        variants_to_extract = [variant_id] if variant_id else []

    extracted_variants = []
    for vid in variants_to_extract:
        items = _first_jsonpath_result(f"$..buildVariants.values[?@.id=='{vid}'].genericBuilder.slots", build_data)
        if not items:
            continue
        items = _as_mapping_list(items)
        paragon_value = _first_jsonpath_result(f"$..buildVariants.values[?@.id=='{vid}'].paragon", build_data)
        paragon_data = _as_mapping(paragon_value) if paragon_value is not None else {}
        v_name = _as_text(_first_jsonpath_result(f"$..childrenVariants[?@.id=='{vid}'].title", state))

        variant = build_variant(
            items=items,
            class_name=class_name,
            config=config,
            driver=driver,
            variant_name=v_name,
            build_name=f"{build_header} {v_name}".strip() if v_name else build_header,
            paragon_data=paragon_data,
            error_type=MobalyticsError,
        )
        extracted_variants.append(variant)

    if not extracted_variants:
        raise MobalyticsError(msg := "No variants could be extracted")
    return ImportPipeline.run_result(
        adapter=StaticBuildGuideAdapter(
            url=url,
            build=ExtractedBuild(
                source_name="mobalytics",
                class_name=class_name,
                build_header=build_header,
                season_number=_extract_mobalytics_season_number(_as_mapping(state)),
                variants=extracted_variants,
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
