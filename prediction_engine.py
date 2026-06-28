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
