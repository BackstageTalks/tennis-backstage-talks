import unicodedata

ELO_RATINGS = {}
FORM = {}

def normalize_basic(name):
    name = name.lower()
    name = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    name = name.replace(".", "").strip()
    return name

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
