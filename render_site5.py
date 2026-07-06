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


def safe_float(value):
    try:
        if value is None:
            return None

        if value == "":
            return None

        return float(value)

    except Exception:
        return None


def pct(value):
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "-"


def pct_plain(value):
    try:
        return f"{float(value):.1f}"
    except Exception:
        return "-"


def odds(value):
    try:
        if value is None or value == "":
            return "-"

        return f"{float(value):.2f}"

    except Exception:
        return "-"


def html_link(url, label):
    return (
        f'">'
        f'{safe(label)}'
        f'</a>'
    )


def render_nav():
    links = [
        html_link(f"{BASE_URL}/", "Corq"),
        html_link(f"{BASE_URL}/BsT/", "Thinq"),
        html_link(f"{BASE_URL}/all/", "ALL"),
        html_link(f"{BASE_URL}/results/", "RESULTS"),
    ]

    return f"""
<nav class="nav" aria-label="Main navigation">
    {" ".join(links)}
</nav>
"""


def format_match_meta(prediction):
    parts = []

    tournament = prediction.get("tournament")
    surface = prediction.get("surface")
    best_of = prediction.get("best_of")

    if tournament:
        parts.append(str(tournament))

    if surface:
        parts.append(str(surface))

    if best_of:
        parts.append(f"BO{best_of}")

    return " • ".join(parts)


def resolve_sets_label(prediction):
    label = prediction.get("sets_probability_label")

    if label:
        return str(label)

    try:
        if int(prediction.get("best_of")) == 5:
            return "5 Sets"
    except Exception:
        pass

    return "3 Sets"


def normalize_probability_for_display(value):
    number = safe_float(value)

    if number is None:
        return None

    if number <= 1.0:
        return number * 100.0

    return number


def format_pct_points(value):
    if value is None:
        return "-"

    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "-"


def resolve_ai_metrics(prediction):
    corq_pct = normalize_probability_for_display(
        prediction.get("corq_ai_probability")
        or prediction.get("corq_display_probability")
        or prediction.get("probability")
    )

    thinq_pct = normalize_probability_for_display(
        prediction.get("bst_ai_probability")
    )

    ai_match = safe_float(
        prediction.get("ai_match")
    )

    return {
        "corq_pct": corq_pct,
        "thinq_pct": thinq_pct,
        "ai_match": ai_match,
    }


def resolve_ai_delta(metrics):
    corq_pct = metrics.get("corq_pct")
    thinq_pct = metrics.get("thinq_pct")

    if corq_pct is None or thinq_pct is None:
        return {
            "label": "Thinq unavailable",
            "class": "delta-muted",
        }

    gap = float(thinq_pct) - float(corq_pct)

    if abs(gap) < 0.05:
        return {
            "label": "Even",
            "class": "delta-even",
        }

    if gap > 0:
        return {
            "label": f"Thinq +{gap:.1f}%",
            "class": "delta-thinq",
        }

    return {
        "label": f"Corq +{abs(gap):.1f}%",
        "class": "delta-corq",
    }


def resolve_marq_signal(prediction):
    signal = prediction.get("marq_ai_signal")
    score = prediction.get("marq_ai_score")

    if score is None:
        return "NO MARKET DATA"

    if not signal:
        return "NEUTRAL"

    return str(signal).upper()


def metric_row(label, value):
    return f"""
            <div class="metric-row">
                <span>{safe(label)}</span>
                <strong>{safe(value)}</strong>
            </div>
"""


def resolve_model_view(title, subtitle):
    text = f"{title or ''} {subtitle or ''}".lower()

    if "bst" in text:
        return "thinq"

    if "thinq" in text:
        return "thinq"

    return "corq"


def render_data_ai_box(prediction, model_view="corq"):
    status = prediction.get("bst_ai_status")
    metrics = resolve_ai_metrics(prediction)

    corq_display = format_pct_points(metrics["corq_pct"])
    thinq_display = format_pct_points(metrics["thinq_pct"])
    ai_match_display = format_pct_points(metrics["ai_match"])

    if status != "OK":
        thinq_display = "No data"
        ai_match_display = "-"
        delta = {
            "label": "Thinq unavailable",
            "class": "delta-muted",
        }
    else:
        delta = resolve_ai_delta(metrics)

    if model_view == "thinq":
        rows = (
            metric_row("Thinq AI", thinq_display)
            + metric_row("Corq AI", corq_display)
            + metric_row("AI Match", ai_match_display)
        )
    else:
        rows = (
            metric_row("Corq AI", corq_display)
            + metric_row("Thinq AI", thinq_display)
            + metric_row("AI Match", ai_match_display)
        )

    return f"""
        <div class="intel-panel data-ai-panel">
            <div class="panel-title">DATA AI</div>

            {rows}

            <div class="ai-delta {safe(delta['class'])}">
                {safe(delta['label'])}
            </div>
        </div>
"""


