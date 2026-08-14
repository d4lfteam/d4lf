import json
import logging
from typing import TYPE_CHECKING, cast

import jsonpath
import lxml.html
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from src.importing.contracts import ImportRequest, ImportResult, ImportSourceError, VariantMetadata
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
    from collections.abc import Iterable

    from selenium.webdriver.remote.webdriver import WebDriver

    from src.type_aliases import JsonValue


LOGGER = logging.getLogger(__name__)
LOGGER.propagate = True
BUILD_GUIDE_BASE_URL = "https://mobalytics.gg/diablo-4/"
BUILD_SCRIPT_PREFIX = "window.__PRELOADED_STATE__="
PROFILE_GUIDE_BASE_URL = f"{BUILD_GUIDE_BASE_URL}profile"
SCRIPT_XPATH = "//script"


class MobalyticsError(ImportSourceError):
    """Raised when Mobalytics page data cannot be extracted."""


def _validated_url(
    request: ImportRequest, driver: WebDriver | None, *, reject_profile: bool = False
) -> tuple[str, WebDriver] | None:
    if driver is None:
        msg = "A Selenium WebDriver is required for Mobalytics imports"
        raise RuntimeError(msg)
    url = request.url.strip().replace("\n", "")
    if BUILD_GUIDE_BASE_URL not in url:
        LOGGER.error("Invalid url, please use a mobalytics build guide")
        return None
    if reject_profile and PROFILE_GUIDE_BASE_URL in url:
        LOGGER.error("Builds from user profiles are not supported at this time.")
        return None
    return url, driver


def _load_build_page(url: str, driver: WebDriver) -> tuple[str, str, JsonValue | None, int]:
    """Load the preloaded state shared by variant discovery and import."""
    normalized_url = _fix_input_url(url=url)
    driver.get(normalized_url)
    wait = WebDriverWait(driver, 10)
    wait.until(ec.presence_of_element_located((By.XPATH, SCRIPT_XPATH)))
    page_source = driver.page_source
    raw_html_data = lxml.html.fromstring(page_source, parser=lxml.html.HTMLParser())
    scripts = list(raw_html_data.iter("script"))
    state = _load_preloaded_state(scripts)
    return normalized_url, page_source, state, len(scripts)


@retry_importer(inject_webdriver=True)
def fetch_variants_mobalytics(request: ImportRequest, driver: WebDriver | None = None) -> list[VariantMetadata]:
    validated = _validated_url(request, driver)
    if validated is None:
        return []
    url, driver = validated
    url, _, state, _ = _load_build_page(url, driver)
    LOGGER.info("Loading %s for variants", url)
    if not state:
        return []

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


def import_mobalytics(request: ImportRequest, driver: WebDriver | None = None) -> ImportResult | None:
    return _import_mobalytics(request, driver)


@retry_importer(inject_webdriver=True)
def _import_mobalytics(request: ImportRequest, driver: WebDriver | None = None) -> ImportResult | None:
    validated = _validated_url(request, driver, reject_profile=True)
    if validated is None:
        return None
    url, driver = validated
    url, page_source, state, script_count = _load_build_page(url, driver)
    LOGGER.info("Loading %s", url)
    variant_id_from_url = None
    if "?variant=" in url:
        variant_id_from_url = url.split("?variant=")[1].split("&")[0]
    elif "activeVariantId," in url:
        variant_id_from_url = url.split("activeVariantId,")[1].split("&")[0]
    if not state:
        _log_mobalytics_page_diagnostics(driver=driver, page_source=page_source, script_count=script_count)
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
    build_variants = _as_mapping_list(_as_mapping(_as_mapping(build_data).get("buildVariants")).get("values", []))
    available_variant_ids = [
        variant_value
        for variant in build_variants
        if isinstance(variant_value := _first_jsonpath_result("id", variant), str)
    ]
    # URLs can retain an id for a variant that was deleted or made private.  In that
    # case import the first available variant rather than failing the whole build.
    if variant_id not in available_variant_ids:
        variant_id = available_variant_ids[0] if available_variant_ids else None
    variants_to_extract = []
    selection = request.variant_selection
    if request.options.multi_build:
        for val in build_variants:
            v_id = _first_jsonpath_result("id", val)
            if isinstance(v_id, str) and (selection is None or v_id in selection):
                variants_to_extract.append(v_id)
        if not variants_to_extract and variant_id and (selection is None or variant_id in selection):
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
            request=request,
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
        request=request,
    )


def _load_preloaded_state(scripts: Iterable[lxml.html.HtmlElement]) -> JsonValue | None:
    for script in scripts:
        script_text = getattr(script, "text", None)
        if not isinstance(script_text, str) or not script_text.strip().startswith(BUILD_SCRIPT_PREFIX):
            continue
        try:
            return cast("JsonValue", json.loads(script_text.strip().replace(BUILD_SCRIPT_PREFIX, "")[:-1]))
        except json.JSONDecodeError as exc:
            message = "Mobalytics build data was not valid JSON"
            raise MobalyticsError(message) from exc
    return None
