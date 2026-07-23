import os
import html
from datetime import datetime, timezone


SITE_TITLE = "Backstage Talks Statistical Engine"
BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks"
HEADER_TITLE = "BackstageTalks Statistical Engine"
HEADER_SUBTITLE = "This data is provided for informational and analytical purposes only"
FOOTER_TEXT = "Powered by BackstageTalks Statistical Engine"


def safe(value, default="-"):
    if value is None or value == "":
        return default
    return html.escape(str(value))


def safe_float(value):
    try:
        if value is None or value == "":
            return None
        return float(value)
    except Exception:
        return None


def pct(value):
    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return "-"


def pct_plain(value):
    try:
        return f"{float(value):.1f}"
    except Exception:
        return "-"


def pct_points(value):
    try:
        if value is None or value == "":
            return "-"
        return f"{float(value):.1f}%"
    except Exception:
        return "-"


def odds(value):
    try:
        if value is None or value == "":
            return "-"
        return f"{float(value):.2f}"
    except Exception:
        return "-"


def first_float_from_prediction(prediction, keys):
    for key in keys:
        try:
            value = prediction.get(key)
            if value not in [None, ""]:
                return float(value)
        except Exception:
            pass
    return None


def odds_badge(value, prefix):
    try:
        if value in [None, ""]:
            return ""
        css_prefix = safe(str(prefix).lower())
        return f'<span class="odds-mini {css_prefix}-odds-mini">{safe(prefix)} @{odds(value)}</span>'
    except Exception:
        return ""


def pick_odds_value(prediction):
    return first_float_from_prediction(
        prediction,
        [
            "pick_odds",
            "odds",
            "marq_current_pick_odds",
            "marq_initial_pick_odds",
            "marq_latest",
            "marq_opening",
        ],
    )


def opponent_odds_value(prediction):
    direct = first_float_from_prediction(
        prediction,
        [
            "opponent_odds",
            "marq_current_opponent_odds",
            "marq_initial_opponent_odds",
            "opponent_price",
            "opp_odds",
            "odds_opponent",
        ],
    )
    if direct is not None:
        return direct

    # Conservative fallback from paired odds when available.
    pick = str(prediction.get("pick") or "").strip().lower()
    opponent = str(prediction.get("opponent") or "").strip().lower()
    player1 = str(prediction.get("player1") or "").strip().lower()
    player2 = str(prediction.get("player2") or "").strip().lower()
    odds1 = first_float_from_prediction(prediction, ["odds_player1", "p1_odds", "home_odds", "odds1", "price1"])
    odds2 = first_float_from_prediction(prediction, ["odds_player2", "p2_odds", "away_odds", "odds2", "price2"])
    if opponent and player1 and (opponent == player1 or opponent in player1 or player1 in opponent) and odds1 is not None:
        return odds1
    if opponent and player2 and (opponent == player2 or opponent in player2 or player2 in opponent) and odds2 is not None:
        return odds2
    if pick and player1 and (pick == player1 or pick in player1 or player1 in pick) and odds2 is not None:
        return odds2
    if pick and player2 and (pick == player2 or pick in player2 or player2 in pick) and odds1 is not None:
        return odds1
    return None


def html_link(url, label):
    return f'<a href="{safe(url)}">{safe(label)}</a>'


def render_nav():
    links = [
        html_link(f"{BASE_URL}/", "Corq"),
        html_link(f"{BASE_URL}/BsT/", "Thinq"),
        html_link(f"{BASE_URL}/Cloq/", "Cloq"),
        html_link(f"{BASE_URL}/tennis.xml", "Corq RSS"),
        html_link(f"{BASE_URL}/tennis_bst.xml", "Thinq RSS"),
        html_link(f"{BASE_URL}/tennis_cloq.xml", "Cloq RSS"),
        html_link(f"{BASE_URL}/all/", "All"),
        html_link(f"{BASE_URL}/results/", "Results"),
    ]
    return f"""
<nav class="nav" aria-label="Main navigation">
    {" ".join(links)}
</nav>
"""


def format_match_meta(prediction):
    parts = []
    for key in ["tournament", "surface"]:
        value = prediction.get(key)
        if value:
            parts.append(str(value))
    if prediction.get("best_of"):
        parts.append(f"BO{prediction.get('best_of')}")
    return " - ".join(parts)


