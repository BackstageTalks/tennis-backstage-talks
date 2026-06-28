import requests
from bs4 import BeautifulSoup

def get_today_matches():
    url = "https://www.flashscore.com/tennis/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    matches = []

    rows = soup.select(".event__match")

    for r in rows[:20]:
        try:
            text = [t.strip() for t in r.text.split("\n") if t.strip()]
            player1 = text[-2]
            player2 = text[-1]

            matches.append((player1, player2, "Live Tour"))
        except:
            continue

    return matches
