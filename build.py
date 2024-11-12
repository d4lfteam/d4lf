import os
import shutil
from pathlib import Path

from src import __version__

BENCHMARK_EXE_NAME = "d4lf_benchmark.exe"
EXE_NAME = "d4lf.exe"


def build(release_dir: Path):
    installer_cmd = f"pyinstaller --clean --onefile --distpath {release_dir} --paths src src\\main.py"
    os.system(installer_cmd)
    (release_dir / "main.exe").rename(release_dir / EXE_NAME)


def build_benchmark(release_dir: Path):
    installer_cmd = f'pyinstaller --clean --onefile --distpath {release_dir} --paths src --add-data "benchmarks\\assets;benchmarks\\assets" benchmarks\\imageproc.py'
    os.system(installer_cmd)
    (release_dir / "imageproc.exe").rename(release_dir / BENCHMARK_EXE_NAME)


def clean_up():
    if (build_dir := Path("build")).exists():
        shutil.rmtree(build_dir)
    for p in Path.cwd().glob("*.spec"):
        p.unlink()


def copy_additional_resources(release_dir: Path):
    shutil.copy("README.md", release_dir)
    shutil.copytree("assets", release_dir / "assets")


def create_batch_for_gui(release_dir: Path, exe_name: str):
    batch_file_path = release_dir / "gui.bat"
    with open(batch_file_path, "w") as f:
        f.write("@echo off\n")
        f.write('cd /d "%~dp0"\n')
        f.write(f'{exe_name} --gui\n')
        f.write(f'start "" {exe_name}\n')


if __name__ == "__main__":
    os.chdir(Path(__file__).parent)
    print(f"Building version: {__version__}")
    RELEASE_DIR = Path(f"d4lf_v{__version__}")
    if RELEASE_DIR.exists():
        shutil.rmtree(RELEASE_DIR.absolute())
    RELEASE_DIR.mkdir(exist_ok=True, parents=True)
    clean_up()
    build(release_dir=RELEASE_DIR)
    # build_benchmark(release_dir=RELEASE_DIR)
    copy_additional_resources(RELEASE_DIR)
    create_batch_for_gui(release_dir=RELEASE_DIR, exe_name=EXE_NAME)
    clean_up()
