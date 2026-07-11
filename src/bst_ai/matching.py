import re
import unicodedata
from typing import Any, Optional


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\xa0", " ")
    text = unicodedata.normalize("NFKC", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_accents(value: Any) -> str:
    text = clean_text(value)
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def normalize_name(name: Any) -> str:
    """
    Stable player-name key for ELO / Thinq lookup.

    Important examples:
    - "Federico Cinà" -> "federicocina"
    - "Federico Cina" -> "federicocina"
    - "Otto  Virtanen" -> "ottovirtanen"
    - "O. Virtanen" remains "ovirtanen" and can still be handled by alias/fallback logic.
    """
    text = strip_accents(name).lower()
    text = text.replace(".", " ").replace("-", " ").replace("_", " ")
    text = re.sub(r"[^a-z0-9]+", "", text)
    return text


def normalize_name_spaced(name: Any) -> str:
    text = strip_accents(name).lower()
    text = text.replace(".", " ").replace("-", " ").replace("_", " ")
    text = re.sub(r"[^a-z0-9]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def normalize_tour(value: Any) -> Optional[str]:
    text = clean_text(value).lower()
    if text in ["atp", "men", "mens", "male", "m"]:
        return "ATP"
    if text in ["wta", "women", "womens", "female", "f"]:
        return "WTA"
    return None


def surface_key(surface: Any) -> Optional[str]:
    text = clean_text(surface).lower()
    if "hard" in text:
        return "hard"
    if "clay" in text:
        return "clay"
    if "grass" in text:
        return "grass"
    return None
