import os
import json
import requests

EVENT_ID = 16486813
HOST = "allsportsapi2.p.rapidapi.com"
URL = f"https://{HOST}/api/tennis/event/{EVENT_ID}/provider/1/winning-odds"


def fractional_to_decimal(value):
    if not value or not isinstance(value, str):
        return None
    value = value.strip()
    try:
        if "/" in value:
            left, right = value.split("/", 1)
            denominator = float(right)
            if denominator == 0:
                return None
            return round(1.0 + float(left) / denominator, 4)
        return round(float(value), 4)
    except Exception:
        return None


def main():
    api_key = os.getenv("RAPIDAPI_KEY", "").strip()
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": HOST,
        "Content-Type": "application/json",
    }

    print("RAPIDAPI_KEY:", "SET" if api_key else "MISSING")
    print("DEBUG ALL SPORTS EVENT:", EVENT_ID)
    print("url:", URL)

    if not api_key:
        print("ERROR: RAPIDAPI_KEY environment variable is missing.")
        return

    try:
        response = requests.get(URL, headers=headers, timeout=30)
        print("status:", response.status_code)
        print("body preview:", response.text[:2000])

        try:
            payload = response.json()
        except Exception as exc:
            print("json parse error:", repr(exc))
            return

        print("top_level_keys:", list(payload.keys()) if isinstance(payload, dict) else type(payload).__name__)

        if not isinstance(payload, dict):
            print("NORMALIZED_NONE")
            return

        home = payload.get("home") or {}
        away = payload.get("away") or {}

        home_fractional = home.get("fractionalValue") if isinstance(home, dict) else None
        away_fractional = away.get("fractionalValue") if isinstance(away, dict) else None

        home_decimal = fractional_to_decimal(home_fractional)
        away_decimal = fractional_to_decimal(away_fractional)

        print("home_fractional:", home_fractional)
        print("away_fractional:", away_fractional)
        print("home_decimal:", home_decimal)
        print("away_decimal:", away_decimal)

        if home_decimal and away_decimal:
            normalized = {
                "event_id": EVENT_ID,
                "odds_source": "all_sports_api",
                "odds_provider": "provider_1",
                "odds_player1": home_decimal,
                "odds_player2": away_decimal,
                "raw_home": home,
                "raw_away": away,
            }
            print("NORMALIZED_OK:", json.dumps(normalized, ensure_ascii=False))
        else:
            print("NORMALIZED_NONE")

    except Exception as exc:
        print("ERROR:", repr(exc))


if __name__ == "__main__":
    main()
