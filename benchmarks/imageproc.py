import dataclasses
import json
import logging
import math
import sys
import timeit
from typing import Any

import cv2
import wmi
from PIL import Image  # noqa #  Note: Somehow needed, otherwise the binary has an issue with tesserocr

import src
import src.logger
from src.cam import Cam
from src.config import BASE_DIR, get_base_dir
from src.item.descr.read_descr import read_descr
from src.item.find_descr import find_descr
from src.ui.char_inventory import CharInventory
from src.ui.chest import Chest

sys.path.insert(0, str(BASE_DIR))

LOGGER = logging.getLogger(__name__)


@dataclasses.dataclass
class Anchor:
    icon_width: int
    start_x: int
    y: int


class BenchHelper:
    def __init__(self, resolution: tuple[int, int], anchor: Anchor):
        self._anchor = anchor
        files = list((get_base_dir(bundled=True) / "benchmarks/assets/imageproc").glob(f"{resolution[1]}*"))
        self._images = {f.stem: cv2.imread(str(f)) for f in files}
        Cam().update_window_pos(0, 0, *resolution)
        self._results = {}

    def run(self):
        for name, image in self._images.items():
            LOGGER.debug(f"Now benchmarking {name}...")
            if any(s in name for s in ["chest", "clear", "inv"]):
                inv = CharInventory()
                self._results[f"{name}_inv_open"] = bench_helper(inv.is_open, image)
                chest = Chest()
                self._results[f"{name}_chest_open"] = bench_helper(chest.is_open, image)
                continue

            anchor = (int(name.split("_")[-1]) * self._anchor.icon_width + self._anchor.start_x, self._anchor.y)
            self._results[f"{name}_find_descr"] = bench_helper(find_descr, image, anchor)
            _, rarity, cropped_descr, _ = find_descr(image, anchor)
            self._results[f"{name}_read_descr"] = bench_helper(read_descr, rarity, cropped_descr)
            # item_descr = read_descr(rarity, cropped_descr)
        return self._results


def bench_func(func, *args):
    start_time = timeit.default_timer()
    func(*args)
    end_time = timeit.default_timer()
    return end_time - start_time


def bench_helper(func, *args):
    # check how long it would take to run the function. aim for 5 seconds (*2 due to overhead). min 10 runs, max 50
    runs = max(min(math.ceil(5 / bench_func(func, *args)), 50), 10)
    return [bench_func(func, *args) for _ in range(runs)]


def get_pc_info():
    result = {}
    w = wmi.WMI()

    i = 1
    for cpu in w.Win32_Processor():
        try:
            key = "cpu"
            if i > 1:
                key = f"cpu_{i}"
            result[key] = {}
            result[key]["name"] = cpu.Name.strip()
            result[key]["cores"] = cpu.NumberOfCores
            result[key]["threads"] = cpu.NumberOfLogicalProcessors
            result[key]["current_clock_speed"] = cpu.CurrentClockSpeed
            result[key]["max_clock_speed"] = cpu.MaxClockSpeed
            LOGGER.info(
                f"CPU: Name: {result[key]['name']}, Cores: {result[key]['cores']}, Threads: {result[key]['threads']}, Current Clock Speed: {result[key]['current_clock_speed']}, Max Clock Speed: {result[key]['max_clock_speed']}"
            )
            i += 1  # noqa SIM113
        except Exception:
            pass

    i = 1
    for gpu in w.Win32_VideoController():
        try:
            key = "gpu"
            if i > 1:
                key = f"gpu_{i}"
            result[key] = {}
            result[key]["name"] = gpu.Name.strip()
            result[key]["vram"] = max(gpu.AdapterRAM / 1024**3, 0) if gpu.AdapterRAM is not None else 0
            LOGGER.info(f"GPU: Name: {result[key]['name']}, VRAM: {result[key]['vram']} GB")
            i += 1
        except Exception:
            pass

    i = 1
    for memory in w.Win32_PhysicalMemory():
        try:
            key = "ram"
            if i > 1:
                key = f"ram_{i}"
            result[key] = {}
            result[key]["manufacturer"] = memory.Manufacturer.strip()
            result[key]["speed"] = memory.Speed
            result[key]["capacity"] = int(memory.Capacity) / 1024**3 if memory.Capacity is not None else 0
            LOGGER.info(
                f"RAM: Manufacturer: {result[key]['manufacturer']}, Speed: {result[key]['speed']}, Capacity: {result[key]['capacity']} GB"
            )
            i += 1
        except Exception:
            pass

    i = 1
    for disk_drive in w.Win32_DiskDrive():
        try:
            key = "drive"
            if i > 1:
                key = f"drive_{i}"
            result[key] = {}
            result[key]["model"] = disk_drive.Model.strip()
            result[key]["size"] = int(disk_drive.Size) / 1024**3 if disk_drive.Size is not None else 0
            LOGGER.info(f"Drive: Model: {result[key]['model']}, Size: {result[key]['size']} GB")
            i += 1
        except Exception:
            pass
    return result


def save_results(results: list[dict[str, Any]], calc: bool = True):
    data = get_pc_info()
    for result in results:
        data.update(result)
        if calc:
            for key, value in result.items():
                if isinstance(value, dict):
                    continue
                res = {
                    "avg": sum(value) / len(value),
                    "max": max(value),
                    "median": sorted(value)[len(value) // 2],
                    "min": min(value),
                }
                LOGGER.info(f"{key}: {res}")
    data["_version"] = src.__version__
    with open(BASE_DIR / "benchmarks.json", "w") as f:
        json.dump(data, f, sort_keys=True, indent=4)


if __name__ == "__main__":
    src.logger.setup(log_level="DEBUG")
    LOGGER.info("Running benchmarks. Might take a few minutes, depending on your system")
    try:
        save_results(
            [
                BenchHelper(resolution=(1920, 1080), anchor=Anchor(icon_width=55, start_x=1240, y=760)).run(),
                BenchHelper(resolution=(2560, 1440), anchor=Anchor(icon_width=70, start_x=1685, y=980)).run(),
                BenchHelper(resolution=(3840, 2160), anchor=Anchor(icon_width=105, start_x=2515, y=1495)).run(),
            ]
        )
    except Exception:
        LOGGER.exception("Unhandled exception")
