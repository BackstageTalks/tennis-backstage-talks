import html
import json
import os
from datetime import datetime, timezone


RESULTS_DATA_PATHS = [
    "public/results_data.json",
    "data/play_results.json",
]

RESULTS_PAGE_PATH = "public/results/index.html"
RESULTS_RSS_PATH = "public/results.xml"

SITE_TITLE = "Backstagetalks Statistic Model"
BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks"

HEADER_TITLE = "Backstagetalks Statistic Model"
HEADER_SUBTITLE = "This data is provided for informational and analytical purposes only."
FOOTER_TEXT = "Powered by Backstagetalks Statistic Model"


def safe(value, default="-"):
    if value is None:
        return default

    if value == "":
        return default

    return html.escape(
        str(value)
    )


def pct(value):
    try:
        if value is None:
            return "-"

        return f"{float(value) * 100:.1f}%"

    except Exception:
        return "-"


def units(value):
    try:
        number = float(value)

        if number > 0:
            return f"+{number:.2f}u"

        if number < 0:
            return f"{number:.2f}u"

        return "0.00u"

    except Exception:
        return "0.00u"


def odds(value):
    try:
        return f"{float(value):.2f}"
    except Exception:
        return "-"


def load_json(path, default):
    try:
        if not os.path.exists(path):
            return default

        with open(
            path,
            "r",
            encoding="utf-8",
        ) as file:
            return json.load(file)

    except Exception:
        return default


def empty_summary():
    return {
        "picks": 0,
        "won": 0,
        "lost": 0,
        "void": 0,
        "pending": 0,
        "unknown": 0,
        "units": 0.0,
        "win_rate": None,
    }


def load_results_data():
    for path in RESULTS_DATA_PATHS:
        data = load_json(
            path,
            None,
        )

        if data:
            return data

    return {
        "generated_at": datetime.now(
            timezone.utc,
        ).isoformat(),
        "today": empty_summary(),
        "last_7_days": empty_summary(),
        "current_month": empty_summary(),
        "all_time": empty_summary(),
        "items": [],
    }


def status_class(status):
    status = str(
        status or "PENDING"
    ).upper()

    if status == "WON":
        return "status-won"

    if status == "LOST":
        return "status-lost"

    if status == "VOID":
        return "status-void"

    if status == "UNKNOWN":
        return "status-unknown"

    return "status-pending"


def render_summary_card(label, summary):
    return f"""
<div class="summary-card">
    <div class="summary-label">{safe(label)}</div>

    <div class="summary-grid">
        <div>
            <span>Picks</span>
            <strong>{safe(summary.get("picks", 0))}</strong>
        </div>

        <div>
            <span>W-L</span>
            <strong>{safe(summary.get("won", 0))}-{safe(summary.get("lost", 0))}</strong>
        </div>

        <div>
            <span>Pending</span>
            <strong>{safe(summary.get("pending", 0))}</strong>
        </div>

        <div>
            <span>Units</span>
            <strong>{units(summary.get("units", 0))}</strong>
        </div>

        <div>
            <span>Win rate</span>
            <strong>{pct(summary.get("win_rate"))}</strong>
        </div>
    </div>
</div>
"""


def render_summary(data):
    return f"""
<div class="summary">
    {render_summary_card("Today", data.get("today", empty_summary()))}
    {render_summary_card("Last 7 days", data.get("last_7_days", empty_summary()))}
    {render_summary_card("Current month", data.get("current_month", empty_summary()))}
    {render_summary_card("All time", data.get("all_time", empty_summary()))}
</div>
"""


