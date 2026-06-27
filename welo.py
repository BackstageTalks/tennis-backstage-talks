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

    def update(self, winner, loser, gw_winner, gw_loser, surface):
        rW = self.get_rating(winner)
        rL = self.get_rating(loser)

        rsW = self.get_rating(winner, surface)
        rsL = self.get_rating(loser, surface)

        eW = self.expected_score(rW, rL)
        w = self.mov_weight(gw_winner, gw_loser)

        # overall
        self.overall[winner] = rW + self.k * w * (1 - eW)
        self.overall[loser]  = rL + self.k * w * (0 - (1 - eW))

        # surface-specific
        self.surface[surface][winner] = rsW + self.k * w * (1 - eW)
        self.surface[surface][loser]  = rsL + self.k * w * (0 - (1 - eW))

    def predict(self, playerA, playerB, surface):
        rA = 0.7 * self.get_rating(playerA, surface) + 0.3 * self.get_rating(playerA)
        rB = 0.7 * self.get_rating(playerB, surface) + 0.3 * self.get_rating(playerB)
        return self.expected_score(rA, rB)
