import html
import json
import os
from datetime import datetime, timezone


RESULTS_DATA_PATHS = [
    "public/results_data.json",
]

RESULTS_PAGE_PATH = "public/results/index.html"
RESULTS_RSS_PATH = "public/results.xml"

SITE_TITLE = "BackstageTalks Statistic Model"
BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks"

HEADER_TITLE = "BackstageTalks Statistic Model"
HEADER_SUBTITLE = "This data is provided for informational and analytical purposes only"
FOOTER_TEXT = "Powered by BackstageTalks Statistic Model"


def safe(value, default="-"):
    if value is None:
        return default

    if value == "":
        return default

    return html.escape(str(value))


def pct(value):
    try:
        if value is None:
            return "-"

        return f"{float(value) * 100:.1f}%"

    except Exception:
        return "-"


def units(value):
    try:
        number = float(value)

        if number > 0:
            return f"+{number:.2f}u"

        if number < 0:
            return f"{number:.2f}u"

        return "0.00u"

    except Exception:
        return "0.00u"


def odds(value):
    try:
        return f"{float(value):.2f}"

    except Exception:
        return "-"


def first_float(item, keys):
    for key in keys:
        try:
            value = item.get(key)
            if value not in [None, ""]:
                return float(value)
        except Exception:
            pass
    return None


def normalized_name(value):
    import unicodedata
    import re
    if value is None:
        return ""
    text = unicodedata.normalize("NFKD", str(value))
    text = "".join(char for char in text if not unicodedata.combining(char))
    text = text.lower()
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def pick_odds_value(item):
    return first_float(item, ["odds", "marq_current_pick_odds", "marq_initial_pick_odds"])


def names_same_or_close(a, b):
    a_name = normalized_name(a)
    b_name = normalized_name(b)
    if not a_name or not b_name:
        return False
    if a_name == b_name or a_name in b_name or b_name in a_name:
        return True
    a_parts = a_name.split()
    b_parts = b_name.split()
    if a_parts and b_parts and a_parts[-1] == b_parts[-1]:
        return True
    return False


def players_from_match_text(match_text):
    text = str(match_text or "").strip()
    for sep in [" vs ", " v ", " - "]:
        if sep in text:
            left, right = text.split(sep, 1)
            return left.strip(), right.strip()
    return None, None


def opponent_odds_value(item):
    direct = first_float(item, ["opponent_odds", "marq_current_opponent_odds", "marq_initial_opponent_odds"])
    if direct is not None:
        return direct

    p1 = item.get("player1")
    p2 = item.get("player2")
    match_p1, match_p2 = players_from_match_text(item.get("match"))
    p1 = p1 or match_p1
    p2 = p2 or match_p2

    pick = item.get("pick")
    opponent = item.get("opponent")
    odds1 = first_float(item, ["odds_player1", "p1_odds", "home_odds", "odds1", "price1"])
    odds2 = first_float(item, ["odds_player2", "p2_odds", "away_odds", "odds2", "price2"])

    if names_same_or_close(opponent, p1) and odds1 is not None:
        return odds1
    if names_same_or_close(opponent, p2) and odds2 is not None:
        return odds2
    if names_same_or_close(pick, p1) and odds2 is not None:
        return odds2
    if names_same_or_close(pick, p2) and odds1 is not None:
        return odds1
    return None


def odds_badge(value, prefix):
    number = first_float({"value": value}, ["value"])
    if number is None:
        return ""
    return f'<span class="odds-mini">{safe(prefix)} @{odds(number)}</span>'



def pct_points(value):
    try:
        if value is None or value == "":
            return "-"
        number = float(str(value).replace("%", "").strip())
        if number <= 1.0:
            number *= 100.0
        return f"{number:.1f}%"
    except Exception:
        return "-"


