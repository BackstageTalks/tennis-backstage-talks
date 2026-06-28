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


def pct(value):
    try:
        return round(float(value) * 100, 1)
    except Exception:
        return 0


def label_for_pick(probability, signals, index, market_agrees, value_edge):
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


def risk_for_pick(probability, market_agrees):
    if probability >= 0.65 and market_agrees:
        return "LOW"

    if probability >= 0.58:
        return "MEDIUM"

    return "HIGH"


def format_alt_bets_html(alt_bets):
    if not alt_bets:
        return "<p>No qualified alternative market signal.</p>"

    rows = ""

    for alt in alt_bets:
        market = html.escape(str(alt.get("market", "")))
        pick = html.escape(str(alt.get("pick", "")))
        probability = alt.get("probability")
        confidence = html.escape(str(alt.get("confidence", "")))
        sample = html.escape(str(alt.get("sample", "")))
        note = html.escape(str(alt.get("note", "")))

        if probability is not None:
            probability_text = f"{pct(probability)}%"
        else:
            probability_text = "N/A"

        rows += f"""
        <tr>
            <td>{market}</td>
            <td>{pick}</td>
            <td>{probability_text}</td>
            <td>{confidence}</td>
            <td>{sample}</td>
            <td>{note}</td>
        </tr>
        """

    return f"""
    <table>
        <thead>
            <tr>
                <th>Market / Signal</th>
                <th>Pick</th>
                <th>Probability</th>
                <th>Confidence</th>
                <th>Sample</th>
                <th>Note</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>
    """


def create_pick_page(index, p, label, risk, page_filename):
    os.makedirs("public/picks", exist_ok=True)

    pick = str(p.get("pick", p.get("player1", "Unknown")))
    opponent = str(p.get("opponent", p.get("player2", "Unknown")))

    player1 = str(p.get("player1", "Unknown"))
    player2 = str(p.get("player2", "Unknown"))
    tournament = str(p.get("tournament", "Tennis"))

    probability = float(p.get("probability", 0))
    confidence = float(p.get("confidence", 0))

    odds = p.get("odds", "")
    odds_player1 = p.get("odds_player1", "")
    odds_player2 = p.get("odds_player2", "")
    odds_source = p.get("odds_source", "")

    market_probability = p.get("market_probability")
    implied_probability = p.get("implied_probability")
    market_agrees = p.get("market_agrees", False)
    value_edge = p.get("bookie_value_edge")
    bookie_signal = p.get("bookie_signal", "")
    overround = p.get("overround")

    match_start = p.get("match_start", "")
    surface = p.get("surface", "Unknown")

    signals = p.get("extra_signals", [])
    alt_bets = p.get("alternative_bets", [])

    pick_metrics = p.get("pick_metrics", {})
    avg_aces = pick_metrics.get("avg_aces")
    ace_rate = pick_metrics.get("ace_rate")
    at_least_one_set_rate = pick_metrics.get("at_least_one_set_rate")
    form_win_rate = pick_metrics.get("win_rate")
    sample = pick_metrics.get("sample", 0)

    signals_html = "".join([f"<li>{html.escape(str(s))}</li>" for s in signals])

    page = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>{html.escape(label)}: {html.escape(pick)} to win</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #111;
            color: #f4f4f4;
            margin: 0;
            padding: 24px;
        }}

        .container {{
            max-width: 900px;
            margin: 0 auto;
        }}

        .card {{
            background: #1f1f1f;
            border-radius: 16px;
            padding: 24px;
            box-shadow: 0 0 20px rgba(0,0,0,0.35);
        }}

        h1 {{
            margin-top: 0;
            font-size: 28px;
        }}

        h2 {{
            margin-top: 32px;
            font-size: 20px;
            color: #ddd;
        }}

        .badge {{
            display: inline-block;
            padding: 8px 12px;
            border-radius: 999px;
            background: #2d6cdf;
            color: white;
            font-weight: bold;
            margin-bottom: 16px;
        }}

        .grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
            gap: 12px;
            margin-top: 16px;
        }}

        .box {{
            background: #2a2a2a;
            padding: 14px;
            border-radius: 12px;
        }}

        .box small {{
            display: block;
            color: #aaa;
            margin-bottom: 6px;
        }}

        .box strong {{
            font-size: 18px;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 12px;
            font-size: 14px;
        }}

        th, td {{
            border-bottom: 1px solid #333;
            padding: 10px;
            text-align: left;
            vertical-align: top;
        }}

        th {{
            color: #bbb;
        }}

        ul {{
            padding-left: 20px;
        }}

        a {{
            color: #7ab7ff;
        }}

        .footer {{
            color: #aaa;
            font-size: 13px;
            margin-top: 28px;
            line-height: 1.5;
        }}

        .disclaimer {{
            background: #332b14;
            color: #ffe9a6;
            padding: 12px;
            border-radius: 10px;
            margin-top: 20px;
            font-size: 14px;
        }}
    </style>
