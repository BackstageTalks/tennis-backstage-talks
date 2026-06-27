import requests

BASE_URL = "https://sportscore.com/api/widget"

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

            # základné info
            surface = m.get("surface", "Unknown")
            tournament_level = m.get("competition", "ATP")

            # skóre
            winner_games = int(m.get("home_score", 0)) if m.get("home_score") else 0
            loser_games = int(m.get("away_score", 0)) if m.get("away_score") else 0

            # sets (SportScore nemusí mať sets → nastavíme 0)
            winner_sets = 0
            loser_sets = 0

            # kontinenty (SportScore nevracia → default EU)
            winner_continent = "EU"
            loser_continent = "EU"

            # štatistiky (SportScore nevracia → default 0)
            winner_stats = {
                "aces": 0,
                "double_faults": 0,
                "first_serve_pct": 0,
                "break_points_saved": 0,
                "return_games_won": 0,
                "break_points_converted": 0,
                "second_serve_return_pct": 0,
                "tiebreak_win_rate": 0,
                "deciding_set_win_rate": 0
            }

            loser_stats = {
                "aces": 0,
                "double_faults": 0,
                "first_serve_pct": 0,
                "break_points_saved": 0,
                "return_games_won": 0,
                "break_points_converted": 0,
                "second_serve_return_pct": 0,
                "tiebreak_win_rate": 0,
                "deciding_set_win_rate": 0
            }

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
