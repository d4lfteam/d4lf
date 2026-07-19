"""Platform TTS backend interface."""

from .core import TTSBackend, load_backend

__all__ = ["TTSBackend", "load_backend"]
