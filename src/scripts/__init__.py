def correct_name(name: str) -> str | None:
    if name:
        return (
            name.lower()
            .replace("'", "")
            .replace(" ", "_")
            .replace("\xa0", "_")
            .replace("\u00a0", "_")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
        )
    return name
