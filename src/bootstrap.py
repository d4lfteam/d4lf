from pathlib import Path


def ensure_runtime_dirs(*paths: Path) -> None:
    for path in paths:
        Path(path).mkdir(exist_ok=True, parents=True)


def resolve_local_prefs_file(home: Path) -> Path | None:
    all_potential_files: list[Path] = [
        home / "Documents" / "Diablo IV" / "LocalPrefs.txt",
        home / "OneDrive" / "Documents" / "Diablo IV" / "LocalPrefs.txt",
        home / "OneDrive" / "MyDocuments" / "Diablo IV" / "LocalPrefs.txt",
    ]

    existing_files: list[Path] = [file for file in all_potential_files if file.exists()]

    if len(existing_files) == 0:
        return None

    if len(existing_files) == 1:
        return existing_files[0]

    most_recently_modified_file = existing_files[0]
    for existing_file in existing_files[1:]:
        if existing_file.stat().st_mtime > most_recently_modified_file.stat().st_mtime:
            most_recently_modified_file = existing_file
    return most_recently_modified_file
