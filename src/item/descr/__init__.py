def keep_letters_and_spaces(text):
    return "".join(char for char in text if char.isalpha() or char.isspace()).strip().replace("  ", " ")
