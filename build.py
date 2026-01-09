import os
import shutil
from pathlib import Path

from src import __version__

EXE_NAME = "d4lf.exe"


def build(release_dir: Path):
    # Use onedir so the EXE and assets live together
    installer_cmd = f"pyinstaller --clean --onedir --windowed --distpath {release_dir} --paths src src\\main.py"
    os.system(installer_cmd)

    # PyInstaller creates: release_dir / "main" / "main.exe"
    exe_dir = release_dir / "main"
    exe_path = exe_dir / "main.exe"

    # Rename main.exe → d4lf.exe
    exe_path.rename(exe_dir / EXE_NAME)

    # Optionally rename the folder "main" → "d4lf"
    exe_dir.rename(release_dir / "d4lf")


def clean_up():
    if (build_dir := Path("build")).exists():
        shutil.rmtree(build_dir)
    for p in Path.cwd().glob("*.spec"):
        p.unlink()


def copy_additional_resources(release_dir: Path):
    # After renaming, the EXE lives in: release_dir / "d4lf"
    exe_root = release_dir / "d4lf"

    shutil.copy("README.md", exe_root)
    shutil.copy("tts/saapi64.dll", exe_root)
    shutil.copytree("assets", exe_root / "assets")


def create_batch_for_gui(release_dir: Path, exe_name: str):
    exe_root = release_dir / "d4lf"
    batch_file_path = exe_root / "gui.bat"

    with batch_file_path.open("w", encoding="utf-8") as f:
        f.write("@echo off\n")
        f.write('cd /d "%~dp0"\n')
        # Correct argument: --mainwindow
        f.write(f'start "" {exe_name} --mainwindow')


def create_batch_for_autoupdater(release_dir: Path, exe_name: str):
    exe_root = release_dir / "d4lf"
    batch_file_path = exe_root / "autoupdater.bat"

    batch_file_path.write_text(
        f"""
@echo off
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
    robocopy "./temp_update/d4lf" "." /E /XF "autoupdater.bat"
    echo Running postprocessing to verify update and clean up files
    start /WAIT {exe_name} --autoupdatepost
)
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    print(f"Building version: {__version__}")

    RELEASE_DIR = Path("d4lf")
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR.absolute())
    RELEASE_DIR.mkdir(exist_ok=True, parents=True)

    clean_up()
    build(release_dir=RELEASE_DIR)
    copy_additional_resources(RELEASE_DIR)
    create_batch_for_gui(release_dir=RELEASE_DIR, exe_name=EXE_NAME)
    create_batch_for_autoupdater(release_dir=RELEASE_DIR, exe_name=EXE_NAME)
    clean_up()
