import os
import shutil
from pathlib import Path

from src import __version__

EXE_NAME = "d4lf.exe"


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


def copy_additional_resources(release_dir: Path):
    shutil.copy("README.md", release_dir)
    shutil.copy("tts/saapi64.dll", release_dir)
    shutil.copytree("assets", release_dir / "assets")


def create_batch_for_consoleonly(release_dir: Path, exe_name: str):
    batch_file_path = release_dir / "consoleonly.bat"
    with Path(batch_file_path).open("w", encoding="utf-8") as f:
        f.write("@echo off\n")
        f.write('cd /d "%~dp0"\n')
        f.write(f'start "" {exe_name} --consoleonly\n')


def create_batch_for_autoupdater(release_dir: Path, exe_name: str):
    batch_file_path = release_dir / "autoupdater.bat"
    Path(batch_file_path).write_text(f"""@echo off
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
)""", encoding="utf-8")

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
    create_batch_for_consoleonly(release_dir=RELEASE_DIR, exe_name=EXE_NAME)
    create_batch_for_autoupdater(release_dir=RELEASE_DIR, exe_name=EXE_NAME)
    clean_up()
