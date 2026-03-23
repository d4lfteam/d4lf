import os
import shutil
import urllib.request
import zipfile
from pathlib import Path

from src import __version__

EXE_NAME = "d4lf.exe"
DEFAULT_RELEASE_DIR = Path("d4lf")
WITH_TOOLS_RELEASE_DIR = Path("d4lf-with-tools")
SIGNTOOL_SDK_VERSION = "10.0.28000.1-rtm"
SIGNTOOL_PACKAGE_URL = f"https://www.nuget.org/api/v2/package/Microsoft.Windows.SDK.BuildTools/{SIGNTOOL_SDK_VERSION}"


def build(release_dir: Path):
    installer_cmd = (
        f"pyinstaller --clean --onefile --icon=assets/logo.ico --distpath {release_dir} --paths src src\\main.py"
    )
    os.system(installer_cmd)
    (release_dir / "main.exe").rename(release_dir / EXE_NAME)


def clean_up():
    if (build_dir := Path("build")).exists():
        shutil.rmtree(build_dir)
    for p in Path.cwd().glob("*.spec"):
        p.unlink()


def prepare_bundled_signtool(cache_root: Path) -> Path:
    package_dir = cache_root / "Microsoft.Windows.SDK.BuildTools" / SIGNTOOL_SDK_VERSION
    package_file = package_dir / f"Microsoft.Windows.SDK.BuildTools.{SIGNTOOL_SDK_VERSION}.nupkg"
    extract_dir = package_dir / "sdk"

    package_dir.mkdir(parents=True, exist_ok=True)

    if not package_file.exists():
        print(f"Downloading bundled signtool package from {SIGNTOOL_PACKAGE_URL}")
        urllib.request.urlretrieve(SIGNTOOL_PACKAGE_URL, package_file)

    if not extract_dir.exists():
        print(f"Extracting bundled signtool package to {extract_dir}")
        with zipfile.ZipFile(package_file, "r") as archive:
            archive.extractall(extract_dir)

    return cache_root


def copy_additional_resources(release_dir: Path, include_tools: bool = False):
    (release_dir / "tts").mkdir()
    shutil.copy("README.md", release_dir)
    shutil.copy("tts/saapi64.dll", release_dir / "tts")
    shutil.copytree("assets", release_dir / "assets")
    shutil.copy("tts/install_dll.cmd", release_dir)
    if include_tools:
        tools_dir = prepare_bundled_signtool(Path("build") / "signing-tools-cache")
        shutil.copytree(tools_dir, release_dir / ".tools")


def create_batch_for_consoleonly(release_dir: Path, exe_name: str):
    batch_file_path = release_dir / "d4lf-consoleonly.bat"
    with Path(batch_file_path).open("w", encoding="utf-8") as f:
        f.write("@echo off\n")
        f.write('cd /d "%~dp0"\n')
        f.write(f'start "" {exe_name} --consoleonly\n')


def create_batch_for_autoupdater(release_dir: Path, exe_name: str):
    batch_file_path = release_dir / "autoupdater.bat"
    Path(batch_file_path).write_text(
        f"""@echo off
cd /d "%~dp0"
echo Starting D4LF auto update preprocessing
start /WAIT {exe_name} --autoupdate
if %errorlevel% == 1 (
    echo Process did not complete successfully, check logs for more information.
) else if %errorlevel% == 2 (
    echo D4Lf is already up to date!
) else (
    echo Killing all existing d4lf processes to perform update
    taskkill /f /im d4lf.exe
    timeout /t 1 /nobreak
    echo Updating files
    robocopy "./temp_update/d4lf" "." /MIR /XF "autoupdater.bat" /XD "temp_update" "logs"
    echo Running postprocessing to verify update and clean up files
    start /WAIT {exe_name} --autoupdatepost
)""",
        encoding="utf-8",
    )


def create_batch_for_install_dll(release_dir: Path):
    return


def prepare_release_dir(release_dir: Path):
    if release_dir.exists():
        shutil.rmtree(release_dir.absolute())
    release_dir.mkdir(exist_ok=True, parents=True)


def create_release_variant(release_dir: Path, include_tools: bool = False):
    prepare_release_dir(release_dir)
    build(release_dir=release_dir)
    copy_additional_resources(release_dir, include_tools=include_tools)
    create_batch_for_consoleonly(release_dir=release_dir, exe_name=EXE_NAME)
    create_batch_for_autoupdater(release_dir=release_dir, exe_name=EXE_NAME)
    create_batch_for_install_dll(release_dir=release_dir)


if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    print(f"Building version: {__version__}")
    clean_up()
    create_release_variant(DEFAULT_RELEASE_DIR, include_tools=False)
    create_release_variant(WITH_TOOLS_RELEASE_DIR, include_tools=True)
    clean_up()
