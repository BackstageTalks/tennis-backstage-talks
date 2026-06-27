import requests
import csv
from io import StringIO

BASE_URL = "https://raw.githubusercontent.com/JeffSackmann/tennis_atp/master/atp_matches_2022.csv"

def get_recent_matches(limit=200):
    r = requests.get(BASE_URL)
    r.raise_for_status()

    csv_data = r.text
    reader = csv.DictReader(StringIO(csv_data))

    matches = []

    for row in list(reader)[:limit]:
        matches.append({
            "winner": row["winner_name"],
            "loser": row["loser_name"],

            "winner_games": int(row.get("w_games", 0)),
            "loser_games": int(row.get("l_games", 0)),

            "winner_sets": int(row.get("w_sets", 0)),
            "loser_sets": int(row.get("l_sets", 0)),

            "surface": row.get("surface", "Unknown"),
            "tournament_level": row.get("tourney_level", "ATP"),

            "winner_continent": row.get("winner_ioc", "EU"),
            "loser_continent": row.get("loser_ioc", "EU"),

            "aces_winner": int(row.get("w_aces", 0)),
            "aces_loser": int(row.get("l_aces", 0)),

            "double_faults_winner": int(row.get("w_df", 0)),
            "double_faults_loser": int(row.get("l_df", 0)),

            "first_serve_pct_winner": int(row.get("w_1stIn", 0)),
            "first_serve_pct_loser": int(row.get("l_1stIn", 0)),

            "break_points_saved_winner": int(row.get("w_bpSaved", 0)),
            "break_points_saved_loser": int(row.get("l_bpSaved", 0)),

            "return_games_won_winner": int(row.get("w_rgWon", 0)),
            "return_games_won_loser": int(row.get("l_rgWon", 0)),

            "break_points_converted_winner": int(row.get("w_bpWon", 0)),
            "break_points_converted_loser": int(row.get("l_bpWon", 0)),

            "second_serve_return_pct_winner": int(row.get("w_2ndWon", 0)),
            "second_serve_return_pct_loser": int(row.get("l_2ndWon", 0)),

            "tiebreak_win_rate_winner": int(row.get("w_tbWon", 0)),
            "tiebreak_win_rate_loser": int(row.get("l_tbWon", 0)),

            "deciding_set_win_rate_winner": int(row.get("w_decision", 0)),
            "deciding_set_win_rate_loser": int(row.get("l_decision", 0)),
        })

    return matches
