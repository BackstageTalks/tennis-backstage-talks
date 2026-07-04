import os
import html
from datetime import datetime, timezone


SITE_TITLE = "Backstage Talks Statistical Engine"
BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks"

HEADER_TITLE = "BackstageTalks Statistical Engine"
HEADER_SUBTITLE = "This data is provided for informational and analytical purposes only"
FOOTER_TEXT = "Powered by BackstageTalks Statistical Engine"


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


def pct_plain(value):
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "-"


def signed_pct(value):
    try:
        number = float(value)

        if number > 0:
            return f"+{number:.1f}%"

        if number < 0:
            return f"{number:.1f}%"

        return "0.0%"

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


def html_link(url, label):
    lt = chr(60)
    gt = chr(62)

    return (
        f'{lt}a href="{safe(url)}"{gt}'
        f'{safe(label)}'
        f'{lt}/a{gt}'
    )


def render_nav():
    links = [
        html_link(f"{BASE_URL}/", "TOP5"),
        html_link(f"{BASE_URL}/all/", "ALL"),
        html_link(f"{BASE_URL}/results/", "RESULTS"),
    ]

    return f"""
<nav class="nav" aria-label="Main navigation">
    {" ".join(links)}
</nav>
"""


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


def normalize_ai_color(value):
    text = str(value or "").lower().strip()

    if text in ["green", "orange", "red", "gray"]:
        return text

    return "gray"


def render_ai_match(prediction):
    status = prediction.get("bst_ai_status")
    bst_probability = prediction.get("bst_ai_probability")
    ai_match = prediction.get("ai_match")

    if status != "OK" or bst_probability is None or ai_match is None:
        reason = prediction.get("bst_ai_reason") or status or "No data"

        return f"""
        <div class="ai-box ai-match-gray">
            <div class="ai-main">AI Match: No data</div>
            <div class="ai-sub">BsT AI: No data</div>
            <div class="ai-sub">Reason: {safe(reason)}</div>
        </div>
"""

    corq_probability = prediction.get("corq_ai_probability")

    if corq_probability is None:
        corq_probability = prediction.get("probability")

    ai_color = normalize_ai_color(
        prediction.get("ai_match_color")
    )

    ai_direction_match = prediction.get("ai_direction_match")
    ai_signed_gap = prediction.get("ai_signed_gap")
    ai_lean = str(prediction.get("ai_lean") or "").upper()

    corq_text = pct(corq_probability)
    bst_text = pct(bst_probability)
    match_text = pct_plain(ai_match)

    if ai_direction_match is False:
        lean_text = "Direction conflict"

    else:
        try:
            gap_number = float(ai_signed_gap)

            if ai_lean == "CORQ" and gap_number > 0:
                lean_text = f"Corq AI {signed_pct(gap_number)}"

            elif ai_lean == "BST" and gap_number < 0:
                lean_text = f"BsT AI +{abs(gap_number):.1f}%"

            else:
                lean_text = "Even"

        except Exception:
            lean_text = "No lean"

    return f"""
        <div class="ai-box ai-match-{ai_color}">
            <div class="ai-main">AI Match: {safe(match_text)}</div>
            <div class="ai-sub">Corq AI: {safe(corq_text)} · BsT AI: {safe(bst_text)}</div>
            <div class="ai-sub">Lean: {safe(lean_text)}</div>
        </div>
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

    ai_match_values = []

    for prediction in predictions:
        value = prediction.get("ai_match")

        if value is None:
            continue

        try:
            ai_match_values.append(float(value))
        except Exception:
            continue

    avg_probability = "-"
    avg_odds = "-"
    avg_ai_match = "-"

    if probabilities:
        avg_probability = f"{sum(probabilities) / len(probabilities) * 100:.1f}%"

    if odds_values:
        avg_odds = f"{sum(odds_values) / len(odds_values):.2f}"

    if ai_match_values:
        avg_ai_match = f"{sum(ai_match_values) / len(ai_match_values):.1f}%"

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
        <div class="summary-label">Average AI Match</div>
        <div class="summary-value">{avg_ai_match}</div>
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
        sets_probability_label = safe(
            resolve_sets_label(prediction)
        )

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

        ai_match_html = render_ai_match(
            prediction
        )

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

        {ai_match_html}

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
    --orange: #fb923c;
    --red: #ef4444;
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
    grid-template-columns: minmax(560px, 1fr) auto;
    gap: 40px;
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
    max-width: 800px;
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
    font-weight: 900;
    font-size: 14px;
    letter-spacing: 0.04em;
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
    color: var(--muted);
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
    min-width: 1040px;
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
    min-width: 260px;
}}

.intel-label {{
    color: var(--muted);
    font-size: 12px;
    margin-right: 4px;
}}

.ai-box {{
    margin-top: 10px;
    padding: 9px 10px;
    border-radius: 12px;
    font-size: 12px;
    line-height: 1.45;
}}

.ai-main {{
    font-weight: 900;
    margin-bottom: 3px;
}}

.ai-sub {{
    font-size: 11px;
    color: var(--muted);
}}

.ai-match-green {{
    background: rgba(34, 197, 94, 0.14);
    border: 1px solid rgba(34, 197, 94, 0.45);
}}

.ai-match-green .ai-main {{
    color: var(--green);
}}

.ai-match-orange {{
    background: rgba(251, 146, 60, 0.14);
    border: 1px solid rgba(251, 146, 60, 0.45);
}}

.ai-match-orange .ai-main {{
    color: var(--orange);
}}

.ai-match-red {{
    background: rgba(239, 68, 68, 0.14);
    border: 1px solid rgba(239, 68, 68, 0.45);
}}

.ai-match-red .ai-main {{
    color: var(--red);
}}

.ai-match-gray {{
    background: rgba(100, 116, 139, 0.18);
    border: 1px solid rgba(100, 116, 139, 0.45);
}}

.ai-match-gray .ai-main {{
    color: var(--muted);
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

@media (max-width: 1050px) {{
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

        bst_status = prediction.get("bst_ai_status")

        if bst_status == "OK":
            corq_ai = pct(
                prediction.get("corq_ai_probability")
                or prediction.get("probability")
            )
            bst_ai = pct(prediction.get("bst_ai_probability"))
            ai_match = pct_plain(prediction.get("ai_match"))
            ai_lean = safe(prediction.get("ai_lean"), default="-")
            ai_signed_gap = signed_pct(prediction.get("ai_signed_gap"))

            ai_text = (
                f"Corq AI: {corq_ai}\n"
                f"BsT AI: {bst_ai}\n"
                f"AI Match: {ai_match}\n"
                f"AI Lean: {ai_lean} {ai_signed_gap}\n"
            )

        else:
            ai_text = (
                "Corq AI: available\n"
                "BsT AI: No data\n"
                "AI Match: No data\n"
            )

        description_text = (
            f"Pick: {pick}\n"
            f"Opponent: {opponent}\n"
            f"Tournament: {tournament}\n"
            f"Surface: {surface}\n"
            f"Best of: {best_of}\n"
            f"Win probability: {probability}\n"
            f"Odds: {odd}\n"
            f"{ai_text}"
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
