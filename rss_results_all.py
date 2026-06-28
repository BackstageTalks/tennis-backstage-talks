import os
import json
import datetime
import html
import requests
from datetime import timezone, timedelta

BASE = "https://backstagetalks.github.io/tennis-backstage-talks/"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json,text/html,*/*",
}

LOCAL_TZ_OFFSET_HOURS = int(os.getenv("LOCAL_TZ_OFFSET_HOURS", "2"))
LOCAL_TZ = timezone(timedelta(hours=LOCAL_TZ_OFFSET_HOURS))


def esc(value):
    return html.escape(str(value if value is not None else ""))


def pct(value):
    try:
        return round(float(value) * 100, 1)
    except Exception:
        return 0


def signed_units(value):
    try:
        number = round(float(value), 2)
    except Exception:
        number = 0.0

    if number > 0:
        return f"+{number:.2f}u"

    if number < 0:
        return f"{number:.2f}u"

    return "0.00u"


def format_match_time(value):
    if not value:
        return ""

    try:
        dt = datetime.datetime.fromisoformat(str(value))
        return dt.strftime("%d.%m.%Y %H:%M CET")
    except Exception:
        return str(value)


def date_range_last_days(days):
    today = datetime.datetime.now(LOCAL_TZ).date()

    return [
        today - datetime.timedelta(days=i)
        for i in range(0, days)
    ]


def current_month_dates():
    today = datetime.datetime.now(LOCAL_TZ).date()
    first = today.replace(day=1)

    dates = []
    current = today

    while current >= first:
        dates.append(current)
        current -= datetime.timedelta(days=1)

    return dates


def empty_summary():
    return {
        "total": 0,
        "won": 0,
        "lost": 0,
        "void": 0,
        "pending": 0,
        "unknown": 0,
        "hit_rate": None,
        "units": 0.0,
    }


def summarize_items(items):
    summary = empty_summary()

    for item in items:
        status = item.get("status")
        units = float(item.get("units", 0) or 0)

        summary["total"] += 1
        summary["units"] += units

        if status == "WON":
            summary["won"] += 1
        elif status == "LOST":
            summary["lost"] += 1
        elif status == "VOID":
            summary["void"] += 1
        elif status == "PENDING":
            summary["pending"] += 1
        else:
            summary["unknown"] += 1

    decided = summary["won"] + summary["lost"]

    if decided > 0:
        summary["hit_rate"] = round(summary["won"] / decided * 100, 1)

    summary["units"] = round(summary["units"], 2)

    return summary


def load_local_results():
    files = [
        f for f in os.listdir("public")
        if f.startswith("all_results_") and f.endswith(".json")
    ]

    payloads = []

    for file_name in sorted(files):
        path = os.path.join("public", file_name)

        try:
            with open(path, "r", encoding="utf-8") as f:
                payloads.append(json.load(f))
        except Exception as e:
            print("ALL RESULT LOCAL LOAD ERROR:", path, str(e))

    return payloads


def fetch_remote_result(date_value):
    url = f"{BASE}all_results_{date_value}.json?v=all-period-summary"

    try:
        response = requests.get(url, headers=HEADERS, timeout=15)

        print("FETCH REMOTE ALL RESULT:", url, response.status_code)

        if response.status_code != 200:
            return None

        data = response.json()

        if isinstance(data, dict) and data.get("type") == "ALL_RESULTS":
            return data

        return None

    except Exception as e:
        print("FETCH REMOTE ALL RESULT ERROR:", url, str(e))
        return None


def load_results_history():
    history = {}

    for payload in load_local_results():
        prediction_date = payload.get("prediction_date")

        if prediction_date:
            history[prediction_date] = payload

    dates_to_fetch = set()

    for date_obj in date_range_last_days(31):
        dates_to_fetch.add(date_obj.isoformat())

    for date_obj in current_month_dates():
        dates_to_fetch.add(date_obj.isoformat())

    for date_value in sorted(dates_to_fetch):
        if date_value in history:
            continue

        payload = fetch_remote_result(date_value)

        if payload:
            history[date_value] = payload

    return history


def latest_results(history):
    if not history:
        return None

    latest_key = sorted(history.keys())[-1]
    return history[latest_key]


def summary_for_dates(history, dates):
    items = []

    wanted = {
        d.isoformat() if hasattr(d, "isoformat") else str(d)
        for d in dates
    }

    for date_value, payload in history.items():
        if date_value not in wanted:
            continue

        items.extend(payload.get("results", []))

    return summarize_items(items)


def today_summary(payload):
    if not payload:
        return empty_summary()

    return payload.get("summary") or summarize_items(payload.get("results", []))


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


def hit_rate_text(summary):
    value = summary.get("hit_rate")

    if value is None:
        return "N/A"

    return f"{value}%"


def record_text(summary):
    return (
        f"{summary.get('won', 0)} WON / "
        f"{summary.get('lost', 0)} LOST / "
        f"{summary.get('void', 0)} VOID / "
        f"{summary.get('pending', 0)} PENDING"
    )


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
    margin: 30px 0 22px;
}

p {
    color: #ddd;
    font-size: 20px;
    line-height: 1.35;
}

.summary {
    display: grid;
    grid-template-columns: repeat(3, minmax(0, 1fr));
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
    display: block;
    font-size: 24px;
    margin-bottom: 4px;
}

.box small {
    color: #cfcfcf;
    font-size: 13px;
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
    min-width: 940px;
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
        grid-template-columns: 1fr;
    }

    th, td {
        padding: 13px 12px;
        font-size: 15px;
    }
}
</style>
"""


def create_results_page(payload, week_summary, month_summary):
    os.makedirs("public/all_results", exist_ok=True)

    prediction_date = payload.get("prediction_date", "")
    summary = today_summary(payload)
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
        units = item.get("units", 0)

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
            f"<td>{esc(signed_units(units))}</td>"
            "</tr>\n"
        )

    page = (
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n"
        "<head>\n"
        "<meta charset='UTF-8'>\n"
        "<title>Backstage Talks Tennis ALL Results</title>\n"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
        f"{INDEX_CSS}\n"
        "</head>\n"
        "<body>\n"
        "<div class='container'>\n"
        "<h1>Backstage Talks Tennis ALL Results</h1>\n"
        f"<p>Automated review for ALL picks from {esc(prediction_date)}.</p>\n"

        "<div class='summary'>\n"

        "<div class='box'>\n"
        "<span>Today</span>\n"
        f"<strong>{esc(signed_units(summary.get('units', 0)))}</strong>\n"
        f"<small>{esc(record_text(summary))}<br>Hit rate: {esc(hit_rate_text(summary))}</small>\n"
        "</div>\n"

        "<div class='box'>\n"
        "<span>Last 7 days</span>\n"
        f"<strong>{esc(signed_units(week_summary.get('units', 0)))}</strong>\n"
        f"<small>{esc(record_text(week_summary))}<br>Hit rate: {esc(hit_rate_text(week_summary))}</small>\n"
        "</div>\n"

        "<div class='box'>\n"
        "<span>Current month</span>\n"
        f"<strong>{esc(signed_units(month_summary.get('units', 0)))}</strong>\n"
        f"<small>{esc(record_text(month_summary))}<br>Hit rate: {esc(hit_rate_text(month_summary))}</small>\n"
        "</div>\n"

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
        "<th>Units</th>\n"
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

    with open("public/all_results/index.html", "w", encoding="utf-8") as f:
        f.write(page)


def generate_rss_all_results():
    history = load_results_history()
    payload = latest_results(history)

    if payload is None:
        payload = {
            "prediction_date": "",
            "summary": empty_summary(),
            "results": [],
        }

    week_dates = date_range_last_days(7)
    month_dates = current_month_dates()

    today = today_summary(payload)
    week = summary_for_dates(history, week_dates)
    month = summary_for_dates(history, month_dates)

    os.makedirs("public", exist_ok=True)

    prediction_date = payload.get("prediction_date", "")
    results = payload.get("results", [])

    summary_title = (
        f"Daily ALL Review | "
        f"Today: {signed_units(today.get('units', 0))} | "
        f"7 days: {signed_units(week.get('units', 0))} | "
        f"Month: {signed_units(month.get('units', 0))}"
    )

    summary_desc = (
        f"Today: {record_text(today)} | "
        f"Hit rate: {hit_rate_text(today)} | "
        f"Units: {signed_units(today.get('units', 0))} | "
        f"Last 7 days: {record_text(week)} | "
        f"Hit rate: {hit_rate_text(week)} | "
        f"Units: {signed_units(week.get('units', 0))} | "
        f"Month: {record_text(month)} | "
        f"Hit rate: {hit_rate_text(month)} | "
        f"Units: {signed_units(month.get('units', 0))}"
    )

    items = f"""
<item>
<title>{esc(summary_title)}</title>
<link>{esc(BASE + "all_results/")}</link>
<guid isPermaLink="false">{esc("all-results-summary-" + str(prediction_date))}</guid>
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
        units = item.get("units", 0)

        title = f"{icon} {status} | {pick} to win | {signed_units(units)}"

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

        desc_parts.append(f"Units: {signed_units(units)}")

        desc = " | ".join(desc_parts)

        guid = f"all-results-{prediction_date}-{i}-{pick}-{opponent}"

        items += f"""
<item>
<title>{esc(title)}</title>
<link>{esc(BASE + "all_results/")}</link>
<guid isPermaLink="false">{esc(guid)}</guid>
<pubDate>{datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
<description>{esc(desc)}</description>
</item>
"""

    create_results_page(payload, week, month)

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Backstage Talks Tennis ALL Results</title>
<link>{BASE}all_results/</link>
<description>Automated ALL pick result review with units, weekly and monthly summaries</description>
{items}
</channel>
</rss>
"""

    with open("public/all_results.xml", "w", encoding="utf-8") as f:
        f.write(rss)

    print("ALL RESULTS RSS GENERATED:", len(results), "items")
    print("TODAY SUMMARY:", today)
    print("WEEK SUMMARY:", week)
    print("MONTH SUMMARY:", month)
    print("ALL RESULTS RSS PREVIEW:")
    print(rss[:2500])


if __name__ == "__main__":
    generate_rss_all_results()
