import datetime
import json
import os
from typing import List, Dict, Any

from api import (
    get_matches,
    get_match_detail,
    get_match_h2h,
    get_match_odds,
    get_rankings
)
from config import TARGET_CATEGORIES, MAX_MATCHES
from prediction_engine import compute_prediction

def build_rank_map(rankings: List[Dict[str, Any]]) -> Dict[str, int]:
    return {r["player"]["name"]: r["position"] for r in rankings}

def run_daily(date: str | None = None) -> List[Dict[str, Any]]:
    if date is None:
        date = datetime.date.today().isoformat()

    matches = get_matches(date)

    atp = build_rank_map(get_rankings("ATP"))
    wta = build_rank_map(get_rankings("WTA"))
    ranks = {**atp, **wta}

    predictions = []

    for m in matches:
        tournament = m.get("tournament", {})
        circuit = (tournament.get("circuit") or "").upper()

        if circuit not in TARGET_CATEGORIES:
            continue

        match_id = m["id"]

        detail = get_match_detail(match_id)
        h2h = get_match_h2h(match_id)
        odds = get_match_odds(match_id)

        pred = compute_prediction(m, detail, h2h, ranks)
        pred["match_id"] = match_id
        pred["tournament"] = tournament.get("name")
        pred["match_date"] = m.get("match_date")
        pred["odds"] = odds

        predictions.append(pred)

        if MAX_MATCHES and len(predictions) >= MAX_MATCHES:
            break

    os.makedirs("data", exist_ok=True)
    out_path = f"data/predictions_{date}.json"

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(predictions, f, indent=2, ensure_ascii=False)

    return predictions

if __name__ == "__main__":
    run_daily()
