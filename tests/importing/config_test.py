from src.importing.config import FilenamePart, ImportConfig


def test_import_config_normalizes_filename_parts() -> None:
    config = ImportConfig("url", True, False, False, False, filename_parts=("class",))
    assert config.filename_parts == (FilenamePart.CLASS,)