def render_marq_ai_box(prediction):
    marq_signal = resolve_marq_signal(prediction)

    signal_class_map = {
        "BULLISH": "market-bullish",
        "SUPPORT": "market-support",
        "NEUTRAL": "market-neutral",
        "CAUTION": "market-caution",
        "BEARISH": "market-bearish",
        "NO MARKET DATA": "market-unavailable",
    }

    signal_class = signal_class_map.get(
        marq_signal,
        "market-neutral",
    )

    score = prediction.get("marq_ai_score")

    if score is None:
        display_signal = "No market data"
        score_html = ""
    else:
        display_signal = marq_signal
        score_html = metric_row("Score", pct_plain(score))

    return f"""
        <div class="intel-panel marq-panel">
            <div class="panel-title">MARQ AI</div>
            {score_html}
            <div class="market-badge {signal_class}">
                {safe(display_signal)}
            </div>
        </div>
"""


def render_sets_box(
    expected_sets,
    sets_probability_label,
    sets_probability,
    most_likely_html,
):
    return f"""
        <div class="intel-panel sets-panel">
            <div class="panel-title">SETS</div>

            {metric_row("Sets", expected_sets)}
            {metric_row(sets_probability_label, sets_probability)}
            {most_likely_html}
        </div>
"""


def render_match_intelligence(
    prediction,
    expected_sets,
    sets_probability_label,
    sets_probability,
    most_likely_html,
    model_view="corq",
):
    return f"""
        <div class="intel-title">Match Intelligence</div>

        <div class="intel-layout">
            {render_data_ai_box(prediction, model_view=model_view)}
            {render_marq_ai_box(prediction)}
            {render_sets_box(expected_sets, sets_probability_label, sets_probability, most_likely_html)}
        </div>
"""


def render_summary(predictions):
    count = len(predictions)

    probabilities = []
    ai_match_values = []

    for prediction in predictions:
        try:
            if prediction.get("probability") is not None:
                probabilities.append(float(prediction.get("probability")))
        except Exception:
            pass

        try:
            if prediction.get("ai_match") is not None:
                ai_match_values.append(float(prediction.get("ai_match")))
        except Exception:
            pass

    avg_probability = "-"
    avg_ai_match = "-"

    if probabilities:
        avg_probability = f"{sum(probabilities) / len(probabilities) * 100:.1f}%"

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


