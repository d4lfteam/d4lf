def correct_name(name: str) -> str | None:
    if name:
        return name.lower().replace("'", "").replace(" ", "_").replace(",", "").replace("(", "").replace(")", "")
    return name
