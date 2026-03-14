from typing import TYPE_CHECKING, Any

import pytest
from pydantic import ValidationError

from src.config.models import ItemRarity, ProfileModel, TributeFilterModel
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


class TestTributes:
    @pytest.fixture(autouse=True)
    def _setup(self, mock_ini_loader: IniConfigLoader) -> None:
        self.mock_ini_loader = mock_ini_loader

    @staticmethod
    def test_simple_rules_serialize_to_readme_friendly_yaml_shape() -> None:
        assert TributeFilterModel(name="mystique").model_dump(mode="json") == "tribute_of_mystique"
        assert TributeFilterModel(rarities=[ItemRarity.Unique]).model_dump(mode="json") == "unique"
        assert TributeFilterModel(rarities=[ItemRarity.Legendary, ItemRarity.Unique]).model_dump(mode="json") == [
            "legendary",
            "unique",
        ]


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
