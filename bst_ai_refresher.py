import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from src.bst_ai.service import build_bst_ai_comparison

PUBLIC_DIR = Path("public")
PICK_HISTORY_DIRS = [Path("data/pick_history/all"), Path("data/pick_history/top5")]

BST_KEYS = [
    "corq_ai_probability",
    "bst_ai_probability",
    "ai_match",
    "ai_gap",
    "ai_signed_gap",
    "ai_lean",
    "ai_direction_match",
    "ai_match_color",
    "bst_ai_status",
    "bst_ai_reason",
    "bst_ai_rating_type",
    "bst_player1_found",
    "bst_player2_found",
]


def load_json(path: Path, default: Any) -> Any:
    try:
        if not path.exists():
            return default
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as exc:
        print("BST REFRESH LOAD ERROR:", path, exc)
        return default


def save_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def normalize_status(value: Any) -> str:
    return str(value or "").upper().strip()


def is_bst_ok(item: Dict[str, Any]) -> bool:
    return normalize_status(item.get("bst_ai_status")) == "OK"


def strip_accents(value: Any) -> str:
    text = str(value or "")
    text = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def cleanup_name(value: Any) -> str:
    text = strip_accents(value)
    text = text.replace(".", " ").replace("-", " ").replace("_", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text


def reversed_name(value: Any) -> str:
    text = cleanup_name(value)
    parts = text.split()
    if len(parts) < 2:
        return text
    return " ".join(parts[::-1])


def infer_tour(item: Dict[str, Any]) -> Optional[str]:
    fields = " ".join(str(item.get(k) or "") for k in ["gender", "category", "tournament", "match"])
    lower = fields.lower()
    if "wta" in lower or "women" in lower or "woman" in lower:
        return "WTA"
    if "atp" in lower or "challenger" in lower or "men" in lower or "man" in lower:
        return "ATP"
    return item.get("gender") or None


def candidate_name_pairs(item: Dict[str, Any]) -> List[Tuple[str, str]]:
    p1 = item.get("player1")
    p2 = item.get("player2")
    match = str(item.get("match") or "")
    if (not p1 or not p2) and " vs " in match:
        left, right = match.split(" vs ", 1)
        p1 = p1 or left.strip()
        p2 = p2 or right.strip()

    pairs = []
    if p1 and p2:
        base = (str(p1), str(p2))
        pairs.append(base)
        pairs.append((cleanup_name(p1), cleanup_name(p2)))
        pairs.append((reversed_name(p1), reversed_name(p2)))
        # Reverse event order as a last attempt; pick remains unchanged.
        pairs.append((str(p2), str(p1)))
        pairs.append((cleanup_name(p2), cleanup_name(p1)))

    # Deduplicate while preserving order.
    seen = set()
    out = []
    for a, b in pairs:
        key = (a.lower(), b.lower())
        if not a or not b or key in seen:
            continue
        seen.add(key)
        out.append((a, b))
    return out


def candidate_tours(item: Dict[str, Any]) -> List[Optional[str]]:
    inferred = infer_tour(item)
    tours = [inferred, item.get("gender"), "WTA", "ATP", None]
    out = []
    seen = set()
    for t in tours:
        key = str(t or "NONE")
        if key in seen:
            continue
        seen.add(key)
        out.append(t)
    return out


def try_refresh_item(item: Dict[str, Any]) -> Tuple[Dict[str, Any], bool]:
    if is_bst_ok(item):
        return item, False

    pick = item.get("pick")
    surface = item.get("surface") or "Hard"
    corq_probability = item.get("corq_ai_probability") or item.get("probability")

    if not pick or corq_probability is None:
        return item, False

    for player1, player2 in candidate_name_pairs(item):
        for tour in candidate_tours(item):
            try:
                result = build_bst_ai_comparison(
                    player1=player1,
                    player2=player2,
                    pick=pick,
                    surface=surface,
                    corq_probability=corq_probability,
                    tour=tour,
                )
            except Exception as exc:
                print("BST REFRESH TRY ERROR:", item.get("match"), player1, player2, tour, exc)
                continue

            if isinstance(result, dict) and normalize_status(result.get("bst_ai_status")) == "OK":
                updated = dict(item)
                for key in BST_KEYS:
                    if key in result:
                        updated[key] = result.get(key)
                updated["bst_ai_refreshed"] = True
                updated["bst_ai_refresh_player1"] = player1
                updated["bst_ai_refresh_player2"] = player2
                updated["bst_ai_refresh_tour"] = tour
                return updated, True

    return item, False


def refresh_list(items: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], int]:
    refreshed = []
    hits = 0
    for item in items:
        if not isinstance(item, dict):
            refreshed.append(item)
            continue
        updated, changed = try_refresh_item(item)
        if changed:
            hits += 1
            print("BST REFRESH HIT:", updated.get("match"), "pick:", updated.get("pick"), "ai_match:", updated.get("ai_match"))
        refreshed.append(updated)
    return refreshed, hits


def refresh_file(path: Path) -> int:
    data = load_json(path, None)
    if data is None:
        return 0

    if isinstance(data, list):
        data, hits = refresh_list(data)
        save_json(path, data)
        return hits

    if isinstance(data, dict):
        total_hits = 0
        for key in ["items", "picks", "matches", "results"]:
            if isinstance(data.get(key), list):
                data[key], hits = refresh_list(data[key])
                total_hits += hits
        if total_hits:
            save_json(path, data)
        return total_hits

    return 0


def prediction_files() -> List[Path]:
    files = []
    files.extend(PUBLIC_DIR.glob("predictions_*.json"))
    files.extend(PUBLIC_DIR.glob("all_predictions_*.json"))
    for directory in PICK_HISTORY_DIRS:
        files.extend(directory.glob("*.json"))
    # newest first, only JSON files
    return sorted(set(files), key=lambda p: str(p), reverse=True)


def main() -> None:
    files = prediction_files()
    total = 0
    for path in files:
        hits = refresh_file(path)
        total += hits
        if hits:
            print("BST REFRESH FILE:", path, "hits:", hits)
    print("BST REFRESH TOTAL HITS:", total)


if __name__ == "__main__":
    main()
