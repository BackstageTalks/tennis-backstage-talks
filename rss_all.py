import os
import json
import datetime
import html
import re

BASE = "https://backstagetalks.github.io/tennis-backstage-talks/"


def esc(value):
    return html.escape(str(value if value is not None else ""))


def tag_open(tag, attrs=""):
    if attrs:
        return f"{chr(60)}{tag} {attrs}{chr(62)}"
    return f"{chr(60)}{tag}{chr(62)}"


def tag_close(tag):
    return f"{chr(60)}/{tag}{chr(62)}"


def pct(value):
    try:
        return round(float(value) * 100, 1)
    except Exception:
        return 0


def format_match_time(value):
    if not value:
        return ""

    try:
        dt = datetime.datetime.fromisoformat(str(value))
        return dt.strftime("%d.%m.%Y %H:%M CET")
    except Exception:
        return str(value)


def latest_all_predictions():
    os.makedirs("public", exist_ok=True)

    files = [
        f for f in os.listdir("public")
        if f.startswith("all_predictions_") and f.endswith(".json")
    ]

    print("ALL prediction files found:", files)

    if not files:
        return []

    latest = sorted(files)[-1]
    path = os.path.join("public", latest)

    print("RSS ALL using prediction file:", path)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


INDEX_CSS = """
<style>
* {
    box-sizing: border-box;
}

body {
    font-family: Arial, sans-serif;
    background: #160f0f;
    color: #f4f4f4;
    margin: 0;
    padding: 20px;
}

.container {
    max-width: 1100px;
    margin: 0 auto;
}

h1 {
    font-size: 46px;
    line-height: 1.1;
    margin: 30px 0 16px;
}

p {
    color: #ddd;
    font-size: 20px;
    line-height: 1.35;
}

.table-wrap {
    width: 100%;
    overflow-x: auto;
    margin-top: 28px;
    border-radius: 18px;
    background: #211818;
}

table {
    width: 100%;
    border-collapse: collapse;
    min-width: 860px;
}

th, td {
    padding: 15px 16px;
    border-bottom: 1px solid #372929;
    text-align: left;
    font-size: 16px;
    vertical-align: middle;
}

th {
    color: #bbb;
    font-weight: 700;
}

td {
    color: #f4f4f4;
}

a {
    color: #f4f4f4;
    text-decoration: none;
}

a:hover {
    color: #9fc8ff;
    text-decoration: underline;
}

.time-col {
    white-space: nowrap;
    color: #d6d6d6;
}

.note {
    color: #aaa;
    margin-top: 24px;
    font-size: 16px;
    line-height: 1.35;
}

.badge {
    display: inline-block;
    background: #2d6cdf;
    color: white;
    padding: 7px 11px;
    border-radius: 999px;
    font-size: 14px;
    font-weight: bold;
    margin-top: 8px;
}

@media (max-width: 640px) {
    body {
        padding: 14px;
    }

    h1 {
        font-size: 38px;
        margin-top: 24px;
    }

    p {
        font-size: 18px;
    }

    th, td {
        padding: 13px 12px;
        font-size: 15px;
    }

    .table-wrap {
        border-radius: 16px;
    }
}
</style>
"""


def create_all_page(predictions):
    os.makedirs("public/all", exist_ok=True)

    sorted_predictions = sorted(
        predictions,
        key=lambda p: (
            str(p.get("match_start", "")),
            -float(p.get("probability", 0)),
        )
    )

    rows = ""

    for i, prediction in enumerate(sorted_predictions, start=1):
        pick = str(prediction.get("pick", "Unknown"))
        opponent = str(prediction.get("opponent", "Unknown"))
        probability = float(prediction.get("probability", 0))
        odds = prediction.get("odds", "")
        match_time = format_match_time(prediction.get("match_start", ""))
        player1 = prediction.get("player1", "")
        player2 = prediction.get("player2", "")

        rows += (
            "<tr>"
            f"<td>#{i}</td>"
            f"<td>{esc(pick)} to win</td>"
            f"<td>{esc(opponent)}</td>"
            f"<td>{esc(player1)} vs {esc(player2)}</td>"
            f"<td>{esc(match_time) if match_time else '-'}</td>"
            f"<td>{esc(odds)}</td>"
            f"<td>{pct(probability)}%</td>"
            "</tr>\n"
        )

    page = (
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n"
        "<head>\n"
        "<meta charset='UTF-8'>\n"
        "<title>Backstage Talks Tennis Picks - RSS ALL</title>\n"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
        f"{INDEX_CSS}\n"
        "</head>\n"
        "<body>\n"
        "<div class='container'>\n"
        "<span class='badge'>RSS ALL</span>\n"
        "<h1>Backstage Talks Tennis Picks - All Matches</h1>\n"
        "<p>All available model picks for the CET window 06:00 → 06:00 next day.</p>\n"
        "<div class='table-wrap'>\n"
        "<table>\n"
        "<thead>\n"
        "<tr>\n"
        "<th>#</th>\n"
        "<th>Pick</th>\n"
        "<th>Opponent</th>\n"
        "<th>Match</th>\n"
        "<th class='time-col'>Match time</th>\n"
        "<th>Odds</th>\n"
        "<th>Win %</th>\n"
        "</tr>\n"
        "</thead>\n"
        "<tbody>\n"
        f"{rows}\n"
        "</tbody>\n"
        "</table>\n"
        "</div>\n"
        "<p class='note'>Generated by BackstageTalks Stat Model for informational and statistical purposes only</p>\n"
        "</div>\n"
        "</body>\n"
        "</html>\n"
    )

    with open("public/all/index.html", "w", encoding="utf-8") as f:
        f.write(page)


def generate_rss_all():
    predictions = latest_all_predictions()

    os.makedirs("public", exist_ok=True)

    items = ""

    for i, prediction in enumerate(predictions, start=1):
        pick = str(prediction.get("pick", "Unknown"))
        opponent = str(prediction.get("opponent", "Unknown"))

        probability = float(prediction.get("probability", 0))
        odds = prediction.get("odds", "")
        match_start = format_match_time(prediction.get("match_start", ""))

        title = f"#{i} RSS ALL: {pick} to win"

        desc_parts = [
            f"Pick: {pick}",
            f"Opponent: {opponent}",
        ]

        if match_start:
            desc_parts.append(f"Match time: {match_start}")

        if odds:
            desc_parts.append(f"Odds: {odds}")

        desc_parts.append(f"Win probability: {pct(probability)}%")

        desc = " | ".join(desc_parts)

        guid_raw = f"rss-all-{pick}-{opponent}-{prediction.get('match_start', '')}-{i}"
        guid = re.sub(r"\s+", "-", guid_raw)

        items += f"""
<item>
<title>{esc(title)}</title>
<link>{esc(BASE + "all/")}</link>
<guid isPermaLink="false">{esc(guid)}</guid>
<pubDate>{datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
<description>{esc(desc)}</description>
</item>
"""

    create_all_page(predictions)

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Backstage Talks Tennis Picks - RSS ALL</title>
<link>{BASE}all/</link>
<description>All available tennis model picks for CET window 06:00 to 06:00 next day</description>
{items}
</channel>
</rss>
"""

    with open("public/tennis_all.xml", "w", encoding="utf-8") as f:
        f.write(rss)

    print("RSS ALL GENERATED:", len(predictions), "items")
    print("RSS ALL PREVIEW:")
    print(rss[:2500])


if __name__ == "__main__":
    generate_rss_all()
