import requests

def get_today_matches():
    url = "https://d.flashscore.com/x/feed/f_2_0_3_en_1"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "X-Fsign": "SW9D1eZo"
    }

    try:
        response = requests.get(url, headers=headers)
        data = response.text.split("\n")

        matches = []

        for line in data:
            # riadky so zápasmi
            if "~" not in line:
                continue

            parts = line.split("~")

            try:
                player1 = parts[2]
                player2 = parts[3]
            except:
                continue

            if not player1 or not player2:
                continue

            # cleanup
            if len(player1) < 3 or len(player2) < 3:
                continue

            matches.append((player1, player2, "Live"))

        # sanity filter
        unique = []
        seen = set()

        for p1, p2, t in matches:
            key = f"{p1}-{p2}"
            if key in seen:
                continue
            seen.add(key)
            unique.append((p1, p2, t))

        print("✅ REAL matches fetched:", len(unique))

        return unique[:10]

    except Exception as e:
        print("❌ fetch error:", e)

        # fallback (len ak všetko padne)
        return [
            ("Djokovic", "Sinner", "Fallback"),
            ("Alcaraz", "Medvedev", "Fallback"),
            ("Zverev", "Rublev", "Fallback"),
            ("Rune", "Tsitsipas", "Fallback")
        ]