def render_rows(predictions, model_view="corq"):
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
            most_likely_html = metric_row("Score", most_likely_score)

        intelligence_html = render_match_intelligence(
            prediction=prediction,
            expected_sets=expected_sets,
            sets_probability_label=sets_probability_label,
            sets_probability=sets_probability,
            most_likely_html=most_likely_html,
            model_view=model_view,
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
        {intelligence_html}
    </td>
</tr>
""")

    return "\n".join(rows)


def render_page(predictions, title, subtitle):
    model_view = resolve_model_view(
        title,
        subtitle,
    )

    rows = render_rows(
        predictions,
        model_view=model_view,
    )

    summary = render_summary(predictions)
    nav = render_nav()
    page_title = safe(title or SITE_TITLE)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>{page_title}</title>

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
    font-size: 18px;
    line-height: 1.18;
    font-weight: 900;
}}

.pick-sub {{
    color: var(--green);
    font-size: 13px;
    line-height: 1.15;
    margin-top: 4px;
    font-weight: 800;
}}

.match-name {{
    color: var(--muted);
    font-size: 12px;
    line-height: 1.2;
    margin-top: 7px;
}}

.match-meta {{
    color: var(--blue);
    font-size: 12px;
    line-height: 1.2;
    margin-top: 5px;
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
    line-height: 1.45;
    min-width: 390px;
}}

.intel-title {{
    margin-bottom: 6px;
    color: var(--muted);
    font-size: 11px;
    font-weight: 900;
    letter-spacing: 0.04em;
    text-transform: uppercase;
}}

.intel-layout {{
    display: grid;
    grid-template-columns: minmax(110px, 1fr) minmax(110px, 1fr) minmax(130px, 1.15fr);
    gap: 8px;
    align-items: stretch;
}}

.intel-panel {{
    min-height: 92px;
    padding: 8px 9px;
    border-radius: 8px;
    font-size: 11px;
    line-height: 1.35;
    background: rgba(100, 116, 139, 0.14);
    border: 1px solid rgba(100, 116, 139, 0.38);
}}

.panel-title {{
    color: #ffffff;
    font-size: 10px;
    font-weight: 900;
    text-transform: uppercase;
    letter-spacing: 0.05em;
    margin-bottom: 6px;
}}

.metric-row {{
    display: grid;
    grid-template-columns: 58px auto;
    column-gap: 7px;
    align-items: center;
    margin-top: 3px;
}}

.metric-row span {{
    color: var(--muted);
}}

.metric-row strong {{
    text-align: right;
    color: var(--text);
    font-weight: 900;
}}

.ai-delta {{
    margin-top: 7px;
    text-align: right;
    font-size: 10px;
    font-weight: 900;
}}

.delta-thinq {{
    color: var(--blue);
}}

.delta-corq {{
    color: var(--orange);
}}

.delta-even {{
    color: var(--muted);
}}

.delta-muted {{
    color: var(--muted);
}}

.market-badge {{
    display: inline-block;
    margin-top: 8px;
    padding: 5px 10px;
    border-radius: 5px;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 0.05em;
    text-transform: uppercase;
}}

.market-bullish {{
    color: #22c55e;
    border: 1px solid rgba(34,197,94,.45);
    background: rgba(34,197,94,.08);
}}

.market-support {{
    color: #38bdf8;
    border: 1px solid rgba(56,189,248,.45);
    background: rgba(56,189,248,.08);
}}

.market-neutral {{
    color: #94a3b8;
    border: 1px solid rgba(148,163,184,.45);
    background: rgba(148,163,184,.08);
}}

.market-caution {{
    color: #fb923c;
    border: 1px solid rgba(251,146,60,.45);
    background: rgba(251,146,60,.08);
}}

.market-bearish {{
    color: #ef4444;
    border: 1px solid rgba(239,68,68,.45);
    background: rgba(239,68,68,.08);
}}

.market-unavailable {{
    color: #94a3b8;
    border: 1px solid rgba(148,163,184,.35);
    background: rgba(148,163,184,.05);
    text-transform: none;
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

@media (max-width: 700px) {{
    .wrapper {{
        padding: 16px;
    }}

    .summary {{
        grid-template-columns: 1fr;
    }}

    .intel-layout {{
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

        tournament = safe(prediction.get("tournament"))
        surface = safe(prediction.get("surface"))
        best_of = safe(prediction.get("best_of"))
        sets_label = safe(resolve_sets_label(prediction))
        sets_probability = pct(prediction.get("sets_probability"))

        most_likely_score = safe(
            prediction.get("most_likely_score"),
            default="-",
        )

        metrics = resolve_ai_metrics(prediction)
        corq_ai = format_pct_points(metrics["corq_pct"])
        thinq_ai = format_pct_points(metrics["thinq_pct"])
        ai_match = format_pct_points(metrics["ai_match"])
        delta = resolve_ai_delta(metrics)
        marq_signal = resolve_marq_signal(prediction)
        marq_score = pct_plain(prediction.get("marq_ai_score"))

        description_text = (
            f"Pick: {pick}\n"
            f"Opponent: {opponent}\n"
            f"Tournament: {tournament}\n"
            f"Surface: {surface}\n"
            f"Best of: {best_of}\n"
            f"Win probability: {probability}\n"
            f"Odds: {odd}\n"
            f"Corq AI: {corq_ai}\n"
            f"Thinq AI: {thinq_ai}\n"
            f"AI Match: {ai_match}\n"
            f"AI Difference: {delta['label']}\n"
            f"Marq AI: {marq_score}\n"
            f"Market Signal: {marq_signal}\n"
            f"Expected sets: {expected_sets}\n"
            f"{sets_label}: {sets_probability}\n"
            f"Most likely score: {most_likely_score}\n\n"
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
