import os
import shutil
from pathlib import Path

from src import __version__

EXE_NAME = "d4lf.exe"
ENTRYPOINT = "src/main.py"
ICON_PATH = "assets/logo.ico"


def run_pyinstaller(release_dir: Path):
    # Minimal, stable, predictable PyInstaller call
    cmd = (
        f'pyinstaller '
        f'--clean '
        f'--onedir '
        f'--windowed '
        f'--noconfirm '
        f'--distpath "{release_dir}" '
        f'--paths src '
        f'--icon "{ICON_PATH}" '
        f'"{ENTRYPOINT}"'
    )
    os.system(cmd)


def clean_pyinstaller_artifacts():
    build_dir = Path("build")
    if build_dir.exists():
        shutil.rmtree(build_dir)

    for spec in Path.cwd().glob("*.spec"):
        spec.unlink()


def rename_output_folder_and_exe(release_dir: Path):
    # PyInstaller outputs: release_dir / "main" / "main.exe"
    temp_dir = release_dir / "main"
    temp_exe = temp_dir / "main.exe"

    # Rename EXE
    final_exe = temp_dir / EXE_NAME
    temp_exe.rename(final_exe)

    # Rename folder
    final_dir = release_dir / "d4lf"
    temp_dir.rename(final_dir)

    return final_dir, final_exe


def copy_manual_resources(exe_root: Path):
    # Manual, predictable copying — no PyInstaller magic
    shutil.copy("README.md", exe_root)
    shutil.copy("tts/saapi64.dll", exe_root)

    assets_src = Path("assets")
    assets_dst = exe_root / "assets"
    shutil.copytree(assets_src, assets_dst)


def create_consoleonly_batch(exe_root: Path):
    batch_path = exe_root / "consoleonly.bat"
    batch_path.write_text(
        "@echo off\n"
        "cd /d \"%~dp0\"\n"
        f"start \"\" {EXE_NAME} --consoleonly\n",
        encoding="utf-8"
    )


def create_autoupdater_batch(exe_root: Path):
    batch_path = exe_root / "autoupdater.bat"
    batch_path.write_text(
        f"""
@echo off
cd /d "%~dp0"
echo Starting D4LF auto update preprocessing
start /WAIT {EXE_NAME} --autoupdate
if %errorlevel% == 1 (
    echo Process did not complete successfully, check logs for more information.
) else if %errorlevel% == 2 (
    echo D4LF is already up to date!
) else (
    echo Killing all existing d4lf processes to perform update
    taskkill /f /im d4lf.exe
    timeout /t 1 /nobreak
    echo Updating files
    robocopy "./temp_update/d4lf" "." /E /XF "autoupdater.bat"
    echo Running postprocessing to verify update and clean up files
    start /WAIT {EXE_NAME} --autoupdatepost
)
""",
        encoding="utf-8"
    )


if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    print(f"Building version: {__version__}")

    RELEASE_DIR = Path("d4lf")
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR)
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)

    clean_pyinstaller_artifacts()
    run_pyinstaller(RELEASE_DIR)

    exe_root, exe_path = rename_output_folder_and_exe(RELEASE_DIR)

    copy_manual_resources(exe_root)
    create_consoleonly_batch(exe_root)
    create_autoupdater_batch(exe_root)

    clean_pyinstaller_artifacts()
