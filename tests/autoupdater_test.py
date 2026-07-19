import zipfile

from src.autoupdater import D4LFUpdater


def test_normalize_version_adds_prefix_and_preserves_missing_values():
    assert D4LFUpdater.normalize_version(" 1.2.3") == "v1.2.3"
    assert D4LFUpdater.normalize_version("v1.2.3") == "v1.2.3"
    assert D4LFUpdater.normalize_version(None) is None


def test_extract_release_writes_version_and_files(tmp_path):
    archive = tmp_path / "release.zip"
    with zipfile.ZipFile(archive, "w") as release:
        release.writestr("d4lf/readme.txt", "ready")
    updater = D4LFUpdater()
    updater.temp_dir = tmp_path / "temp_update"
    updater.version_file = updater.temp_dir / "version"

    assert updater.extract_release(archive, "v4.5.6")
    assert (updater.temp_dir / "d4lf/readme.txt").read_text() == "ready"
    assert updater.version_file.read_text() == "v4.5.6"


def test_download_file_writes_streamed_content_without_network(monkeypatch, tmp_path):
    class Response:
        headers = {"content-length": "5"}

        def raise_for_status(self):
            return None

        def iter_content(self, chunk_size):
            assert chunk_size == 8192
            return [b"he", b"llo"]

    monkeypatch.setattr("src.autoupdater.requests.get", lambda *_args, **_kwargs: Response())
    target = tmp_path / "download.zip"

    assert D4LFUpdater.download_file("https://example.invalid/release.zip", target)
    assert target.read_bytes() == b"hello"