</head>
<body>
<div class="container">
    <div class="card">
        <div class="badge">#{index} {html.escape(label)}</div>

        <h1>{html.escape(pick)} to win</h1>

        <p>
            <strong>Main pick:</strong> {html.escape(pick)} to beat {html.escape(opponent)}<br>
            <strong>Main market:</strong> Match Winner<br>
            <strong>Match:</strong> {html.escape(player1)} vs {html.escape(player2)}<br>
            <strong>Tournament:</strong> {html.escape(tournament)}<br>
            <strong>Match start:</strong> {html.escape(str(match_start))}<br>
            <strong>Surface:</strong> {html.escape(str(surface))}
        </p>

        <div class="grid">
            <div class="box">
                <small>Model win probability</small>
                <strong>{pct(probability)}%</strong>
            </div>
            <div class="box">
                <small>Confidence</small>
                <strong>{pct(confidence)}%</strong>
            </div>
            <div class="box">
                <small>Risk</small>
                <strong>{html.escape(risk)}</strong>
            </div>
            <div class="box">
                <small>Pick odds</small>
                <strong>{html.escape(str(odds))}</strong>
            </div>
        </div>

        <h2>Bookmaker data</h2>
        <div class="grid">
            <div class="box">
                <small>Odds player1 / player2</small>
                <strong>{html.escape(str(odds_player1))} / {html.escape(str(odds_player2))}</strong>
            </div>
            <div class="box">
                <small>Odds source</small>
                <strong>{html.escape(str(odds_source))}</strong>
            </div>
            <div class="box">
                <small>Raw implied probability</small>
                <strong>{pct(implied_probability) if implied_probability is not None else "N/A"}%</strong>
            </div>
            <div class="box">
                <small>Fair market probability</small>
                <strong>{pct(market_probability) if market_probability is not None else "N/A"}%</strong>
            </div>
            <div class="box">
                <small>Bookie value edge</small>
                <strong>{pct(value_edge) if value_edge is not None else "N/A"}%</strong>
            </div>
            <div class="box">
                <small>Market agrees with model</small>
                <strong>{html.escape(str(market_agrees))}</strong>
            </div>
            <div class="box">
                <small>Bookie signal</small>
                <strong>{html.escape(str(bookie_signal))}</strong>
            </div>
            <div class="box">
                <small>Bookie overround</small>
                <strong>{html.escape(str(overround))}</strong>
            </div>
        </div>

        <h2>Form and stats</h2>
        <div class="grid">
            <div class="box">
                <small>Recent / surface form win rate</small>
                <strong>{pct(form_win_rate) if form_win_rate is not None else "N/A"}%</strong>
            </div>
            <div class="box">
                <small>Historical over 0.5 set rate</small>
                <strong>{pct(at_least_one_set_rate) if at_least_one_set_rate is not None else "N/A"}%</strong>
            </div>
            <div class="box">
                <small>Average aces</small>
                <strong>{html.escape(str(avg_aces)) if avg_aces is not None else "N/A"}</strong>
            </div>
            <div class="box">
                <small>Ace rate</small>
                <strong>{pct(ace_rate) if ace_rate is not None else "N/A"}%</strong>
            </div>
            <div class="box">
                <small>Historical sample</small>
                <strong>{html.escape(str(sample))} matches</strong>
            </div>
        </div>

        <h2>Signals</h2>
        <ul>
            {signals_html}
        </ul>

        <h2>Alternative markets / signals</h2>
        {format_alt_bets_html(alt_bets)}

        <div class="disclaimer">
            This is a model-based data signal, not financial advice. Use responsibly.
        </div>

        <div class="footer">
            <a href="../index.html">Back to all picks</a>
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


