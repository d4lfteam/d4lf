import logging
import shutil
import sys
import zipfile
from pathlib import Path

import requests

import src.logger
from src import __version__
from src.config.loader import IniConfigLoader

LOGGER = logging.getLogger(__name__)


# This autoupdater was almost entirely provided by iAmPilcrow
class D4LFUpdater:
    def __init__(self):
        self.repo_owner = "d4lfteam"
        self.repo_name = "d4lf"
        self.api_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/releases/latest"
        self.changes_base_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/compare/"
        self.current_dir = Path.cwd()

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

            LOGGER.info("\nDownload complete!")
            return True
        except requests.exceptions.RequestException as e:
            LOGGER.error(f"\nError downloading file: {e}")
            return False

    def extract_and_update(self, zip_path):
        """Extract zip and move files to current directory"""
        LOGGER.info("Extracting files...")
        temp_dir = self.current_dir / "temp_update"

        try:
            # Create temp directory
            temp_dir.mkdir(exist_ok=True)

            # Extract zip
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            LOGGER.info("Moving files to installation directory...")

            # Check if files are in a subfolder (common with GitHub releases)
            extracted_items = list(temp_dir.iterdir())

            # If there's only one folder, use that as the source
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                source_dir = extracted_items[0]
                LOGGER.info(f"Found subfolder: {source_dir.name}")
            else:
                source_dir = temp_dir

            # Move all files from source to current directory
            for item in source_dir.rglob("*"):
                if item.is_file():
                    relative_path = item.relative_to(source_dir)
                    dest_path = self.current_dir / relative_path

                    # Create parent directories if needed
                    dest_path.parent.mkdir(parents=True, exist_ok=True)

                    # Move and overwrite
                    shutil.copy2(item, dest_path)
                    LOGGER.info(f"Updated: {relative_path}")

            LOGGER.info("Files updated successfully!")
            return True

        except Exception as e:
            LOGGER.error(f"Error during extraction: {e}")
            return False
        finally:
            # Cleanup
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            if zip_path.exists():
                Path(zip_path).unlink()

    def run(self):
        """Main update process"""
        LOGGER.info("=" * 50)
        LOGGER.info("D4LF Auto-Updater")
        LOGGER.info("=" * 50)
        LOGGER.info("")

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
            LOGGER.info("\n✓ You're already on the latest version!")
            return True

        LOGGER.info(f"\n→ Update available: {current_version} → {latest_version}")
        self.print_changes_between_releases(current_version, latest_version)

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

        download_url = zip_asset["browser_download_url"]
        zip_filename = self.current_dir / zip_asset["name"]

        LOGGER.info("")
        # Download
        if not self.download_file(download_url, zip_filename):
            return False

        # Extract and update
        if not self.extract_and_update(zip_filename):
            return False

        LOGGER.info("\n" + "=" * 50)
        LOGGER.info(f"✓ Successfully updated to {latest_version}!")
        LOGGER.info("=" * 50)
        return True


if __name__ == "__main__":
    src.logger.setup(log_level=IniConfigLoader().advanced_options.log_lvl.value)
    updater = D4LFUpdater()
    try:
        success = updater.run()
        input("\nPress Enter to exit...")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        LOGGER.warning("\n\nUpdate cancelled by user.")
        sys.exit(1)
    except Exception as e:
        LOGGER.error(f"\n\nUnexpected error: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)
