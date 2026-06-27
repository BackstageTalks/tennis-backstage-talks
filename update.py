from welo import WElo
from api import get_recent_matches

w = WElo()

matches = get_recent_matches(tour="ATP", limit=200)

for m in matches:
    winner = m["winner"]
    loser = m["loser"]

    gw_winner = m["winner_games"]
    gw_loser = m["loser_games"]

    winner_sets = m.get("winner_sets", 2)
    loser_sets = m.get("loser_sets", 0)

    surface = m["surface"]
    tournament_level = m.get("tournament_level", "ATP250")

    winner_continent = m.get("winner_continent", "EU")
    loser_continent = m.get("loser_continent", "EU")

    winner_stats = {
        "aces": m.get("aces_winner", 0),
        "double_faults": m.get("double_faults_winner", 0),
        "first_serve_pct": m.get("first_serve_pct_winner", 0),
        "break_points_saved": m.get("break_points_saved_winner", 0),
        "return_games_won": m.get("return_games_won_winner", 0),
        "break_points_converted": m.get("break_points_converted_winner", 0),
        "second_serve_return_pct": m.get("second_serve_return_pct_winner", 0),
        "tiebreak_win_rate": m.get("tiebreak_win_rate_winner", 0),
        "deciding_set_win_rate": m.get("deciding_set_win_rate_winner", 0)
    }

    loser_stats = {
        "aces": m.get("aces_loser", 0),
        "double_faults": m.get("double_faults_loser", 0),
        "first_serve_pct": m.get("first_serve_pct_loser", 0),
        "break_points_saved": m.get("break_points_saved_loser", 0),
        "return_games_won": m.get("return_games_won_loser", 0),
        "break_points_converted": m.get("break_points_converted_loser", 0),
        "second_serve_return_pct": m.get("second_serve_return_pct_loser", 0),
        "tiebreak_win_rate": m.get("tiebreak_win_rate_loser", 0),
        "deciding_set_win_rate": m.get("deciding_set_win_rate_loser", 0)
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