def resolve_sets_label(prediction):
    label = prediction.get("sets_probability_label")
    if label:
        return str(label)
    try:
        if int(prediction.get("best_of")) == 5:
            return "5 Sets"
    except Exception:
        pass
    return "3 Sets"


def normalize_probability_for_display(value):
    number = safe_float(value)
    if number is None:
        return None
    if number <= 1.0:
        return number * 100.0
    return number


def format_pct_points(value):
    if value is None:
        return "-"
    try:
        return f"{float(value):.1f}%"
    except Exception:
        return "-"


def resolve_ai_metrics(prediction):
    corq_pct = normalize_probability_for_display(
        prediction.get("corq_ai_probability")
        or prediction.get("corq_display_probability")
        or prediction.get("probability")
    )
    thinq_pct = normalize_probability_for_display(
        prediction.get("bst_ai_probability")
        or prediction.get("thinq_ai_probability")
        or prediction.get("thinq_display_probability")
    )
    cloq_pct = normalize_probability_for_display(
        prediction.get("cloq_ai_probability")
        or prediction.get("cloq_display_probability")
        or prediction.get("blend_ai_probability")
        or prediction.get("blenq_ai_probability")
    )
    ai_match = safe_float(prediction.get("ai_match"))
    return {"corq_pct": corq_pct, "thinq_pct": thinq_pct, "cloq_pct": cloq_pct, "ai_match": ai_match}


def resolve_ai_delta(metrics, model_view="corq"):
    corq_pct = metrics.get("corq_pct")
    thinq_pct = metrics.get("thinq_pct")
    cloq_pct = metrics.get("cloq_pct")

    if model_view == "cloq":
        if cloq_pct is None:
            return {"label": "Cloq unavailable", "class": "delta-muted"}
        compare_pct = corq_pct if corq_pct is not None else thinq_pct
        compare_name = "Corq" if corq_pct is not None else "Thinq"
        if compare_pct is None:
            return {"label": "Cloq active", "class": "delta-cloq"}
        gap = float(cloq_pct) - float(compare_pct)
        if abs(gap) < 0.05:
            return {"label": "Even", "class": "delta-even"}
        if gap > 0:
            return {"label": f"Cloq +{gap:.1f}%", "class": "delta-cloq"}
        return {"label": f"{compare_name} +{abs(gap):.1f}%", "class": "delta-corq"}

    if corq_pct is None or thinq_pct is None:
        return {"label": "Thinq unavailable", "class": "delta-muted"}
    gap = float(thinq_pct) - float(corq_pct)
    if abs(gap) < 0.05:
        return {"label": "Even", "class": "delta-even"}
    if gap > 0:
        return {"label": f"Thinq +{gap:.1f}%", "class": "delta-thinq"}
    return {"label": f"Corq +{abs(gap):.1f}%", "class": "delta-corq"}


def resolve_marq_signal(prediction):
    signal = prediction.get("marq_ai_signal")
    score = prediction.get("marq_ai_score")
    if score is None:
        return "NO MARKET DATA"
    if not signal:
        return "NEUTRAL"
    return str(signal).upper()


def metric_row(label, value):
    return f"""
            <div class="metric-row">
                <span>{safe(label)}</span>
                <strong>{safe(value)}</strong>
            </div>
"""


def resolve_model_view(title, subtitle):
    text = f"{title or ''} {subtitle or ''}".lower()
    if "cloq" in text or "close" in text:
        return "cloq"
    if "bst" in text or "thinq" in text:
        return "thinq"
    return "corq"


def render_data_ai_box(prediction, model_view="corq"):
    status = prediction.get("bst_ai_status")
    metrics = resolve_ai_metrics(prediction)
    corq_display = format_pct_points(metrics["corq_pct"])
    thinq_display = format_pct_points(metrics["thinq_pct"])
    cloq_display = format_pct_points(metrics["cloq_pct"])
    ai_match_display = format_pct_points(metrics["ai_match"])

    if status != "OK" and model_view != "cloq":
        thinq_display = "No data"
        ai_match_display = "-"
        delta = {"label": "Thinq unavailable", "class": "delta-muted"}
    else:
        delta = resolve_ai_delta(metrics, model_view=model_view)

    if model_view == "thinq":
        rows = (
            metric_row("Thinq AI", thinq_display)
            + metric_row("Corq AI", corq_display)
            + metric_row("AI Match", ai_match_display)
        )
    elif model_view == "cloq":
        rows = (
            metric_row("Cloq AI", cloq_display)
            + metric_row("Corq AI", corq_display)
            + metric_row("Thinq AI", thinq_display)
        )
    else:
        rows = (
            metric_row("Corq AI", corq_display)
            + metric_row("Thinq AI", thinq_display)
            + metric_row("AI Match", ai_match_display)
        )

    return f"""
        <div class="intel-panel data-ai-panel">
            <div class="panel-title">MODEL DATA</div>
            {rows}
            <div class="ai-delta {safe(delta['class'])}">{safe(delta['label'])}</div>
        </div>
"""


