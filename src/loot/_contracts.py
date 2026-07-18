"""Contracts shared by loot modes and the application lifecycle."""

from typing import Protocol


class VisionMode(Protocol):
    def start(self) -> None: ...

    def stop(self) -> None: ...

    def running(self) -> bool: ...
