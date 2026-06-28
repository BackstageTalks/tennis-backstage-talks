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
        return dt.strftime("%d.%m.%Y %H:%M Bratislava time")
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


def signal_summary(signals):
    if not signals:
        return "No extra signal"

    return ", ".join(str(s) for s in signals)


def create_alt_cards(alt_bets):
    if not alt_bets:
        return """
        <div class="mini-card">
            <div class="mini-title">Alternative signal</div>
            <div>No qualified alternative signal.</div>
        </div>
        """

    cards = ""

    for alt in alt_bets:
        market = html.escape(str(alt.get("market", "")))
        alt_pick = html.escape(str(alt.get("pick", "")))
        alt_probability = alt.get("probability")
        alt_confidence = html.escape(str(alt.get("confidence", "")))
        alt_sample = html.escape(str(alt.get("sample", "")))
        note = html.escape(str(alt.get("note", "")))

        probability_text = f"{pct(alt_probability)}%" if alt_probability is not None else "N/A"

        cards += f"""
        <div class="mini-card">
            <div class="mini-title">{market}</div>
            <div><span>Pick</span><strong>{alt_pick}</strong></div>
            <div><span>Probability</span><strong>{probability_text}</strong></div>
            <div><span>Confidence</span><strong>{alt_confidence}</strong></div>
            <div><span>Sample</span><strong>{alt_sample}</strong></div>
            <p class="muted">{note}</p>
        </div>
        """

    return cards


def create_pick_page(index, prediction, label, risk, page_filename):
    os.makedirs("public/picks", exist_ok=True)

    pick = str(prediction.get("pick", prediction.get("player1", "Unknown")))
    opponent = str(prediction.get("opponent", prediction.get("player2", "Unknown")))

    player1 = str(prediction.get("player1", "Unknown"))
    player2 = str(prediction.get("player2", "Unknown"))

    tournament = clean_tournament_name(prediction.get("tournament", ""))

    probability = float(prediction.get("probability", 0))
