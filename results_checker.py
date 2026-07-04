import logging
from typing import Any, Dict, Optional

from tennisapi_client import TennisApiClient, normalize_event


logger = logging.getLogger(__name__)


def check_result_with_tennisapi(match_id: int) -> Optional[Dict[str, Any]]:
    client = TennisApiClient()

    try:
        details = client.get_match_details(match_id)
        normalized = normalize_event(details)

        if not normalized.get("match_id"):
            normalized["match_id"] = match_id

        return {
            "source": "TennisApi",
            "match_id": normalized.get("match_id"),
            "status": normalized.get("status"),
            "status_raw": normalized.get("status_raw"),
            "winner_code": normalized.get("winner_code"),
            "winner": normalized.get("winner"),
            "player1": normalized.get("player1"),
            "player2": normalized.get("player2"),
            "home_score_current": normalized.get("home_score_current"),
            "away_score_current": normalized.get("away_score_current"),
            "home_score_period1": normalized.get("home_score_period1"),
            "away_score_period1": normalized.get("away_score_period1"),
            "home_score_period2": normalized.get("home_score_period2"),
            "away_score_period2": normalized.get("away_score_period2"),
            "home_score_period3": normalized.get("home_score_period3"),
            "away_score_period3": normalized.get("away_score_period3"),
            "home_score_period4": normalized.get("home_score_period4"),
            "away_score_period4": normalized.get("away_score_period4"),
            "home_score_period5": normalized.get("home_score_period5"),
            "away_score_period5": normalized.get("away_score_period5"),
            "raw": normalized.get("raw"),
        }

    except Exception as exc:
        logger.warning("TennisApi result check failed. match_id=%s error=%s", match_id, exc)
        return None


def is_finished(result: Dict[str, Any]) -> bool:
    return result.get("status") == "FINISHED"


def get_winner_from_result(result: Dict[str, Any]) -> Optional[str]:
    return result.get("winner")


def normalize_name(name: Optional[str]) -> str:
    if not name:
        return ""
    return (
        str(name)
        .lower()
        .replace(".", "")
        .replace("-", " ")
        .replace("_", " ")
        .strip()
    )


def evaluate_pick_result(match_id: int, picked_player: str) -> Dict[str, Any]:
    result = check_result_with_tennisapi(match_id)

    if not result:
        return {
            "match_id": match_id,
            "status": "NO_RESULT",
            "won": None,
            "winner": None,
            "source": None,
        }

    if not is_finished(result):
        return {
            "match_id": match_id,
            "status": result.get("status"),
            "won": None,
            "winner": result.get("winner"),
            "source": result.get("source"),
            "result": result,
        }

    winner = result.get("winner")

    if not winner:
        return {
            "match_id": match_id,
            "status": "NO_WINNER",
            "won": None,
            "winner": None,
            "source": result.get("source"),
            "result": result,
        }

    won = normalize_name(winner) == normalize_name(picked_player)

    return {
        "match_id": match_id,
        "status": "FINISHED",
        "won": won,
        "winner": winner,
        "picked_player": picked_player,
        "source": result.get("source"),
        "result": result,
    }


def check_stored_pick(pick: Dict[str, Any]) -> Dict[str, Any]:
    match_id = pick.get("match_id") or pick.get("event_id") or pick.get("id")
    picked_player = (
        pick.get("pick")
        or pick.get("selected_player")
        or pick.get("player")
        or pick.get("prediction")
    )

    if not match_id or not picked_player:
        return {
            "status": "INVALID_PICK",
            "won": None,
            "reason": "Missing match_id or picked_player",
            "pick": pick,
        }

    return evaluate_pick_result(match_id=int(match_id), picked_player=str(picked_player))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    test_match_id = 189477
    result = check_result_with_tennisapi(test_match_id)
    print(result)
