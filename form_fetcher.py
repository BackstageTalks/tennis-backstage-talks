import random

def get_player_form(player):
    # ✅ stabilná forma (rovnaký hráč = rovnaký výsledok)
    random.seed(hash(player) % 100000)
    wins = random.randint(4, 8)
    return wins / 10
``
