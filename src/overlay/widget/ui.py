import tkinter as tk
from contextlib import suppress
from typing import Literal

from src.loot import get_filter_colors
from src.overlay.statistics import SessionStats
from src.overlay.widget.shared import (
    ACCENT,
    CARD_BG,
    HELLTIDE_RED,
    LEGION_BLUE,
    LOGGER,
    TEXT,
    WB_ORANGE,
    OverlayContract,
)
from src.settings import get_settings


class _OverlayUI(OverlayContract):
    def _setup_ui(self):
        self.labels_to_resize = []
        stats = SessionStats()
        colors = get_filter_colors()
        is_colorblind = False
        with suppress(Exception):
            is_colorblind = get_settings().general.colorblind_mode

        self.overlay_frame = tk.Frame(self, bg=CARD_BG, highlightthickness=1, highlightbackground=colors.matched)
        self.overlay_frame.pack(padx=5, pady=5)

        self.wb_group = tk.Frame(self.overlay_frame, bg=CARD_BG)
        lbl_wb = tk.Label(
            self.wb_group,
            text="World Boss:",
            bg=CARD_BG,
            fg=colors.codex_upgrade if is_colorblind else WB_ORANGE,
            font=(self.font_family, self.font_size, "bold"),
        )
        lbl_wb.pack(side="left")
        self.labels_to_resize.append(lbl_wb)
        self.wb_timer = tk.Label(
            self.wb_group, text="--:--:--", bg=CARD_BG, fg=TEXT, font=(self.font_family, self.font_size, "bold")
        )
        self.wb_timer.pack(side="left")
        self.labels_to_resize.append(self.wb_timer)

        self.legion_group = tk.Frame(self.overlay_frame, bg=CARD_BG)
        self.lbl_legion = tk.Label(
            self.legion_group,
            text="Legion:",
            bg=CARD_BG,
            fg=colors.matched if is_colorblind else LEGION_BLUE,
            font=(self.font_family, self.font_size, "bold"),
        )
        self.lbl_legion.pack(side="left")
        self.labels_to_resize.append(self.lbl_legion)
        self.legion_timer = tk.Label(
            self.legion_group, text="--:--:--", bg=CARD_BG, fg=TEXT, font=(self.font_family, self.font_size, "bold")
        )
        self.legion_timer.pack(side="left")
        self.labels_to_resize.append(self.legion_timer)

        self.ht_group = tk.Frame(self.overlay_frame, bg=CARD_BG)
        self.lbl_ht = tk.Label(
            self.ht_group,
            text="Helltide:",
            bg=CARD_BG,
            fg=colors.no_match if is_colorblind else HELLTIDE_RED,
            font=(self.font_family, self.font_size, "bold"),
        )
        self.lbl_ht.pack(side="left")
        self.labels_to_resize.append(self.lbl_ht)
        self.ht_timer = tk.Label(
            self.ht_group, text="--:--:--", bg=CARD_BG, fg=TEXT, font=(self.font_family, self.font_size, "bold")
        )
        self.ht_timer.pack(side="left")
        self.labels_to_resize.append(self.ht_timer)

        self.stats_group = tk.Frame(self.overlay_frame, bg=CARD_BG)
        self.lbl_gph_title = tk.Label(
            self.stats_group,
            text="GPH:",
            bg=CARD_BG,
            fg=colors.matched if is_colorblind else ACCENT,
            font=(self.font_family, self.font_size, "bold"),
        )
        self.lbl_gph_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_gph_title)
        self.gph_value_label = tk.Label(
            self.stats_group,
            text="Pending" if self.capture_gold_stats else "0",
            bg=CARD_BG,
            fg=TEXT,
            font=(self.font_family, self.font_size, "bold"),
        )
        self.gph_value_label.pack(side="left")
        self.labels_to_resize.append(self.gph_value_label)

        self.lbl_total_gained_title = tk.Label(
            self.stats_group,
            text="|Gained:",
            bg=CARD_BG,
            fg=colors.matched if is_colorblind else ACCENT,
            font=(self.font_family, self.font_size, "bold"),
        )
        self.lbl_total_gained_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_total_gained_title)
        self.total_gained_value_label = tk.Label(
            self.stats_group,
            text=f"{stats.total_gold:,}" if self.capture_gold_stats else "0",
            bg=CARD_BG,
            fg=TEXT,
            font=(self.font_family, self.font_size, "bold"),
        )
        self.total_gained_value_label.pack(side="left")
        self.labels_to_resize.append(self.total_gained_value_label)

        self.exp_group = tk.Frame(self.overlay_frame, bg=CARD_BG)
        self.lbl_eph_title = tk.Label(
            self.exp_group,
            text="EPH:",
            bg=CARD_BG,
            fg=colors.matched if is_colorblind else LEGION_BLUE,
            font=(self.font_family, self.font_size, "bold"),
        )
        self.lbl_eph_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_eph_title)
        self.eph_value_label = tk.Label(
            self.exp_group,
            text="Pending" if self.capture_exp_stats else "0",
            bg=CARD_BG,
            fg=TEXT,
            font=(self.font_family, self.font_size, "bold"),
        )
        self.eph_value_label.pack(side="left")
        self.labels_to_resize.append(self.eph_value_label)

        self.lbl_total_exp_title = tk.Label(
            self.exp_group,
            text="|Exp:",
            bg=CARD_BG,
            fg=colors.matched if is_colorblind else LEGION_BLUE,
            font=(self.font_family, self.font_size, "bold"),
        )
        self.lbl_total_exp_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_total_exp_title)
        self.total_exp_value_label = tk.Label(
            self.exp_group,
            text=f"{stats.total_exp:,}" if self.capture_exp_stats else "0",
            bg=CARD_BG,
            fg=TEXT,
            font=(self.font_family, self.font_size, "bold"),
        )
        self.total_exp_value_label.pack(side="left")
        self.labels_to_resize.append(self.total_exp_value_label)

        self.t2l_group = tk.Frame(self.overlay_frame, bg=CARD_BG)
        self.lbl_t2l_title = tk.Label(
            self.t2l_group,
            text="T2L:",
            bg=CARD_BG,
            fg=colors.matched if is_colorblind else LEGION_BLUE,
            font=(self.font_family, self.font_size, "bold"),
        )
        self.lbl_t2l_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_t2l_title)
        self.t2l_value_label = tk.Label(
            self.t2l_group, text="-", bg=CARD_BG, fg=TEXT, font=(self.font_family, self.font_size, "bold")
        )
        self.t2l_value_label.pack(side="left")
        self.labels_to_resize.append(self.t2l_value_label)

        self.lbl_next_scan_title = tk.Label(
            self.t2l_group,
            text="|Next Scan:",
            bg=CARD_BG,
            fg=colors.matched if is_colorblind else LEGION_BLUE,
            font=(self.font_family, self.font_size, "bold"),
        )
        self.lbl_next_scan_title.pack(side="left")
        self.labels_to_resize.append(self.lbl_next_scan_title)
        self.next_scan_value_label = tk.Label(
            self.t2l_group, text="Ready", bg=CARD_BG, fg=TEXT, font=(self.font_family, self.font_size, "bold")
        )
        self.next_scan_value_label.pack(side="left")
        self.labels_to_resize.append(self.next_scan_value_label)

        self._repack()
        self.geometry(f"+{self.x}+{self.y}")

    def _repack(self):
        """Recalculate component packing based on current settings."""
        LOGGER.debug(
            "Repacking overlay. "
            f"show_gold={self.show_gold}, _gold_initialized={self._gold_initialized}, "
            f"show_gph={self.show_gph}, show_total_gold={self.show_total_gold}, "
            f"show_exp={self.show_exp}, _exp_initialized={self._exp_initialized}, "
            f"show_eph={self.show_eph}, show_total_exp={self.show_total_exp}, "
            f"show_t2l={self.show_t2l}, show_next_scan={self.show_next_scan}"
        )
        # Hide everything first
        self.wb_group.pack_forget()
        self.legion_group.pack_forget()
        self.ht_group.pack_forget()
        self.stats_group.pack_forget()
        self.exp_group.pack_forget()
        self.t2l_group.pack_forget()

        side: Literal["top", "left"] = "top" if self.orientation == "vertical" else "left"
        anchor: Literal["w"] | None = "w" if self.orientation == "vertical" else None

        def pack_group(group: tk.Frame) -> None:
            if anchor is None:
                group.pack(side=side, padx=2)
            else:
                group.pack(side=side, anchor=anchor, padx=2)

        if self.show_wb:
            pack_group(self.wb_group)
        if self.show_legion:
            pack_group(self.legion_group)
        if self.show_ht:
            pack_group(self.ht_group)
        if self.capture_gold_stats and (self.show_gph or self.show_total_gold):
            self._repack_gold_group()
            pack_group(self.stats_group)
        if self.capture_exp_stats:
            if self.show_eph or self.show_total_exp:
                self._repack_exp_group()
                pack_group(self.exp_group)
            if self.show_t2l or self.show_next_scan:
                self._repack_t2l_group()
                pack_group(self.t2l_group)

    def _repack_gold_group(self):
        self.lbl_gph_title.pack_forget()
        self.gph_value_label.pack_forget()
        self.lbl_total_gained_title.pack_forget()
        self.total_gained_value_label.pack_forget()
        count = 0
        if self.show_gph:
            self.lbl_gph_title.config(text="GPH:")
            self.lbl_gph_title.pack(side="left")
            self.gph_value_label.config(
                text="Pending" if not self._gold_initialized else self.gph_value_label.cget("text")
            )
            self.gph_value_label.pack(side="left")
            count += 1
        if self.show_total_gold:
            self.lbl_total_gained_title.config(text="|Gained:" if count > 0 else "Gained:")
            self.lbl_total_gained_title.pack(side="left")
            self.total_gained_value_label.config(text=self.total_gained_value_label.cget("text"))
            self.total_gained_value_label.pack(side="left")

    def _repack_exp_group(self):
        self.lbl_eph_title.pack_forget()
        self.eph_value_label.pack_forget()
        self.lbl_total_exp_title.pack_forget()
        self.total_exp_value_label.pack_forget()
        count = 0
        if self.show_eph:
            self.lbl_eph_title.config(text="EPH:")
            self.lbl_eph_title.pack(side="left")
            self.eph_value_label.config(
                text="Pending" if not self._exp_initialized else self.eph_value_label.cget("text")
            )
            self.eph_value_label.pack(side="left")
            count += 1
        if self.show_total_exp:
            self.lbl_total_exp_title.config(text="|Exp:" if count > 0 else "Exp:")
            self.lbl_total_exp_title.pack(side="left")
            self.total_exp_value_label.config(text=self.total_exp_value_label.cget("text"))
            self.total_exp_value_label.pack(side="left")
            count += 1

    def _repack_t2l_group(self):
        self.lbl_t2l_title.pack_forget()
        self.t2l_value_label.pack_forget()
        self.lbl_next_scan_title.pack_forget()
        self.next_scan_value_label.pack_forget()
        count = 0
        if self.show_t2l:
            self.lbl_t2l_title.config(text="T2L:")
            self.lbl_t2l_title.pack(side="left")
            self.t2l_value_label.pack(side="left")
            count += 1
        if self.show_next_scan:
            self.lbl_next_scan_title.config(text="|Next Scan:" if count > 0 else "Next Scan:")
            self.lbl_next_scan_title.pack(side="left")
            self.next_scan_value_label.pack(side="left")
