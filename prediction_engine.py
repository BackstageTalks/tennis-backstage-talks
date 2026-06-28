import requests
import random


# ✅ FETCH REAL MATCHES (Flashscore data feed)
def get_today_matches():
    url = "https://d.flashscore.com/x/feed/f_2_0_3_en_1"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Fsign": "SW9D1eZo"
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.text.split("\n")

        matches = []
        seen = set()

        for line in data:
            if "~" not in line:
                continue

            parts = line.split("~")

            if len(parts) < 4:
                continue

            p1 = parts[2].strip()
            p2 = parts[3].strip()

            # základné čistenie
            if len(p1) < 3 or len(p2) < 3 or p1 == p2:
                continue

            key = f"{p1}-{p2}"
            if key in seen:
                continue

            seen.add(key)

            matches.append((p1, p2, "Live"))

        print("✅ REAL matches fetched:", len(matches))

        return matches[:15]

    except Exception as e:
        print("❌ fetch error:", e)

        # fallback len ak úplne zlyhá
        return [
            ("Djokovic", "Sinner", "Fallback"),
            ("Alcaraz", "Medvedev", "Fallback"),
            ("Zverev", "Rublev", "Fallback"),
            ("Rune", "Tsitsipas", "Fallback")
        ]


# ✅ STABILNÁ FORMA (bez random chaosu)
def get_form(player):
    random.seed(hash(player) % 100000)
    wins = random.randint(4, 8)
    return wins / 10


# ✅ ELO (basic skill model)
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


# ✅ WIN PROBABILITY (ELO + FORM + BOOST)
def win_probability(p1, p2):
    elo1 = get_elo(p1)
    elo2 = get_elo(p2)

    base = 1 / (1 + 10 ** ((elo2 - elo1) / 400))

    f1 = get_form(p1)
    f2 = get_form(p2)

    form_boost = (f1 - f2) * 0.2

    prob = base + form_boost

    # favorit boost
    if prob > 0.6:
        prob += 0.04
    elif prob > 0.55:
        prob += 0.02

    return max(0.05, min(0.95, prob))


# ✅ MAIN ENGINE
def get_daily_predictions():
    matches = get_today_matches()

    print("MATCH SOURCE:", matches[:5])

    predictions = []

    for p1, p2, tournament in matches:

        prob = win_probability(p1, p2)
        confidence = abs(prob - 0.5)

        odds = 1.90
        value = prob - (1 / odds)

        # ✅ FILTRY (critické!)
        if prob < 0.55:
            continue
        if confidence < 0.05:
            continue

        score = (prob * 0.85) + (confidence * 0.15)

        predictions.append({
            "player1": p1,
            "player2": p2,
            "tournament": tournament,
            "probability": round(prob, 3),
            "confidence": round(confidence, 3),
            "value": round(value, 3),
            "score": score
        })

    # fallback ak všetko vyfiltruje
    if not predictions:
        print("⚠️ fallback predictions used")
        predictions = [{
            "player1": "Djokovic",
            "player2": "Sinner",
            "tournament": "Fallback",
            "probability": 0.6,
            "confidence": 0.1,
            "value": 0.02,
            "score": 0.1
        }]

    predictions.sort(key=lambda x: x["score"], reverse=True)

    return predictions[:4]
