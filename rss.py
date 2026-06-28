import os
import json
import datetime
import html
import re

BASE = "https://backstagetalks.github.io/tennis-backstage-talks/"


def safe_slug(value):
    value = str(value).lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = value.strip("-")
    return value[:80] if value else "pick"


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


def clean_tournament_name(value):
    value = str(value or "").strip()

    hidden_values = [
        "",
        "SportScore Tennis",
        "Tennis",
        "Unknown",
        "None",
        "null"
    ]

    if value in hidden_values:
        return ""

    return value


def latest_predictions():
    os.makedirs("public", exist_ok=True)

    files = [
        f for f in os.listdir("public")
        if f.startswith("predictions_") and f.endswith(".json")
    ]

    print("Prediction files found:", files)

    if not files:
        return []

    latest = sorted(files)[-1]
    path = os.path.join("public", latest)

    print("RSS using prediction file:", path)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def label_for_pick(probability, signals=None, index=1, market_agrees=False, value_edge=None):
    if signals is None:
        signals = []

    if index == 1:
        return "🔥 TOP PICK"

    if market_agrees and probability >= 0.56:
        return "✅ SAFE PICK"

    if value_edge is not None and value_edge >= 0.04:
        return "💎 VALUE PICK"

    if "🎯 Strong over 0.5 set signal" in signals:
        return "🎯 SET SAFETY PICK"

    if probability >= 0.58:
        return "✅ SAFE PICK"

    return "⚖️ QUALIFIED PICK"


def risk_for_pick(probability, market_agrees=False):
    if probability >= 0.65 and market_agrees:
        return "LOW"

    if probability >= 0.58:
        return "MEDIUM"

    return "HIGH"


def signal_text(signals):
    if not signals:
        return "No extra signal"

    return ", ".join(str(s) for s in signals)


def alternative_text(alt_bets):
    if not alt_bets:
        return "No qualified alternative signal"

    parts = []

    for alt in alt_bets:
        market = alt.get("market", "")
        pick = alt.get("pick", "")
        probability = alt.get("probability")
        confidence = alt.get("confidence", "")
        sample = alt.get("sample", "")
        note = alt.get("note", "")

        if probability is not None:
            probability_text = f"{pct(probability)}%"
        else:
            probability_text = "N/A"

        parts.append(
            f"{market}: {pick} | Probability: {probability_text} | "
            f"Confidence: {confidence} | Sample: {sample} | {note}"
        )

    return " / ".join(parts)


def create_pick_page(index, prediction, label, risk, page_filename):
    os.makedirs("public/picks", exist_ok=True)

    pick = str(prediction.get("pick", prediction.get("player1", "Unknown")))
    opponent = str(prediction.get("opponent", prediction.get("player2", "Unknown")))

    player1 = str(prediction.get("player1", "Unknown"))
    player2 = str(prediction.get("player2", "Unknown"))

    tournament = clean_tournament_name(prediction.get("tournament", ""))

    probability = float(prediction.get("probability", 0))
    confidence = float(prediction.get("confidence", 0))
    model_edge = confidence

    odds = prediction.get("odds", "")
    odds_player1 = prediction.get("odds_player1", "")
    odds_player2 = prediction.get("odds_player2", "")
    odds_source = prediction.get("odds_source", "")

    market_probability = prediction.get("market_probability")
    implied_probability = prediction.get("implied_probability")
    market_agrees = prediction.get("market_agrees", False)
    value_edge = prediction.get("bookie_value_edge")
    bookie_signal = prediction.get("bookie_signal", "")

    match_start = format_match_time(prediction.get("match_start", ""))
    surface = prediction.get("surface", "Unknown")

    signals = prediction.get("extra_signals", [])
    alt_bets = prediction.get("alternative_bets", [])

    pick_metrics = prediction.get("pick_metrics", {})

    avg_aces = pick_metrics.get("avg_aces")
    ace_rate = pick_metrics.get("ace_rate")
    over_set_rate = pick_metrics.get("at_least_one_set_rate")
    form_win_rate = pick_metrics.get("win_rate")
    sample = pick_metrics.get("sample", 0)

    tournament_line = ""
    if tournament:
        tournament_line = f"""
        <div class="data-row">
            <span>Tournament</span>
            <strong>{html.escape(tournament)}</strong>
        </div>
        """

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>{html.escape(label)}: {html.escape(pick)} to win</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
* {{
    box-sizing: border-box;
}}

