import os
import re
import json
import datetime
import requests
from bs4 import BeautifulSoup

TODAY = datetime.date.today().isoformat()

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


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


def is_bad_name(name):
    if not name:
        return True

    name = clean_text(name)

    if len(name) < 3 or len(name) > 60:
        return True

    bad_words = [
        "tennis", "live", "scores", "fixtures", "results", "rankings",
        "scheduled", "finished", "upcoming", "advertisement", "favorites",
        "privacy", "terms", "login", "register", "wimbledon", "atp", "wta",
        "challenger", "singles", "doubles", "draw", "final", "semi",
        "quarter", "court", "odds", "today", "tomorrow", "yesterday"
    ]

    lower = name.lower()

    if any(word in lower for word in bad_words):
        return True

    if not re.search(r"[A-Za-z]", name):
        return True

    return False


def add_match(matches, seen, source, p1, p2, tournament="Tennis"):
    p1 = clean_text(p1)
    p2 = clean_text(p2)

    if is_bad_name(p1) or is_bad_name(p2):
        return

    if p1.lower() == p2.lower():
        return

    key = f"{source}:{p1.lower()}:{p2.lower()}"

    if key in seen:
        return

    seen.add(key)

    matches.append({
        "source": source,
        "player1": p1,
        "player2": p2,
        "tournament": tournament
    })


def parse_vs_text(source, text, tournament="Tennis"):
    matches = []
    seen = set()

    text = clean_text(text)

    patterns = [
        r"([A-Z][A-Za-zÀ-ž\.\-'\s]{2,45})\s+vs\s+([A-Z][A-Za-zÀ-ž\.\-'\s]{2,45})",
        r"([A-Z][A-Za-zÀ-ž\.\-'\s]{2,45})\s+v\s+([A-Z][A-Za-zÀ-ž\.\-'\s]{2,45})",
    ]

    for pattern in patterns:
        for m in re.finditer(pattern, text):
            p1 = m.group(1)
            p2 = m.group(2)
            add_match(matches, seen, source, p1, p2, tournament)

    return matches


def fetch_sportscore():
    header("SPORTSCORE TEST")

    url = "https://sportscore.com/tennis/"

    try:
        r = requests.get(url, headers=HEADERS, timeout=20)

        print("URL:", url)
        print("HTTP:", r.status_code)

        if r.status_code != 200:
            print("RAW ERROR:", r.text[:800])
            return []

        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        matches = parse_vs_text("sportscore", text, "SportScore Tennis")

        print("SPORTSCORE MATCHES:", len(matches))
        print(json.dumps(matches[:15], indent=2, ensure_ascii=False))

        return matches

    except Exception as e:
        print("SPORTSCORE ERROR:", str(e))
        return []


def fetch_espn_html():
    header("ESPN HTML SCOREBOARD TEST")

    urls = [
        "https://www.espn.com/tennis/scoreboard/_/865",
        "https://www.espn.com/tennis/scoreboard",
    ]

    all_matches = []
    seen = set()

    for url in urls:
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)

            print("URL:", url)
            print("HTTP:", r.status_code)

            if r.status_code != 200:
                print("RAW ERROR:", r.text[:500])
                continue

            soup = BeautifulSoup(r.text, "html.parser")
            text = soup.get_text("\n", strip=True)

            lines = [clean_text(x) for x in text.split("\n") if clean_text(x)]

            candidate_names = []

            for line in lines:
                if is_bad_name(line):
                    continue

                if len(re.findall(r"\d", line)) > 3:
                    continue

                if 3 <= len(line) <= 45:
                    candidate_names.append(line)

            dedup = []
            name_seen = set()

            for n in candidate_names:
                k = n.lower()
                if k not in name_seen:
                    name_seen.add(k)
                    dedup.append(n)

            for i in range(0, min(len(dedup) - 1, 30), 2):
                add_match(all_matches, seen, "espn_html", dedup[i], dedup[i + 1], "ESPN Tennis")

        except Exception as e:
            print("ESPN HTML ERROR:", str(e))

    print("ESPN HTML MATCHES:", len(all_matches))
    print(json.dumps(all_matches[:15], indent=2, ensure_ascii=False))

    return all_matches


def fetch_zappscore():
    header("ZAPPSCORE TEST")

    url = "https://zappscore.com/tennis"

    try:
        r = requests.get(url, headers=HEADERS, timeout=20)

        print("URL:", url)
        print("HTTP:", r.status_code)

        if r.status_code != 200:
            print("RAW ERROR:", r.text[:800])
            return []

        soup = BeautifulSoup(r.text, "html.parser")
        text = soup.get_text(" ", strip=True)

        matches = parse_vs_text("zappscore", text, "Zappscore Tennis")

        print("ZAPPSCORE MATCHES:", len(matches))
        print(json.dumps(matches[:15], indent=2, ensure_ascii=False))

        return matches

    except Exception as e:
        print("ZAPPSCORE ERROR:", str(e))
        return []


def fetch_espn_json():
    header("ESPN JSON TEST")

    urls = [
        "https://site.api.espn.com/apis/site/v2/sports/tennis/atp/scoreboard",
        "https://site.api.espn.com/apis/site/v2/sports/tennis/wta/scoreboard",
    ]

    matches = []
    seen = set()

    for url in urls:
        try:
            r = requests.get(url, timeout=15)

            print("URL:", url)
            print("HTTP:", r.status_code)

            if r.status_code != 200:
                print("RAW ERROR:", r.text[:500])
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

                    add_match(matches, seen, "espn_json", p1, p2, tournament)

        except Exception as e:
            print("ESPN JSON ERROR:", str(e))

    print("ESPN JSON MATCHES:", len(matches))
    print(json.dumps(matches[:15], indent=2, ensure_ascii=False))

    return matches


def choose_best_source(sportscore, espn_html, zappscore, espn_json):
    if len(sportscore) > 0:
        return "sportscore"

    if len(espn_html) > 0:
        return "espn_html"

    if len(zappscore) > 0:
        return "zappscore"

    if len(espn_json) > 0:
        return "espn_json"

    return "none"


def main():
    sportscore = fetch_sportscore()
    espn_html = fetch_espn_html()
    zappscore = fetch_zappscore()
    espn_json = fetch_espn_json()

    best = choose_best_source(sportscore, espn_html, zappscore, espn_json)

    summary = {
        "date": TODAY,
        "sportscore_count": len(sportscore),
        "espn_html_count": len(espn_html),
        "zappscore_count": len(zappscore),
        "espn_json_count": len(espn_json),
        "best_source": best
    }

    full = {
        "summary": summary,
        "sportscore": sportscore,
        "espn_html": espn_html,
        "zappscore": zappscore,
        "espn_json": espn_json
    }

    header("FINAL SUMMARY")
    print(json.dumps(summary, indent=2, ensure_ascii=False))

    save_output(summary, full)


if __name__ == "__main__":
    main()
