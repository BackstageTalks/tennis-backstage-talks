import requests

BASE_URL = "https://sportscore.com/api/widget"

def normalize_surface(surface):
    if not surface or surface == "Unknown":
        return "Hard"
    surface = surface.lower()
    if "clay" in surface:
        return "Clay"
    if "grass" in surface:
        return "Grass"
    if "hard" in surface:
        return "Hard"
    if "carpet" in surface:
        return "Carpet"
    return "Hard"  # fallback

def get_recent_matches(limit=50):
    url = f"{BASE_URL}/matches/?sport=tennis&limit={limit}"
    r = requests.get(url)
    r.raise_for_status()

    data = r.json()
    matches = []

    for m in data.get("matches", []):
        try:
            winner = m["home"]
            loser = m["away"]

            # surface normalization
            surface_raw = m.get("surface", "Unknown")
            surface = normalize_surface(surface_raw)

            tournament_level = m.get("competition", "ATP")

            winner_games = int(m.get("home_score", 0) or 0)
            loser_games = int(m.get("away_score", 0) or 0)

            winner_sets = 0
            loser_sets = 0

            winner_continent = "EU"
            loser_continent = "EU"

            # SportScore does not provide stats → default 0
            winner_stats = {k: 0 for k in [
                "aces", "double_faults", "first_serve_pct", "break_points_saved",
                "return_games_won", "break_points_converted", "second_serve_return_pct",
                "tiebreak_win_rate", "deciding_set_win_rate"
            ]}
            loser_stats = {k: 0 for k in winner_stats}

            matches.append({
                "winner": winner,
                "loser": loser,

                "winner_games": winner_games,
                "loser_games": loser_games,

                "winner_sets": winner_sets,
                "loser_sets": loser_sets,

                "surface": surface,
                "tournament_level": tournament_level,

                "winner_continent": winner_continent,
                "loser_continent": loser_continent,

                "aces_winner": winner_stats["aces"],
                "aces_loser": loser_stats["aces"],

                "double_faults_winner": winner_stats["double_faults"],
                "double_faults_loser": loser_stats["double_faults"],

                "first_serve_pct_winner": winner_stats["first_serve_pct"],
                "first_serve_pct_loser": loser_stats["first_serve_pct"],

                "break_points_saved_winner": winner_stats["break_points_saved"],
                "break_points_saved_loser": loser_stats["break_points_saved"],

                "return_games_won_winner": winner_stats["return_games_won"],
                "return_games_won_loser": loser_stats["return_games_won"],

                "break_points_converted_winner": winner_stats["break_points_converted"],
                "break_points_converted_loser": loser_stats["break_points_converted"],

                "second_serve_return_pct_winner": winner_stats["second_serve_return_pct"],
                "second_serve_return_pct_loser": loser_stats["second_serve_return_pct"],

                "tiebreak_win_rate_winner": winner_stats["tiebreak_win_rate"],
                "tiebreak_win_rate_loser": loser_stats["tiebreak_win_rate"],

                "deciding_set_win_rate_winner": winner_stats["deciding_set_win_rate"],
                "deciding_set_win_rate_loser": loser_stats["deciding_set_win_rate"],
            })

        except Exception:
            continue

    return matches
