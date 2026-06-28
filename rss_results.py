import os
import json
import datetime
import html

BASE = "https://backstagetalks.github.io/tennis-backstage-talks/"


def esc(value):
    return html.escape(str(value if value is not None else ""))


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


def latest_results():
    os.makedirs("public", exist_ok=True)

    files = [
        f for f in os.listdir("public")
        if f.startswith("results_") and f.endswith(".json")
    ]

    print("RESULT files found:", files)

    if not files:
        return None

    latest = sorted(files)[-1]
    path = os.path.join("public", latest)

    print("RSS RESULTS using file:", path)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def status_icon(status):
    if status == "WON":
        return "✅"
    if status == "LOST":
        return "❌"
    if status == "VOID":
        return "⚪"
    if status == "PENDING":
        return "⏳"

    return "❔"


def status_label(status):
    return f"{status_icon(status)} {status or 'UNKNOWN'}"


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
    max-width: 980px;
    margin: 0 auto;
}

h1 {
    font-size: 46px;
    line-height: 1.1;
    margin: 30px 0 22px;
}

p {
    color: #ddd;
    font-size: 20px;
    line-height: 1.35;
}

.summary {
    display: grid;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 12px;
    margin-top: 24px;
}

.box {
    background: #211818;
    border-radius: 16px;
    padding: 16px;
}

.box span {
    display: block;
    color: #aaa;
    font-size: 13px;
    margin-bottom: 6px;
}

