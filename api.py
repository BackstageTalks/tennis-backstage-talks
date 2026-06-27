import requests
import os

API_KEY = os.getenv("API_SPORTS_KEY")

BASE_URL = "https://v1.tennis.api-sports.io"

headers = {
    "x-apisports-key": API_KEY
}

def get_recent_matches(tour="ATP", limit=200):
    url = f"{BASE_URL}/matches?league={tour}&season=2024"

    r = requests.get(url, headers=headers)
    r.raise_for_status()

    data = r.json()

    matches = []

    for m in data.get("response", [])[:limit]:
        matches.append({
            "winner": m["teams"]["winner"]["name"],
            "loser": m["teams"]["loser"]["name"],

            "winner_games": m["scores"]["winner"]["games"],
            "loser_games": m["scores"]["loser"]["games"],

            "winner_sets": m["scores"]["winner"]["sets"],
            "loser_sets": m["scores"]["loser"]["sets"],

            "surface": m["surface"],
            "tournament_level": m["league"]["name"],

            "winner_continent": m["teams"]["winner"]["country"]["code"],
            "loser_continent": m["teams"]["loser"]["country"]["code"],

            # stats (ak API nemá, dá default)
            "aces_winner": m.get("statistics", {}).get("winner", {}).get("aces", 0),
            "aces_loser": m.get("statistics", {}).get("loser", {}).get("aces", 0),

            "double_faults_winner": m.get("statistics", {}).get("winner", {}).get("double_faults", 0),
            "double_faults_loser": m.get("statistics", {}).get("loser", {}).get("double_faults", 0),

            "first_serve_pct_winner": m.get("statistics", {}).get("winner", {}).get("first_serve_pct", 0),
            "first_serve_pct_loser": m.get("statistics", {}).get("loser", {}).get("first_serve_pct", 0),

            "break_points_saved_winner": m.get("statistics", {}).get("winner", {}).get("break_points_saved", 0),
            "break_points_saved_loser": m.get("statistics", {}).get("loser", {}).get("break_points_saved", 0),

            "return_games_won_winner": m.get("statistics", {}).get("winner", {}).get("return_games_won", 0),
            "return_games_won_loser": m.get("statistics", {}).get("loser", {}).get("return_games_won", 0),

            "break_points_converted_winner": m.get("statistics", {}).get("winner", {}).get("break_points_converted", 0),
            "break_points_converted_loser": m.get("statistics", {}).get("loser", {}).get("break_points_converted", 0),

            "second_serve_return_pct_winner": m.get("statistics", {}).get("winner", {}).get("second_serve_return_pct", 0),
            "second_serve_return_pct_loser": m.get("statistics", {}).get("loser", {}).get("second_serve_return_pct", 0),

            "tiebreak_win_rate_winner": m.get("statistics", {}).get("winner", {}).get("tiebreak_win_rate", 0),
            "tiebreak_win_rate_loser": m.get("statistics", {}).get("loser", {}).get("tiebreak_win_rate", 0),

            "deciding_set_win_rate_winner": m.get("statistics", {}).get("winner", {}).get("deciding_set_win_rate", 0),
            "deciding_set_win_rate_loser": m.get("statistics", {}).get("loser", {}).get("deciding_set_win_rate", 0),
        })

    return matches
