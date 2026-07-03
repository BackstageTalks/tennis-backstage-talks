import json
import os
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from collections import defaultdict


DATA_DIR = "data"
PUBLIC_DIR = "public"
HISTORY_PATH = os.path.join(DATA_DIR, "bet_history.jsonl")
STATS_DIR = os.path.join(PUBLIC_DIR, "stats")
STATS_JSON_PATH = os.path.join(PUBLIC_DIR, "stats.json")

LOCAL_TZ = ZoneInfo("Europe/Bratislava")


def load_history():
    if not os.path.exists(HISTORY_PATH):
        return []

    records = []

    with open(HISTORY_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            try:
                records.append(json.loads(line))
            except Exception:
                continue

    return records


def parse_date(value):
    if not value:
        return None

    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except Exception:
        return None


def safe_float(value):
    try:
        if value is None:
            return None
        return float(value)
    except Exception:
        return None


def settled(record):
    return record.get("result") in ["WON", "LOST"]


def calc_summary(records):
    won = sum(1 for r in records if r.get("result") == "WON")
    lost = sum(1 for r in records if r.get("result") == "LOST")
    pending = sum(1 for r in records if r.get("result") == "PENDING")
    void = sum(1 for r in records if r.get("result") == "VOID")
    unknown = sum(1 for r in records if r.get("result") == "UNKNOWN")

    settled_count = won + lost

    hit_rate = None
    if settled_count:
        hit_rate = won / settled_count

    odds_values = [
        safe_float(r.get("odds"))
        for r in records
        if settled(r) and safe_float(r.get("odds")) is not None
    ]

    avg_odds = None
    if odds_values:
        avg_odds = sum(odds_values) / len(odds_values)

    profit = 0.0

    for r in records:
        odds = safe_float(r.get("odds"))

        if odds is None:
            continue

        if r.get("result") == "WON":
            profit += odds - 1

        elif r.get("result") == "LOST":
            profit -= 1

    roi = None
    if settled_count:
        roi = profit / settled_count

    return {
        "total_records": len(records),
        "won": won,
        "lost": lost,
        "pending": pending,
        "void": void,
        "unknown": unknown,
        "settled": settled_count,
        "hit_rate": hit_rate,
        "avg_odds": avg_odds,
        "profit_units_flat_1u": profit,
        "roi_flat_1u": roi,
    }


def fmt_pct(value):
    if value is None:
        return "n/a"

    return f"{value * 100:.1f}%"


def fmt_num(value):
    if value is None:
        return "n/a"

    return f"{value:.2f}"


def filter_by_date(records, start_date, end_date):
    output = []

    for r in records:
        d = parse_date(r.get("date"))

        if d is None:
            continue

        if start_date <= d <= end_date:
            output.append(r)

    return output


def month_range(year, month):
    start = datetime(year, month, 1).date()

    if month == 12:
        end = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        end = datetime(year, month + 1, 1).date() - timedelta(days=1)

    return start, end


def previous_month(year, month):
    if month == 1:
        return year - 1, 12

    return year, month - 1


def split_by_feed(records):
    feeds = defaultdict(list)

    for r in records:
        feeds[r.get("feed", "UNKNOWN")].append(r)

    return feeds


def build_stats(records):
    today = datetime.now(LOCAL_TZ).date()

    last_7_start = today - timedelta(days=6)
    last_7_end = today

    current_month_start, current_month_end = month_range(today.year, today.month)

    py, pm = previous_month(today.year, today.month)
    previous_month_start, previous_month_end = month_range(py, pm)

    periods = {
        "last_7_days": {
            "label": "Last 7 days",
            "start": str(last_7_start),
            "end": str(last_7_end),
            "records": filter_by_date(records, last_7_start, last_7_end),
        },
        "current_month": {
            "label": "Current month",
            "start": str(current_month_start),
            "end": str(current_month_end),
            "records": filter_by_date(records, current_month_start, current_month_end),
        },
        "previous_month": {
            "label": "Previous month",
            "start": str(previous_month_start),
            "end": str(previous_month_end),
            "records": filter_by_date(records, previous_month_start, previous_month_end),
        },
        "all_time": {
            "label": "All time",
            "start": None,
            "end": None,
            "records": records,
        },
    }

    result = {}

    for key, period in periods.items():
        period_records = period["records"]
        feeds = split_by_feed(period_records)

        result[key] = {
            "label": period["label"],
            "start": period["start"],
            "end": period["end"],
            "overall": calc_summary(period_records),
            "feeds": {
                feed: calc_summary(items)
                for feed, items in sorted(feeds.items())
            }
        }

    return result


def render_summary_card(title, summary):
    return f"""
    <div class="card">
      <h3>{title}</h3>
      <div class="line"><span>Settled</span><strong>{summary["settled"]}</strong></div>
      <div class="line"><span>WON</span><strong>{summary["won"]}</strong></div>
      <div class="line"><span>LOST</span><strong>{summary["lost"]}</strong></div>
      <div class="line"><span>Hit rate</span><strong>{fmt_pct(summary["hit_rate"])}</strong></div>
      <div class="line"><span>Avg odds</span><strong>{fmt_num(summary["avg_odds"])}</strong></div>
      <div class="line"><span>Profit 1u flat</span><strong>{fmt_num(summary["profit_units_flat_1u"])}u</strong></div>
      <div class="line"><span>ROI 1u flat</span><strong>{fmt_pct(summary["roi_flat_1u"])}</strong></div>
      <div class="line muted"><span>Pending</span><strong>{summary["pending"]}</strong></div>
      <div class="line muted"><span>Void / Unknown</span><strong>{summary["void"] + summary["unknown"]}</strong></div>
    </div>
    """


def generate_html(stats):
    os.makedirs(STATS_DIR, exist_ok=True)

    period_sections = []

    for key in ["last_7_days", "current_month", "previous_month", "all_time"]:
        period = stats[key]

        date_range = ""
        if period["start"] and period["end"]:
            date_range = f"{period['start']} → {period['end']}"

        cards = []

        cards.append(
            render_summary_card("Overall", period["overall"])
        )

        for feed in ["TOP", "ALL"]:
            feed_summary = period["feeds"].get(feed, calc_summary([]))
            cards.append(
                render_summary_card(feed, feed_summary)
            )

        period_sections.append(f"""
        <section class="section">
          <h2>{period["label"]}</h2>
          <div class="range">{date_range}</div>
          <div class="grid">
            {''.join(cards)}
          </div>
        </section>
        """)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Backstage Talks Tennis Stats</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">

  <style>
    body {{
      margin: 0;
      padding: 18px;
      background: #130d0d;
      color: #ffffff;
      font-family: Arial, Helvetica, sans-serif;
    }}

    h1 {{
      font-size: 42px;
      margin: 0 0 8px 0;
      line-height: 1.05;
    }}

    .disclaimer {{
      color: #c9b8ad;
      font-size: 14px;
      margin-bottom: 24px;
      line-height: 1.5;
    }}

    .section {{
      background: #211717;
      border: 1px solid #3a2929;
      border-radius: 18px;
      padding: 18px;
      margin-bottom: 18px;
    }}

    .section h2 {{
      margin: 0 0 6px 0;
      font-size: 26px;
      color: #fff3e8;
    }}

    .range {{
      color: #c9b8ad;
      font-size: 13px;
      margin-bottom: 14px;
    }}

    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 14px;
    }}

    .card {{
      background: #2a1e1e;
      border: 1px solid #463232;
      border-radius: 16px;
      padding: 16px;
    }}

    .card h3 {{
      margin: 0 0 12px 0;
      font-size: 20px;
    }}

    .line {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      padding: 6px 0;
      border-bottom: 1px solid #3a2929;
      font-size: 14px;
    }}

    .line:last-child {{
      border-bottom: none;
    }}

    .muted {{
      color: #c9b8ad;
    }}

    .footer {{
      color: #a99790;
      font-size: 13px;
      margin-top: 22px;
      line-height: 1.5;
    }}
  </style>
</head>

<body>
  <h1>📈 Backstage Talks Tennis Stats</h1>

  <div class="disclaimer">
    The data generated by the Backstage Talks STAT model is for statistical and informational purposes only.
  </div>

  {''.join(period_sections)}

  <div class="footer">
    Generated: {generated_at}<br>
    Metrics count only WON and LOST as settled bets. PENDING, VOID and UNKNOWN are excluded from hit rate.
  </div>
</body>
</html>
"""

    with open(os.path.join(STATS_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(html)


def main():
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    records = load_history()
    stats = build_stats(records)

    with open(STATS_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)

    generate_html(stats)

    print("Stats generated:", os.path.join(STATS_DIR, "index.html"))
    print("Stats JSON generated:", STATS_JSON_PATH)


if __name__ == "__main__":
    main()