def _title_case_signal(value, default="-"):
    if value is None or value == "":
        return default
    text = str(value).replace("_", " ").strip()
    if not text:
        return default
    return " ".join(part.capitalize() for part in text.split())


def _marq_badge_class(value):
    signal = str(value or "").strip().upper()
    if signal in {"ALIGN", "CONSENSUS", "EXCHANGE", "TOWARD PICK"}:
        return "market-support"
    if signal in {"DISAGREE", "MIXED", "MIXED MARKET", "AGAINST PICK"}:
        return "market-caution"
    if signal in {"OUTLIER"}:
        return "market-bearish"
    if signal in {"THIN", "THIN MARKET", "NO SHARP DATA", "NO MARKET DATA", "UNKNOWN"}:
        return "market-unavailable"
    if signal in {"STABLE", "PENDING"}:
        return "market-neutral"
    return "market-neutral"





def market_pct(value):
    try:
        if value is None or value == "":
            return "-"
        return f"{float(value):.1f}%"
    except Exception:
        return "-"


def yes_no_market_probability(value):
    try:
        if value is None or value == "":
            return "-"
        number = float(value)
        if number <= 1.0:
            number *= 100.0
        return f"{number:.1f}%"
    except Exception:
        return "-"


def _simple_name_key(value):
    try:
        text = str(value or "").strip().lower()
        for ch in [".", ",", "'", "`", "’", "-", "_", "(", ")", "[", "]"]:
            text = text.replace(ch, " ")
        return " ".join(text.split())
    except Exception:
        return ""


def _same_player_name(a, b):
    a_norm = _simple_name_key(a)
    b_norm = _simple_name_key(b)
    if not a_norm or not b_norm:
        return False
    if a_norm == b_norm or a_norm in b_norm or b_norm in a_norm:
        return True
    return bool(set(a_norm.split()) & set(b_norm.split()))


def resolve_pick_score_display(prediction):
    """
    Convert raw player1-player2 score into pick-opponent orientation.
    Example: player1 0-2 player2 and pick == player2 -> Pick/Opp 2-0.
    """
    score = str(prediction.get("most_likely_score") or "").strip()
    if not score or "-" not in score:
        return score
    try:
        p1_sets, p2_sets = score.split("-", 1)
        p1_sets = int(str(p1_sets).strip())
        p2_sets = int(str(p2_sets).strip())
        pick = prediction.get("pick")
        player1 = prediction.get("player1")
        player2 = prediction.get("player2")
        if _same_player_name(pick, player1):
            return f"{p1_sets}-{p2_sets}"
        if _same_player_name(pick, player2):
            return f"{p2_sets}-{p1_sets}"
    except Exception:
        pass
    return score


def resolve_market_lean(prediction):
    pick_pct = safe_float(prediction.get("marq_crowd_pick_pct"))
    opp_pct = safe_float(prediction.get("marq_crowd_opponent_pct"))
    if pick_pct is None or opp_pct is None:
        return "-"
    if abs(pick_pct - opp_pct) < 0.05:
        return "Even"
    return "Pick" if pick_pct > opp_pct else "Opponent"



def resolve_h2h_display(prediction):
    signal = str(prediction.get("h2h_signal") or "").strip().upper()
    total = safe_float(prediction.get("h2h_total_matches"))
    pick_wins = safe_float(prediction.get("h2h_pick_wins"))
    opp_wins = safe_float(prediction.get("h2h_opponent_wins"))
    if not signal or signal == "NO_DATA" or total is None or total <= 0:
        return "-"
    try:
        record = f"{int(pick_wins or 0)}-{int(opp_wins or 0)}"
    except Exception:
        record = "-"
    if signal == "SUPPORT":
        return f"Support {record}"
    if signal == "AGAINST":
        return f"Against {record}"
    if signal == "NEUTRAL":
        return f"Neutral {record}"
    return record


