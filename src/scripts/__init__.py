def correct_name(name: str) -> str | None:
    if name:
        name = name.strip().lower()
        from src.dataloader import Dataloader  # noqa: PLC0415

        for err, corr in Dataloader().error_map.items():
            name = name.replace(err, corr)

        return (
            name
            .replace(" (crucible)", "")  # S12 Crucible items are identical to regular uniques
            .replace("'", "")
            .replace(" ", "_")
            .replace("\xa0", "_")
            .replace("\u00a0", "_")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
        )
    return name