def create_index_page(predictions = ""

    for i, p in enumerate(predictions, start=1):
        pick = str(p.get("pick", p.get("player1", "Unknown")))
        opponent = str(p.get("opponent", p.get("player2", "Unknown")))
        tournament = str(p.get("tournament", "Tennis"))
        probability = float(p.get("probability", 0))
        odds = p.get("odds", "")
        page_url = p.get("_page_url", "#")

        rows += f"""
        <tr>
            <td>#{i}</td>
            <td>">{html.escape(pick)} to win</a></td>
            <td>{html.escape(opponent)}</td>
            <td>{html.escape(tournament)}</td>
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
            background: #111;
            color: #f4f4f4;
            margin: 0;
            padding: 24px;
        }}

        .container {{
            max-width: 1000px;
            margin: 0 auto;
        }}

        h1 {{
            margin-top: 0;
        }}

        table {{
            width: 100%;
            border-collapse: collapse;
            background: #1f1f1f;
            border-radius: 12px;
            overflow: hidden;
        }}

        th, td {{
            padding: 12px;
            border-bottom: 1px solid #333;
            text-align: left;
        }}

        th {{
            color: #bbb;
        }}

        a {{
            color: #7ab7ff;
        }}

        .note {{
            color: #aaa;
            margin-top: 16px;
            font-size: 14px;
        }}
    </style>
</head>
<body>
<div class="container">
    <h1>Backstage Talks Tennis Picks</h1>
    <p>Daily model picks based on real match data, market odds and historical player stats.</p>

    <table>
        <thead>
            <tr>
                <th>#</th>
                <th>Pick</th>
                <th>Opponent</th>
                <th>Tournament</th>
                <th>Win probability</th>
                <th>Odds</th>
            </tr>
        </thead>
        <tbody>
            {rows}
        </tbody>
    </table>

    <p class="note">Model-based data signals only. Not financial advice.</p>
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

    for i, p in enumerate(predictions, start=1):
        pick = str(p.get("pick", p.get("player1", "Unknown")))
        opponent = str(p.get("opponent", p.get("player2", "Unknown")))
        tournament = str(p.get("tournament", "Tennis"))

        probability = float(p.get("probability", 0))
        confidence = float(p.get("confidence", 0))

        odds = p.get("odds", "")
        market_agrees = p.get("market_agrees", False)
        value_edge = p.get("bookie_value_edge")
        signals = p.get("extra_signals", [])

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
        relative_page = create_pick_page(i, p, label, risk, page_filename)
        full_link = BASE + relative_page

        p["_page_url"] = relative_page

        title = f"#{i} {label}: {pick} to win"

        # KRÁTKY FEEDFLOW TEXT
        desc = (
            f"Pick: {pick} | "
            f"Opponent: {opponent} | "
            f"Tournament: {tournament} | "
            f"Win probability: {pct(probability)}% | "
            f"Odds: {odds} | "
            f"Risk: {risk}"
        )

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
<description>Daily tennis picks - short feed with detailed pick pages</description>
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
