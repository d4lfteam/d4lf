"""Application facade for profile loading and item filtering."""

from dataclasses import replace
from typing import TYPE_CHECKING, ClassVar, Self, cast, override

from src.item.filter.evaluator import FilterEvaluator
from src.item.filter.repository import (
    ProfileLoadFailure,
    ProfileLoadListener,
    ProfileLoadReport,
    ProfileRulesRepository,
)
from src.item.filter.rules import EvaluationSettings, LoadedRules
from src.settings import get_settings

if TYPE_CHECKING:
    from pathlib import Path

    from src.item.models import FilterResult, Item
    from src.profiles import ParagonPayloadModel


class Filter(FilterEvaluator):
    """Singleton facade retaining the historic load-and-evaluate interface."""

    _instance: ClassVar[Self | None] = None

    def __new__(cls) -> Self:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        if getattr(self, "_initialized", False):
            return
        self._repository = ProfileRulesRepository(lambda: get_settings())
        super().__init__(rules=self._repository.rules, evaluation_settings=EvaluationSettings())
        self._initialized = True

    @property
    @override
    def rules(self) -> LoadedRules:
        return self._rules

    @rules.setter
    @override
    def rules(self, value: LoadedRules) -> None:
        self._rules = value
        if hasattr(self, "_repository"):
            self._repository.replace_rules(value)

    @property
    def files_loaded(self) -> bool:
        return self._repository.files_loaded

    @files_loaded.setter
    def files_loaded(self, value: bool) -> None:
        self._repository.files_loaded = value

    @property
    def all_file_paths(self) -> list[Path]:
        return self._repository.all_file_paths

    @all_file_paths.setter
    def all_file_paths(self, value: list[Path]) -> None:
        self.rules = replace(self.rules, all_file_paths=tuple(value))

    @property
    def last_loaded(self) -> float | None:
        return self._repository.last_loaded

    @last_loaded.setter
    def last_loaded(self, value: float | None) -> None:
        self._repository.last_loaded = value

    @property
    def last_profile_list(self) -> list[str] | None:
        return self._repository.last_profile_list

    @last_profile_list.setter
    def last_profile_list(self, value: list[str] | None) -> None:
        self._repository.last_profile_list = value

    @property
    def load_failures(self) -> tuple[str, ...]:
        return self._repository.load_failures

    def _did_files_change(self) -> bool:
        return self._repository.did_files_change()

    @staticmethod
    def _profile_signature(path: Path) -> tuple[int, int] | None:
        return ProfileRulesRepository.profile_signature(path)

    def register_profile_failure_listener(self, listener: ProfileLoadListener) -> None:
        self._repository.register_profile_failure_listener(listener)

    def unregister_profile_failure_listener(self, listener: ProfileLoadListener) -> None:
        self._repository.unregister_profile_failure_listener(listener)

    def load_files(self) -> None:
        self._repository.load_files()
        self._rules = self._repository.rules

    def get_paragon_filters(self) -> dict[str, ParagonPayloadModel]:
        """Return the loaded Paragon payloads, reloading profiles when needed."""
        if not self.files_loaded or self._did_files_change():
            self.load_files()
        return cast("dict[str, ParagonPayloadModel]", self.paragon_filters)

    @override
    def should_keep(self, item: Item) -> FilterResult:
        """Load changed profiles and evaluate an item with one settings snapshot."""
        if not self.files_loaded or self._did_files_change():
            self.load_files()
        self._rules = self._repository.rules
        self.evaluation_settings = EvaluationSettings.from_settings(get_settings())
        return super().should_keep(item)


__all__ = ["Filter", "ProfileLoadFailure", "ProfileLoadReport"]