def render_marq_ai_box(prediction):
    pick_marq = prediction.get("marq_crowd_pick_pct")
    opponent_marq = prediction.get("marq_crowd_opponent_pct")

    if pick_marq is None and opponent_marq is None and prediction.get("marq_ai_score") is None:
        return f"""
        <div class="intel-panel marq-panel">
            <div class="panel-title">MARQ</div>
            <div class="market-badge market-unavailable">No market data</div>
        </div>
"""

    def _format_signed_pct(value):
        try:
            if value is None or value == "":
                return "-"
            number = float(value)
            sign = "+" if number > 0 else ""
            return f"{sign}{number:.1f}%"
        except Exception:
            return "-"

    def _format_move_signal(value):
        if value is None or value == "":
            return "Pending"
        text = str(value).replace("_", " ").strip()
        upper = text.upper()
        if upper in {"TOWARD PICK", "TOWARD_PICK"}:
            return "Toward"
        if upper in {"AGAINST PICK", "AGAINST_PICK"}:
            return "Against"
        return " ".join(part.capitalize() for part in text.split())

    edge = prediction.get("marq_edge_pct")
    if edge is None:
        model_pct = normalize_probability_for_display(prediction.get("probability"))
        pick_pct = safe_float(pick_marq)
        if model_pct is not None and pick_pct is not None:
            edge = float(model_pct) - float(pick_pct)

    move_signal = prediction.get("marq_display_move_signal") or prediction.get("marq_move_signal") or "Pending"
    move_pct = prediction.get("marq_move_pct")
    if move_pct is None:
        move_pct = prediction.get("marq_market_move_pct")
    move_range = prediction.get("marq_move_range")
    if not move_range:
        initial_pick = safe_float(prediction.get("marq_initial_pick_odds")) or safe_float(prediction.get("marq_opening"))
        current_pick = safe_float(prediction.get("marq_current_pick_odds")) or safe_float(prediction.get("marq_latest"))
        if initial_pick is not None and current_pick is not None and initial_pick > 1 and current_pick > 1:
            move_range = f"{initial_pick:.2f} -> {current_pick:.2f}"
            if move_pct is None:
                move_pct = abs((current_pick - initial_pick) / initial_pick) * 100.0

    rows = (
        metric_row("Pick Marq", market_pct(pick_marq))
        + metric_row("Opp Marq", market_pct(opponent_marq))
        + metric_row("Marq Edge", _format_signed_pct(edge))
        + metric_row("Move", _format_move_signal(move_signal))
        + metric_row("Move %", market_pct(move_pct))
    )
    if move_range:
        rows += metric_row("Range", move_range)

    return f"""
        <div class="intel-panel marq-panel">
            <div class="panel-title">MARQ</div>
            {rows}
        </div>
"""


def render_sets_box(expected_sets, sets_probability_label, sets_probability, most_likely_html, prediction=None):
    prediction = prediction or {}
    games_line = prediction.get("games_line")
    games_over_probability = prediction.get("games_over_probability")

    extra_rows = ""
    if games_line is not None:
        extra_rows += metric_row("Games", f"{games_line}")
    if games_over_probability is not None:
        extra_rows += metric_row("Over", yes_no_market_probability(games_over_probability))

    return f"""
        <div class="intel-panel sets-panel">
            <div class="panel-title">SETS</div>
            {metric_row("Sets", expected_sets)}
            {metric_row(sets_probability_label, sets_probability)}
            {most_likely_html}
            {extra_rows}
        </div>
"""



def _signed_pct_from_decimal(value):
    try:
        if value is None or value == "":
            return "-"
        number = float(value)
        sign = "+" if number > 0 else ""
        return f"{sign}{number * 100:.1f}%"
    except Exception:
        return "-"


def _thinq_conf_display(prediction):
    value = prediction.get("thinq_confidence")
    if value in [None, ""]:
        return "-"
    try:
        number = float(value)
        if number <= 1.0:
            number *= 100.0
        return f"{number:.0f}%"
    except Exception:
        return "-"


