import logging
from typing import Any, Dict, Optional

from tennisapi_client import TennisApiClient, normalize_winning_odds


logger = logging.getLogger(__name__)


def get_tennisapi_odds(match_id: int) -> Optional[Dict[str, Any]]:
    """
    Primary odds datasource pre tenis.

    Potvrdené zo screenshotu:
    {
        "home": {
            "fractionalValue": "73/100",
            "expected": 58,
            "actual": 53
        },
        "away": {
            "fractionalValue": "11/10",
            "expected": 48,
            "actual": 60
        }
    }
    """
    client = TennisApiClient()

    try:
        payload = client.get_match_winning_odds(match_id)
        normalized = normalize_winning_odds(payload)

        if normalized:
            normalized["match_id"] = match_id
            return normalized

    except Exception as exc:
        logger.warning("TennisApi odds failed. match_id=%s error=%s", match_id, exc)

    return None


def get_the_odds_api_fallback(match: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Sem sa napojí tvoja existujúca The Odds API logika.

    Nechávam to ako bezpečný fallback wrapper, aby tento súbor bol copy-paste safe.
    Ak už máš existujúcu funkciu, vlož ju sem alebo importni pôvodný modul.
    """
    return None


def get_match_odds(
    match: Dict[str, Any],
    prefer_tennisapi: bool = True,
) -> Optional[Dict[str, Any]]:
    """
    Nové poradie podľa nášho rozhodnutia:

    TennisApi
        ↓
    The Odds API
        ↓
    null

    match musí obsahovať minimálne:
    {
        "match_id": 123
    }
    """
    match_id = match.get("match_id") or match.get("event_id") or match.get("id")

    if prefer_tennisapi and match_id:
        odds = get_tennisapi_odds(int(match_id))
        if odds:
            return odds

    fallback = get_the_odds_api_fallback(match)
    if fallback:
        fallback["source"] = fallback.get("source") or "TheOddsAPI"
        return fallback

    if not prefer_tennisapi and match_id:
        odds = get_tennisapi_odds(int(match_id))
        if odds:
            return odds

    return None


def enrich_match_with_odds(match: Dict[str, Any]) -> Dict[str, Any]:
    enriched = dict(match)

    odds = get_match_odds(match)

    if not odds:
        enriched["odds_status"] = "NO_ODDS"
        enriched["odds_source"] = None
        enriched["p1_odds"] = None
        enriched["p2_odds"] = None
        return enriched

    enriched["odds_status"] = "OK"
    enriched["odds_source"] = odds.get("source")

    enriched["p1_odds"] = odds.get("p1_odds") or odds.get("home_odds")
    enriched["p2_odds"] = odds.get("p2_odds") or odds.get("away_odds")

    enriched["home_odds"] = odds.get("home_odds")
    enriched["away_odds"] = odds.get("away_odds")

    enriched["odds_raw"] = odds.get("raw")

    enriched["home_expected"] = odds.get("home_expected")
    enriched["away_expected"] = odds.get("away_expected")
    enriched["home_actual"] = odds.get("home_actual")
    enriched["away_actual"] = odds.get("away_actual")

    return enriched


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    test_match = {
        "match_id": 14232981,
        "player1": "Home Player",
        "player2": "Away Player",
    }

    print(enrich_match_with_odds(test_match))