def ai_match_value(item):
    value = item.get("ai_match")
    if value is None or value == "":
        value = item.get("ai_match_display")
    if value is not None and value != "":
        try:
            number = float(str(value).replace("%", "").strip())
            if number <= 1.0:
                number *= 100.0
            return number
        except Exception:
            pass

    # Backfill in the renderer if results_data was generated before ai_match enrichment.
    gap_pp = item.get("result_model_gap_pp")
    if gap_pp is None:
        gap = item.get("result_model_gap") or item.get("model_gap")
        try:
            gap_number = float(gap)
            gap_pp = gap_number * 100.0 if gap_number <= 1.0 else gap_number
        except Exception:
            gap_pp = None

    if gap_pp is not None:
        try:
            return max(0.0, 100.0 - float(gap_pp))
        except Exception:
            pass

    corq = (
        item.get("result_corq_probability")
        or item.get("corq_ai_probability")
        or item.get("corq_raw_probability")
        or item.get("corq_q_probability")
    )
    thinq = (
        item.get("result_thinq_probability")
        or item.get("bst_ai_probability")
        or item.get("thinq_ai_probability")
        or item.get("thinq_raw_probability")
        or item.get("thinq_q_probability")
    )
    try:
        corq_number = float(corq)
        thinq_number = float(thinq)
        if corq_number > 1.0:
            corq_number /= 100.0
        if thinq_number > 1.0:
            thinq_number /= 100.0
        return max(0.0, 100.0 - abs(corq_number - thinq_number) * 100.0)
    except Exception:
        return None


def ai_match_display(item):
    value = ai_match_value(item)
    if value is None:
        return "-"
    return f"{value:.1f}%"


def ai_match_class(item):
    value = ai_match_value(item)
    if value is None:
        return "ai-match-missing"
    if value >= 94.0:
        return "ai-match-strong"
    if value >= 90.0:
        return "ai-match-good"
    if value >= 80.0:
        return "ai-match-watch"
    return "ai-match-low"



def compact_pct(value):
    try:
        if value is None or value == "":
            return None
        number = float(value)
        if number <= 1.0:
            number *= 100.0
        return f"{number:.1f}%"
    except Exception:
        return None


def result_line(label, predicted, actual, hit=None):
    if hit is True:
        status = "hit"
        verdict = "HIT"
    elif hit is False:
        status = "miss"
        verdict = "MISS"
    else:
        status = "neutral"
        verdict = "INFO"

    if predicted not in [None, ""]:
        text = f"{label}: Pred {predicted} → Real {actual} · {verdict}"
    else:
        text = f"{label}: Real {actual}"
    return f'<span class="result-line result-{safe(status)}">{safe(text)}</span>'


def strip_html(value):
    import re
    return re.sub(r"<[^>]+>", "", str(value or ""))


def parse_score_sets(score):
    if not score:
        return []
    import re
    parsed = []
    for first, second in re.findall(r"(\d+)\s*-\s*(\d+)", str(score)):
        try:
            parsed.append((int(first), int(second)))
        except Exception:
            pass
    return parsed


def actual_set_score_from_score(score):
    sets = parse_score_sets(score)
    if not sets:
        return None, None, None
    p1_sets = 0
    p2_sets = 0
    total_games = 0
    for first, second in sets:
        total_games += first + second
        if first > second:
            p1_sets += 1
        elif second > first:
            p2_sets += 1
    return f"{p1_sets}-{p2_sets}", len(sets), total_games


def evaluate_score_prediction(item):
    actual_score = item.get("score")
    predicted_score = item.get("most_likely_score")
    actual_set_score, actual_sets, total_games = actual_set_score_from_score(actual_score)

    if actual_set_score is None:
        return ""

    rows = []

    if predicted_score:
        predicted_text = str(predicted_score).strip()
        score_hit = predicted_text == str(actual_set_score).strip()
        rows.append(result_line("Score", predicted_text, actual_set_score, score_hit))
    else:
        rows.append(result_line("Score", None, actual_set_score, None))

    sets_label = item.get("sets_probability_label")
    if sets_label and actual_sets is not None:
        expected_sets = None
        label_text = str(sets_label)
        if "3" in label_text:
            expected_sets = 3
        elif "2" in label_text:
            expected_sets = 2
        elif "5" in label_text:
            expected_sets = 5
        if expected_sets is not None:
            sets_hit = expected_sets == actual_sets
            rows.append(result_line("Sets", str(expected_sets), str(actual_sets), sets_hit))

    games_pick = str(item.get("games_pick") or "").strip()
    games_line = item.get("games_line")
    if games_pick and games_line not in [None, ""] and total_games is not None:
        try:
            line = float(games_line)
            lower = games_pick.lower()
            games_hit = None
            if "over" in lower:
                games_hit = total_games > line
            elif "under" in lower:
                games_hit = total_games < line
            if games_hit is not None:
                rows.append(result_line("Games", games_pick, f"{total_games}g", games_hit))
        except Exception:
            pass
    elif total_games is not None:
        rows.append(result_line("Games", None, f"{total_games}g", None))

    return "<br>".join(rows)


