import os
import json
import datetime
import html
import re

BASE = "https://backstagetalks.github.io/tennis-backstage-talks/"


def esc(value):
    return html.escape(str(value if value is not None else ""))


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


DETAIL_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>__PAGE_TITLE__</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">

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
