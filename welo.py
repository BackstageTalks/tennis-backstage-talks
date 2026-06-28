ELO_RATINGS = {
    "Djokovic": 2100,
    "Alcaraz": 2050,
    "Sinner": 2000,
    "Medvedev": 2020,
    "Zverev": 1980,
    "Rublev": 1950,
    "Rune": 1940,
    "Tsitsipas": 1970,
    "Ruud": 1960,
    "Hurkacz": 1980,
    "Fritz": 1990,
    "Paul": 1950
}

FORM = {
    "Djokovic": 0.9,
    "Alcaraz": 0.85,
    "Sinner": 0.8,
    "Medvedev": 0.75,
    "Zverev": 0.7,
    "Rublev": 0.65,
    "Rune": 0.6,
    "Tsitsipas": 0.7,
    "Ruud": 0.75,
    "Hurkacz": 0.7,
    "Fritz": 0.8,
    "Paul": 0.7
}


def get_elo(player):
    return ELO_RATINGS.get(player, 1800)


def get_form(player):
    return FORM.get(player, 0.5)


def win_probability(p1, p2):
    elo1 = get_elo(p1)
    elo2 = get_elo(p2)

    base = 1 / (1 + 10 ** ((elo2 - elo1) / 400))

    form_boost = (get_form(p1) - get_form(p2)) * 0.1

    prob = base + form_boost

    return max(0.01, min(0.99, prob))
