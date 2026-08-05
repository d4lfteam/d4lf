import re

import rapidfuzz
import rapidfuzz.distance.Levenshtein

from src.game_data import GameCatalog


def correct_name(name: str) -> str | None:
    if name:
        return (
            name
            .strip()
            .lower()
            .replace(" (crucible)", "")
            .replace("'", "")
            .replace(" ", "_")
            .replace("\xa0", "_")
            .replace(",", "")
            .replace("(", "")
            .replace(")", "")
        )
    return name


def keep_letters_and_spaces(text: str) -> str:
    return "".join(char for char in text if char.isalpha() or char.isspace()).strip().replace("  ", " ")


def closest_match(target, candidates):
    keys, values = zip(*candidates.items(), strict=False)
    result = rapidfuzz.process.extractOne(
        target, values, scorer=rapidfuzz.distance.Levenshtein.distance, score_cutoff=100
    )
    return keys[values.index(result[0])] if result else None


def closest_to(value, choices):
    return min(choices, key=lambda x: abs(x - value))


def find_number(s: str, idx: int = 0) -> float | None:
    s = remove_text_after_first_keyword(s, GameCatalog().filter_after_keyword)
    s = s.replace(r",", "")  # remove commas because of large numbers having a comma seperator
    matches = re.findall(r"[+-]?(\d+\.\d+|\.\d+|\d+\.?|\d+)\%?", s)
    number = (
        (matches[1] if len(matches) > 1 else None)
        if "up to a 5%" in s
        else matches[idx]
        if matches and len(matches) > idx
        else None
    )
    if number is not None:
        number = re.sub(r"[+%]", "", number)
        return float(number)
    return None


def remove_text_after_first_keyword(text: str, keywords: list[str]) -> str:
    start_pos = None
    for keyword in keywords:
        match = re.search(re.escape(keyword), text)
        if match and (start_pos is None or start_pos > match.start()):
            start_pos = match.start() if start_pos is None or start_pos > match.start() else start_pos
    if start_pos is not None:
        return text[:start_pos]
    return text


def clean_str(s: str) -> str:
    cleaned_str = re.sub(r"(\d)[, ]+(\d)", r"\1\2", s)  # Remove , between numbers (large number seperator)
    cleaned_str = re.sub(r"(\+)?\d+(\.\d+)?%?", "", cleaned_str)  # Remove numbers and trailing % or preceding +
    cleaned_str = cleaned_str.replace("[x]", "")  # Remove all [x]
    cleaned_str = cleaned_str.replace("durability:", "")
    cleaned_str = re.sub(r"[\[\]+\-:%\'#]", "", cleaned_str)  # Remove [ and ] and leftover +, -, %, :, '
    cleaned_str = remove_text_after_first_keyword(cleaned_str, GameCatalog().filter_after_keyword)
    for s in GameCatalog().filter_words:
        cleaned_str = cleaned_str.replace(s, "")
    if "(" in cleaned_str:
        cleaned_str = cleaned_str[: cleaned_str.rfind("(")]
    return " ".join(cleaned_str.split()).strip().lower()  # Remove extra spaces
