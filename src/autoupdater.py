import shutil
import sys
import zipfile
from pathlib import Path

import requests

from src import __version__


# This autoupdater was almost entirely provided by iAmPilcrow
class D4LFUpdater:
    def __init__(self):
        self.repo_owner = "d4lfteam"
        self.repo_name = "d4lf"
        self.api_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}/releases/latest"
        self.init_url = f"https://raw.githubusercontent.com/{self.repo_owner}/{self.repo_name}/main/src/__init__.py"
        self.version_file_name = "version"
        self.current_dir = Path.cwd()

    @staticmethod
    def normalize_version(version):
        """Ensure version has 'v' prefix"""
        if version and not version.startswith("v"):
            return f"v{version.strip()}"
        return version

    def get_current_version(self):
        """Read the currently installed version from local version file"""
        version_path = self.current_dir / "assets" / self.version_file_name
        if version_path.exists():
            try:
                with Path(version_path).open("r") as f:
                    version = f.read()
                    return self.normalize_version(version) if version else None
            except Exception as e:
                print(f"Warning: Could not read version from JSON: {e}")
        return None

    def get_latest_release(self):
        """Fetch latest release info from GitHub API"""
        print("Checking for latest release...")
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error fetching release info: {e}")
            return None

    def download_file(self, url, filename):
        """Download file with progress indication"""
        print(f"Downloading {filename}...")
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

            print("\nDownload complete!")
            return True
        except requests.exceptions.RequestException as e:
            print(f"\nError downloading file: {e}")
            return False

    def extract_and_update(self, zip_path):
        """Extract zip and move files to current directory"""
        print("Extracting files...")
        temp_dir = self.current_dir / "temp_update"

        try:
            # Create temp directory
            temp_dir.mkdir(exist_ok=True)

            # Extract zip
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(temp_dir)

            print("Moving files to installation directory...")

            # Check if files are in a subfolder (common with GitHub releases)
            extracted_items = list(temp_dir.iterdir())

            # If there's only one folder, use that as the source
            if len(extracted_items) == 1 and extracted_items[0].is_dir():
                source_dir = extracted_items[0]
                print(f"Found subfolder: {source_dir.name}")
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
                    print(f"Updated: {relative_path}")

            print("Files updated successfully!")
            return True

        except Exception as e:
            print(f"Error during extraction: {e}")
            return False
        finally:
            # Cleanup
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
            if zip_path.exists():
                Path(zip_path).unlink()

    def run(self):
        """Main update process"""
        print("=" * 50)
        print("D4LF Auto-Updater")
        print("=" * 50)
        print()

        # Get current installed version
        current_version = __version__
        # current_version = self.get_current_version()
        if current_version:
            print(f"Current installed version: {current_version}")
        else:
            print("No version info found (potentially running from source)")

        # Get latest release info
        release_data = self.get_latest_release()
        if not release_data:
            print("Failed to check for updates.")
            return False

        latest_version = self.normalize_version(release_data.get("tag_name"))
        print(f"Latest release tag: {latest_version}")

        # Check if update needed
        if current_version and current_version == latest_version:
            print("\n✓ You're already on the latest version!")
            return True

        if current_version:
            print(f"\n→ Update available: {current_version} → {latest_version}")
        else:
            print(f"\n→ Installing version: {latest_version}")

        # Find the d4lf zip asset
        assets = release_data.get("assets", [])
        zip_asset = None

        for asset in assets:
            if asset["name"].startswith("d4lf_") and asset["name"].endswith(".zip"):
                zip_asset = asset
                break

        if not zip_asset:
            print("Error: Could not find d4lf zip file in release assets.")
            return False

        download_url = zip_asset["browser_download_url"]
        zip_filename = self.current_dir / zip_asset["name"]

        print()
        # Download
        if not self.download_file(download_url, zip_filename):
            return False

        # Extract and update
        if not self.extract_and_update(zip_filename):
            return False

        print("\n" + "=" * 50)
        print(f"✓ Successfully updated to {latest_version}!")
        print("=" * 50)
        return True


if __name__ == "__main__":
    updater = D4LFUpdater()
    try:
        success = updater.run()
        input("\nPress Enter to exit...")
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nUpdate cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\nUnexpected error: {e}")
        input("\nPress Enter to exit...")
        sys.exit(1)
