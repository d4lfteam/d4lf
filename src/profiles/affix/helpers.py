from src.game_data import GameCatalog, ItemType


def _item_type_summary(item_types: list[ItemType]) -> str:
    if not item_types:
        return "All item types"
    return ", ".join(item_type.value for item_type in item_types)


def get_set_and_base_for_key(key: str, set_list: list[str]) -> tuple[str | None, str]:
    for set_name in sorted(set_list, key=len, reverse=True):
        prefix = set_name + "_"
        if key.startswith(prefix):
            return set_name, key[len(prefix) :]
    return None, key


def get_affixes_for_set(affix_dict: dict[str, str], set_list: list[str], target_set: str | None) -> dict[str, str]:
    result = {}
    for key, value in affix_dict.items():
        set_name, _ = get_set_and_base_for_key(key, set_list)
        if set_name == target_set:
            if set_name:
                prefix = set_name.replace("_", " ") + " "
                result[key] = value.removeprefix(prefix)
            else:
                result[key] = value
    return result


def affix_dict_for_widget(widget) -> dict[str, str]:
    current = widget
    while current:
        config = getattr(current, "config", None)
        if config.__class__.__name__ == "SealFilterModel":
            return GameCatalog().seal_affix_dict
        if config.__class__.__name__ == "CharmFilterModel":
            return GameCatalog().charm_affix_dict
        current = current.parent()
    return GameCatalog().affix_dict
