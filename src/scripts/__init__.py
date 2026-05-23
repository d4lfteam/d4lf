def correct_name(name: str) -> str | None:
    if name:
        return (
            name
            .strip()
            .replace(" (CRUCIBLE)", "")  # S12 Crucible items are identical to regular uniques
            .lower()
            .replace("'", "")
            .replace(" ", "_")
            .replace("\xa0", "_")
            .replace("\u00a0", "_")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
        )
    return name
