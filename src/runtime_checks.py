from __future__ import annotations

import logging
import subprocess
from pathlib import Path

import psutil

from src.bootstrap import resolve_local_prefs_file
from src.config.loader import IniConfigLoader
from src.config.models import VisionModeType
from src.scripts.common import SETUP_INSTRUCTIONS_URL

LOGGER = logging.getLogger(__name__)


def get_d4_local_prefs_file() -> Path | None:
    return resolve_local_prefs_file(Path.home())


def check_for_proper_tts_configuration() -> None:
    d4_process_found = False
    tts_dll = None
    for proc in psutil.process_iter(["name", "exe"]):
        if proc.name().lower() == "diablo iv.exe":
            d4_dir = Path(proc.exe()).parent
            tts_dll = d4_dir / "saapi64.dll"
            if not tts_dll.exists():
                LOGGER.warning(
                    "TTS DLL was not found in %s. Have you followed the instructions in %s?",
                    d4_dir,
                    SETUP_INSTRUCTIONS_URL,
                )
            else:
                LOGGER.debug("TTS DLL found at %s", tts_dll)
            d4_process_found = True
            break

    if tts_dll and tts_dll.exists():
        try:
            powershell_cmd = ["powershell", "-Command", f"(Get-AuthenticodeSignature '{tts_dll}').Status"]
            result = subprocess.run(powershell_cmd, capture_output=True, text=True, check=True)
            status = result.stdout.strip()
            if status == "Valid":
                LOGGER.debug("%s is locally signed and valid.", tts_dll)
            else:
                LOGGER.error(
                    "As of season 12, the saapi64.dll must be locally signed. Follow all instructions in %s to get the dll signed (specifically, run install_dll.bat). It currently has a status of %s",
                    SETUP_INSTRUCTIONS_URL,
                    status,
                )
        except subprocess.CalledProcessError as e:
            LOGGER.error("Error checking saapi64.dll signature: %s", e)

    if not d4_process_found:
        LOGGER.warning(
            "No process named Diablo IV.exe was found and unable to automatically determine if TTS DLL is installed."
        )

    if IniConfigLoader().advanced_options.disable_tts_warning:
        LOGGER.debug("Disable TTS warning is enabled, skipping TTS local prefs check")
        return

    local_prefs = get_d4_local_prefs_file()
    if local_prefs:
        with Path(local_prefs).open(encoding="utf-8") as file:
            prefs = file.read()
            if 'UseScreenReader "1"' not in prefs:
                LOGGER.error(
                    "Use Screen Reader is not enabled in Accessibility Settings in D4. No items will be read. Read more about initial setup here: %s",
                    SETUP_INSTRUCTIONS_URL,
                )
            if 'UseThirdPartyReader "1"' not in prefs:
                LOGGER.error(
                    "3rd Party Screen Reader is not enabled in Accessibility Settings in D4. No items will be read. Read more about initial setup here: %s",
                    SETUP_INSTRUCTIONS_URL,
                )
            if 'FontScale "2"' in prefs and IniConfigLoader().general.vision_mode_type == VisionModeType.highlight_matches:
                LOGGER.error(
                    "A font scale set to Large is not supported when using the highlight matches vision mode. Change to medium or small in the graphics options, or use the fast vision mode."
                )
    else:
        LOGGER.warning(
            "Unable to find a Diablo 4 local prefs file. Can't automatically check if TTS is configured properly in-game. If d4lf is working without issue for you, you can disable this warning by enabling 'disable_tts_warning' in the Advanced settings."
        )
