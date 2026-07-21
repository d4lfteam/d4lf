import typing

if typing.TYPE_CHECKING:
    from pytest_mock import MockerFixture

from src.overlay.widget.ui import _OverlayUI


def test_repack_shows_only_enabled_timer_groups(mocker: MockerFixture):
    overlay = object.__new__(_OverlayUI)
    overlay.orientation = "horizontal"
    overlay.show_wb = True
    overlay.show_legion = False
    overlay.show_ht = False
    overlay.show_gold = True
    overlay.show_gph = True
    overlay.show_total_gold = True
    overlay.show_exp = True
    overlay.show_eph = True
    overlay.show_total_exp = True
    overlay.show_t2l = True
    overlay.show_next_scan = True
    overlay.capture_gold_stats = False
    overlay.capture_exp_stats = False
    overlay._gold_initialized = False
    overlay._exp_initialized = False
    overlay.wb_group = mocker.Mock()
    overlay.legion_group = mocker.Mock()
    overlay.ht_group = mocker.Mock()
    overlay.stats_group = mocker.Mock()
    overlay.exp_group = mocker.Mock()
    overlay.t2l_group = mocker.Mock()

    overlay._repack()

    overlay.wb_group.pack.assert_called_once_with(side="left", padx=2)
    overlay.legion_group.pack.assert_not_called()
    overlay.ht_group.pack.assert_not_called()
