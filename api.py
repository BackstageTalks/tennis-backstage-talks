import requests
from datetime import datetime

API_KEY = "BTalks"
BASE_URL = "https://api.sportradar.com/tennis/trial/v2/en"

headers = {
    "Ocp-Apim-Subscription-Key": API_KEY
}

def get_daily_matches(date=None):
    if date is None:
        date = datetime.utcnow().strftime("%Y-%m-%d")

    url = f"{BASE_URL}/schedules/{date}.json"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json().get("sport_events", [])


def get_match_summary(match_id):
    url = f"{BASE_URL}/matches/{match_id}/summary.json"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def get_match_statistics(match_id):
    url = f"{BASE_URL}/matches/{match_id}/statistics.json"
    r = requests.get(url, headers=headers)
    r.raise_for_status()
    return r.json()


def get_recent_matches(limit=50):
    matches = []
    daily = get_daily_matches()

    for event in daily[:limit]:
        match_id = event["id"]

        summary = get_match_summary(match_id)
        stats = get_match_statistics(match_id)

        try:
            winner = summary["sport_event_status"]["winner"]["name"]
            loser = summary["sport_event"]["competitors"][0]["name"] \
                if summary["sport_event"]["competitors"][1]["name"] == winner \
                else summary["sport_event"]["competitors"][1]["name"]
        except:
            continue

        matches.append({
            "winner": winner,
            "loser": loser,

            "winner_games": summary["sport_event_status"]["period_scores"][0]["home_score"],
            "loser_games": summary["sport_event_status"]["period_scores"][0]["away_score"],

            "winner_sets": summary["sport_event_status"]["set_scores"][0]["home_score"],
            "loser_sets": summary["sport_event_status"]["set_scores"][0]["away_score"],

            "surface": summary["sport_event"]["venue"].get("surface", "Unknown"),
            "tournament_level": summary["sport_event"]["tournament"]["name"],

            "winner_continent": summary["sport_event"]["competitors"][0]["country"]["code"],
            "loser_continent": summary["sport_event"]["competitors"][1]["country"]["code"],

            "aces_winner": stats["statistics"]["home"]["aces"],
            "aces_loser": stats["statistics"]["away"]["aces"],

            "double_faults_winner": stats["statistics"]["home"]["double_faults"],
            "double_faults_loser": stats["statistics"]["away"]["double_faults"],

            "first_serve_pct_winner": stats["statistics"]["home"]["first_serve_success"],
            "first_serve_pct_loser": stats["statistics"]["away"]["first_serve_success"],

            "break_points_saved_winner": stats["statistics"]["home"]["break_points_saved"],
            "break_points_saved_loser": stats["statistics"]["away"]["break_points_saved"],

            "return_games_won_winner": stats["statistics"]["home"]["return_games_won"],
            "return_games_won_loser": stats["statistics"]["away"]["return_games_won"],

            "break_points_converted_winner": stats["statistics"]["home"]["break_points_converted"],
            "break_points_converted_loser": stats["statistics"]["away"]["break_points_converted"],

            "second_serve_return_pct_winner": stats["statistics"]["home"]["second_serve_points_won"],
            "second_serve_return_pct_loser": stats["statistics"]["away"]["second_serve_points_won"],

            "tiebreak_win_rate_winner": stats["statistics"]["home"].get("tiebreaks_won", 0),
            "tiebreak_win_rate_loser": stats["statistics"]["away"].get("tiebreaks_won", 0),

            "deciding_set_win_rate_winner": stats["statistics"]["home"].get("deciding_sets_won", 0),
            "deciding_set_win_rate_loser": stats["statistics"]["away"].get("deciding_sets_won", 0),
        })

    return matches