body {{
    font-family: Arial, sans-serif;
    background: #160f0f;
    color: #f4f4f4;
    margin: 0;
    padding: 16px;
}}

.container {{
    max-width: 780px;
    margin: 0 auto;
}}

.back-link {{
    display: inline-block;
    margin-bottom: 14px;
    color: #9fc8ff;
    text-decoration: none;
    font-size: 15px;
}}

.card {{
    background: #211818;
    border-radius: 18px;
    padding: 20px;
    overflow: hidden;
}}

.badge {{
    display: inline-block;
    padding: 7px 11px;
    border-radius: 999px;
    background: #2d6cdf;
    color: #ffffff;
    font-weight: bold;
    margin-bottom: 14px;
    font-size: 14px;
}}

h1 {{
    margin: 0 0 8px 0;
    font-size: 28px;
    line-height: 1.2;
}}

.subtitle {{
    color: #bdbdbd;
    font-size: 15px;
    line-height: 1.5;
    margin-bottom: 18px;
}}

.metric-grid {{
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 10px;
    margin-bottom: 20px;
}}

.metric {{
    background: #2d2222;
    border-radius: 14px;
    padding: 14px;
    min-height: 78px;
}}

.metric span {{
    display: block;
    color: #aaa;
    font-size: 13px;
    margin-bottom: 6px;
}}

.metric strong {{
    display: block;
    font-size: 22px;
    line-height: 1.2;
    word-break: break-word;
}}

h2 {{
    font-size: 18px;
    margin: 22px 0 10px;
}}

.section {{
    background: #2a2020;
    border-radius: 14px;
    padding: 12px 14px;
    margin-bottom: 14px;
}}

.data-row {{
    display: grid;
    grid-template-columns: 42% 58%;
    gap: 10px;
    padding: 9px 0;
    border-bottom: 1px solid #3a2d2d;
}}

.data-row:last-child {{
    border-bottom: none;
}}

.data-row span {{
    color: #aaa;
    font-size: 14px;
}}

.data-row strong {{
    text-align: right;
    font-size: 14px;
    line-height: 1.35;
    word-break: break-word;
}}

.text-box {{
    background: #2d2222;
    border-radius: 14px;
    padding: 14px;
    line-height: 1.55;
    color: #f2f2f2;
    word-break: break-word;
}}

.footer-note {{
    margin-top: 22px;
    padding: 14px;
    border-radius: 14px;
    background: #181818;
    color: #bdbdbd;
    font-size: 13px;
    line-height: 1.5;
}}

@media (max-width: 520px) {{
    body {{
        padding: 12px;
    }}

    .card {{
        padding: 16px;
    }}

    h1 {{
        font-size: 24px;
    }}

    .metric-grid {{
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 8px;
    }}

    .metric {{
        padding: 12px;
    }}

    .metric strong {{
        font-size: 19px;
    }}

    .data-row {{
        display: block;
    }}

    .data-row strong {{
        display: block;
        text-align: left;
        margin-top: 3px;
    }}
}}
</style>
</head>

