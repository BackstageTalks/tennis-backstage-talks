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


def label_for_pick(probability, signals, index, market_agrees, value_edge):
    if index == 1:
        return "🔥 TOP PICK"

    if market_agrees and probability >= 0.56:
        return "✅ BOOKIE + MODEL PICK"

    if value_edge is not None and value_edge >= 0.04:
        return "💎 VALUE PICK"

    if "🎯 Strong over 0.5 set signal" in signals:
        return "🎯 SET SAFETY PICK"

    if "💣 Ace edge vs opponent" in signals:
        return "💣 ACE EDGE WATCH"

    if probability >= 0.58:
        return "✅ SAFE PICK"

    return "⚖️ QUALIFIED PICK"


def risk_for_pick(probability, market_agrees):
    if probability >= 0.65 and market_agrees:
        return "LOW"

    if probability >= 0.58:
        return "MEDIUM"

    return "HIGH"


def format_alt_bets(alt_bets):
    if not alt_bets:
        return "Alternative market: No qualified alternative signal"

    parts = []

    for alt in alt_bets:
        market = alt.get("market", "")
        pick = alt.get("pick", "")
        probability = alt.get("probability")
        confidence = alt.get("confidence", "")
        sample = alt.get("sample", 0)
        note = alt.get("note", "")

        if probability is not None:
            parts.append(
                f"Alternative market: {market} | Pick: {pick} | "
                f"Probability: {pct(probability)}% | "
                f"Confidence: {confidence} | "
                f"Sample: {sample} | "
                f"{note}"
            )
        else:
            parts.append(
                f"Alternative signal: {market} | Player: {pick} | "
                f"Confidence: {confidence} | "
                f"Sample: {sample} | "
                f"{note}"
            )

    return " || ".join(parts)


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

        label = label_for_pick(
            probability=probability,
            signals=signals,
            index=i,
            market_agrees=market_agrees,
            value_edge=value_edge
        )

        risk = risk_for_pick(probability, market_agrees)

        title = f"#{i} {label}: {pick} to win"

        desc_parts = [
            f"Main pick: {pick} to beat {opponent}",
            "Main market: Match Winner",
            f"Match: {player1} vs {player2}",
            f"Tournament: {tournament}",
            f"Match start: {match_start}",
            f"Surface: {surface}",
            f"Model win probability: {pct(probability)}%",
            f"Confidence: {pct(confidence)}%",
            f"Risk: {risk}",
            f"Pick odds: {odds}",
            f"Odds player1/player2: {odds_player1} / {odds_player2}",
            f"Odds source: {odds_source}",
        ]

        if implied_probability is not None:
            desc_parts.append(f"Raw implied probability: {pct(implied_probability)}%")

        if market_probability is not None:
            desc_parts.append(f"Fair market probability: {pct(market_probability)}%")

        if value_edge is not None:
            desc_parts.append(f"Bookie value edge: {pct(value_edge)}%")

        if overround is not None:
            desc_parts.append(f"Bookie overround: {round(overround, 3)}")

        desc_parts.append(f"Bookie signal: {bookie_signal}")
        desc_parts.append(f"Market agrees with model: {market_agrees}")

        if form_win_rate is not None:
            desc_parts.append(f"Recent/surface form win rate: {pct(form_win_rate)}%")

        if at_least_one_set_rate is not None:
            desc_parts.append(f"Historical over 0.5 set rate: {pct(at_least_one_set_rate)}%")

        if avg_aces is not None:
            desc_parts.append(f"Avg aces: {avg_aces}")

        if ace_rate is not None:
            desc_parts.append(f"Ace rate: {pct(ace_rate)}% of serve points")

        desc_parts.append(f"Historical sample: {sample} matches")
        desc_parts.append("Signals: " + ", ".join(signals))
        desc_parts.append(format_alt_bets(alt_bets))

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
<description>REAL DATA v8 - Top tennis picks with real SportScore odds, quality gate, value edge, set safety and ace profile</description>
{items}
</channel>
</rss>
"""

    with open("public/tennis.xml", "w", encoding="utf-8") as f:
        f.write(rss)

    print("RSS GENERATED:", len(predictions), "items")
    print("RSS PREVIEW:")
    print(rss[:4000])


if __name__ == "__main__":
    generate_rss()
