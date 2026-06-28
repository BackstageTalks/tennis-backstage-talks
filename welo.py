import random


BASE_ELO = 1800


def stable_form(player):
    random.seed(hash(player) % 100000)
    return random.randint(45, 60) / 100


def get_elo(player):
    known = {
        "Djokovic": 2100,
        "Alcaraz": 2050,
        "Sinner": 2040,
        "Medvedev": 2010,
        "Zverev": 1990,
        "Rublev": 1950,
        "Basilashvili": 1850,
        "Cecchinato": 1830,
    }

    for key, value in known.items():
        if key.lower() in player.lower():
            return value

    return BASE_ELO


def win_probability(p1, p2):
    elo1 = get_elo(p1)
    elo2 = get_elo(p2)

    base = 1 / (1 + 10 ** ((elo2 - elo1) / 400))

    form1 = stable_form(p1)
    form2 = stable_form(p2)

    form_boost = (form1 - form2) * 0.15

    prob = base + form_boost

    if prob > 0.6:
        prob += 0.02

    return max(0.05, min(0.95, prob))
