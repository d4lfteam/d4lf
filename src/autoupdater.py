import logging
import shutil
import sys
import time
import zipfile
from pathlib import Path

import requests

import src.logger
from src import __version__

LOGGER = logging.getLogger(__name__)


# This autoupdater was almost entirely provided by iAmPilcrow
class D4LFUpdater:
    def __init__(self):
        self.repo_owner = "d4lfteam"
        self.repo_name = "d4lf"
        self.api_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/releases/latest"
        self.changes_base_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/compare/"
        self.current_dir = Path.cwd()
        self.temp_dir = self.current_dir / "temp_update"
        self.version_file = self.temp_dir / "version"

    @staticmethod
    def normalize_version(version):
        """Ensure version has 'v' prefix"""
        if version and not version.startswith("v"):
            return f"v{version.strip()}"
        return version

    def get_latest_release(self, silent=False):
        """Fetch latest release info from GitHub API"""
        if not silent:
            LOGGER.info("Checking for latest release...")
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            LOGGER.error(f"Error fetching release info: {e}")
            return None

    def print_changes_between_releases(self, current_version, latest_version):
        try:
            url = self.changes_base_url + current_version + "..." + latest_version
            response = requests.get(url, timeout=10)
            response.raise_for_status()

            LOGGER.info("Changes since last update:")
            for commit in response.json()["commits"]:
                LOGGER.info(f"- {commit['commit']['message']}")
        except requests.exceptions.RequestException as e:
            LOGGER.error(f"Error fetching changes since last update: {e}")

    @staticmethod
    def download_file(url, filename):
        """Download file with progress indication"""
        LOGGER.info(f"Downloading {filename}...")
        try:
            response = requests.get(url, stream=True, timeout=30)
            response.raise_for_status()

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with Path(filename).open("wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total_size > 0:
                            percent = (downloaded / total_size) * 100
                            print(f"\rProgress: {percent:.1f}%", end="")
                print("\n")

            LOGGER.info("Download complete!")
            return True
        except requests.exceptions.RequestException as e:
            LOGGER.error(f"\nError downloading file: {e}")
            return False

    def extract_release(self, zip_path, latest_version):
        """Extract zip so batch process can copy files"""
        LOGGER.info("Extracting files...")

        try:
            # Extract zip
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(self.temp_dir)

            # Also create an update file with information post processing will need
            # with Path(self.update_file).open("w") as f:
            #     update_data = {"version": latest_version, "zip_path": zip_path}
            #     json.dump(update_data, f)
            Path(self.version_file).write_text(latest_version)

            LOGGER.info("Files extracted successfully!")
            return True
        except Exception as e:
            LOGGER.error(f"Error during extraction: {e}")
            return False

    @staticmethod
    def _get_major_version_number(version: str) -> int:
        return int(version.replace("v", "").split(".")[0])

    def preprocess(self):
        """Main update process. This will:
        - Check if update is needed
        - Download new release
        - Extract files to a temp directory
        Additional updating and cleanup will be handled by the post process
        """
        self._print_header()

        # Get current installed version
        current_version = self.normalize_version(__version__)
        LOGGER.info(f"Current installed version: {current_version}")

        # Get latest release info
        release_data = self.get_latest_release()
        if not release_data:
            LOGGER.warning("Unable to find latest release on github, can't automatically update.")
            return False

        latest_version = self.normalize_version(release_data.get("tag_name"))
        LOGGER.info(f"Latest release tag: {latest_version}")

        # Check if update needed
        if current_version == latest_version:
            LOGGER.info("✓ You're already on the latest version!")
            input("\nPress Enter to exit...")
            sys.exit(2)

        LOGGER.info(f"→ Update available: {current_version} → {latest_version}")
        self.print_changes_between_releases(current_version, latest_version)

        # Check if it's an update to a major version and warn of the consequences
        if self._get_major_version_number(latest_version) > self._get_major_version_number(current_version):
            LOGGER.warning(
                "You are upgrading a major version. This means your existing profiles might no longer work and will need to be reimported or recreated. Do you want to proceed?"
            )
            proceed = input("Enter yes or y to proceed, all other inputs will cancel: ")
            if proceed.lower() not in ["yes", "y"]:
                LOGGER.info("Cancelling update.")
                return False

        # Find the d4lf zip asset
        assets = release_data.get("assets", [])
        zip_asset = None

        for asset in assets:
            if asset["name"].startswith("d4lf_") and asset["name"].endswith(".zip"):
                zip_asset = asset
                break

        if not zip_asset:
            LOGGER.error("Could not find d4lf zip file in release assets.")
            return False

        # Create temp directory
        self.temp_dir.mkdir(exist_ok=True)

        download_url = zip_asset["browser_download_url"]
        zip_filename = self.temp_dir / zip_asset["name"]

        LOGGER.info("")
        # Download
        if not self.download_file(download_url, zip_filename):
            return False

        # Extract the zip
        if not self.extract_release(zip_filename, latest_version):
            return False

        LOGGER.info("=" * 50)
        LOGGER.info("✓ Preprocessing is done, shutting down to allow update to happen. A new window will open shortly.")
        LOGGER.info("=" * 50)
        return True

    def postprocess(self):
        """Post process will handle the cleanup. It will:
        - Delete the temporary files that were extracted
        - Verify the version is truly updated
        """
        self._print_header()
        with self.version_file.open("r") as f:
            updated_to_version = f.read().strip()

        if not updated_to_version:
            LOGGER.error(
                "Pre-processing update data was missing! Try to update manually by downloading the newest D4LF release."
            )
            return False

        current_version = self.normalize_version(__version__)
        if updated_to_version != current_version:
            LOGGER.error(
                f"Current version is {current_version} but we attempted to update to {updated_to_version}. Check logs for errors and update manually."
            )
            return False

        LOGGER.info("Cleaning up temporary files")
        if self.temp_dir.exists():
            shutil.rmtree(self.temp_dir, ignore_errors=True)
        LOGGER.info("Temporary files are removed")

        LOGGER.info("=" * 50)
        LOGGER.info(f"✓ Successfully updated to {updated_to_version}!")
        LOGGER.info("=" * 50)
        return True

    @staticmethod
    def _print_header():
        LOGGER.info("=" * 50)
        LOGGER.info("D4LF Auto-Updater")
        LOGGER.info("=" * 50)
        LOGGER.info("")


def start_auto_update(postprocess=False):
    updater = D4LFUpdater()
    try:
        success = updater.postprocess() if postprocess else updater.preprocess()
        input("\nPress Enter to exit...")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        LOGGER.warning("\n\nUpdate cancelled by user.")
        sys.exit(1)
    except Exception as e:
        LOGGER.error(f"\n\nUnexpected error: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)


def notify_if_update():
    if not _should_check_for_update():
        LOGGER.debug("Still within 4 hours of previous update check, skipping automatic update check.")
        return

    updater = D4LFUpdater()
    current_version = updater.normalize_version(__version__)

    release = updater.get_latest_release(silent=True)
    if not release:
        LOGGER.warning("Unable to find latest release of d4lf on github, skipping check for updates.")
        return

    latest_version = updater.normalize_version(release.get("tag_name"))
    if current_version != latest_version:
        LOGGER.info("=" * 50)
        LOGGER.info(
            f"An update has been detected. Run d4lf_autoupdater.exe to automatically update. Version {current_version} → {latest_version}"
        )
        updater.print_changes_between_releases(current_version=current_version, latest_version=latest_version)
        LOGGER.info("=" * 50)


def _should_check_for_update(check_interval_hours=4):
    """Check if it's time to check for updates based on a cooldown period."""
    check_file = Path.cwd() / "assets" / "last_update"
    current_time = time.time()
    last_check_time = 0

    # Read the last check time from file if it exists
    if Path.exists(check_file):
        with Path(check_file).open("r") as f:
            last_check_time = float(f.read().strip())

    # Calculate elapsed time since last check
    elapsed_time = current_time - last_check_time

    # Check if enough time has passed
    if elapsed_time >= (check_interval_hours * 3600):
        # Update the last check time
        Path(check_file).write_text(str(current_time))
        return True
    return False


# Main is only used for testing as files will not actually be copied
if __name__ == "__main__":
    src.logger.setup(log_level="debug")
    start_auto_update()
    # start_auto_update(postprocess=True)
