import os
import html
from datetime import datetime, timezone


SITE_TITLE = "BackstageTalks Statistic Model"
BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks"

HEADER_TITLE = "BackstageTalks Statistic Model"
HEADER_SUBTITLE = "This data is provided for informational and analytical purposes only."
FOOTER_TEXT = "Powered by BackstageTalks Statistic Model"


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


def render_nav():
    return f"""
<nav class="nav" aria-label="Main navigation">
    <a href="{BASE_URL}/">TOP5</a>
    <a href="{BASE_URL}/all/">ALL</a>
    <a href="{BASE_URL}/results/">RESULTS</a>
</nav>
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

    avg_probability = "-"
    avg_odds = "-"

    if probabilities:
        avg_probability = f"{sum(probabilities) / len(probabilities) * 100:.1f}%"

    if odds_values:
        avg_odds = f"{sum(odds_values) / len(odds_values):.2f}"

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
        <div class="summary-label">Average Odds</div>
        <div class="summary-value">{avg_odds}</div>
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
        sets_probability_label = safe(resolve_sets_label(prediction))

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