def _thinq_elo_pick_display(prediction):
    edge = safe_float(prediction.get("thinq_elo_edge"))
    if edge is None:
        return "No data"
    if abs(edge) < 0.005:
        return "Even"
    player = prediction.get("player1") if edge > 0 else prediction.get("player2")
    return f"{safe(player)} {_signed_pct_from_decimal(edge)}"


def _thinq_h2h_display(prediction):
    ctx = prediction.get("thinq_h2h_context") if isinstance(prediction.get("thinq_h2h_context"), dict) else {}
    status = str(prediction.get("thinq_h2h_status") or ctx.get("h2h_status") or "NO_DATA").upper()
    total = safe_float(prediction.get("thinq_h2h_total_matches") or ctx.get("h2h_total_matches"))
    p1w = safe_float(prediction.get("thinq_h2h_player1_wins") or ctx.get("h2h_player1_wins"))
    p2w = safe_float(prediction.get("thinq_h2h_player2_wins") or ctx.get("h2h_player2_wins"))
    if status in {"ERROR", "ERROR_NON_BLOCKING"}:
        return "Error safe"
    if total is None or total <= 0:
        return "No data"
    return f"{int(p1w or 0)}-{int(p2w or 0)} ({int(total)})"


def render_thinq_box(prediction):
    available = prediction.get("thinq_available")
    if available is False:
        error = prediction.get("thinq_error") or "Unavailable"
        return f"""
<div class=\"mini-card thinq-card\">
  <div class=\"mini-title\">THINQ</div>
  {metric_row("Status", "Unavailable")}
  {metric_row("Reason", str(error)[:42])}
</div>
"""
    adj = prediction.get("corq_thinq_adjustment")
    rows = (
        metric_row("Conf", _thinq_conf_display(prediction)) +
        metric_row("ELO PICK", _thinq_elo_pick_display(prediction)) +
        metric_row("H2H", _thinq_h2h_display(prediction)) +
        metric_row("ADJ", _signed_pct_from_decimal(adj))
    )
    return f"""
<div class=\"mini-card thinq-card\">
  <div class=\"mini-title\">THINQ</div>
  {rows}
</div>
"""

def render_match_intelligence(
    prediction,
    expected_sets,
    sets_probability_label,
    sets_probability,
    most_likely_html,
    model_view="corq",
):
    return f"""
        <div class="intel-title">Match Intelligence</div>
        <div class="intel-layout">
            {render_data_ai_box(prediction, model_view=model_view)}
            {render_marq_ai_box(prediction)}
            {render_sets_box(expected_sets, sets_probability_label, sets_probability, most_likely_html, prediction=prediction)}
        </div>
"""


def render_summary(predictions):
    count = len(predictions)
    probabilities = []
    ai_match_values = []

    for prediction in predictions:
        try:
            if prediction.get("probability") is not None:
                probabilities.append(float(prediction.get("probability")))
        except Exception:
            pass

        try:
            if prediction.get("ai_match") is not None:
                ai_match_values.append(float(prediction.get("ai_match")))
        except Exception:
            pass

    avg_probability = "-"
    avg_ai_match = "-"

    if probabilities:
        avg_probability = f"{sum(probabilities) / len(probabilities) * 100:.1f}%"

    if ai_match_values:
        avg_ai_match = f"{sum(ai_match_values) / len(ai_match_values):.1f}%"

    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""
<div class="summary">
    <div class="summary-card"><div class="summary-label">Picks</div><div class="summary-value">{count}</div></div>
    <div class="summary-card"><div class="summary-label">Average Win %</div><div class="summary-value">{avg_probability}</div></div>
    <div class="summary-card"><div class="summary-label">Average AI Match</div><div class="summary-value">{avg_ai_match}</div></div>
    <div class="summary-card"><div class="summary-label">Updated</div><div class="summary-value small">{updated}</div></div>