def expected_sets_short_label(item):
    label = str(item.get("sets_probability_label") or "").strip()
    if "5" in label:
        return "5S"
    if "3" in label:
        return "3S"
    try:
        if int(item.get("best_of") or 3) == 5:
            return "5S"
    except Exception:
        pass
    return "3S"


def format_sets_games(item):
    """Compact one-line Sets/Games display for Results page only.

    Example BO3:
    S 2.46 • 3S 45.5% • S 2-0 • G 22.6

    BO5 automatically uses 5S when sets_probability_label/best_of says BO5.
    """
    bits = []

    expected_sets = item.get("expected_sets")
    if expected_sets not in [None, ""]:
        try:
            bits.append(f"S {float(expected_sets):.2f}")
        except Exception:
            bits.append(f"S {expected_sets}")

    sets_probability = compact_pct(item.get("sets_probability"))
    if sets_probability:
        bits.append(f"{expected_sets_short_label(item)} {sets_probability}")

    most_likely_score = item.get("most_likely_score")
    if most_likely_score:
        bits.append(f"S {most_likely_score}")

    expected_games = item.get("expected_games") or item.get("thinq_projected_games")
    if expected_games not in [None, ""]:
        try:
            bits.append(f"G {float(expected_games):.1f}")
        except Exception:
            bits.append(f"G {expected_games}")

    if not bits:
        return "-"
    return safe(" • ".join(str(part) for part in bits))


def plain_sets_games(item):
    text = format_sets_games(item)
    if text == "-":
        return "-"
    return strip_html(text.replace("<br>", " | "))


def load_json(path, default):
    try:
        if not os.path.exists(path):
            return default

        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)

    except Exception:
        return default


def empty_summary():
    return {
        "picks": 0,
        "won": 0,
        "lost": 0,
        "void": 0,
        "pending": 0,
        "unknown": 0,
        "units": 0.0,
        "win_rate": None,
    }


def empty_dataset(dataset):
    return {
        "dataset": dataset,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "today": empty_summary(),
        "last_7_days": empty_summary(),
        "current_month": empty_summary(),
        "all_time": empty_summary(),
        "items": [],
    }


def normalize_results_payload(data):
    if not isinstance(data, dict):
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "top5": empty_dataset("top5"),
            "all": empty_dataset("all"),
        }

    if "top5" in data and "all" in data:
        return data

    legacy = {
        "dataset": "legacy",
        "generated_at": data.get("generated_at"),
        "today": data.get("today", empty_summary()),
        "last_7_days": data.get("last_7_days", empty_summary()),
        "current_month": data.get("current_month", empty_summary()),
        "all_time": data.get("all_time", empty_summary()),
        "items": data.get("items", []),
    }

    return {
        "generated_at": data.get("generated_at") or datetime.now(timezone.utc).isoformat(),
        "top5": empty_dataset("top5"),
        "all": legacy,
    }


def load_results_data():
    for path in RESULTS_DATA_PATHS:
        data = load_json(path, None)

        if data:
            return normalize_results_payload(data)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "top5": empty_dataset("top5"),
        "all": empty_dataset("all"),
    }


def status_class(status):
    status = str(status or "PENDING").upper()

    if status == "WON":
        return "status-won"

    if status == "LOST":
        return "status-lost"

    if status == "VOID":
        return "status-void"

    if status == "UNKNOWN":
        return "status-unknown"

    return "status-pending"


def html_link(url, label):
    lt = chr(60)
    gt = chr(62)

    return (
        f'{lt}a href="{safe(url)}"{gt}'
        f'{safe(label)}'
        f'{lt}/a{gt}'
    )


def render_nav():
    links = [
        html_link(f"{BASE_URL}/", "TOP5"),
        html_link(f"{BASE_URL}/all/", "ALL"),
        html_link(f"{BASE_URL}/results/", "RESULTS"),
    ]

    return f"""
<nav class="nav" aria-label="Main navigation">
    {" ".join(links)}
</nav>
"""


def render_summary_card(label, summary):
    return f"""
<div class="summary-card">
    <div class="summary-label">{safe(label)}</div>

    <div class="summary-grid">
        <div>
            <span>Picks</span>
            <strong>{safe(summary.get("picks", 0))}</strong>
        </div>

        <div>
            <span>W-L</span>
            <strong>{safe(summary.get("won", 0))}-{safe(summary.get("lost", 0))}</strong>
        </div>

        <div>
            <span>Pending</span>
            <strong>{safe(summary.get("pending", 0))}</strong>
        </div>

        <div>
            <span>Units</span>
            <strong>{units(summary.get("units", 0))}</strong>
        </div>

        <div>
            <span>Win rate</span>
            <strong>{pct(summary.get("win_rate"))}</strong>
        </div>
    </div>
</div>
"""


