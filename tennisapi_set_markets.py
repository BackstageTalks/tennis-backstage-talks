import logging
from typing import Any, Dict, List, Optional, Tuple

from tennisapi_client import TennisApiClient, fractional_to_decimal

logger = logging.getLogger(__name__)

_SET_MARKET_CACHE: Dict[int, Dict[str, Any]] = {}


def safe_float(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def implied_probability(decimal_odds: Optional[float]) -> Optional[float]:
    if not decimal_odds or decimal_odds <= 1:
        return None
    return 1.0 / decimal_odds


def normalize_pair_probability(p1_odds: Optional[float], p2_odds: Optional[float]) -> Tuple[Optional[float], Optional[float]]:
    p1_raw = implied_probability(p1_odds)
    p2_raw = implied_probability(p2_odds)
    if p1_raw is None or p2_raw is None:
        return None, None
    total = p1_raw + p2_raw
    if total <= 0:
        return None, None
    return p1_raw / total, p2_raw / total


def choice_decimal(choice: Dict[str, Any]) -> Optional[float]:
    if not isinstance(choice, dict):
        return None
    for key in ["fractionalValue", "initialFractionalValue"]:
        value = choice.get(key)
        if value:
            decimal = fractional_to_decimal(str(value))
            if decimal and decimal > 1.0:
                return decimal
    for key in ["decimalValue", "value", "price"]:
        value = choice.get(key)
        if value is None:
            continue
        try:
            decimal = float(value)
            if decimal > 1.0:
                return decimal
        except Exception:
            continue
    return None


def market_choices_pair(market: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    choices = market.get("choices")
    if not isinstance(choices, list) or len(choices) < 2:
        return None, None
    return choice_decimal(choices[0]), choice_decimal(choices[1])


def find_over_under(market: Dict[str, Any]) -> Tuple[Optional[float], Optional[float]]:
    choices = market.get("choices")
    if not isinstance(choices, list) or len(choices) < 2:
        return None, None

    over_odds = None
    under_odds = None
    for choice in choices:
        name = str(choice.get("name") or choice.get("choiceName") or "").lower()
        decimal = choice_decimal(choice)
        if "over" in name:
            over_odds = decimal
        elif "under" in name:
            under_odds = decimal

    if over_odds is None or under_odds is None:
        # TennisApi usually returns Over first, Under second for marketId 12.
        over_odds = choice_decimal(choices[0])
        under_odds = choice_decimal(choices[1])

    return over_odds, under_odds


def parse_line(value: Any) -> Optional[float]:
    try:
        if value is None or value == "":
            return None
        return float(str(value).replace(",", "."))
    except Exception:
        return None


def normalize_markets_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("markets"), list):
        return payload["markets"]
    featured = payload.get("featured")
    if isinstance(featured, dict):
        markets = []
        for value in featured.values():
            if isinstance(value, dict):
                markets.append(value)
        return markets
    return []


def parse_set_markets(payload: Dict[str, Any], event_id: Optional[int] = None) -> Dict[str, Any]:
    markets = normalize_markets_payload(payload)
    output: Dict[str, Any] = {
        "event_id": event_id or payload.get("eventId"),
        "match_winner": None,
        "first_set_winner": None,
        "total_games": None,
        "tie_break": None,
        "raw_market_count": len(markets),
    }

    for market in markets:
        if not isinstance(market, dict):
            continue
        market_id = market.get("marketId")
        market_name = str(market.get("marketName") or "").lower()
        market_period = str(market.get("marketPeriod") or "").lower()

        if market_id == 1 or ("full time" in market_name and "match" in market_period):
            p1, p2 = market_choices_pair(market)
            p1_prob, p2_prob = normalize_pair_probability(p1, p2)
            if p1 and p2:
                output["match_winner"] = {
                    "p1_odds": p1,
                    "p2_odds": p2,
                    "p1_probability": p1_prob,
                    "p2_probability": p2_prob,
                    "raw": market,
                }

        elif market_id == 11 or "first set winner" in market_name:
            p1, p2 = market_choices_pair(market)
            p1_prob, p2_prob = normalize_pair_probability(p1, p2)
            if p1 and p2:
                output["first_set_winner"] = {
                    "p1_odds": p1,
                    "p2_odds": p2,
                    "p1_probability": p1_prob,
                    "p2_probability": p2_prob,
                    "raw": market,
                }

        elif market_id == 12 or "total games" in market_name:
            line = parse_line(market.get("choiceGroup"))
            over_odds, under_odds = find_over_under(market)
            over_prob, under_prob = normalize_pair_probability(over_odds, under_odds)
            if line is not None and over_odds and under_odds:
                output["total_games"] = {
                    "line": line,
                    "over_odds": over_odds,
                    "under_odds": under_odds,
                    "over_probability": over_prob,
                    "under_probability": under_prob,
                    "raw": market,
                }

        elif market_id == 13 or "tie break" in market_name:
            yes_odds, no_odds = market_choices_pair(market)
            yes_prob, no_prob = normalize_pair_probability(yes_odds, no_odds)
            if yes_odds and no_odds:
                output["tie_break"] = {
                    "yes_odds": yes_odds,
                    "no_odds": no_odds,
                    "yes_probability": yes_prob,
                    "no_probability": no_prob,
                    "raw": market,
                }

    return output


def get_set_markets(event_id: Optional[int], force_refresh: bool = False) -> Dict[str, Any]:
    if not event_id:
        return {}
    event_id = int(event_id)
    if not force_refresh and event_id in _SET_MARKET_CACHE:
        return _SET_MARKET_CACHE[event_id]

    client = TennisApiClient()
    payload = client.get_all_odds_for_event(event_id) or {}
    parsed = parse_set_markets(payload, event_id=event_id)
    _SET_MARKET_CACHE[event_id] = parsed
    return parsed


if __name__ == "__main__":
    import sys, json
    logging.basicConfig(level=logging.INFO)
    eid = int(sys.argv[1]) if len(sys.argv) > 1 else 14232981
    print(json.dumps(get_set_markets(eid, force_refresh=True), ensure_ascii=False, indent=2))