</div>
"""


def resolve_match_time(prediction, default="-"):
    for key in ["time", "match_time", "start_time", "startTime", "scheduled_time", "event_time", "datetime", "match_datetime", "utc_time"]:
        value = prediction.get(key)
        if value is not None and value != "":
            return str(value)
    return default


def render_rows(predictions, model_view="corq"):
    if not predictions:
        return '<tr><td colspan="7" class="empty">No picks available.</td></tr>'

    rows = []

    for index, prediction in enumerate(predictions, start=1):
        pick = safe(prediction.get("pick"))
        opponent = safe(prediction.get("opponent"))
        match = safe(prediction.get("match"))
        time = safe(resolve_match_time(prediction))
        probability = pct(prediction.get("probability"))
        pick_odd_value = pick_odds_value(prediction)
        opponent_odd_value = opponent_odds_value(prediction)
        pick_odds_badge = odds_badge(pick_odd_value, "Pick")
        opponent_odds_badge = odds_badge(opponent_odd_value, "Opp")
        odd = odds(pick_odd_value)
        expected_sets = safe(prediction.get("expected_sets"))
        sets_probability = pct(prediction.get("sets_probability"))
        sets_probability_label = safe(resolve_sets_label(prediction))
        most_likely_score = safe(resolve_pick_score_display(prediction), default="")
        match_meta = safe(format_match_meta(prediction), default="")
        match_meta_html = f'<div class="match-meta">{match_meta}</div>' if match_meta else ""
        most_likely_html = metric_row("Pick/Opp", most_likely_score) if most_likely_score else ""

        intelligence_html = render_match_intelligence(
            prediction,
            expected_sets,
            sets_probability_label,
            sets_probability,
            most_likely_html,
            model_view=model_view,
        )

        rows.append(f"""
<tr>
    <td class="rank">#{index}</td>
    <td class="pick-cell">
        <div class="pick-name">{pick}</div>
        <div class="pick-odds-under">{pick_odds_badge}</div>
        <div class="pick-sub">TO WIN</div>
        <div class="match-name">{match}</div>
        {match_meta_html}
    </td>
    <td class="opponent-cell">
        <div class="opponent-name">{opponent}</div>
        <div class="opponent-odds-under">{opponent_odds_badge}</div>
    </td>
    <td>{time}</td>
    <td class="probability">{probability}</td>
    <td class="odds">{odd}</td>
    <td class="intel">{intelligence_html}</td>