def render_summary(data):
    return f"""
<div class="summary">
    {render_summary_card("Today", data.get("today", empty_summary()))}
    {render_summary_card("Last 7 days", data.get("last_7_days", empty_summary()))}
    {render_summary_card("Current month", data.get("current_month", empty_summary()))}
    {render_summary_card("All time", data.get("all_time", empty_summary()))}
</div>
"""


def render_rows(items):
    if not items:
        return """
<tr>
    <td colspan="11" class="empty">
        No results available yet.
    </td>
</tr>
"""

    rows = []

    for item in items[:300]:
        status = str(item.get("result_status") or "PENDING").upper()
        css = status_class(status)

        tournament = item.get("tournament")
        surface = item.get("surface")
        best_of = item.get("best_of")

        meta_parts = []

        if tournament:
            meta_parts.append(str(tournament))

        if surface:
            meta_parts.append(str(surface))

        if best_of:
            meta_parts.append(f"BO{best_of}")

        meta = " • ".join(meta_parts)

        rows.append(
            f"""
<tr>
    <td>{safe(item.get("date"))}</td>

    <td>
        <div class="pick">{safe(item.get("pick"))}</div>
        <div class="pick-odds-under">{odds_badge(pick_odds_value(item), "Pick")}</div>
        <div class="pick-sub">TO WIN</div>
        <div class="match">{safe(item.get("match"))}</div>
        <div class="meta">{safe(meta, "")}</div>
    </td>

    <td class="opponent-cell">
        <div class="opponent-name">{safe(item.get("opponent"))}</div>
        <div class="opponent-odds-under">{odds_badge(opponent_odds_value(item), "Opp")}</div>
    </td>

    <td>{pct(item.get("probability"))}</td>


    <td class="ai-match-cell">
        <span class="ai-match-pill {ai_match_class(item)}">
            {safe(ai_match_display(item))}
        </span>
    </td>

    <td class="sets-games-cell">
        <div>{format_sets_games(item)}</div>
        <div class="sets-eval">{evaluate_score_prediction(item)}</div>
    </td>

    <td class="pick-odds-cell">
        <span class="pick-odds-main">{odds(pick_odds_value(item))}</span>
        <div class="opp-odds-mini-mobile">{odds_badge(opponent_odds_value(item), "Opp")}</div>
    </td>

    <td>
        <span class="status {css}">
            {safe(status)}
        </span>
    </td>

    <td>{safe(item.get("winner"))}</td>

    <td>{safe(item.get("score"))}</td>

    <td class="units">
        {units(item.get("units"))}
    </td>
</tr>
"""
        )

    return "\n".join(rows)


def render_table(items):
    rows = render_rows(items)

    return f"""
<div class="table-wrap">
    <table>
        <thead>
            <tr>
                <th>Date</th>
                <th>Pick</th>
                <th>Opponent</th>
                <th>Win %</th>
                <th>AI Match</th>
                <th>Sets/Games</th>
                <th>Odds</th>
                <th>Status</th>
                <th>Winner</th>
                <th>Score</th>
                <th>Units</th>
            </tr>
        </thead>

        <tbody>
            {rows}
        </tbody>
    </table>
</div>
"""


def render_dataset_section(title, subtitle, data):
    return f"""
<section class="dataset-section">
    <div class="section-header">
        <h2>{safe(title)}</h2>
        <p>{safe(subtitle)}</p>
    </div>

    {render_summary(data)}

    {render_table(data.get("items", []))}
</section>
"""


def render_page(data):
    nav = render_nav()

    top5_data = data.get("top5", empty_dataset("top5"))
    all_data = data.get("all", empty_dataset("all"))

    top5_section = render_dataset_section(
        "TOP5 Results",
        "Track record for the daily TOP5 snapshot.",
        top5_data,
    )

    all_section = render_dataset_section(
        "ALL Results",
        "Track record for all model-quality daily snapshot picks.",
        all_data,
    )

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">

<title>{safe(SITE_TITLE)}</title>

