import os
import html
from datetime import datetime, timezone


SITE_TITLE = "BackstageTalks Statistic Model"
BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks"

HEADER_TITLE = "BackstageTalks Statistic Model"
HEADER_SUBTITLE = "This data is provided for informational and analytical purposes only."
FOOTER_TEXT = "Powered by BackstageTalks Statistic Model"


def safe(value, default="-"):
    if value is None:
        return default

    if value == "":
        return default

    return html.escape(str(value))


def pct(value):
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "-"


def odds(value):
    try:
        return f"{float(value):.2f}"
    except Exception:
        return "-"


def tag_class(tag):
    tag = str(tag or "").upper()

    if tag == "PLAY":
        return "tag-play"

    if tag == "PLAY SMALL":
        return "tag-small"

    if tag == "WATCH":
        return "tag-watch"

    return "tag-info"


def format_match_meta(prediction):
    tournament = prediction.get("tournament")
    surface = prediction.get("surface")
    best_of = prediction.get("best_of")

    parts = []

    if tournament:
        parts.append(str(tournament))

    if surface:
        parts.append(str(surface))

    if best_of:
        parts.append(f"BO{best_of}")

    if not parts:
        return ""

    return " • ".join(parts)


def resolve_sets_label(prediction):
    label = prediction.get("sets_probability_label")

    if label:
        return str(label)

    best_of = prediction.get("best_of")

    try:
        if int(best_of) == 5:
            return "5 Sets"
    except Exception:
        pass

    return "3 Sets"


def render_nav():
    return f"""
<nav class="nav" aria-label="Main navigation">
    <a href="{BASE_URL}/">TOP5</a>
    <a href="{BASE_URL}/all/">ALL</a>
    <a href="{BASE_URL}/results/">RESULTS</a>
</nav>
"""


def render_summary(predictions):
    count = len(predictions)

    probabilities = []

    for prediction in predictions:
        value = prediction.get("probability")

        if value is None:
            continue

        try:
            probabilities.append(float(value))
        except Exception:
            continue

    odds_values = []

    for prediction in predictions:
        value = prediction.get("odds")

        if value is None:
            continue

        try:
            odds_values.append(float(value))
        except Exception:
            continue

    avg_probability = "-"
    avg_odds = "-"

    if probabilities:
        avg_probability = f"{sum(probabilities) / len(probabilities) * 100:.1f}%"

    if odds_values:
        avg_odds = f"{sum(odds_values) / len(odds_values):.2f}"

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""
<div class="summary">
    <div class="summary-card">
        <div class="summary-label">Picks</div>
        <div class="summary-value">{count}</div>
    </div>

    <div class="summary-card">
        <div class="summary-label">Average Win %</div>
        <div class="summary-value">{avg_probability}</div>
    </div>

    <div class="summary-card">
        <div class="summary-label">Average Odds</div>
        <div class="summary-value">{avg_odds}</div>
    </div>

    <div class="summary-card">
        <div class="summary-label">Updated</div>
        <div class="summary-value small">{updated}</div>
    </div>
</div>
"""


def render_rows(predictions):
    if not predictions:
        return """
<tr>
    <td colspan="7" class="empty">
        No picks available.
    </td>
</tr>
"""

    rows = []

    for index, prediction in enumerate(predictions, start=1):
        pick = safe(prediction.get("pick"))
        opponent = safe(prediction.get("opponent"))
        match = safe(prediction.get("match"))
        time = safe(prediction.get("time"))

        probability = pct(prediction.get("probability"))
        odd = odds(prediction.get("odds"))

        expected_sets = safe(prediction.get("expected_sets"))
        sets_probability = pct(prediction.get("sets_probability"))
        sets_probability_label = safe(resolve_sets_label(prediction))

        most_likely_score = safe(
            prediction.get("most_likely_score"),
            default="",
        )

        bet_tag = safe(prediction.get("bet_tag", "INFO ONLY"))
        css_tag = tag_class(prediction.get("bet_tag", "INFO ONLY"))

        match_meta = safe(
            format_match_meta(prediction),
            default="",
        )

        match_meta_html = ""

        if match_meta:
            match_meta_html = f"""
        <div class="match-meta">
            {match_meta}
        </div>
"""

        most_likely_html = ""

        if most_likely_score:
            most_likely_html = f"""
        <div>
            <span class="intel-label">Most likely score:</span>
            {most_likely_score}
        </div>
"""

        rows.append(f"""
<tr>
    <td class="rank">#{index}</td>

    <td class="pick-cell">
        <div class="pick-name">{pick}</div>
        <div class="pick-sub">to win</div>
        <div class="match-name">{match}</div>
        {match_meta_html}
    </td>

    <td>{opponent}</td>
    <td>{time}</td>
    <td class="probability">{probability}</td>
    <td class="odds">{odd}</td>

    <td class="intel">
        <div>
            <span class="intel-label">Sets:</span>
            {expected_sets}
        </div>

        <div>
            <span class="intel-label">{sets_probability_label}:</span>
            {sets_probability}
        </div>

        {most_likely_html}

        <div class="tag {css_tag}">
            {bet_tag}
        </div>
    </td>
