import logging
import pathlib
import time
from typing import TYPE_CHECKING

from src.item.data.item_type import ItemType, is_sigil
from src.item.data.rarity import ItemRarity
from src.item.filter.equipment import FilterEquipmentMixin
from src.item.filter.matching import FilterContext, FilterMatchingMixin
from src.item.filter.special import FilterSpecialMixin
from src.item.models import FilterResult, MatchedFilter
from src.profiles import ProfileDocumentError, ProfileDocumentStore
from src.scripts.common import ASPECT_UPGRADES_LABEL
from src.settings import get_settings

if TYPE_CHECKING:
    from src.item.models import Item
    from src.profiles import (
        DynamicCharmFilterModel,
        DynamicItemFilterModel,
        DynamicSealFilterModel,
        GlobalUniqueModel,
        ParagonPayloadModel,
        SigilFilterModel,
        TributeFilterModel,
    )

LOGGER = logging.getLogger(__name__)


class Filter(FilterSpecialMixin, FilterEquipmentMixin, FilterMatchingMixin, FilterContext):
    affix_filters: dict[str, list[DynamicItemFilterModel]] = {}
    aspect_upgrade_filters: dict[str, list[str]] = {}
    paragon_filters: dict[str, ParagonPayloadModel] = {}
    global_unique_filters: dict[str, list[GlobalUniqueModel]] = {}
    seal_filters: dict[str, list[DynamicSealFilterModel]] = {}
    charm_filters: dict[str, list[DynamicCharmFilterModel]] = {}
    sigil_filters: dict[str, SigilFilterModel] = {}
    tribute_filters: dict[str, TributeFilterModel] = {}

    files_loaded: bool = False
    all_file_paths: list[pathlib.Path] = []
    last_loaded: float | None = None
    last_profile_list: list[str] | None = None

    _initialized: bool = False
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def _did_files_change(self) -> bool:
        if self.last_loaded is None:
            return True
        get_settings().load()
        current_profiles = [p.strip() for p in get_settings().general.profiles if p.strip()]
        if self.last_profile_list != current_profiles:
            LOGGER.info(f"Profile list changed: {self.last_profile_list} → {current_profiles}")
            return True
        return any(pathlib.Path(file_path).stat().st_mtime > self.last_loaded for file_path in self.all_file_paths)

    def load_files(self):
        self.files_loaded = True
        self.affix_filters = {}
        self.aspect_upgrade_filters = {}
        self.paragon_filters = {}
        self.seal_filters = {}
        self.charm_filters = {}
        self.sigil_filters = {}
        self.tribute_filters = {}
        self.global_unique_filters = {}
        profiles = [p.strip() for p in get_settings().general.profiles if p.strip()]
        if not profiles:
            LOGGER.warning(
                "No profiles are currently loaded. Please load a profile via the Importer, Settings, or Edit Profile sections to begin using the tool."
            )
            self.last_loaded = time.time()
            self.last_profile_list = []
            return

        custom_profile_path = get_settings().user_dir / "profiles"
        self.all_file_paths = []
        for profile_str in profiles:
            custom_file_path = custom_profile_path / f"{profile_str}.yaml"
            if custom_file_path.is_file():
                profile_path = custom_file_path
            else:
                LOGGER.error(f"Could not load profile {profile_str}. Checked: {custom_file_path}")
                continue
            self.all_file_paths.append(profile_path)
            try:
                data = ProfileDocumentStore.default().load(profile_path).profile
            except ProfileDocumentError as e:
                LOGGER.error(str(e))
                continue

            info_str = f"Loading profile {profile_str}: "
            sections: list[str] = []
            if data.affixes:
                self.affix_filters[data.name] = data.affixes
                sections.append("Affixes")
            if data.aspect_upgrades:
                self.aspect_upgrade_filters[data.name] = data.aspect_upgrades
                sections.append(ASPECT_UPGRADES_LABEL)
            if data.seals:
                self.seal_filters[data.name] = data.seals
                sections.append("Seals")
            if data.charms:
                self.charm_filters[data.name] = data.charms
                sections.append("Charms")
            if data.sigils and (data.sigils.blacklist or data.sigils.whitelist or data.sigils.rarities):
                self.sigil_filters[data.name] = data.sigils
                sections.append("Sigils")
            if data.tributes is not None:
                self.tribute_filters[data.name] = data.tributes
                sections.append("Tributes")
            if data.global_uniques:
                self.global_unique_filters[data.name] = data.global_uniques
                sections.append("GlobalUniques")
            if data.paragon:
                self.paragon_filters[profile_path.stem] = data.paragon
                sections.append("Paragon")
            LOGGER.info((info_str + " ".join(sections)).rstrip())
            self.last_loaded = time.time()
            self.last_profile_list = get_settings().general.profiles.copy()

    def get_paragon_filters(self) -> dict[str, ParagonPayloadModel]:
        """Return the loaded Paragon payloads, reloading profiles when needed."""
        if not self.files_loaded or self._did_files_change():
            self.load_files()
        return self.paragon_filters

    def should_keep(self, item: Item) -> FilterResult:
        if not self.files_loaded or self._did_files_change():
            self.load_files()
        res = FilterResult(keep=False, matched=[])
        if is_sigil(item.item_type):
            return self._check_sigil(item)
        if item.item_type == ItemType.Tribute:
            return self._check_tribute(item)
        if item.item_type == ItemType.HoradricSeal:
            return self._check_seal_charm_filters(item, self.seal_filters, "Seals", "Mythic Seal")
        if item.item_type == ItemType.Charm:
            return self._check_seal_charm_filters(item, self.charm_filters, "Charms", "Mythic Charm")
        if item.item_type is None or item.power is None:
            return res
        keep_affixes = self._check_affixes(item)
        if keep_affixes.keep:
            return keep_affixes
        if item.rarity == ItemRarity.Legendary:
            res = self._check_aspect_upgrades(item)
        elif item.rarity == ItemRarity.Unique:
            res = self._check_global_unique_filter(item)
        elif item.rarity == ItemRarity.Mythic:  # mythics are always kept
            res = FilterResult(keep=True, matched=[MatchedFilter(profile="Mythics always kept", aspect_match=True)])
        if not res.keep:  # then check for a cosmetic upgrade
            return self._check_cosmetic(item)
        return res
