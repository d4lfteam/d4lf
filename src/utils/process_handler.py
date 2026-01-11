import ctypes
import logging
import os
import time

import psutil

from src.utils.window import get_window_spec_id

LOGGER = logging.getLogger(__name__)


def kill_thread(thread):
    thread_id = thread.ident
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, ctypes.py_object(SystemExit))
    if res > 1:
        ctypes.pythonapi.PyThreadState_SetAsyncExc(thread_id, 0)
        LOGGER.error("Exception raise failure")


def safe_exit(error_code=0):
    """Shutdown ALL D4LF instances."""
    # Find and terminate all D4LF processes
    current_pid = os.getpid()
    processes_to_kill = []

    try:
        for proc in psutil.process_iter(["pid", "name", "cmdline"]):
            try:
                if not proc.info["cmdline"]:
                    continue

                cmdline_str = " ".join(proc.info["cmdline"])

                # Look for python processes with d4lf or main.py
                if (
                    "python" in proc.info["name"].lower()
                    and ("main.py" in cmdline_str or "d4lf" in cmdline_str.lower())
                    and proc.pid != current_pid
                ):
                    processes_to_kill.append(proc)
            except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
                LOGGER.debug(f"Error accessing process: {e}")
    except Exception as e:
        LOGGER.debug(f"Error iterating processes: {e}")

    # Kill all processes silently
    for proc in processes_to_kill:
        try:
            proc.kill()
            proc.wait(timeout=2)
        except (psutil.NoSuchProcess, psutil.TimeoutExpired, Exception) as e:
            LOGGER.debug(f"Error killing process {proc.pid}: {e}")

    time.sleep(0.3)
    os._exit(error_code)


def set_process_name(name, window_spec):
    try:
        hwnd = get_window_spec_id(window_spec)
        kernel32 = ctypes.WinDLL("kernel32")
        kernel32.SetConsoleTitleW(hwnd, name)
    except Exception:
        LOGGER.exception("Failed to set process name")
