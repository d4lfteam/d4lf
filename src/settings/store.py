from dataclasses import dataclass

from pydantic import BaseModel, ValidationError
from pydantic_core import PydanticUndefined

from src.settings.loader import IniConfigLoader

type CategorySetting = tuple[BaseModel, str, str]
type SectionModel = tuple[BaseModel, str]
type ResetChange = tuple[str, str, object]


@dataclass(frozen=True)
class SetValueResult:
    success: bool
    previous_value: object
    validation_error: str | None


class SettingsStore:
    def __init__(self, loader: IniConfigLoader | None = None) -> None:
        self._loader = loader or IniConfigLoader()

    def models_with_sections(self) -> tuple[SectionModel, ...]:
        return (
            (self._loader.general, "general"),
            (self._loader.char, "char"),
            (self._loader.advanced_options, "advanced_options"),
        )

    def model_for_section(self, section: str) -> BaseModel:
        section_models = {section_name: model for model, section_name in self.models_with_sections()}
        if section not in section_models:
            msg = f"Unknown settings section: {section}"
            raise KeyError(msg)
        return section_models[section]

    def set_value(self, model: BaseModel, section: str, key: str, value: object) -> SetValueResult:
        previous_value = getattr(model, key)
        validated_values = model.model_dump(mode="python")
        validated_values[key] = value
        try:
            type(model)(**validated_values)
        except ValidationError as error:
            return SetValueResult(success=False, previous_value=previous_value, validation_error=str(error))

        self._loader.save_value(section, key, value)
        return SetValueResult(success=True, previous_value=previous_value, validation_error=None)

    def default_value_for(self, model: BaseModel, key: str) -> object:
        field = type(model).model_fields[key]
        if field.default is not PydanticUndefined:
            return field.default
        if field.default_factory is not None:
            return field.default_factory()
        return None

    def reset_category(self, settings: list[CategorySetting]) -> list[ResetChange]:
        reset_changes: list[ResetChange] = []
        for model, section, key in settings:
            reset_changes.append(self.reset_field(model, section, key))
        return reset_changes

    def reset_field(self, model: BaseModel, section: str, key: str) -> ResetChange:
        default_value = self.default_value_for(model, key)
        self._loader.save_value(section, key, default_value)
        return (section, key, default_value)

    def reset_all(self) -> None:
        self._loader.load(clear=True)
