import lxml.html

from src.importing import ImportSourceError
from src.importing.d4builds import metadata as d4builds_metadata


def test_d4builds_errors_are_import_source_errors() -> None:
    assert issubclass(d4builds_metadata.D4BuildsError, ImportSourceError)


def test_extract_build_metadata_from_planner_header() -> None:
    data = lxml.html.fromstring("""
        <div class="builder__header">
            <div class="builder__header__title">
                <div class="builder__header__selection builder__header__selection--planner">
                    <h1 class="builder__header__name">
                        <span>Necromancer Build</span>
                        <form class="builder__header__form">
                            <input class="builder__header__input" value="Rob&#39;s Golem Minion Necro (S4) Pit 142+">
                        </form>
                    </h1>
                </div>
            </div>
            <div class="variant__navigation">
                <input class="builder__variant__input" value="Standard Build">
            </div>
        </div>
        <div class="builder__gear">
            <div class="builder__dropdown__wrapper">
                <div class="dropdown">
                    <div class="dropdown__button">Season 4</div>
                </div>
            </div>
        </div>
    """)

    assert d4builds_metadata._extract_build_metadata(data) == (
        "Necromancer",
        "Rob's Golem Minion Necro (S4) Pit 142+",
        "4",
        "Standard Build",
    )


def test_extract_build_metadata_prefers_description_for_guides() -> None:
    data = lxml.html.fromstring("""
        <div class="builder">
          <div class="builder__header">
            <h1 class="builder__header__name">Blessed Shield Paladin Build Guide - Diablo 4</h1>
            <h2 class="builder__header__description">Rob's Cpt. America (S12)</h2>
            <div class="variant__navigation">
                <input class="builder__variant__input" value="Pit Push (Glasscannon)">
            </div>
          </div>
          <div class="builder__gear">
            <div class="builder__dropdown__wrapper">
                <div class="dropdown">
                    <div class="dropdown__button">Season 12</div>
                </div>
            </div>
          </div>
        </div>
    """)

    assert d4builds_metadata._extract_build_metadata(data) == (
        "Paladin",
        "Rob's Cpt. America (S12)",
        "12",
        "Pit Push (Glasscannon)",
    )


def test_extract_d4builds_season_number_from_gear_dropdown() -> None:
    data = lxml.html.fromstring("""
        <div class="builder">
            <div class="builder__gear">
                <div class="builder__dropdown__wrapper">
                    <div class="dropdown">
                        <div class="dropdown__button">Season 12</div>
                    </div>
                </div>
                <div class="builder__gear__items season_12">
                    <div>Gear</div>
                </div>
            </div>
            <div>Active Runes</div>
            <div>Season 10 appears later in the page and should be ignored.</div>
        </div>
    """)

    assert d4builds_metadata._extract_d4builds_season_number(data) == "12"