</tr>
""")

    return "\n".join(rows)


def render_page(predictions, title, subtitle):
    rows = render_rows(predictions)
    summary = render_summary(predictions)
    nav = render_nav()

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>{safe(SITE_TITLE)}</title>

<style>
:root {{
    --bg: #0f172a;
    --panel: #111827;
    --panel-2: #1e293b;
    --border: #334155;
    --text: #e5e7eb;
    --muted: #94a3b8;
    --green: #22c55e;
    --yellow: #facc15;
    --blue: #38bdf8;
    --gray: #64748b;
}}

* {{
    box-sizing: border-box;
}}

html, body {{
    margin: 0;
    padding: 0;
    background: var(--bg);
    color: var(--text);
    font-family: Arial, Helvetica, sans-serif;
}}

.wrapper {{
    max-width: 1440px;
    margin: 0 auto;
    padding: 28px;
}}

.header {{
    display: grid;
    grid-template-columns: minmax(520px, 1fr) auto;
    gap: 32px;
    align-items: start;
    margin-bottom: 24px;
}}

.logo {{
    font-size: 30px;
    font-weight: 900;
    line-height: 1.15;
    color: var(--text);
    letter-spacing: 0.2px;
    white-space: nowrap;
}}

.subtitle {{
    color: var(--muted);
    margin-top: 10px;
    font-size: 14px;
    line-height: 1.45;
    max-width: 760px;
}}

.nav {{
    display: flex;
    gap: 18px;
    align-items: center;
    flex-wrap: nowrap;
    padding-top: 8px;
    white-space: nowrap;
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
    padding:color: var(--muted);
    font-size: 13px;
    margin-bottom: 8px;
}}

.summary-value {{
    font-size: 22px;
    font-weight: 800;
}}

.summary-value.small {{
    font-size: 14px;
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
    min-width: 920px;
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
    padding: 16px 12px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
}}

tr:hover {{
    background: rgba(255, 255, 255, 0.03);
}}

.rank {{
    font-weight: 800;
    color: var(--blue);
}}

.pick-name {{
    font-size: 16px;
    font-weight: 800;
}}

.pick-sub {{
    color: var(--green);
    font-size: 12px;
    margin-top: 4px;
    font-weight: 700;
}}

.match-name {{
    color: var(--muted);
    font-size: 12px;
    margin-top: 8px;
}}

.match-meta {{
    color: var(--blue);
    font-size: 12px;
    margin-top: 6px;
    font-weight: 700;
}}

.probability {{
    font-weight: 800;
    color: var(--green);
}}

.odds {{
    font-weight: 800;
    color: var(--yellow);
}}

.intel {{
    line-height: 1.55;
    min-width: 220px;
}}

.intel-label {{
    color: var(--muted);
    font-size: 12px;
    margin-right: 4px;
}}

.tag {{
    display: inline-block;
    margin-top: 10px;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 800;
}}

.tag-play {{
    background: rgba(34, 197, 94, 0.18);
    color: var(--green);
    border: 1px solid rgba(34, 197, 94, 0.45);
}}

.tag-small {{
    background: rgba(250, 204, 21, 0.16);
    color: var(--yellow);
    border: 1px solid rgba(250, 204, 21, 0.45);
}}

.tag-watch {{
    background: rgba(56, 189, 248, 0.15);
    color: var(--blue);
    border: 1px solid rgba(56, 189, 248, 0.45);
}}

.tag-info {{
    background: rgba(100, 116, 139, 0.18);
    color: var(--muted);
    border: 1px solid rgba(100, 116, 139, 0.45);
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

@media (max-width: 950px) {{
    .header {{
        display: block;
    }}

    .logo {{
        white-space: normal;
    }}

    .nav {{
        margin-top: 16px;
        padding-top: 0;
        flex-wrap: wrap;
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

        {nav}
    </div>

    {summary}

    <div class="table-wrap">
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>Pick</th>
                    <th>Opponent</th>
                    <th>Time</th>
                    <th>Win %</th>
                    <th>Odds</th>
                    <th>Match Intelligence</th>
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


def write_page(predictions, title, subtitle, destination):
    html_text = render_page(
        predictions=predictions,
        title=title,
        subtitle=subtitle,
    )

    directory = os.path.dirname(destination)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(destination, "w", encoding="utf-8") as file:
        file.write(html_text)


def render_rss(predictions, title, link):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    items = []

    for prediction in predictions:
        pick = safe(prediction.get("pick"))
        opponent = safe(prediction.get("opponent"))
        probability = pct(prediction.get("probability"))
        odd = odds(prediction.get("odds"))
        expected_sets = safe(prediction.get("expected_sets"))
        bet_tag = safe(prediction.get("bet_tag", "INFO ONLY"))

        tournament = safe(prediction.get("tournament"))
        surface = safe(prediction.get("surface"))
        best_of = safe(prediction.get("best_of"))
        sets_label = safe(resolve_sets_label(prediction))
        sets_probability = pct(prediction.get("sets_probability"))

        most_likely_score = safe(
            prediction.get("most_likely_score"),
            default="-",
        )

        description_text = (
            f"Pick: {pick}\n"
            f"Opponent: {opponent}\n"
            f"Tournament: {tournament}\n"
            f"Surface: {surface}\n"
            f"Best of: {best_of}\n"
            f"Win probability: {probability}\n"
            f"Odds: {odd}\n"
            f"Expected sets: {expected_sets}\n"
            f"{sets_label}: {sets_probability}\n"
            f"Most likely score: {most_likely_score}\n"
            f"Tag: {bet_tag}\n\n"
            f"{HEADER_SUBTITLE}\n"
            f"{FOOTER_TEXT}"
        )

        description = html.escape(description_text)

        items.append(f"""
<item>
<title>{pick} to win vs {opponent}</title>
<link>{link}</link>
<description>{description}</description>
<pubDate>{now}</pubDate>
</item>
""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>{html.escape(title)}</title>
<link>{link}</link>
<description>{html.escape(HEADER_TITLE)}</description>
{''.join(items)}
</channel>
</rss>
"""


def write_rss(predictions, title, link, destination):
    xml = render_rss(
        predictions=predictions,
        title=title,
        link=link,
    )

    directory = os.path.dirname(destination)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(destination, "w", encoding="utf-8") as file:
        file.write(xml)
