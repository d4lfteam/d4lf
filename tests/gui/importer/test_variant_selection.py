from src.gui.importer import d4builds
from src.gui.importer.d4builds import (
    _build_variant_url,
    _get_variant_probe_ids,
    _load_variant_options,
    _normalize_variant_options,
    _probe_variant_options_by_url,
    get_d4builds_variant_options,
)
from src.gui.importer.importer_config import ImportConfig, ImportVariantOption
from src.gui.importer.maxroll import _resolve_profile_indices
from src.gui.importer.mobalytics import _resolve_variants_to_import, get_mobalytics_variant_options


def test_maxroll_resolve_profile_indices_single_import_uses_selected_profile():
    config = ImportConfig(
        url="https://maxroll.gg/d4/build-guides/example",
        import_uniques=True,
        import_aspect_upgrades=True,
        add_to_profiles=False,
        import_greater_affixes=True,
        require_greater_affixes=True,
        import_multiple_variants=False,
    )
    build_data = {"profiles": [{"items": {"a": 1}}, {"items": {"b": 2}}]}

    assert _resolve_profile_indices(
        url=config.url, build_data=build_data, selected_profile_index=1, config=config
    ) == [1]


def test_maxroll_resolve_profile_indices_multi_import_honors_selected_variants():
    config = ImportConfig(
        url="https://maxroll.gg/d4/build-guides/example",
        import_uniques=True,
        import_aspect_upgrades=True,
        add_to_profiles=False,
        import_greater_affixes=True,
        require_greater_affixes=True,
        import_multiple_variants=True,
        selected_variants=("1",),
    )
    build_data = {"profiles": [{"items": {"a": 1}}, {"items": {"b": 2}}, {"items": {}}]}

    assert _resolve_profile_indices(
        url=config.url, build_data=build_data, selected_profile_index=0, config=config
    ) == [1]


def test_mobalytics_resolve_variants_to_import_returns_all_for_multi_import():
    config = ImportConfig(
        url="https://mobalytics.gg/diablo-4/builds/example",
        import_uniques=True,
        import_aspect_upgrades=True,
        add_to_profiles=False,
        import_greater_affixes=True,
        require_greater_affixes=True,
        import_multiple_variants=True,
    )
    variants = [{"id": "alpha"}, {"id": "beta"}]

    assert [variant_id for _, variant_id in _resolve_variants_to_import(variants, None, config)] == ["alpha", "beta"]


def test_mobalytics_resolve_variants_to_import_honors_selected_variants():
    config = ImportConfig(
        url="https://mobalytics.gg/diablo-4/builds/example",
        import_uniques=True,
        import_aspect_upgrades=True,
        add_to_profiles=False,
        import_greater_affixes=True,
        require_greater_affixes=True,
        import_multiple_variants=True,
        selected_variants=("beta",),
    )
    variants = [{"id": "alpha"}, {"id": "beta"}]

    assert [variant_id for _, variant_id in _resolve_variants_to_import(variants, None, config)] == ["beta"]


def test_mobalytics_variant_options_return_implicit_current_build_when_no_variants(monkeypatch):
    monkeypatch.setattr(
        "src.gui.importer.mobalytics._load_mobalytics_build_context",
        lambda _url: (
            "https://mobalytics.gg/diablo-4/builds/example",
            {},
            "RootDocument",
            "Starter Build",
            "sorcerer",
        ),
    )
    monkeypatch.setattr("src.gui.importer.mobalytics._get_variants", lambda **_kwargs: [])

    assert get_mobalytics_variant_options("https://mobalytics.gg/diablo-4/builds/example") == [
        ImportVariantOption(id="current", label="Starter Build")
    ]


def test_d4builds_build_variant_url_replaces_existing_var_query():
    source_url = "https://d4builds.gg/builds/pulverize-druid-endgame/?foo=bar&var=0"

    assert _build_variant_url(source_url, "5") == "https://d4builds.gg/builds/pulverize-druid-endgame/?foo=bar&var=5"


