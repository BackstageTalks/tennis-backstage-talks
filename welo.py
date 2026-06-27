import math

class WElo:
    def __init__(self, k=32):
        self.k = k
        self.overall = {}
        self.surface = {
            "Clay": {},
            "Grass": {},
            "Hard": {},
            "Carpet": {}
        }

        # form index storage
        self.form = {}

        # fatigue storage
        self.fatigue = {}

    def get_rating(self, player, surface=None):
        if surface:
            return self.surface[surface].get(player, 1500)
        return self.overall.get(player, 1500)

    def expected_score(self, rA, rB):
        return 1 / (1 + 10 ** ((rB - rA) / 400))

    def mov_weight(self, games_won, games_lost):
        mov = games_won - games_lost
        mov = max(-6, min(6, mov))
        return 1 + (mov / 6)

    # -------------------------
    # PLAYER STATS ADJUSTMENT
    # -------------------------
    def stats_adjustment(self, stats):
        aces = stats.get("aces", 0)
        double_faults = stats.get("double_faults", 0)
        first_serve_pct = stats.get("first_serve_pct", 0)
        break_points_saved = stats.get("break_points_saved", 0)

        return_games_won = stats.get("return_games_won", 0)
        break_points_converted = stats.get("break_points_converted", 0)
        second_serve_return_pct = stats.get("second_serve_return_pct", 0)

        tiebreak_win_rate = stats.get("tiebreak_win_rate", 0)
        deciding_set_win_rate = stats.get("deciding_set_win_rate", 0)

        SSI = (
            aces * 0.4
            - double_faults * 0.3
            + first_serve_pct * 0.2
            + break_points_saved * 0.1
        )

        RSI = (
            return_games_won * 0.5
            + break_points_converted * 0.3
            + second_serve_return_pct * 0.2
        )

        PI = (
            tiebreak_win_rate * 0.6
            + deciding_set_win_rate * 0.4
        )

        total = SSI * 0.25 + RSI * 0.25 + PI * 0.20
        total = max(-40, min(40, total))

        return total

    # -------------------------
    # FORM INDEX
    # -------------------------
    def update_form(self, player, won):
        if player not in self.form:
            self.form[player] = []

        self.form[player].append(1 if won else 0)

        if len(self.form[player]) > 10:
            self.form[player] = self.form[player][-10:]

    def form_adjustment(self, player):
        results = self.form.get(player, [])
        if not results:
            return 0

        weight = 1.0
        total = 0.0

        for r in reversed(results):
            total += r * weight
            weight *= 0.85

        adj = (total - 3.5) * 8
        return max(-30, min(30, adj))

    # -------------------------
    # FATIGUE MODEL
    # -------------------------
    def update_fatigue(self, player, sets, games, continent):
        if player not in self.fatigue:
            self.fatigue[player] = {
                "last_continent": continent,
                "fatigue_score": 0
            }

        f = self.fatigue[player]

        # base fatigue from match length
        base = sets * 4 + games * 0.5

        # travel fatigue
        travel = 0
        if f["last_continent"] != continent:
            travel = 12  # long travel penalty

        # accumulate fatigue
        f["fatigue_score"] += base + travel

        # cap fatigue
        f["fatigue_score"] = min(f["fatigue_score"], 80)

        # update continent
        f["last_continent"] = continent

    def fatigue_adjustment(self, player):
        if player not in self.fatigue:
            return 0

        score = self.fatigue[player]["fatigue_score"]

        # convert fatigue score to rating penalty
        penalty = -(score * 0.4)

        return max(-40, min(0, penalty))

    # -------------------------
    # TOURNAMENT STRENGTH
    # -------------------------
    def tournament_adjustment(self, level):
        weights = {
            "GS": 25,
            "ATP_FINALS": 20,
            "M1000": 15,
            "ATP500": 10,
            "ATP250": 5,
            "CH": -10,
            "ITF": -20
        }
        return weights.get(level, 0)

    # -------------------------
    # UPDATE RATINGS
    # -------------------------
    def update(self, winner, loser, gw_winner, gw_loser, surface,
               winner_stats, loser_stats, tournament_level,
               winner_sets, loser_sets, winner_continent, loser_continent):

        rW = self.get_rating(winner)
        rL = self.get_rating(loser)

        rsW = self.get_rating(winner, surface)
        rsL = self.get_rating(loser, surface)

        eW = self.expected_score(rW, rL)
        w = self.mov_weight(gw_winner, gw_loser)

        self.overall[winner] = rW + self.k * w * (1 - eW)
        self.overall[loser]  = rL + self.k * w * (0 - (1 - eW))

        self.surface[surface][winner] = rsW + self.k * w * (1 - eW)
        self.surface[surface][loser]  = rsL + self.k * w * (0 - (1 - eW))

        # stats adjustment
        adj_winner = self.stats_adjustment(winner_stats)
        adj_loser  = self.stats_adjustment(loser_stats)

        self.overall[winner] += adj_winner
        self.overall[loser]  += adj_loser

        self.surface[surface][winner] += adj_winner
        self.surface[surface][loser]  += adj_loser

        # form update
        self.update_form(winner, True)
        self.update_form(loser, False)

        # form adjustment
        self.overall[winner] += self.form_adjustment(winner)
        self.overall[loser]  += self.form_adjustment(loser)

        self.surface[surface][winner] += self.form_adjustment(winner)
        self.surface[surface][loser]  += self.form_adjustment(loser)

        # fatigue update
        self.update_fatigue(winner, winner_sets, gw_winner, winner_continent)
        self.update_fatigue(loser, loser_sets, gw_loser, loser_continent)

        # fatigue adjustment
        self.overall[winner] += self.fatigue_adjustment(winner)
        self.overall[loser]  += self.fatigue_adjustment(loser)

        self.surface[surface][winner] += self.fatigue_adjustment(winner)
        self.surface[surface][loser]  += self.fatigue_adjustment(loser)

        # tournament strength
        t_adj = self.tournament_adjustment(tournament_level)

        self.overall[winner] += t_adj
        self.surface[surface][winner] += t_adj

    # -------------------------
    # PREDICT
    # -------------------------
    def predict(self, playerA, playerB, surface):
        rA = 0.7 * self.get_rating(playerA, surface) + 0.3 * self.get_rating(playerA)
        rB = 0.7 * self.get_rating(playerB, surface) + 0.3 * self.get_rating(playerB)
        return self.expected_score(rA, rB)
