import os
import re
import json
import datetime
import requests
from bs4 import BeautifulSoup

TODAY = datetime.date.today().isoformat()


def header(title):
    print("\n" + "=" * 80)
    print(title)
    print("=" * 80)


def clean_text(value):
    if not value:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def save_output(summary, full):
    os.makedirs("public", exist_ok=True)

    with open("public/tennis_sources_probe_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    with open("public/tennis_sources_probe_full.json", "w", encoding="utf-8") as f:
        json.dump(full, f, indent=2, ensure_ascii=False)


# ============================================================
# 1) SOFASCORE NO-KEY TEST
# ============================================================

def fetch_sofascore():
    header("SOFASCORE NO-KEY TEST")

    url = f"https://api.sofascore.com/api/v1/sport/tennis/scheduled-events/{TODAY}"

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Accept": "application/json",
        "Referer": "https://www.sofascore.com/tennis"
    }

    try:
        r = requests.get(url, headers=headers, timeout=20)

        print("URL:", url)
        print("HTTP:", r.status_code)

        if r.status_code != 200:
            print("RAW ERROR:", r.text[:700])
            return []

        data = r.json()
        events = data.get("events", [])

        matches = []

        for event in events:
            home = event.get("homeTeam", {})
            away = event.get("awayTeam", {})
            tournament = event.get("tournament", {})
            category = tournament.get("category", {})

            p1 = home.get("name")
            p2 = away.get("name")

            tournament_name = tournament.get("name") or category.get("name") or "SofaScore Tennis"

            status = event.get("status", {})
            status_type = status.get("type")
            status_desc = status.get("description")

            start_ts = event.get("startTimestamp")

            if not p1 or not p2:
                continue

            matches.append({
                "source": "sofascore",
                "player1": clean_text(p1),
                "player2": clean_text(p2),
                "tournament": clean_text(tournament_name),
                "status_type": status_type,
                "status": status_desc,
                "startTimestamp": start_ts,
                "event_id": event.get("id")
            })

        print("SOFASCORE MATCHES:", len(matches))
        print(json.dumps(matches[:10], indent=2, ensure_ascii=False))

        return matches

    except Exception as e:
        print("SOFASCORE ERROR:", str(e))
        return []


# ============================================================
# 2) ESPN NO-KEY TEST
# ============================================================

def fetch_espn():
    header("ESPN NO-KEY TEST")

    urls = [
        "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard",
    ]

    matches = []

    for url in urls:
        try:
            r = requests.get(url, timeout=15)
            print("URL:", url)
            print("HTTP:", r.status_code)

            if r.status_code != 200:
                print("RAW ERROR:", r.text[:300])
                continue

            data = r.json()
            events = data.get("events", [])

            for event in events:
                tournament = event.get("name") or event.get("shortName") or "ESPN Tennis"

                for comp in event.get("competitions", []):
                    competitors = comp.get("competitors", [])

                    if len(competitors) < 2:
                        continue

                    p1 = competitors[0].get("athlete", {}).get("displayName")
                    p2 = competitors[1].get("athlete", {}).get("displayName")

                    if p1 and p2:
                        matches.append({
                            "source": "espn",
                            "player1": clean_text(p1),
                            "player2": clean_text(p2),
                            "tournament": clean_text(tournament),
                        })

        except Exception as e:
            print("ESPN ERROR:", str(e))

    print("ESPN MATCHES:", len(matches))
    print(json.dumps(matches[:10], indent=2, ensure_ascii=False))
    return matches


# ============================================================
# 3) TIPERO PUBLIC JSON TEST
# ============================================================

