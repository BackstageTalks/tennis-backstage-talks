import requests
from bs4 import BeautifulSoup

def get_today_matches():
    url = "https://www.flashscore.com/tennis/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    matches = []
    seen = set()

    rows = soup.select(".event__match")

    for r in rows[:20]:
        try:
            txt = [x.strip() for x in r.text.split("\n") if x.strip()]
            p1 = txt[-2]
            p2 = txt[-1]

            if p1 == p2:
                continue

            key = f"{p1}-{p2}"
            if key in seen:
                continue

            seen.add(key)

            matches.append((p1, p2, "Live"))

        except:
            continue

    # ✅ fallback
    if not matches:
        return [
            ("Djokovic", "Alcaraz", "Fallback"),
            ("Sinner", "Medvedev", "Fallback"),
            ("Zverev", "Rublev", "Fallback"),
            ("Rune", "Tsitsipas", "Fallback")
        ]

    return matches