def test_d4builds_normalize_variant_options_handles_dropdown_records_and_deduplicates():
    raw_variants = [
        {"id": "renameVariant0", "label": "Uber (P230)"},
        {"href": "/builds/pulverize-druid-endgame/?var=1", "label": "Starter"},
        {"data_variant_value": "2", "label": "Pit Push"},
        {"id": "0", "label": "Uber (P230)"},
        {"label": "Missing id should be ignored"},
    ]

    assert _normalize_variant_options(raw_variants) == [
        ImportVariantOption(id="0", label="Uber (P230)"),
        ImportVariantOption(id="1", label="Starter"),
        ImportVariantOption(id="2", label="Pit Push"),
    ]


def test_d4builds_variant_probe_ids_cover_current_variant_and_padding():
    known_variants = [ImportVariantOption(id="1", label="No Uber")]

    assert _get_variant_probe_ids(
        source_url="https://d4builds.gg/builds/pulverize-druid-endgame/?var=5",
        known_variants=known_variants,
    ) == [str(index) for index in range(12)]


def test_d4builds_load_variant_options_falls_back_to_url_probing(monkeypatch):
    dom_variants = [ImportVariantOption(id="1", label="No Uber")]
    probed_variants = [
        ImportVariantOption(id="0", label="Starter"),
        ImportVariantOption(id="1", label="No Uber"),
        ImportVariantOption(id="2", label="Mythic"),
    ]

    monkeypatch.setattr(d4builds, "_read_variant_options_from_driver", lambda _driver: dom_variants)

    def fake_probe_variant_options_by_url(**_kwargs):
        return probed_variants

    monkeypatch.setattr(
        d4builds,
        "_probe_variant_options_by_url",
        fake_probe_variant_options_by_url,
    )

    assert _load_variant_options(
        driver=object(),
        source_url="https://d4builds.gg/builds/crackling-energy-sorcerer-endgame/?var=1",
    ) == probed_variants


def test_d4builds_probe_variant_options_stops_after_consecutive_misses(monkeypatch):
    probed_ids = []
    known_variants = [ImportVariantOption(id="1", label="No Uber")]

    monkeypatch.setattr(d4builds, "_get_variant_probe_ids", lambda **_kwargs: ["0", "2", "3", "4", "5"])

    def fake_probe_variant_option(*, driver, source_url, variant_id):
        probed_ids.append(variant_id)
        if variant_id == "0":
            return ImportVariantOption(id="0", label="Uber")
        return None

    monkeypatch.setattr(d4builds, "_probe_variant_option", fake_probe_variant_option)

    assert _probe_variant_options_by_url(
        driver=object(),
        source_url="https://d4builds.gg/builds/crackling-energy-sorcerer-endgame/?var=1",
        known_variants=known_variants,
    ) == [
        ImportVariantOption(id="0", label="Uber"),
        ImportVariantOption(id="1", label="No Uber"),
    ]
    assert probed_ids == ["0", "2"]


def test_d4builds_variant_options_use_headless_browser(monkeypatch):
    class DummyDriver:
        def __init__(self):
            self.quit_called = False

        def quit(self):
            self.quit_called = True

    driver = DummyDriver()
    wait_calls = []
    webdriver_calls = []
    expected_options = [ImportVariantOption(id="1", label="No Uber")]

    def fake_setup_webdriver(*, headless=True, uc=False):
        webdriver_calls.append({"headless": headless, "uc": uc})
        return driver

    monkeypatch.setattr(d4builds, "setup_webdriver", fake_setup_webdriver)
    monkeypatch.setattr(d4builds, "WebDriverWait", lambda current_driver, timeout: ("wait", current_driver, timeout))
    monkeypatch.setattr(
        d4builds,
        "_wait_for_d4builds_page",
        lambda driver, source_url, wait: wait_calls.append((driver, source_url, wait)),
    )
    monkeypatch.setattr(d4builds, "_read_variant_options_from_driver", lambda _driver: expected_options)

    result = get_d4builds_variant_options("https://d4builds.gg/builds/golem-necromancer-endgame/?var=1")

    assert result == expected_options
    assert webdriver_calls == [{"headless": True, "uc": False}]
    assert wait_calls == [
        (
            driver,
            "https://d4builds.gg/builds/golem-necromancer-endgame/?var=1",
            ("wait", driver, 10),
        )
    ]
    assert driver.quit_called is True
