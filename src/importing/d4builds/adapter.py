import logging
import re
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING

import lxml.html
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as ec
from selenium.webdriver.support.wait import WebDriverWait

from src.importing.contracts import ImportRequest, ImportResult, VariantMetadata, VariantSelection
from src.importing.d4builds.constants import BASE_URL, BUILD_OVERVIEW_XPATH, PAPERDOLL_XPATH
from src.importing.d4builds.metadata import D4BuildsError, _extract_build_metadata
from src.importing.d4builds.variants import extract_variant
from src.importing.pipeline import ExtractedBuild, ImportPipeline, StaticBuildGuideAdapter
from src.importing.web import retry_importer

if TYPE_CHECKING:
    from collections.abc import Iterator

    from selenium.webdriver.remote.webdriver import WebDriver


LOGGER = logging.getLogger(__name__)
MAX_VARIANTS = 50


@dataclass(frozen=True, slots=True)
class _LoadedVariantPage:
    data: lxml.html.HtmlElement
    class_name: str
    build_header: str
    season_number: str
    variant_name: str


def _validated_url(request: ImportRequest, driver: WebDriver | None) -> tuple[str, WebDriver] | None:
    if driver is None:
        msg = "A Selenium WebDriver is required for D4Builds imports"
        raise RuntimeError(msg)
    url = request.url
    if BASE_URL not in url:
        LOGGER.error("Invalid url, please use a d4builds url")
        return None
    return url, driver


def _load_variant_page(url: str, driver: WebDriver, *, wait_for_paperdoll: bool = False) -> _LoadedVariantPage:
    driver.get(url)
    wait = WebDriverWait(driver, 10)
    wait.until(ec.presence_of_element_located((By.XPATH, BUILD_OVERVIEW_XPATH)))
    if wait_for_paperdoll:
        wait.until(ec.presence_of_element_located((By.XPATH, PAPERDOLL_XPATH)))
        time.sleep(5)
    data = lxml.html.fromstring(driver.page_source)
    class_name, build_header, season_number, variant_name = _extract_build_metadata(data=data)
    return _LoadedVariantPage(data, class_name, build_header, season_number, variant_name)


def _variant_url(url: str, variant_index: int) -> str:
    url_variant = url if "?" not in url else re.sub(r"var=\d+", f"var={variant_index}", url)
    if "var=" not in url_variant:
        url_variant += f"&var={variant_index}" if "?" in url_variant else f"?var={variant_index}"
    return url_variant


def _variant_key(loaded_page: _LoadedVariantPage) -> str:
    if loaded_page.variant_name:
        return loaded_page.variant_name
    return lxml.html.tostring(loaded_page.data, encoding="unicode")


def _iter_variant_pages(
    url: str, driver: WebDriver, *, selection: VariantSelection | None = None, wait_for_paperdoll: bool = False
) -> Iterator[tuple[int, _LoadedVariantPage]]:
    seen_variant_keys: set[str] = set()
    for variant_index in range(MAX_VARIANTS):
        if selection is not None and str(variant_index) not in selection:
            continue
        url_variant = _variant_url(url, variant_index)
        LOGGER.info("Loading %s", url_variant)
        loaded_page = _load_variant_page(url_variant, driver, wait_for_paperdoll=wait_for_paperdoll)
        if selection is None:
            variant_key = _variant_key(loaded_page)
            if variant_key in seen_variant_keys:
                break
            seen_variant_keys.add(variant_key)
        yield variant_index, loaded_page


@retry_importer(inject_webdriver=True)
def fetch_variants_d4builds(request: ImportRequest, driver: WebDriver | None = None) -> list[VariantMetadata]:
    validated = _validated_url(request, driver)
    if validated is None:
        return []
    url, driver = validated

    variants = []
    for var_index, loaded_page in _iter_variant_pages(url, driver, selection=request.variant_selection):
        variant_name = loaded_page.variant_name
        variants.append(VariantMetadata(id=str(var_index), name=variant_name or f"Variant {var_index + 1}"))

    if len(variants) == MAX_VARIANTS:
        LOGGER.warning("Stopped D4Builds variant discovery after %s variants", MAX_VARIANTS)

    return variants


@retry_importer(inject_webdriver=True)
def import_d4builds(request: ImportRequest, driver: WebDriver | None = None) -> ImportResult | None:
    validated = _validated_url(request, driver)
    if validated is None:
        return None
    url, driver = validated
    variants = []
    final_class_name = ""
    final_build_header = ""
    final_season_number = ""

    if request.options.multi_build:
        pages = _iter_variant_pages(url, driver, selection=request.variant_selection, wait_for_paperdoll=True)
    else:
        pages = iter(((0, _load_variant_page(url, driver, wait_for_paperdoll=True)),))

    for _var_index, loaded_page in pages:
        data = loaded_page.data
        class_name = loaded_page.class_name
        build_header = loaded_page.build_header
        season_number = loaded_page.season_number
        variant_name = loaded_page.variant_name

        final_class_name = class_name
        final_build_header = build_header
        final_season_number = season_number
        if not data.xpath(BUILD_OVERVIEW_XPATH):
            message = "No items found"
            LOGGER.error(message)
            if not request.options.multi_build:
                raise D4BuildsError(message)
            continue
        variants.append(
            extract_variant(
                data=data,
                driver=driver,
                request=request,
                class_name=class_name,
                build_header=build_header,
                variant_name=variant_name,
            )
        )

        if not request.options.multi_build:
            break

    if request.options.multi_build and len(variants) == MAX_VARIANTS:
        LOGGER.warning("Stopped D4Builds import after %s variants", MAX_VARIANTS)

    if not variants:
        message = "No variants could be extracted"
        raise D4BuildsError(message)

    return ImportPipeline.run_result(
        adapter=StaticBuildGuideAdapter(
            url=url,
            build=ExtractedBuild(
                source_name="d4builds",
                class_name=final_class_name,
                build_header=final_build_header,
                season_number=final_season_number,
                variants=variants,
            ),
        ),
        request=request,
    )