<style>
:root {{
    --bg: #0f172a;
    --panel: #111827;
    --panel-2: #1e293b;
    --border: #334155;
    --text: #e5e7eb;
    --muted: #94a3b8;
    --green: #22c55e;
    --red: #ef4444;
    --yellow: #facc15;
    --blue: #38bdf8;
    --gray: #64748b;
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
    max-width: 1760px;
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

.dataset-section {{
    margin-top: 30px;
}}

.section-header {{
    margin-bottom: 16px;
}}

.section-header h2 {{
    margin: 0;
    font-size: 24px;
    font-weight: 900;
    color: var(--text);
}}

.section-header p {{
    margin: 8px 0 0;
    color: var(--muted);
    font-size: 14px;
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
    color: var(--blue);
    font-weight: 800;
    margin-bottom: 12px;
}}

.summary-grid {{
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 8px;
}}

.summary-grid span {{
    display: block;
    color: var(--muted);
    font-size: 12px;
}}

.summary-grid strong {{
    display: block;
    font-size: 16px;
    margin-top: 3px;
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
    min-width: 1680px;
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
    padding: 15px 12px;
    border-bottom: 1px solid var(--border);
    vertical-align: top;
}}

tr:hover {{
    background: rgba(255, 255, 255, 0.03);
}}

.pick {{
    font-weight: 800;
    color: var(--text);
}}

.match {{
    color: var(--muted);
    font-size: 12px;
    margin-top: 6px;
}}

.meta {{
    color: var(--blue);
    font-size: 12px;
    margin-top: 6px;
    font-weight: 700;
}}

.pick-odds-under,
.opponent-odds-under,
.opp-odds-mini-mobile {{
    margin-top: 5px;
}}
.odds-mini {{
    display: inline-block;
    padding: 3px 7px;
    border-radius: 999px;
    font-size: 11px;
    font-weight: 900;
    line-height: 1.2;
    color: #94a3b8;
    background: rgba(100, 116, 139, 0.14);
    border: 1px solid rgba(100, 116, 139, 0.34);
}}
.pick-odds-under .odds-mini {{
    color: #22c55e;
    background: rgba(34, 197, 94, 0.16);
    border: 1px solid rgba(34, 197, 94, 0.42);
}}
.opponent-name {{
    font-weight: 800;
    color: var(--text);
}}
.pick-odds-cell {{
    white-space: nowrap;
}}
.pick-sub {
    color: #22c55e;
    font-size: 12px;
    line-height: 1.1;
    margin-top: 4px;
    font-weight: 900;
    letter-spacing: .03em;
}
.pick-odds-main {{
    display: inline-block;
    padding: 6px 10px;
    border-radius: 10px;
    font-weight: 1000;
    color: var(--yellow);
    background: rgba(34, 197, 94, 0.16);
    border: 1px solid rgba(34, 197, 94, 0.45);
}}
.opp-odds-mini-mobile {{
    display: none;
}}

.ai-match-cell {{
    white-space: nowrap;
}}
.ai-match-pill {{
    display: inline-block;
    padding: 5px 9px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 900;
    letter-spacing: 0.02em;
}}
.ai-match-strong {{
    color: #22c55e;
    background: rgba(34, 197, 94, 0.16);
    border: 1px solid rgba(34, 197, 94, 0.45);
}}
.ai-match-good {{
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.15);
    border: 1px solid rgba(56, 189, 248, 0.45);
}}
.ai-match-watch {{
    color: #facc15;
    background: rgba(250, 204, 21, 0.14);
    border: 1px solid rgba(250, 204, 21, 0.42);
}}
.ai-match-low {{
    color: #fb923c;
    background: rgba(251, 146, 60, 0.14);
    border: 1px solid rgba(251, 146, 60, 0.42);
}}
.ai-match-missing {{
    color: var(--muted);
    background: rgba(100, 116, 139, 0.16);
    border: 1px solid rgba(100, 116, 139, 0.4);
}}

.result-line {{
    display: inline-block;
    margin: 2px 0;
    padding: 3px 7px;
    border-radius: 6px;
    font-size: 11px;
    font-weight: 900;
    line-height: 1.35;
    white-space: nowrap;
}}
.result-hit {{
    color: #22c55e;
    background: rgba(34, 197, 94, 0.16);
    border: 1px solid rgba(34, 197, 94, 0.42);
}}
.result-miss {{
    color: #f87171;
    background: rgba(239, 68, 68, 0.16);
    border: 1px solid rgba(239, 68, 68, 0.45);
}}
.result-neutral {{
    color: #94a3b8;
    background: rgba(100, 116, 139, 0.14);
    border: 1px solid rgba(100, 116, 139, 0.36);
}}

.sets-eval {
    margin-top: 6px;
    white-space: normal;
}
.sets-games-cell {{
    min-width: 360px;
    max-width: 520px;
    color: var(--muted);
    font-size: 12px;
    line-height: 1.35;
    white-space: nowrap;
    word-break: keep-all;
    overflow-wrap: normal;
}}

.status {{
    display: inline-block;
    padding: 5px 10px;
    border-radius: 999px;
    font-size: 12px;
    font-weight: 800;
}}

.status-won {{
    background: rgba(34, 197, 94, 0.18);
    color: var(--green);
    border: 1px solid rgba(34, 197, 94, 0.45);
}}

.status-lost {{
    background: rgba(239, 68, 68, 0.18);
    color: var(--red);
    border: 1px solid rgba(239, 68, 68, 0.45);
}}

.status-pending {{
    background: rgba(250, 204, 21, 0.16);
    color: var(--yellow);
    border: 1px solid rgba(250, 204, 21, 0.45);
}}

.status-void {{
    background: rgba(100, 116, 139, 0.18);
    color: var(--muted);
    border: 1px solid rgba(100, 116, 139, 0.45);
}}

.status-unknown {{
    background: rgba(56, 189, 248, 0.15);
    color: var(--blue);
    border: 1px solid rgba(56, 189, 248, 0.45);
}}

.units {{
    font-weight: 800;
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

@media (max-width: 600px) {{
    .wrapper {{
        padding: 16px;
    }}

    .summary {{
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

    {top5_section}

    {all_section}

    <div class="footer">
        {safe(FOOTER_TEXT)}
    </div>

</div>
</body>
</html>
"""


def render_rss(data):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")

    items = []

    rss_candidates = []

    for dataset_label, dataset_key in [
        ("TOP5", "top5"),
        ("ALL", "all"),
    ]:
        dataset = data.get(dataset_key, empty_dataset(dataset_key))

        for item in dataset.get("items", [])[:50]:
            rss_candidates.append(
                (
                    dataset_label,
                    item,
                )
            )

    for dataset_label, item in rss_candidates[:100]:
        title = (
            f"{dataset_label}: {item.get('pick')} vs {item.get('opponent')} "
            f"— {item.get('result_status', 'PENDING')}"
        )

        description_text = (
            f"Dataset: {dataset_label}\n"
            f"Date: {item.get('date')}\n"
            f"Match: {item.get('match')}\n"
            f"Pick: {item.get('pick')}\n"
            f"Opponent: {item.get('opponent')}\n"
            f"Odds: {odds(item.get('odds'))}\n"
            f"Win probability: {pct(item.get('probability'))}\n"
            f"AI Match: {ai_match_display(item)}\n"
            f"Sets/Games: {plain_sets_games(item)}\n"
            f"Tournament: {item.get('tournament')}\n"
            f"Surface: {item.get('surface')}\n"
            f"Best of: {item.get('best_of')}\n"
            f"Status: {item.get('result_status')}\n"
            f"Winner: {item.get('winner')}\n"
            f"Score: {item.get('score')}\n"
            f"Units: {units(item.get('units'))}\n\n"
            f"{HEADER_SUBTITLE}\n"
            f"{FOOTER_TEXT}"
        )

        items.append(
            f"""
<item>
<title>{html.escape(str(title))}</title>
<link>{BASE_URL}/results/</link>
<description>{html.escape(description_text)}</description>
<pubDate>{now}</pubDate>
</item>
"""
        )

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>{html.escape(SITE_TITLE)}</title>
<link>{BASE_URL}/results/</link>
<description>{html.escape(HEADER_TITLE)}</description>
{''.join(items)}
</channel>
</rss>
"""


def write_file(path, content):
    directory = os.path.dirname(path)

    if directory:
        os.makedirs(directory, exist_ok=True)

    with open(path, "w", encoding="utf-8") as file:
        file.write(content)


def run():
    data = load_results_data()

    page = render_page(data)
    rss = render_rss(data)

    write_file(RESULTS_PAGE_PATH, page)
    write_file(RESULTS_RSS_PATH, rss)

    print("RESULTS PAGE WRITTEN:", RESULTS_PAGE_PATH)
    print("RESULTS RSS WRITTEN:", RESULTS_RSS_PATH)


if __name__ == "__main__":
    run()
