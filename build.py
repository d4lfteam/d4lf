import os
import shutil
from pathlib import Path

from src import __version__

EXE_BASENAME = "D4LF"  # PyInstaller --name
EXE_NAME = f"{EXE_BASENAME}.exe"


def clean_up():
    build_dir = Path("build")
    if build_dir.exists():
        shutil.rmtree(build_dir)

    for p in Path.cwd().glob("*.spec"):
        p.unlink()


def build(release_dir: Path):
    Path(release_dir).mkdir(exist_ok=True, parents=True)

    icon_path = Path("assets/logo.ico")

    cmd = (
        "pyinstaller "
        "--clean "
        "--noconfirm "
        "--windowed "
        f"--name {EXE_BASENAME} "
        f"--distpath {release_dir} "
        "--workpath build "
        "--paths src "
        f"--icon {icon_path} "
        '--add-data "assets;assets" '
        '--add-data "tts/saapi64.dll;tts" '
        "--exclude-module PyQt6.QtWebEngineWidgets "
        "--exclude-module PyQt6.QtWebEngineCore "
        "--exclude-module PyQt6.QtWebEngine "
        "--exclude-module PyQt6.QtQml "
        "--exclude-module PyQt6.QtQuick "
        "--exclude-module PyQt6.QtMultimedia "
        "--exclude-module PyQt6.QtSensors "
        "--exclude-module PyQt6.QtLocation "
        "--exclude-module PyQt6.QtSerialPort "
        "--exclude-module PyQt6.QtSql "
        "--exclude-module PyQt6.QtTest "
        "--exclude-module PyQt6.QtXml "
        "--exclude-module PyQt6.QtHelp "
        "--exclude-module PyQt6.QtDesigner "
        "src/main.py"
    )

    os.system(cmd)


def create_consoleonly_batch(release_dir: Path):
    batch_file = release_dir / "consoleonly.bat"
    batch_file.write_text(f'@echo off\ncd /d "%~dp0"\nstart "" {EXE_NAME} --consoleonly\n', encoding="utf-8")


def create_autoupdater_batch(release_dir: Path):
    batch_file = release_dir / "autoupdater.bat"
    batch_file.write_text(
        """
@echo off
cd /d "%~dp0"
echo Starting D4LF auto update preprocessing
start /WAIT D4LF.exe --autoupdate
if %errorlevel% == 1 (
    echo Process did not complete successfully, check logs for more information.
) else if %errorlevel% == 2 (
    echo D4LF is already up to date!
) else (
    echo Killing all existing d4lf processes to perform update
    taskkill /f /im D4LF.exe
    timeout /t 1 /nobreak
    echo Updating files
    robocopy "./temp_update/d4lf" "." /E /XF "autoupdater.bat"
    echo Running postprocessing to verify update and clean up files
    start /WAIT D4LF.exe --autoupdatepost
)
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    os.chdir(Path(__file__).parent)

    print(f"Building version: {__version__}")

    release_dir = Path("d4lf")
    if release_dir.exists():
        shutil.rmtree(release_dir)
    release_dir.mkdir(parents=True, exist_ok=True)

    clean_up()
    build(release_dir)
    create_consoleonly_batch(release_dir)
    create_autoupdater_batch(release_dir)
    clean_up()
