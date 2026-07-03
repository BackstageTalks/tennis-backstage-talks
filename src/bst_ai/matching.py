import re


def clean_text(value):
    if value is None:
        return ""

    text = str(value)
    text = text.replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def normalize_name(name):
    text = clean_text(name).lower()
    text = re.sub(r"[^a-z0-9]+", "", text)

    return text


def normalize_tour(value):
    text = clean_text(value).lower()

    if text in ["atp", "men", "mens", "male", "m"]:
        return "ATP"

    if text in ["wta", "women", "womens", "female", "f"]:
        return "WTA"

    return None


def surface_key(surface):
    text = clean_text(surface).lower()

    if "hard" in text:
        return "hard"

    if "clay" in text:
        return "clay"

    if "grass" in text:
        return "grass"

    return None