def render_rows(items):
    if not items:
        return """
<tr>
    <td colspan="9" class="empty">
        No results available yet.
    </td>
</tr>
"""

    rows = []

    for item in items[:300]:
        status = str(
            item.get("result_status") or "PENDING"
        ).upper()

        css = status_class(status)

        tournament = item.get("tournament")
        surface = item.get("surface")
        best_of = item.get("best_of")

        meta_parts = []

        if tournament:
            meta_parts.append(str(tournament))

        if surface:
            meta_parts.append(str(surface))

        if best_of:
            meta_parts.append(f"BO{best_of}")

        meta = " • ".join(meta_parts)

        rows.append(f"""
<tr>
    <td>{safe(item.get("date"))}</td>

    <td>
        <div class="pick">{safe(item.get("pick"))}</div>
        <div class="match">{safe(item.get("match"))}</div>
        <div class="meta">{safe(meta, "")}</div>
    </td>

    <td>{safe(item.get("opponent"))}</td>

    <td>{pct(item.get("probability"))}</td>

    <td>{odds(item.get("odds"))}</td>

    <td>
        <span class="status {css}">
            {safe(status)}
        </span>
    </td>

    <td>{safe(item.get("winner"))}</td>

    <td>{safe(item.get("score"))}</td>

    <td class="units">
        {units(item.get("units"))}
    </td>
</tr>
""")

    return "\n".join(rows)


def render_page(data):
    rows = render_rows(
        data.get("items", []),
    )

    summary = render_summary(
        data,
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>{SITE_TITLE}</title>

<style>
:root {{
    --bg: #0f172a;
    --panel: #111827;
    --panel-2: #1e293b;
    --border: #334155;
    --text: #e5e7eb;
    --muted: #94a3b8;
    --green: #22c55e;
    --red: #ef4444;
    --yellow: #facc15;
    --blue: #38bdf8;
    --gray: #64748b;
}}

* {{
    box-sizing: border-box;
}}

body {{
    margin: 0;
    background: var(--bg);
    color: var(--text);
    font-family: Arial, Helvetica, sans-serif;
}}

.wrapper {{
    max-width: 1320px;
    margin: 0 auto;
    padding: 28px;
}}

.header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 20px;
    margin-bottom: 24px;
}}

.logo {{
    font-size: 28px;
    font-weight: 800;
    line-height: 1.2;
}}

.subtitle {{
    color: var(--muted);
    margin-top: 8px;
    font-size: 14px;
    line-height: 1.45;
}}

.nav {{
    display: flex;
    gap: 18px;
    align-items: center;
    flex-wrap: wrap;
    padding-top: 6px;
}}

.nav a {{
    color: var(--text);
    text-decoration: none;
    font-weight: 800;
    font-size: 14px;
}}

.nav a:hover {{
    color: var(--blue);
}}

.summary {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 14px;
    margin-bottom: 22px;
}}

.summary-card {{
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 14px;
    padding: 16px;
}}

.summary-label {{
    color: var(--blue);
    font-weight: 800;
    margin-bottom: 12px;
}}

.summary-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}}

.summary-grid span {{
    display: block;
    color: var(--muted);
    font-size: 12px;
}}

.summary-grid strong {{
    display: block;
    font-size: 16px;
    margin-top: 3px;
}}

.table-wrap {{
    overflow-x: auto;
    background: var(--panel);
    border: 1px solid var(--border);
    border-radius: 16px;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    min-width: 1050px;
}}

thead {{
    background: var(--panel-2);
}}

th {{
    padding: 14px 12px;
    text-align: left;
    font-size: 13px;
    color: var(--muted);
    border-bottom: 1px solid var(--border);
    text-transform: uppercase;
    letter-spacing: 0.04em;
}}

td {{
    padding: 15px 12px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
}}

tr:hover {{
    background: rgba(255, 255, 255, 0.03);
}}

.pick {{
    font-weight: 800;
    color: var(--text);
}}

.match {{
    color: var(--muted);
    font-size: 12px;
    margin-top: 6px;
}}

.meta {{
    color: var(--blue);
    font-size: 12px;
    margin-top: 6px;
    font-weight: 700;
}}

.status {{
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 800;
}}

.status-won {{
    background: rgba(34, 197, 94, 0.18);
    color: var(--green);
    border: 1px solid rgba(34, 197, 94, 0.45);
}}

.status-lost {{
    background: rgba(239, 68, 68, 0.18);
    color: var(--red);
    border: 1px solid rgba(239, 68, 68, 0.45);
}}

.status-pending {{
    background: rgba(250, 204, 21, 0.16);
    color: var(--yellow);
    border: 1px solid rgba(250, 204, 21, 0.45);
}}

.status-void {{
    background: rgba(100, 116, 139, 0.18);
    color: var(--muted);
    border: 1px solid rgba(100, 116, 139, 0.45);
}}

