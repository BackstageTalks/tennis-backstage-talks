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
        "null",
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

        probability_text = f"{pct(probability)}%" if probability is not None else "N/A"

        parts.append(
            f"{market}: {pick} | Probability: {probability_text} | "
            f"Confidence: {confidence} | Sample: {sample} | {note}"
        )

    return " / ".join(parts)


def create_data_row(label, value):
    return (
        '<div class="data-row">'
        f'<span>{esc(label)}</span>'
        f'<strong>{esc(value)}</strong>'
        '</div>'
    )


DETAIL_CSS = """
<style>
* {
    box-sizing: border-box;
}

body {
    font-family: Arial, sans-serif;
    background: #160f0f;
    color: #f4f4f4;
    margin: 0;
    padding: 16px;
}

.container {
    max-width: 780px;
    margin: 0 auto;
}

.back-link {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 46px;
    height: 46px;
    border-radius: 999px;
    background: #3a2d2d;
    color: #ffffff;
    text-decoration: none;
    font-size: 26px;
    margin-bottom: 22px;
}

.back-link:hover {
    background: #4a3939;
}

.card {
    background: #211818;
    border-radius: 22px;
    padding: 22px;
    overflow: hidden;
}

.badge {
    display: inline-block;
    padding: 8px 12px;
    border-radius: 999px;
    background: #2d6cdf;
    color: #ffffff;
    font-weight: bold;
    margin-bottom: 16px;
    font-size: 14px;
}

h1 {
    margin: 0 0 10px 0;
    font-size: 34px;
    line-height: 1.15;
}

.subtitle {
    color: #d2c9c9;
    font-size: 17px;
    line-height: 1.45;
    margin-bottom: 22px;
}

.metric-grid {
    display: grid;
    grid-template-columns: repeat(2, minmax(0, 1fr));
    gap: 12px;
    margin-bottom: 24px;
}

.metric {
    background: #2d2222;
    border-radius: 16px;
    padding: 15px;
    min-height: 82px;
}

.metric span {
    display: block;
    color: #aaa;
    font-size: 13px;
    margin-bottom: 7px;
}

.metric strong {
    display: block;
    font-size: 24px;
    line-height: 1.15;
    word-break: break-word;
}

h2 {
    font-size: 22px;
    margin: 26px 0 12px;
}

.section {
    background: #2a2020;
    border-radius: 16px;
    padding: 12px 15px;
    margin-bottom: 16px;
}

.data-row {
    display: grid;
    grid-template-columns: 42% 58%;
    gap: 10px;
    padding: 10px 0;
    border-bottom: 1px solid #3a2d2d;
}

.data-row:last-child {
    border-bottom: none;
}

.data-row span {
    color: #aaa;
    font-size: 14px;
}

.data-row strong {
    text-align: right;
    font-size: 15px;
    line-height: 1.35;
    word-break: break-word;
}

.text-box {
    background: #2d2222;
    border-radius: 16px;
    padding: 15px;
    line-height: 1.55;
    color: #f2f2f2;
    word-break: break-word;
}

.footer-note {
    margin-top: 24px;
    padding: 15px;
    border-radius: 16px;
    background: #181818;
    color: #bdbdbd;
    font-size: 14px;
    line-height: 1.45;
}

@media (max-width: 520px) {
    body {
        padding: 12px;
    }

    .card {
        padding: 18px;
        border-radius: 20px;
    }

    h1 {
        font-size: 30px;
    }

    .subtitle {
        font-size: 16px;
    }

    .metric-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
    }

    .metric {
        padding: 13px;
    }

    .metric strong {
        font-size: 21px;
    }

    .data-row {
        display: block;
    }

    .data-row strong {
        display: block;
        text-align: left;
        margin-top: 4px;
    }
}
</style>
"""


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
    min-width: 760px;
}