</tr>
""")

    return "\n".join(rows)


def render_page(predictions, title, subtitle):
    model_view = resolve_model_view(title, subtitle)
    rows = render_rows(predictions, model_view=model_view)
    summary = render_summary(predictions)
    nav = render_nav()
    page_title = safe(title or SITE_TITLE)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{page_title}</title>
<style>
:root {{ --bg:#0f172a; --panel:#111827; --panel-2:#1e293b; --border:#334155; --text:#e5e7eb; --muted:#94a3b8; --green:#22c55e; --orange:#fb923c; --red:#ef4444; --yellow:#facc15; --blue:#38bdf8; --purple:#c084fc; }}
* {{ box-sizing:border-box; }}
html, body {{ margin:0; padding:0; background:var(--bg); color:var(--text); font-family:Arial, Helvetica, sans-serif; }}
.wrapper {{ max-width:1440px; margin:0 auto; padding:28px; }}
.header {{ display:grid; grid-template-columns:minmax(560px,1fr) auto; gap:40px; align-items:start; margin-bottom:24px; }}
.logo {{ font-size:30px; font-weight:900; line-height:1.15; color:var(--text); letter-spacing:.2px; white-space:nowrap; }}
.subtitle {{ color:var(--muted); margin-top:10px; font-size:14px; line-height:1.45; max-width:800px; }}
.nav {{ display:flex; gap:18px; align-items:center; flex-wrap:nowrap; padding-top:8px; white-space:nowrap; }}
.nav a {{ color:var(--text); text-decoration:none; font-weight:900; font-size:14px; letter-spacing:.04em; }}
.nav a:hover {{ color:var(--blue); }}
.summary {{ display:grid; grid-template-columns:repeat(4,1fr); gap:14px; margin-bottom:22px; }}
.summary-card {{ background:var(--panel); border:1px solid var(--border); border-radius:14px; padding:16px; }}
.summary-label {{ color:var(--muted); font-size:13px; margin-bottom:8px; }}
.summary-value {{ font-size:22px; font-weight:800; }}
.summary-value.small {{ font-size:14px; }}
.table-wrap {{ overflow-x:auto; background:var(--panel); border:1px solid var(--border); border-radius:16px; }}
table {{ width:100%; border-collapse:collapse; min-width:1040px; }}
thead {{ background:var(--panel-2); }}
th {{ padding:14px 12px; text-align:left; font-size:13px; color:var(--muted); border-bottom:1px solid var(--border); text-transform:uppercase; letter-spacing:.04em; }}
td {{ padding:16px 12px; border-bottom:1px solid var(--border); vertical-align:top; }}
tr:hover {{ background:rgba(255,255,255,.03); }}
.rank {{ font-weight:800; color:var(--blue); }}
.pick-name {{ font-size:20px; line-height:1.12; font-weight:900; }}
.pick-sub {{ color:var(--green); font-size:14px; line-height:1.1; margin-top:4px; font-weight:900; }}
.match-name {{ color:var(--muted); font-size:12px; line-height:1.18; margin-top:7px; }}
.match-meta {{ color:var(--blue); font-size:12px; line-height:1.18; margin-top:5px; font-weight:700; }}
.probability {{ font-weight:800; color:var(--green); }}
.odds {{ font-weight:800; color:var(--yellow); }}
.intel {{ line-height:1.45; min-width:390px; }}
.intel-title {{ margin-bottom:6px; color:var(--muted); font-size:11px; font-weight:900; letter-spacing:.04em; text-transform:uppercase; }}
.intel-layout {{ display:grid; grid-template-columns:minmax(110px,1fr) minmax(110px,1fr) minmax(130px,1.15fr); gap:8px; align-items:stretch; }}
.intel-panel {{ min-height:92px; padding:8px 9px; border-radius:8px; font-size:11px; line-height:1.35; background:rgba(100,116,139,.14); border:1px solid rgba(100,116,139,.38); }}
.panel-title {{ color:#fff; font-size:10px; font-weight:900; text-transform:uppercase; letter-spacing:.05em; margin-bottom:6px; }}
.metric-row {{ display:grid; grid-template-columns:58px auto; column-gap:7px; align-items:center; margin-top:3px; }}
.metric-row span {{ color:var(--muted); }}
.metric-row strong {{ text-align:right; color:var(--text); font-weight:900; }}
.ai-delta {{ margin-top:7px; text-align:right; font-size:10px; font-weight:900; }}
.delta-thinq {{ color:var(--blue); }} .delta-corq {{ color:var(--orange); }} .delta-cloq {{ color:var(--purple); }} .delta-even {{ color:var(--muted); }} .delta-muted {{ color:var(--muted); }}
.market-badge {{ display:inline-block; margin-top:8px; padding:5px 10px; border-radius:5px; font-size:10px; font-weight:800; letter-spacing:.05em; text-transform:uppercase; }}
.market-bullish {{ color:#22c55e; border:1px solid rgba(34,197,94,.45); background:rgba(34,197,94,.08); }}
.market-support {{ color:#38bdf8; border:1px solid rgba(56,189,248,.45); background:rgba(56,189,248,.08); }}
.market-neutral {{ color:#94a3b8; border:1px solid rgba(148,163,184,.45); background:rgba(148,163,184,.08); }}
.market-caution {{ color:#fb923c; border:1px solid rgba(251,146,60,.45); background:rgba(251,146,60,.08); }}
.market-bearish {{ color:#ef4444; border:1px solid rgba(239,68,68,.45); background:rgba(239,68,68,.08); }}
.market-unavailable {{ color:#94a3b8; border:1px solid rgba(148,163,184,.35); background:rgba(148,163,184,.05); text-transform:none; }}
.empty {{ text-align:center; color:var(--muted); padding:40px; }}
.footer {{ max-width:900px; margin:38px auto 0; color:var(--muted); font-size:12px; text-align:center; line-height:1.7; }}
@media (max-width:1050px) {{ .header{{display:block;}} .logo{{white-space:normal;}} .nav{{margin-top:16px; padding-top:0; flex-wrap:wrap;}} .summary{{grid-template-columns:1fr 1fr;}} }}
@media (max-width:700px) {{ .wrapper{{padding:16px;}} .summary{{grid-template-columns:1fr;}} .intel-layout{{grid-template-columns:1fr;}} }}
</style>
</head>
<body>
<div class="wrapper">
    <div class="header"><div><div class="logo">{safe(HEADER_TITLE)}</div><div class="subtitle">{safe(HEADER_SUBTITLE)}</div></div>{nav}</div>
    {summary}
    <div class="table-wrap"><table><thead><tr><th>#</th><th>Pick</th><th>Opponent</th><th>Time</th><th>Win %</th><th>Odds</th><th>Match Intelligence</th></tr></thead><tbody>{rows}</tbody></table></div>
    <div class="footer">{safe(FOOTER_TEXT)}</div>
</div>
</body>
</html>
"""


