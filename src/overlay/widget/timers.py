import datetime
import threading
import time
import tkinter as tk
from contextlib import suppress

import httpx

from src.automation import is_self_foreground, is_window_foreground
from src.loot import get_filter_colors
from src.overlay.settings import load_settings as load_info_settings
from src.overlay.settings import setting_int as _setting_int
from src.overlay.statistics import SessionStats
from src.overlay.tracking import InventoryExpTracker
from src.overlay.widget.shared import LOGGER, PROGRESS_YELLOW, TEXT, WARNING_ORANGE, OverlayContract


class _OverlayTimers(OverlayContract):
    def _auto_sync(self):
        """Fetch schedule from helltides.com and sync the timer."""
        threading.Thread(target=self._fetch_schedule, daemon=True).start()

    def _fetch_schedule(self):
        try:
            url = "https://helltides.com/api/schedule"
            with httpx.Client(timeout=10) as client:
                response = client.get(url)
                if response.status_code == 200:
                    data = response.json()
                    now = datetime.datetime.now(datetime.UTC)

                    # Process World Bosses
                    best_wb = None
                    for wb in data.get("world_boss", []):
                        dt_str = wb.get("startTime")
                        name = wb.get("boss")
                        if dt_str and name:
                            dt = datetime.datetime.fromisoformat(dt_str)
                            if dt > now and (best_wb is None or dt < best_wb[0]):
                                best_wb = (dt, name)

                    if best_wb:
                        self.synced_wb = best_wb
                        self.wb_reference = best_wb[0]
                        self.next_boss_name = best_wb[1]
                        self._save_settings()
                        LOGGER.info(f"Auto-synced World Boss: {best_wb[1]} at {best_wb[0]}")

                    # Process Legions
                    best_legion = None
                    for legion in data.get("legion", []):
                        dt_str = legion.get("startTime")
                        if dt_str:
                            dt = datetime.datetime.fromisoformat(dt_str)
                            if dt > now and (best_legion is None or dt < best_legion):
                                best_legion = dt
                    if best_legion:
                        self.synced_legion = best_legion
                        LOGGER.info(f"Auto-synced Legion: {best_legion}")

                    # Process Helltides
                    # Find the helltide start time for the current or next cycle.
                    # Current seasons have helltides starting every hour.
                    latest_start = None
                    for ht in data.get("helltide", []):
                        dt_str = ht.get("startTime")
                        if dt_str:
                            dt = datetime.datetime.fromisoformat(dt_str)
                            if dt <= now:
                                if latest_start is None or dt > latest_start:
                                    latest_start = dt
                            elif dt > now and latest_start is None:
                                latest_start = dt
                    if latest_start:
                        self.synced_helltide = latest_start
                        LOGGER.info(f"Auto-synced Helltide: {latest_start}")

                    # Schedule the update on the UI thread to avoid cross-thread GUI errors
                    def _safe_update():
                        if self.winfo_exists():
                            self._update_timers()

                    self.after(0, _safe_update)
        except (httpx.HTTPError, KeyError, RuntimeError, TypeError, ValueError, tk.TclError) as e:
            LOGGER.error(f"Failed to auto-sync from helltides.com: {e}")

    def _update_timers(self):
        if self._closing or not self.winfo_exists():
            return

        # Toggle visibility based on window focus
        is_interacting = self._is_dragging or is_self_foreground()
        if not is_interacting:
            if self._settings_popup and self._settings_popup.winfo_exists() and self._settings_popup.winfo_viewable():
                is_interacting = True
            else:
                for sub in self._open_submenus.values():
                    if sub.winfo_exists() and sub.winfo_viewable():
                        is_interacting = True
                        break

        is_fgrnd = is_window_foreground(self._win_spec) or is_interacting
        now = time.time()
        if is_fgrnd:
            self._last_focus_time = now

        # Hysteresis: Stay visible for 750ms after focus is lost to prevent flashing on release
        should_be_visible = is_fgrnd or (now - self._last_focus_time < 0.75)

        if should_be_visible and self.state() == "withdrawn":
            self.deiconify()
        elif not should_be_visible and self.state() != "withdrawn":
            self.withdraw()

        if not should_be_visible:
            aid = self.after(500, self._update_timers)
            self._after_ids.append(aid)
            return

        now = datetime.datetime.now(datetime.UTC)
        self._flash_toggle = not self._flash_toggle
        colors = get_filter_colors()

        def get_flash_color(seconds, base_color, threshold=300):
            if 0 < seconds < threshold and not self._flash_toggle:
                return TEXT
            if 0 < seconds < threshold:
                return WARNING_ORANGE
            return base_color

        # --- World Boss ---

        # World Boss
        if self.synced_wb and self.synced_wb[0] > now:
            next_wb = self.synced_wb[0]
        else:
            # Fallback to 3.5h interval from reference
            wb_interval = datetime.timedelta(hours=3.5)
            time_since_wb = now - self.wb_reference
            intervals_passed = time_since_wb // wb_interval
            next_wb = self.wb_reference + (intervals_passed + 1) * wb_interval
            if next_wb < now:
                next_wb += wb_interval

        wb_remaining = next_wb - now
        if wb_remaining.total_seconds() < 0:
            self.wb_timer.config(text="ACTIVE")
            self.wb_timer.config(fg=colors.matched)
        else:
            self.wb_timer.config(
                text=str(wb_remaining).split(".")[0], fg=get_flash_color(wb_remaining.total_seconds(), colors.matched)
            )
        # --- Legion ---
        # Legion
        if self.synced_legion and self.synced_legion > now:
            legion_remaining = self.synced_legion - now
        else:
            # Fallback to 25m interval
            legion_interval = datetime.timedelta(minutes=25)
            legion_ref = datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.UTC)
            time_since_legion = now - legion_ref
            legion_passed = time_since_legion // legion_interval
            next_legion = legion_ref + (legion_passed + 1) * legion_interval
            legion_remaining = next_legion - now
        self.legion_timer.config(
            text=str(legion_remaining).split(".")[0],
            fg=get_flash_color(legion_remaining.total_seconds(), colors.matched),
        )

        # --- Helltide ---
        # Helltide
        # Diablo 4 Helltides cycle every hour: 55 minutes active, 5 minutes break.
        ht_ref = self.synced_helltide or now.replace(minute=0, second=0, microsecond=0)
        diff = (now - ht_ref).total_seconds()

        if diff < 0:
            # Synced reference is in the future
            ht_rem = ht_ref - now
            self.ht_timer.config(
                text=str(ht_rem).split(".")[0], fg=get_flash_color(ht_rem.total_seconds(), colors.matched, 60)
            )
        else:
            # Normalized position in the infinite 1-hour cycle
            cycle_pos = diff % 3600
            if cycle_pos < 3300:
                # Active (0-55 mins)
                rem = datetime.timedelta(seconds=int(3300 - cycle_pos))
                self.ht_timer.config(
                    text=str(rem).split(".")[0], fg=get_flash_color(rem.total_seconds(), PROGRESS_YELLOW, 300)
                )
            else:
                # Break / Warning (55-60 mins)
                rem = datetime.timedelta(seconds=int(3600 - cycle_pos))
                self.ht_timer.config(
                    text=str(rem).split(".")[0], fg=get_flash_color(rem.total_seconds(), colors.matched, 60)
                )

        # --- Next Scan Cooldown ---
        with suppress(Exception):
            info_conf = load_info_settings()
            if not info_conf["check_exp_on_inventory_open"]:
                self.next_scan_value_label.config(text="Off")
            elif info_conf["exp_age_before_refresh"] == -1:
                self.next_scan_value_label.config(text="Never")
            elif SessionStats().last_exp is None:
                self.next_scan_value_label.config(text="Ready")
            else:
                remaining = (_setting_int(info_conf, "exp_age_before_refresh", 5) * 60) - (
                    time.time() - InventoryExpTracker().last_hover_time
                )
                if remaining <= 0:
                    self.next_scan_value_label.config(text="Ready")
                else:
                    m, s = divmod(int(remaining), 60)
                    self.next_scan_value_label.config(text=f"{m}m {s}s" if m > 0 else f"{s}s")

        aid = self.after(250, self._update_timers)
        self._after_ids.append(aid)

    def update_stats(
        self,
        gph: int | None = None,
        total_gained: int | None = None,
        eph: int | None = None,
        total_exp: int | None = None,
        t2l: str | None = None,
    ):
        """Update the gold and experience statistics display."""

        def _do_update():
            if self._closing or not self.winfo_exists():
                return
            repack_needed = False
            if gph is not None and self.capture_gold_stats:
                self.gph_value_label.config(text=f"{gph:,}")
                if not self._gold_initialized:
                    self._gold_initialized = True
                    repack_needed = True
            if total_gained is not None and self.capture_gold_stats:
                self.total_gained_value_label.config(text=f"{total_gained:,}")
                if not self._gold_initialized:
                    self._gold_initialized = True
                    repack_needed = True
            if eph is not None and self.capture_exp_stats:
                self.eph_value_label.config(text=f"{eph:,}")
                if not self._exp_initialized:
                    self._exp_initialized = True
                    repack_needed = True
            if total_exp is not None and self.capture_exp_stats:
                self.total_exp_value_label.config(text=f"{total_exp:,}")
                if not self._exp_initialized:
                    self._exp_initialized = True
                    repack_needed = True
            if t2l is not None and self.capture_exp_stats:
                self.t2l_value_label.config(text=t2l)

            if repack_needed:
                self._repack()
                self.update_idletasks()

        if not self._closing:
            aid = self.after(0, _do_update)
            self._after_ids.append(aid)