.status-unknown {{
    background: rgba(56, 189, 248, 0.15);
    color: var(--blue);
    border: 1px solid rgba(56, 189, 248, 0.45);
}}

.units {{
    font-weight: 800;
}}

.empty {{
    text-align: center;
    color: var(--muted);
    padding: 40px;
}}

.footer {{
    max-width: 900px;
    margin: 38px auto 0;
    color: var(--muted);
    font-size: 12px;
    text-align: center;
    line-height: 1.7;
}}

@media (max-width: 900px) {{
    .header {{
        display: block;
    }}

    .nav {{
        margin-top: 16px;
        padding-top: 0;
    }}

    .summary {{
        grid-template-columns: 1fr 1fr;
    }}
}}

@media (max-width: 600px) {{
    .wrapper {{
        padding: 16px;
    }}

    .summary {{
        grid-template-columns: 1fr;
    }}
}}
</style>
</head>

<body>
<div class="wrapper">

    <div class="header">
        <div>
            <div class="logo">
                {safe(HEADER_TITLE)}
            </div>

            <div class="subtitle">
                {safe(HEADER_SUBTITLE)}
            </div>
        </div>

        <div class="nav">
            {BASE_URL}/TOP5</a>
            {BASE_URL}/all/ALL</a>
            {BASE_URL}/results/RESULTS</a>
        </div>
    </div>

    {summary}

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Pick</th>
                    <th>Opponent</th>
                    <th>Win %</th>
                    <th>Odds</th>
                    <th>Status</th>
                    <th>Winner</th>
                    <th>Score</th>
                    <th>Units</th>
                </tr>
            </thead>

            <tbody>
                {rows}
            </tbody>
        </table>
    </div>

    <div class="footer">
        {safe(FOOTER_TEXT)}
    </div>

</div>
</body>
</html>
"""


def render_rss(data):
    now = datetime.now(
        timezone.utc,
    ).strftime("%a, %d %b %Y %H:%M:%S GMT")

    items = []

    for item in data.get("items", [])[:50]:
        title = (
            f"{item.get('pick')} vs {item.get('opponent')} "
            f"— {item.get('result_status', 'PENDING')}"
        )

        description_text = (
            f"Date: {item.get('date')}\n"
            f"Match: {item.get('match')}\n"
            f"Pick: {item.get('pick')}\n"
            f"Opponent: {item.get('opponent')}\n"
            f"Odds: {odds(item.get('odds'))}\n"
            f"Win probability: {pct(item.get('probability'))}\n"
            f"Tournament: {item.get('tournament')}\n"
            f"Surface: {item.get('surface')}\n"
            f"Best of: {item.get('best_of')}\n"
            f"Status: {item.get('result_status')}\n"
            f"Winner: {item.get('winner')}\n"
            f"Score: {item.get('score')}\n"
            f"Units: {units(item.get('units'))}\n\n"
            f"{HEADER_SUBTITLE}\n"
            f"{FOOTER_TEXT}"
        )

        items.append(f"""
<item>
<title>{html.escape(str(title))}</title>
<link>{BASE_URL}/results/</link>
<description>{html.escape(description_text)}</description>
<pubDate>{now}</pubDate>
</item>
""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>{html.escape(SITE_TITLE)}</title>
<link>{BASE_URL}/results/</link>
<description>{html.escape(HEADER_TITLE)}</description>
{''.join(items)}
</channel>
</rss>
"""


def write_file(path, content):
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(
            directory,
            exist_ok=True,
        )

    with open(
        path,
        "w",
        encoding="utf-8",
    ) as file:
        file.write(content)


def run():
    data = load_results_data()

    page = render_page(
        data,
    )

    rss = render_rss(
        data,
    )

    write_file(
        RESULTS_PAGE_PATH,
        page,
    )

    write_file(
        RESULTS_RSS_PATH,
        rss,
    )

    print(
        "RESULTS PAGE WRITTEN:",
        RESULTS_PAGE_PATH,
    )

    print(
        "RESULTS RSS WRITTEN:",
        RESULTS_RSS_PATH,
    )


if __name__ == "__main__":
    run()
