import logging

from src.settings import get_settings

LOGGER = logging.getLogger(__name__)


def add_to_profiles(build_name: str) -> None:
    profiles = get_settings().general.profiles
    if build_name in profiles:
        LOGGER.info(f"Profile {build_name} was already an active profile.")
    else:
        profiles.append(build_name)
        get_settings().save_value("general", "profiles", ", ".join(profiles))
        LOGGER.info(f"Added {build_name} to active profiles configuration")
