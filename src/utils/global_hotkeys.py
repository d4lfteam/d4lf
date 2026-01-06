import ctypes
import ctypes.wintypes
from threading import Thread

# WinAPI constants
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Virtual key codes for modifiers
VK_SHIFT = 0x10
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt

_hotkey_callbacks = {}
_hook_proc_pointer = None


class KBDLLHOOKSTRUCT(ctypes.Structure):
    _fields_ = [
        ("vkCode", ctypes.wintypes.DWORD),
        ("scanCode", ctypes.wintypes.DWORD),
        ("flags", ctypes.wintypes.DWORD),
        ("time", ctypes.wintypes.DWORD),
        ("dwExtraInfo", ctypes.wintypes.ULONG),
    ]


def _get_modifiers():
    mods = []

    if user32.GetKeyState(VK_CONTROL) & 0x8000:
        mods.append("ctrl")
    if user32.GetKeyState(VK_SHIFT) & 0x8000:
        mods.append("shift")
    if user32.GetKeyState(VK_MENU) & 0x8000:
        mods.append("alt")

    return mods


def _low_level_keyboard_proc(nCode, wParam, lParam):
    if nCode == 0 and wParam == WM_KEYDOWN:
        kb = ctypes.cast(lParam, ctypes.POINTER(KBDLLHOOKSTRUCT)).contents
        vk = kb.vkCode

        mods = _get_modifiers()

        # Build composite key string
        parts = mods + [f"vk_{vk}"]
        hotkey_str = "+".join(parts)

        callback = _hotkey_callbacks.get(hotkey_str)
        if callback:
            try:
                callback()
            except Exception:
                pass

    return user32.CallNextHookEx(None, nCode, wParam, lParam)


def register_hotkey(hotkey_str, callback):
    """
    hotkey_str example:
        "shift+vk_122"  (Shift+F11)
        "ctrl+shift+vk_122"
        "vk_120"        (F9)
    """
    _hotkey_callbacks[hotkey_str] = callback


def start_hotkey_listener():
    def run():
        global _hook_proc_pointer

        # Force creation of a message queue for this thread
        msg = ctypes.wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), 0, 0, 0, 0)

        HOOKPROC = ctypes.WINFUNCTYPE(
            ctypes.c_int,
            ctypes.c_int,
            ctypes.wintypes.WPARAM,
            ctypes.wintypes.LPARAM,
        )

        _hook_proc_pointer = HOOKPROC(_low_level_keyboard_proc)

        hook = user32.SetWindowsHookExW(
            WH_KEYBOARD_LL,
            _hook_proc_pointer,
            kernel32.GetModuleHandleW(None),
            0,
        )

        if not hook:
            return

        msg = ctypes.wintypes.MSG()
        while True:
            ret = user32.GetMessageW(ctypes.byref(msg), 0, 0, 0)
            if ret == 0:
                break

    Thread(target=run, daemon=True).start()