.box strong {
    font-size: 24px;
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
    min-width: 820px;
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

.note {
    color: #aaa;
    margin-top: 24px;
    font-size: 16px;
    line-height: 1.35;
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

    .summary {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

    th, td {
        padding: 13px 12px;
        font-size: 15px;
    }
}
</style>
"""


def create_results_page(payload):
    os.makedirs("public/results", exist_ok=True)

    prediction_date = payload.get("prediction_date", "")
    summary = payload.get("summary", {})
    results = payload.get("results", [])

    rows = ""

    for i, item in enumerate(results, start=1):
        status = item.get("status", "UNKNOWN")
        pick = item.get("pick", "Unknown")
        opponent = item.get("opponent", "Unknown")
        odds = item.get("odds", "")
        probability = item.get("probability", 0)
        result_score = item.get("result_score", "")
        winner = item.get("winner", "")
        match_time = format_match_time(item.get("match_start", ""))

        rows += (
            "<tr>"
            f"<td>#{i}</td>"
            f"<td>{esc(status_label(status))}</td>"
            f"<td>{esc(pick)} to win</td>"
            f"<td>{esc(opponent)}</td>"
            f"<td>{esc(match_time) if match_time else '-'}</td>"
            f"<td>{pct(probability)}%</td>"
            f"<td>{esc(odds)}</td>"
            f"<td>{esc(result_score) if result_score else '-'}</td>"
            f"<td>{esc(winner) if winner else '-'}</td>"
            "</tr>\n"
        )

    hit_rate = summary.get("hit_rate")

    if hit_rate is None:
        hit_rate_text = "N/A"
    else:
        hit_rate_text = f"{hit_rate}%"

    page = (
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n"
        "<head>\n"
        "<meta charset='UTF-8'>\n"
        "<title>Backstage Talks Tennis TOP7 Results</title>\n"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
        f"{INDEX_CSS}\n"
        "</head>\n"
        "<body>\n"
        "<div class='container'>\n"
        "<h1>Backstage Talks Tennis TOP7 Results</h1>\n"
        f"<p>Automated review for TOP7 picks from {esc(prediction_date)}.</p>\n"
        "<div class='summary'>\n"
        "<div class='box'><span>Won</span>"
        f"<strong>{summary.get('won', 0)}</strong></div>\n"
        "<div class='box'><span>Lost</span>"
        f"<strong>{summary.get('lost', 0)}</strong></div>\n"
        "<div class='box'><span>Void / Pending</span>"
        f"<strong>{summary.get('void', 0)} / {summary.get('pending', 0)}</strong></div>\n"
        "<div class='box'><span>Hit rate</span>"
        f"<strong>{esc(hit_rate_text)}</strong></div>\n"
        "</div>\n"
        "<div class='table-wrap'>\n"
        "<table>\n"
        "<thead>\n"
        "<tr>\n"
        "<th>#</th>\n"
        "<th>Status</th>\n"
        "<th>Pick</th>\n"
        "<th>Opponent</th>\n"
        "<th>Match time</th>\n"
        "<th>Win %</th>\n"
        "<th>Odds</th>\n"
        "<th>Result</th>\n"
        "<th>Winner</th>\n"
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

    with open("public/results/index.html", "w", encoding="utf-8") as f:
        f.write(page)


def generate_rss_results():
    payload = latest_results()

    if payload is None:
        payload = {
            "prediction_date": "",
            "summary": {
                "total": 0,
                "won": 0,
                "lost": 0,
                "void": 0,
                "pending": 0,
                "unknown": 0,
                "hit_rate": None,
            },
            "results": [],
        }

    os.makedirs("public", exist_ok=True)

    prediction_date = payload.get("prediction_date", "")
    summary = payload.get("summary", {})
    results = payload.get("results", [])

    hit_rate = summary.get("hit_rate")
    hit_rate_text = "N/A" if hit_rate is None else f"{hit_rate}%"

    summary_title = (
        f"Daily TOP7 Review | "
        f"{summary.get('won', 0)} WON / "
        f"{summary.get('lost', 0)} LOST / "
        f"{summary.get('void', 0)} VOID / "
        f"{summary.get('pending', 0)} PENDING"
    )

    summary_desc = (
        f"Prediction date: {prediction_date} | "
        f"Hit rate: {hit_rate_text} | "
        f"Total: {summary.get('total', 0)}"
    )

    items = f"""
<item>
<title>{esc(summary_title)}</title>
<link>{esc(BASE + "results/")}</link>
<guid isPermaLink="false">{esc("results-summary-" + str(prediction_date))}</guid>
<pubDate>{datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
<description>{esc(summary_desc)}</description>
</item>
"""

    for i, item in enumerate(results, start=1):
        status = item.get("status", "UNKNOWN")
        icon = status_icon(status)

        pick = item.get("pick", "Unknown")
        opponent = item.get("opponent", "Unknown")
        odds = item.get("odds", "")
        probability = item.get("probability", 0)
        result_score = item.get("result_score", "")
        winner = item.get("winner", "")

        title = f"{icon} {status} | {pick} to win"

        desc_parts = [
            f"Pick: {pick}",
            f"Opponent: {opponent}",
        ]

        if odds:
            desc_parts.append(f"Odds: {odds}")

        desc_parts.append(f"Win probability: {pct(probability)}%")

        if result_score:
            desc_parts.append(f"Result: {result_score}")

        if winner:
            desc_parts.append(f"Winner: {winner}")

        desc = " | ".join(desc_parts)

        guid = f"results-{prediction_date}-{i}-{pick}-{opponent}"

        items += f"""
<item>
<title>{esc(title)}</title>
<link>{esc(BASE + "results/")}</link>
<guid isPermaLink="false">{esc(guid)}</guid>
<pubDate>{datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
<description>{esc(desc)}</description>
</item>
"""

    create_results_page(payload)

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Backstage Talks Tennis TOP7 Results</title>
<link>{BASE}results/</link>
<description>Automated TOP7 pick result review</description>
{items}
</channel>
</rss>
"""

    with open("public/results.xml", "w", encoding="utf-8") as f:
        f.write(rss)

    print("RESULTS RSS GENERATED:", len(results), "items")
    print("RESULTS RSS PREVIEW:")
    print(rss[:2500])


if __name__ == "__main__":
    generate_rss_results()