th, td {
    padding: 15px 16px;
    border-bottom: 1px solid #372929;
    text-align: left;
    font-size: 17px;
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


def create_pick_page(index, prediction, label, page_filename):
    os.makedirs("public/picks", exist_ok=True)

    pick = str(prediction.get("pick", prediction.get("player1", "Unknown")))
    opponent = str(prediction.get("opponent", prediction.get("player2", "Unknown")))

    player1 = str(prediction.get("player1", "Unknown"))
    player2 = str(prediction.get("player2", "Unknown"))

    tournament = clean_tournament_name(prediction.get("tournament", ""))

    probability = float(prediction.get("probability", 0))
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

    pick_details_rows = ""
    pick_details_rows += create_data_row("Pick", pick)
    pick_details_rows += create_data_row("Opponent", opponent)
    pick_details_rows += create_data_row("Match", f"{player1} vs {player2}")

    if tournament:
        pick_details_rows += create_data_row("Tournament", tournament)

    pick_details_rows += create_data_row("Surface", surface)

    market_rows = ""
    market_rows += create_data_row("Pick odds", odds)
    market_rows += create_data_row("Odds player1 / player2", f"{odds_player1} / {odds_player2}")
    market_rows += create_data_row(
        "Fair market probability",
        f"{pct(market_probability)}%" if market_probability is not None else "N/A",
    )
    market_rows += create_data_row(
        "Value edge",
        f"{pct(value_edge)}%" if value_edge is not None else "N/A",
    )
    market_rows += create_data_row("Market agrees", market_agrees)
    market_rows += create_data_row("Bookie signal", bookie_signal)
    market_rows += create_data_row("Odds source", odds_source)
    market_rows += create_data_row(
        "Raw implied probability",
        f"{pct(implied_probability)}%" if implied_probability is not None else "N/A",
    )

    stats_rows = ""
    stats_rows += create_data_row(
        "Recent / surface form",
        f"{pct(form_win_rate)}%" if form_win_rate is not None else "N/A",
    )
    stats_rows += create_data_row(
        "Over 0.5 set rate",
        f"{pct(over_set_rate)}%" if over_set_rate is not None else "N/A",
    )
    stats_rows += create_data_row(
        "Avg aces",
        avg_aces if avg_aces is not None else "N/A",
    )
    stats_rows += create_data_row(
        "Ace rate",
        f"{pct(ace_rate)}%" if ace_rate is not None else "N/A",
    )
    stats_rows += create_data_row("Historical sample", f"{sample} matches")

    back_link = (
        tag_open("a", 'class="back-link" href="../index.html"')
        + "←"
        + tag_close("a")
    )

    page = (
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n"
        "<head>\n"
        "<meta charset='UTF-8'>\n"
        f"<title>{esc(label)}: {esc(pick)} to win</title>\n"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
        f"{DETAIL_CSS}\n"
        "</head>\n"
        "<body>\n"
        "<div class='container'>\n"
        f"{back_link}\n"
        "<div class='card'>\n"
        f"<div class='badge'>#{index} {esc(label)}</div>\n"
        f"<h1>{esc(pick)} to win</h1>\n"
        "<div class='subtitle'>\n"
        f"{esc(pick)} vs {esc(opponent)}<br>\n"
        f"{esc(match_start)}\n"
        "</div>\n"
        "<div class='metric-grid'>\n"
        "<div class='metric'>\n"
        "<span>Win probability</span>\n"
        f"<strong>{pct(probability)}%</strong>\n"
        "</div>\n"
        "<div class='metric'>\n"
        "<span>Odds</span>\n"
        f"<strong>{esc(odds)}</strong>\n"
        "</div>\n"
        "</div>\n"
        "<h2>Pick details</h2>\n"
        "<div class='section'>\n"
        f"{pick_details_rows}\n"
        "</div>\n"
        "<h2>Market</h2>\n"
        "<div class='section'>\n"
        f"{market_rows}\n"
        "</div>\n"
        "<h2>Form & stats</h2>\n"
        "<div class='section'>\n"
        f"{stats_rows}\n"
        "</div>\n"
        "<h2>Signals</h2>\n"
        "<div class='text-box'>\n"
        f"{esc(signal_text(signals))}\n"
        "</div>\n"
        "<h2>Alternative signal</h2>\n"
        "<div class='text-box'>\n"
        f"{esc(alternative_text(alt_bets))}\n"
        "</div>\n"
        "<div class='footer-note'>\n"
        "Generated by <strong>BackstageTalks Stat Model</strong> for informational and statistical purposes only\n"
        "</div>\n"
        "</div>\n"
        "</div>\n"
        "</body>\n"
        "</html>\n"
    )

    path = os.path.join("public", "picks", page_filename)

    with open(path, "w", encoding="utf-8") as f:
        f.write(page)

    return f"picks/{page_filename}"


def create_index_page(predictions):
    sorted_predictions = sorted(
        predictions,
        key=lambda p: float(p.get("probability", 0)),
        reverse=True,
    )

    rows = ""

    for i, prediction in enumerate(sorted_predictions, start=1):
        pick = str(prediction.get("pick", prediction.get("player1", "Unknown")))
        opponent = str(prediction.get("opponent", prediction.get("player2", "Unknown")))
        probability = float(prediction.get("probability", 0))
        odds = prediction.get("odds", "")
        page_url = prediction.get("_page_url", "#")
        match_time = format_match_time(prediction.get("match_start", ""))

        pick_link = (
            tag_open("a", f'href="{esc(page_url)}"')
            + f"{esc(pick)} to win"
            + tag_close("a")
        )

        rows += (
            "<tr>"
            f"<td>#{i}</td>"
            f"<td>{pick_link}</td>"
            f"<td>{esc(opponent)}</td>"
            f"<td>{esc(match_time) if match_time else '-'}</td>"
            f"<td>{pct(probability)}%</td>"
            f"<td>{esc(odds)}</td>"
            "</tr>\n"
        )

    page = (
        "<!DOCTYPE html>\n"
        "<html lang='en'>\n"
        "<head>\n"
        "<meta charset='UTF-8'>\n"
        "<title>Backstage Talks Tennis Picks</title>\n"
        "<meta name='viewport' content='width=device-width, initial-scale=1.0'>\n"
        f"{INDEX_CSS}\n"
        "</head>\n"
        "<body>\n"
        "<div class='container'>\n"
        "<h1>Backstage Talks Tennis Picks</h1>\n"
        "<p>Daily model picks based on match data, market odds and historical player stats.</p>\n"
        "<div class='table-wrap'>\n"
        "<table>\n"
        "<thead>\n"
        "<tr>\n"
        "<th>#</th>\n"
        "<th>Pick</th>\n"
        "<th>Opponent</th>\n"
        "<th class='time-col'>Match time</th>\n"
        "<th>Win %</th>\n"
        "<th>Odds</th>\n"
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
            value_edge=value_edge,
        )

        slug = safe_slug(f"{i}-{pick}-vs-{opponent}")
        page_filename = f"{datetime.date.today().isoformat()}-{slug}.html"

        relative_page = create_pick_page(
            index=i,
            prediction=prediction,
            label=label,
            page_filename=page_filename,
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
<title>{esc(title)}</title>
<link>{esc(full_link)}</link>
<guid isPermaLink="false">{esc(guid)}</guid>
<pubDate>{datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
<description>{esc(desc)}</description>
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

    os.makedirs("public", exist_ok=True)

    with open("public/tennis.xml", "w", encoding="utf-8") as f:
        f.write(rss)

    print("RSS GENERATED:", len(predictions), "items")
    print("RSS PREVIEW:")
    print(rss[:2500])


if __name__ == "__main__":
    generate_rss()
