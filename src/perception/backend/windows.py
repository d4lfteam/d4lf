import sys
import threading

import pywintypes
import win32file
import win32pipe
import win32security


def _require_message_size(value: object) -> int:
    if not isinstance(value, int):
        message = "Named pipe returned an invalid message size"
        raise TypeError(message)
    return value


def _require_message_bytes(value: object) -> bytes:
    if not isinstance(value, bytes):
        message = "Named pipe returned a non-byte message"
        raise TypeError(message)
    return value


class WindowsTTSBackend:
    @staticmethod
    def _create_named_pipe() -> int:
        return win32pipe.CreateNamedPipe(
            r"\\.\pipe\d4lf",
            win32pipe.PIPE_ACCESS_DUPLEX,
            win32pipe.PIPE_TYPE_MESSAGE | win32pipe.PIPE_READMODE_MESSAGE | win32pipe.PIPE_WAIT,
            1,
            65536,
            65536,
            0,
            win32security.SECURITY_ATTRIBUTES(),
        )

    def create_pipe(self, logger):
        try:
            return self._create_named_pipe()
        except pywintypes.error as error:
            if error.args[0] == 231:
                logger.error("")
                logger.error("=" * 80)
                logger.error("D4LF IS ALREADY RUNNING")
                logger.error("=" * 80)
                logger.error("")
                logger.error("You already have D4LF running in another window.")
                logger.error("Please close your windows and re-launch.")
                logger.error("")
                logger.error("=" * 80)
                sys.exit(1)
            raise

    def read_pipe(self, create_pipe, data_queue, logger, set_connected) -> None:
        while True:
            handle = create_pipe()
            logger.debug("Waiting for TTS client to connect")
            win32pipe.ConnectNamedPipe(handle, None)
            logger.info("TTS client connected")
            set_connected(True)
            while True:
                try:
                    win32file.ReadFile(handle, 0)
                    _, _, message_size = win32pipe.PeekNamedPipe(handle, 0)
                    message_size = _require_message_size(message_size)
                    _, raw_data = win32file.ReadFile(handle, message_size)
                    data = _require_message_bytes(raw_data).decode().replace("\x00", "")
                    if data and "DISCONNECTED" not in data:
                        data_queue.put(data)
                    elif "DISCONNECTED" in data:
                        break
                except Exception:
                    logger.exception("Error while reading data")
            win32file.CloseHandle(handle)
            logger.info("TTS client disconnected")
            set_connected(False)

    def start_connection(self, start_find_item, start_read_pipe, logger) -> None:
        logger.info("Starting TTS listener. Hover over an item or button to perform the TTS connection.")
        threading.Thread(target=start_find_item, daemon=True).start()
        threading.Thread(target=start_read_pipe, daemon=True).start()
