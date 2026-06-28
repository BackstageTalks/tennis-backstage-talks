import requests
from bs4 import BeautifulSoup

def get_finished_matches():
    url = "https://www.flashscore.com/tennis/"
    response = requests.get(url)
    soup = BeautifulSoup(response.text, "html.parser")

    results = []

    rows = soup.select(".event__match--finished")

    for r in rows[:30]:
        try:
            t = [x.strip() for x in r.text.split("\n") if x.strip()]

            player1 = t[-4]
            player2 = t[-3]
            s1 = int(t[-2])
            s2 = int(t[-1])

            winner = player1 if s1 > s2 else player2

            results.append({
                "player1": player1,
                "player2": player2,
                "winner": winner
            })
        except:
            continue

    return results
