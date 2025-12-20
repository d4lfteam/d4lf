from typing import TYPE_CHECKING, Any

import pytest
from pydantic import ValidationError

from src.config.models import ProfileModel
from tests.config.data import sigils, uniques

if TYPE_CHECKING:
    from src.config.loader import IniConfigLoader


class TestSigil:
    @pytest.fixture(autouse=True)
    def _setup(self, mock_ini_loader: IniConfigLoader) -> None:
        self.mock_ini_loader = mock_ini_loader

    @staticmethod
    @pytest.mark.parametrize("data", sigils.all_bad_cases)
    def test_all_bad_cases(data: dict[str, Any]) -> None:
        data["name"] = "bad"
        with pytest.raises(ValidationError):
            ProfileModel(**data)

    @staticmethod
    @pytest.mark.parametrize("data", sigils.all_good_cases)
    def test_all_good_cases(data: dict[str, Any]) -> None:
        data["name"] = "good"
        assert ProfileModel(**data)


class TestUnique:
    @pytest.fixture(autouse=True)
    def _setup(self, mock_ini_loader: IniConfigLoader) -> None:
        self.mock_ini_loader = mock_ini_loader

    @staticmethod
    @pytest.mark.parametrize("data", uniques.all_bad_cases)
    def test_all_bad_cases(data: dict[str, Any]) -> None:
        data["name"] = "bad"
        with pytest.raises(ValidationError):
            ProfileModel(**data)

    @staticmethod
    def test_all_good_cases() -> None:
        assert ProfileModel(**uniques.all_good_cases)
