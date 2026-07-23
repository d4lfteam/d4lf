import typing

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

from src.overlay.base import Overlay


def test_overlay_builds_canvas_on_shared_ui_thread(monkeypatch, mocker: MockerFixture):
    root = mocker.Mock()
    canvas = mocker.Mock()
    root.winfo_screenheight.return_value = 900
    root.winfo_screenwidth.return_value = 1600
    monkeypatch.setattr("src.overlay.base.get_root", lambda: root)
    monkeypatch.setattr("src.overlay.base.create_overlay_toplevel", lambda _: (root, canvas))
    monkeypatch.setattr("src.overlay.base.call_on_ui_thread", lambda callback: callback())

    overlay = Overlay()

    assert overlay.root is root
    canvas.config.assert_called_once_with(height=900, width=1600)