<body>
<div class="container">

    <a class="back-link" href="../index.html">← Back to all picks</a>

    <div class="card">
        <div class="badge">#{index} {html.escape(label)}</div>

        <h1>{html.escape(pick)} to win</h1>

        <div class="subtitle">
       html.escape(opponent)}<br>
            {html.escape(match_start)}
        </div>

        <div class="metric-grid">
            <div class="metric">
                <span>Win probability</span>
                <strong>{pct(probability)}%</strong>
            </div>

            <div class="metric">
                <span>Odds</span>
                <strong>{html.escape(str(odds))}</strong>
            </div>

            <div class="metric">
                <span>Risk</span>
                <strong>{html.escape(risk)}</strong>
            </div>

            <div class="metric">
                <span>Model edge</span>
                <strong>+{pct(model_edge)}%</strong>
            </div>
        </div>

        <h2>Pick details</h2>
        <div class="section">
            <div class="data-row">
                <span>Pick</span>
                <strong>{html.escape(pick)}</strong>
            </div>

            <div class="data-row">
                <span>Opponent</span>
                <strong>{html.escape(opponent)}</strong>
            </div>

            <div class="data-row">
                <span>Match</span>
                <strong>{html.escape(player1)} vs {html.escape(player2)}</strong>
            </div>

            {tournament_line}

            <div class="data-row">
                <span>Surface</span>
                <strong>{html.escape(str(surface))}</strong>
            </div>
        </div>

        <h2>Market</h2>
        <div class="section">
            <div class="data-row">
                <span>Pick odds</span>
                <strong>{html.escape(str(odds))}</strong>
            </div>

            <div class="data-row">
                <span>Odds player1 / player2</span>
                <strong>{html.escape(str(odds_player1))} / {html.escape(str(odds_player2))}</strong>
            </div>

            <div class="data-row">
                <span>Fair market probability</span>
                <strong>{pct(market_probability) if market_probability is not None else "N/A"}%</strong>
            </div>

            <div class="data-row">
                <span>Value edge</span>
                <strong>{pct(value_edge) if value_edge is not None else "N/A"}%</strong>
            </div>

            <div class="data-row">
                <span>Market agrees</span>
                <strong>{html.escape(str(market_agrees))}</strong>
            </div>

            <div class="data-row">
                <span>Bookie signal</span>
                <strong>{html.escape(str(bookie_signal))}</strong>
            </div>

            <div class="data-row">
                <span>Odds source</span>
                <strong>{html.escape(str(odds_source))}</strong>
            </div>

            <div class="data-row">
                <span>Raw implied probability</span>
                <strong>{pct(implied_probability) if implied_probability is not None else "N/A"}%</strong>
            </div>
        </div>

        <h2>Form & stats</h2>
        <div class="section">
            <div class="data-row">
                <span>Recent / surface form</span>
                <strong>{pct(form_win_rate) if form_win_rate is not None else "N/A"}%</strong>
            </div>

            <div class="data-row">
                <span>Over 0.5 set rate</span>
                <strong>{pct(over_set_rate) if over_set_rate is not None else "N/A"}%</strong>
            </div>

            <div class="data-row">
                <span>Avg aces</span>
                <strong>{html.escape(str(avg_aces)) if avg_aces is not None else "N/A"}</strong>
            </div>

            <div class="data-row">
                <span>Ace rate</span>
                <strong>{pct(ace_rate) if ace_rate is not None else "N/A"}%</strong>
            </div>

            <div class="data-row">
                <span>Historical sample</span>
                <strong>{html.escape(str(sample))} matches</strong>
            </div>
        </div>

        <h2>Signals</h2>
        <div class="text-box">
            {html.escape(signal_text(signals))}
        </div>

        <h2>Alternative signal</h2>
        <div class="text-box">
            {html.escape(alternative_text(alt_bets))}
        </div>

        <div class="footer-note">
            Generated by <strong>BackstageTalks Stat Model</strong> for informational and statistical purposes only
        </div>
    </div>