def write_page(predictions, title, subtitle, destination):
    html_text = render_page(predictions=predictions, title=title, subtitle=subtitle)
    directory = os.path.dirname(destination)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(destination, "w", encoding="utf-8") as file:
        file.write(html_text)


def render_rss(predictions, title, link):
    now = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")
    items = []

    for prediction in predictions:
        pick = safe(prediction.get("pick"))
        opponent = safe(prediction.get("opponent"))
        match_time = safe(resolve_match_time(prediction))
        probability = pct(prediction.get("probability"))
        pick_odd_value = pick_odds_value(prediction)
        opponent_odd_value = opponent_odds_value(prediction)
        pick_odds_badge = odds_badge(pick_odd_value, "Pick")
        opponent_odds_badge = odds_badge(opponent_odd_value, "Opp")
        odd = odds(pick_odd_value)
        expected_sets = safe(prediction.get("expected_sets"))
        tournament = safe(prediction.get("tournament"))
        surface = safe(prediction.get("surface"))
        best_of = safe(prediction.get("best_of"))
        sets_label = safe(resolve_sets_label(prediction))
        sets_probability = pct(prediction.get("sets_probability"))
        most_likely_score = safe(resolve_pick_score_display(prediction), default="-")

        metrics = resolve_ai_metrics(prediction)
        corq_ai = format_pct_points(metrics["corq_pct"])
        thinq_ai = format_pct_points(metrics["thinq_pct"])
        cloq_ai = format_pct_points(metrics["cloq_pct"])
        ai_match = format_pct_points(metrics["ai_match"])
        model_view = resolve_model_view(title, "")
        delta = resolve_ai_delta(metrics, model_view=model_view)

        marq_pick_market = market_pct(prediction.get("marq_crowd_pick_pct"))
        marq_opp_market = market_pct(prediction.get("marq_crowd_opponent_pct"))
        marq_market_lean = resolve_market_lean(prediction)

        marq_move = safe(prediction.get("marq_move_signal"), default="-")
        marq_sharp = safe(prediction.get("marq_sharp_signal"), default="-")
        marq_quality = safe(prediction.get("marq_quality_signal"), default="-")
        marq_clv = safe(prediction.get("marq_clv_status"), default="Pending")

        description_text = (
            f"Time: {match_time}\n"
            f"Pick: {pick}\nOpponent: {opponent}\nTournament: {tournament}\nSurface: {surface}\n"
            f"Best of: {best_of}\nWin probability: {probability}\nOdds: {odd}\n"
            f"Corq AI: {corq_ai}\nThinq AI: {thinq_ai}\nCloq AI: {cloq_ai}\nAI Match: {ai_match}\nAI Difference: {delta['label']}\n"
            f"MARQ Pick Marq: {marq_pick_market}\nMARQ Opp Marq: {marq_opp_market}\n"
            f"MARQ Move: {marq_move}\n"
            f""
            f"Expected sets: {expected_sets}\n{sets_label}: {sets_probability}\n"
            f"Most likely score: {most_likely_score}\n"
            f"Games line: {safe(prediction.get('games_line'))}\n"
            f"Games over probability: {yes_no_market_probability(prediction.get('games_over_probability'))}\n"
            f"Tie-break probability: {yes_no_market_probability(prediction.get('tie_break_probability'))}\n\n{HEADER_SUBTITLE}\n{FOOTER_TEXT}"
        )

        description = html.escape(description_text)

        items.append(f"""
<item>
<title>{match_time} | {pick} to win vs {opponent}</title>
<link>{link}</link>
<description>{description}</description>
<pubDate>{now}</pubDate>
</item>
""")

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
<channel>
<title>{html.escape(title)}</title>
<link>{link}</link>
<description>{html.escape(HEADER_TITLE)}</description>
{''.join(items)}
</channel>
</rss>
"""


def write_rss(predictions, title, link, destination):
    xml = render_rss(predictions=predictions, title=title, link=link)
    directory = os.path.dirname(destination)
    if directory:
        os.makedirs(directory, exist_ok=True)
    with open(destination, "w", encoding="utf-8") as file:
        file.write(xml)
