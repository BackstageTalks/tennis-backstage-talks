import os
import json
import datetime
import html

BASE = "https://backstagetalks.github.io/tennis-backstage-talks/"


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


def label_for_pick(probability, signals, index):
    if index == 1:
        return "🔥 TOP PICK"

    if "🎯 Strong set safety" in signals:
        return "🎯 SET SAFETY PICK"

    if "💣 Ace edge vs opponent" in signals:
        return "💣 ACE EDGE WATCH"

    if probability >= 0.58:
        return "✅ SAFE PICK"

    return "⚖️ LEAN PICK"


def risk_for_pick(probability):
    if probability >= 0.65:
        return "LOW"
    elif probability >= 0.58:
        return "MEDIUM"
    return "HIGH"


def generate_rss():
    predictions = latest_predictions()

    items = ""

    for i, p in enumerate(predictions, start=1):
        pick = str(p.get("pick", p.get("player1", "Unknown")))
        opponent = str(p.get("opponent", p.get("player2", "Unknown")))

        player1 = str(p.get("player1", "Unknown"))
        player2 = str(p.get("player2", "Unknown"))
        tournament = str(p.get("tournament", "Tennis"))

        probability = float(p.get("probability", 0))
        confidence = float(p.get("confidence", 0))
        value = float(p.get("value", 0))

        odds = p.get("odds", "")

        signals = p.get("extra_signals", [])

        pick_stats = p.get("pick_stats", {})

        avg_aces = pick_stats.get("avg_aces")
        at_least_one_set_rate = pick_stats.get("at_least_one_set_rate")
        matches_found = pick_stats.get("matches_found", 0)
        aces_sample = pick_stats.get("aces_sample", 0)
        set_sample = pick_stats.get("matches_with_score", 0)

        label = label_for_pick(probability, signals, i)
        risk = risk_for_pick(probability)

        title = f"#{i} {label}: {pick} to win"

        desc_parts = [
            f"Pick: {pick} to beat {opponent}",
            "Market: Match Winner",
            f"Match: {player1} vs {player2}",
            f"Tournament: {tournament}",
            f"Win probability: {pct(probability)}%",
            f"Confidence: {pct(confidence)}%",
            f"Risk: {risk}",
            f"Odds reference: {odds}",
            f"Value edge: {pct(value)}%",
        ]

        if at_least_one_set_rate is not None:
            desc_parts.append(
                f"Set safety: {pct(at_least_one_set_rate)}% to win at least one set historically"
            )

        if avg_aces is not None:
            desc_parts.append(
                f"Avg aces: {avg_aces}"
            )

        desc_parts.append(
            f"Historical sample: {matches_found} matches"
        )

        if aces_sample:
            desc_parts.append(
                f"Ace sample: {aces_sample} matches"
            )

        if set_sample:
            desc_parts.append(
                f"Set sample: {set_sample} matches"
            )

        desc_parts.append(
            "Signals: " + ", ".join(signals)
        )

        desc = " | ".join(desc_parts)

        guid = f"{pick}-{opponent}-{datetime.date.today().isoformat()}-{i}"

        items += f"""
<item>
<title>{html.escape(title)}</title>
<link>{BASE}</link>
<guid isPermaLink="false">{html.escape(guid)}</guid>
<pubDate>{datetime.datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S GMT')}</pubDate>
<description>{html.escape(desc)}</description>
</item>
"""

    rss = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>Backstage Talks Tennis Picks</title>
<link>{BASE}</link>
<description>REAL DATA v6 - Tennis picks with winner, set safety and ace profile signals</description>
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
