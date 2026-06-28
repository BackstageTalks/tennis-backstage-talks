import requests

def get_today_matches():
    url = "https://site.web.api.espn.com/apis/v2/sports/tennis/atp/scoreboard"

    try:
        response = requests.get(url, timeout=10)
        data = response.json()

        matches = []

        events = data.get("events", [])

        for event in events:
            comps = event.get("competitions", [])

            for comp in comps:
                competitors = comp.get("competitors", [])

                if len(competitors) < 2:
                    continue

                p1 = competitors[0]["athlete"]["displayName"]
                p2 = competitors[1]["athlete"]["displayName"]

                matches.append((p1, p2, "ATP"))

        print("✅ ESPN matches:", len(matches))

        return matches

    except Exception as e:
        print("❌ ESPN error:", e)

        return [
            ("Djokovic", "Sinner", "Fallback"),
            ("Alcaraz", "Medvedev", "Fallback"),
            ("Zverev", "Rublev", "Fallback"),
            ("Rune", "Tsitsipas", "Fallback")
        ]
