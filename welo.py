from form_fetcher import get_player_form

ELO = {
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

def get_elo(player):
    return ELO.get(player, 1800)

def win_probability(p1, p2):
    elo1 = get_elo(p1)
    elo2 = get_elo(p2)

    base = 1 / (1 + 10 ** ((elo2 - elo1) / 400))

    form1 = get_player_form(p1)
    form2 = get_player_form(p2)

    form_boost = (form1 - form2) * 0.2

    prob = base + form_boost

    # ✅ favorit boost
    if prob > 0.6:
        prob += 0.04
    elif prob > 0.55:
        prob += 0.02

    return max(0.05, min(0.95, prob))
