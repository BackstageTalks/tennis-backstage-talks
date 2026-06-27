from welo import WElo
from api import get_recent_matches

class PredictionEngine:
    def __init__(self, tour="ATP", limit=500):
        self.tour = tour
        self.limit = limit
        self.welo = WElo()
        self._bootstrap()

    def _bootstrap(self):
        matches = get_recent_matches(tour=self.tour, limit=self.limit)

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

            self.welo.update(
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

    def predict_match(self, player1, player2, surface):
        p1 = self.welo.predict(player1, player2, surface)
        p2 = 1 - p1

        favorite = player1 if p1 >= p2 else player2

        return {
            "match": {
                "player1": {
                    "name": player1,
                    "win_prob": round(p1 * 100, 2)
                },
                "player2": {
                    "name": player2,
                    "win_prob": round(p2 * 100, 2)
                },
                "surface": surface
            },
            "prediction": {
                "favorite": favorite
            }
        }


if __name__ == "__main__":
    engine = PredictionEngine()

    print(engine.predict_match("Nadal", "Djokovic", "Grass"))
    print(engine.predict_match("Ruud", "Alcaraz", "Clay"))
