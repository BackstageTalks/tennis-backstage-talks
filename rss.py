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

    hidden = ["", "SportScore Tennis", "Tennis", "Unknown", "None", "null"]

    if value in hidden:
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