</div>
</body>
</html>
"""

    path = os.path.join("public", "picks", page_filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(page)

    return f"picks/{page_filename}"


def create_index_page(predictions):
    rows = ""

    for i, prediction in enumerate(predictions, start=1):
        pick = str(prediction.get("pick", prediction.get("player1", "Unknown")))
        opponent = str(prediction.get("opponent", prediction.get("player2", "Unknown")))
        probability = float(prediction.get("probability", 0))
        odds = prediction.get("odds", "")
        page_url = prediction.get("_page_url", "#")

        rows += f"""
        <tr>
            <td>#{i}</td>
            <td>">{html.escape(pick)} to win</a></td>
            <td>{html.escape(opponent)}</td>
            <td>{pct(probability)}%</td>
            <td>{html.escape(str(odds))}</td>
        </tr>
        """

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Backstage Talks Tennis Picks</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

<style>
body {{
    font-family: Arial, sans-serif;
    background: #160f0f;
    color: #f4f4f4;
    margin: 0;
    padding: 20px;
}}

.container {{
    max-width: 900px;
    margin: 0 auto;
}}

table {{
    width: 100%;
    border-collapse: collapse;
    background: #211818;
    border-radius: 14px;
    overflow: hidden;
}}

th, td {{
    padding: 12px;
    border-bottom: 1px solid #372929;
    text-align: left;
}}

th {{
    color: #bbb;
}}

a {{
    color: #9fc8ff;
}}

.note {{
    color: #aaa;
    margin-top: 16px;
    font-size: 14px;
}}

@media (max-width: 520px) {{
    th:nth-child(3), td:nth-child(3) {{
        display: none;
    }}

    th, td {{
        padding: 10px;
        font-size: 14px;
    }}
}}
</style>
</head>

<body>
<div class="container">
    <h1>Backstage Talks Tennis Picks</h1>
    <p>Daily model picks based on match data, market odds and historical player stats.</p>

    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Pick</th>
                <th>Opponent</th>
                <th>Win %</th>
                <th>Odds</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>

    <p class="note">Generated by BackstageTalks Stat Model for informational and statistical purposes only</p>
</div>
</body>
</html>
"""

    with open("public/index.html", "w", encoding="utf-8") as f:
        f.write(page)


def generate_rss():
    predictions = latest_predictions()

    os.makedirs("public/picks", exist_ok=True)

    items = ""

    for i, prediction in enumerate(predictions, start=1):
        pick = str(prediction.get("pick", prediction.get("player1", "Unknown")))
        opponent = str(prediction.get("opponent", prediction.get("player2", "Unknown")))

        probability = float(prediction.get("probability", 0))
        odds = prediction.get("odds", "")
        match_start = format_match_time(prediction.get("match_start", ""))

        market_agrees = prediction.get("market_agrees", False)
        value_edge = prediction.get("bookie_value_edge")
        signals = prediction.get("extra_signals", [])

        label = label_for_pick(
            probability=probability,
            signals=signals,
            index=i,
            market_agrees=market_agrees,
            value_edge=value_edge
        )

        risk = risk_for_pick(probability, market_agrees)

        slug = safe_slug(f"{i}-{pick}-vs-{opponent}")
        page_filename = f"{datetime.date.today().isoformat()}-{slug}.html"

        relative_page = create_pick_page(
            index=i,
            prediction=prediction,
            label=label,
            risk=risk,
            page_filename=page_filename
        )

        full_link = BASE + relative_page
        prediction["_page_url"] = relative_page

        title = f"#{i} {label}: {pick} to win"

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

        guid = f"{pick}-{opponent}-{datetime.date.today().isoformat()}-{i}"

        items += f"""
<item>
<title>{html.escape(title)}</title>
<link>{html.escape(full_link)}</link>
<guid isPermaLink="false">{html.escape(guid)}</guid>
<pubDate>{datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
<description>{html.escape(desc)}</description>
</item>
"""

    create_index_page(predictions)

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Backstage Talks Tennis Picks</title>
<link>{BASE}</link>
<description>Daily tennis picks - compact RSS with full details on pick pages</description>
{items}
</channel>
</rss>
"""

    with open("public/tennis.xml", "w", encoding="utf-8") as f:
        f.write(rss)

    print("RSS GENERATED:", len(predictions), "items")
    print("RSS PREVIEW:")
    print(rss[:2500])


if __name__ == "__main__":
    generate_rss()
