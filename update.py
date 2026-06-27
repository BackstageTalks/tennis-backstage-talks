from welo import WElo
from api import get_recent_matches

w = WElo()

matches = get_recent_matches(limit=500)

for m in matches:
    winner = m["winner"]
    loser = m["loser"]

    gw_winner = m["winner_games"]
    gw_loser = m["loser_games"]

    winner_sets = m["winner_sets"]
    loser_sets = m["loser_sets"]

    surface = m["surface"]
    tournament_level = m["tournament_level"]

    winner_continent = m["winner_continent"]
    loser_continent = m["loser_continent"]

    winner_stats = {
        "aces": m["aces_winner"],
        "double_faults": m["double_faults_winner"],
        "first_serve_pct": m["first_serve_pct_winner"],
        "break_points_saved": m["break_points_saved_winner"],
        "return_games_won": m["return_games_won_winner"],
        "break_points_converted": m["break_points_converted_winner"],
        "second_serve_return_pct": m["second_serve_return_pct_winner"],
        "tiebreak_win_rate": m["tiebreak_win_rate_winner"],
        "deciding_set_win_rate": m["deciding_set_win_rate_winner"]
    }

    loser_stats = {
        "aces": m["aces_loser"],
        "double_faults": m["double_faults_loser"],
        "first_serve_pct": m["first_serve_pct_loser"],
        "break_points_saved": m["break_points_saved_loser"],
        "return_games_won": m["return_games_won_loser"],
        "break_points_converted": m["break_points_converted_loser"],
        "second_serve_return_pct": m["second_serve_return_pct_loser"],
        "tiebreak_win_rate": m["tiebreak_win_rate_loser"],
        "deciding_set_win_rate": m["deciding_set_win_rate_loser"]
    }

    w.update(
        winner,
        loser,
        gw_winner,
        gw_loser,
        surface,
        winner_stats,
        loser_stats,
        tournament_level,
        winner_sets,
        loser_sets,
        winner_continent,
        loser_continent
    )

print("Nadal vs Djokovic (Grass):", w.predict("Nadal", "Djokovic", "Grass"))
print("Ruud vs Alcaraz (Clay):", w.predict("Ruud", "Alcaraz", "Clay"))