def fetch_tipero():
    header("TIPERO PUBLIC JSON TEST")

    url = "https://api.tipero.app/api/latest"

    try:
        r = requests.get(url, timeout=15)
        print("HTTP:", r.status_code)

        if r.status_code != 200:
            print("RAW ERROR:", r.text[:500])
            return []

        data = r.json()
        picks = data.get("picks", [])

        matches = []

        for p in picks:
            player1 = p.get("player1")
            player2 = p.get("player2")
            tournament = p.get("tournament") or p.get("tour") or "TIPERO"

            if not player1 or not player2:
                display = p.get("display_match", "")
                if " vs " in display:
                    parts = display.split(" vs ")
                    player1 = parts[0].strip()
                    player2 = parts[1].strip()

            if player1 and player2:
                matches.append({
                    "source": "tipero",
                    "player1": clean_text(player1),
                    "player2": clean_text(player2),
                    "tournament": clean_text(tournament),
                    "pick": p.get("pick"),
                    "confidence": p.get("confidence"),
                    "odds": p.get("odds"),
                    "tier": p.get("tier"),
                    "match_date": p.get("match_date"),
                })

        print("TIPERO MATCHES/PICKS:", len(matches))
        print(json.dumps(matches[:10], indent=2, ensure_ascii=False))
        return matches

    except Exception as e:
        print("TIPERO ERROR:", str(e))
        return []


# ============================================================
# 4) ATP TOUR CURRENT PAGE TEST
# ============================================================

def possible_player_name(text):
    if not text:
        return False

    text = clean_text(text)

    if len(text) < 3 or len(text) > 45:
        return False

    blacklist = [
        "scores", "draw", "schedule", "stats", "tickets",
        "news", "rankings", "official", "atp", "tour",
        "live", "all scores", "view all", "completed",
        "singles", "doubles", "court", "centre court",
        "center court", "h2h", "match stats", "ump",
        "game set and match", "players are currently",
    ]

    lower = text.lower()

    if any(b in lower for b in blacklist):
        return False

    if not re.search(r"[A-Za-z]", text):
        return False

    digit_count = len(re.findall(r"\d", text))
    if digit_count > 2:
        return False

    return True


def fetch_atp_page():
    header("ATP TOUR CURRENT PAGE TEST")

    url = "https://www.atptour.com/en/scores/current"

    try:
        headers = {
            "User-Agent": "Mozilla/5.0"
        }

        r = requests.get(url, headers=headers, timeout=20)
        print("HTTP:", r.status_code)

        if r.status_code != 200:
            print("RAW ERROR:", r.text[:500])
            return []

        soup = BeautifulSoup(r.text, "html.parser")

        texts = []

        for tag in soup.find_all(["a", "span", "div", "td"]):
            txt = clean_text(tag.get_text(" ", strip=True))
            if possible_player_name(txt):
                texts.append(txt)

        deduped = []
        seen = set()

        for t in texts:
            key = t.lower()
            if key not in seen:
                seen.add(key)
                deduped.append(t)

        matches = []

        for i in range(0, min(len(deduped) - 1, 40), 2):
            p1 = deduped[i]
            p2 = deduped[i + 1]

            if p1 != p2:
                matches.append({
                    "source": "atp_page_scrape",
                    "player1": p1,
                    "player2": p2,
                    "tournament": "ATP Current",
                })

        print("ATP TEXT CANDIDATES:", len(deduped))
        print("ATP SCRAPED PAIRS:", len(matches))
        print(json.dumps(matches[:10], indent=2, ensure_ascii=False))

        return matches[:20]

    except Exception as e:
        print("ATP PAGE ERROR:", str(e))
        return []


# ============================================================
# 5) BEST SOURCE DECISION
# ============================================================

def choose_best_source(sofascore, espn, tipero, atp):
    if len(sofascore) > 0:
        return "sofascore"

    if len(espn) > 0:
        return "espn"

    if len(atp) > 0:
        return "atp_page_scrape"

    if len(tipero) > 0:
        return "tipero"

    return "none"


def main():
    sofascore = fetch_sofascore()
    espn = fetch_espn()
    tipero = fetch_tipero()
    atp = fetch_atp_page()

    best = choose_best_source(sofascore, espn, tipero, atp)

    summary = {
        "date": TODAY,
        "sofascore_count": len(sofascore),
        "espn_count": len(espn),
        "tipero_count": len(tipero),
        "atp_page_count": len(atp),
        "best_source": best,
    }

    full = {
        "summary": summary,
        "sofascore": sofascore,
        "espn": espn,
        "tipero": tipero,
        "atp_page_scrape": atp,
    }

    header("FINAL SUMMARY")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    save_output(summary, full)


if __name__ == "__main__":
    main()
