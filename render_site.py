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


def html_link(url, label):
    return f'<a href="{html.escape(str(url), quote=True)}">{safe(label)}</a>'


def render_nav():
    return f"""
<nav class="nav" aria-label="Main navigation">
    {html_link(f"{BASE_URL}/", "TOP5")}
    {html_link(f"{BASE_URL}/all/", "ALL")}
    {html_link(f"{BASE_URL}/results/", "RESULTS")}
</nav>
"""


def format_match_meta(prediction):
    parts = []
    for key in ["tournament", "surface"]:
        if prediction.get(key):
            parts.append(str(prediction.get(key)))
    if prediction.get("best_of"):
        parts.append(f"BO{prediction.get('best_of')}")
    return " • ".join(parts)


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


def resolve_marq_signal(prediction):
    signal = prediction.get("marq_ai_signal")
    score = prediction.get("marq_ai_score")
    if score is None:
        return "NO MARKET DATA"
    if not signal:
        return "NEUTRAL"
    return str(signal).upper()


def normalize_probability_for_display(value):
    """
    Project convention:
    - Corq probability is usually stored as 0.792.
    - BsT probability may be stored as 75.4 or 0.754 depending on source.
    Returns percentage points, e.g. 79.2.
    """
    number = safe_float(value)
    if number is None:
        return None
    if number <= 1.0:
        return number * 100.0
    return number


def resolve_ai_metrics(prediction):
    corq_pct = normalize_probability_for_display(
        prediction.get("corq_ai_probability") or prediction.get("probability")
    )
    bst_pct = normalize_probability_for_display(prediction.get("bst_ai_probability"))

    ai_match = safe_float(prediction.get("ai_match"))
    if ai_match is None and corq_pct is not None and bst_pct is not None:
        ai_match = max(0.0, 100.0 - abs(corq_pct - bst_pct))

    signed_gap = safe_float(prediction.get("ai_signed_gap"))
    if signed_gap is None and corq_pct is not None and bst_pct is not None:
        signed_gap = corq_pct - bst_pct

    if signed_gap is None:
        lean_label = "-"
        gap_text = "-"
    elif signed_gap > 0:
        lean_label = "Corq"
        gap_text = f"Corq +{abs(signed_gap):.1f} pp"
    elif signed_gap < 0:
        lean_label = "BsT"
        gap_text = f"BsT +{abs(signed_gap):.1f} pp"
    else:
        lean_label = "Even"
        gap_text = "Even 0.0 pp"

    ai_color = str(prediction.get("ai_match_color") or "").lower().strip()
    if ai_color not in ["green", "orange", "red", "gray"]:
        if ai_match is None:
            ai_color = "gray"
        elif ai_match >= 90:
            ai_color = "green"
        elif ai_match >= 75:
            ai_color = "orange"
        else:
            ai_color = "red"

    return {
        "corq_pct": corq_pct,
        "bst_pct": bst_pct,
        "ai_match": ai_match,
        "signed_gap": signed_gap,
        "gap_text": gap_text,
        "lean_label": lean_label,
        "ai_color": ai_color,
    }


def format_pct_points(value):
    if value is None:
        return "-"
    return f"{float(value):.1f}%"


def render_data_ai_box(prediction):
    status = prediction.get("bst_ai_status")
    metrics = resolve_ai_metrics(prediction)
    corq_display = format_pct_points(metrics["corq_pct"])

    if status != "OK":
        return f"""
        <div class="intel-box data-ai-box">
            <div class="box-title">DATA AI</div>
            <div class="intel-row"><span>Corq AI</span><span>{corq_display}</span></div>
            <div class="intel-row muted-row"><span>BsT AI</span><span>No data</span></div>
            <div class="intel-row muted-row"><span>AI Match</span><span>-</span></div>
            <div class="ai-diff ai-diff-gray">BsT unavailable</div>
        </div>
"""

    color_class = f"ai-match-{metrics['ai_color']}"
    ai_match_display = format_pct_points(metrics["ai_match"])
    bst_display = format_pct_points(metrics["bst_pct"])
    gap_text = safe(metrics["gap_text"])

    return f"""
        <div class="intel-box data-ai-box">
            <div class="box-title">DATA AI</div>
            <div class="intel-row ai-main-row {color_class}"><span>AI Match</span><span>{ai_match_display}</span></div>
            <div class="intel-row"><span>Corq AI</span><span>{corq_display}</span></div>
            <div class="intel-row"><span>BsT AI</span><span>{bst_display}</span></div>
            <div class="ai-diff {color_class}">{gap_text}</div>
        </div>
"""


def render_marq_ai_box(prediction):
    marq_signal = resolve_marq_signal(prediction)
    signal_class_map = {
        "BULLISH": "market-bullish",
        "SUPPORT": "market-support",
        "NEUTRAL": "market-neutral",
        "CAUTION": "market-caution",
        "BEARISH": "market-bearish",
        "NO MARKET DATA": "market-unavailable",
    }
    signal_class = signal_class_map.get(marq_signal, "market-neutral")
    display_signal = "No market data" if marq_signal == "NO MARKET DATA" else marq_signal
    return f"""
        <div class="intel-box marq-ai-box">
            <div class="box-title">MARQ AI</div>
            <div class="marq-signal {signal_class}">{safe(display_signal)}</div>
        </div>
"""


def render_sets_box(expected_sets, sets_probability_label, sets_probability, most_likely_html):
    return f"""
        <div class="intel-box sets-box">
            <div class="box-title">SETS</div>
            <div class="intel-row"><span>Sets</span><span>{expected_sets}</span></div>
            <div class="intel-row"><span>{sets_probability_label}</span><span>{sets_probability}</span></div>
            {most_likely_html}
        </div>
"""


def render_match_intelligence(prediction, expected_sets, sets_probability_label, sets_probability, most_likely_html):
    return f"""
        <div class="intel-title">Match Intelligence</div>
        <div class="intel-layout">
            {render_data_ai_box(prediction)}
            {render_marq_ai_box(prediction)}
            {render_sets_box(expected_sets, sets_probability_label, sets_probability, most_likely_html)}
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

    avg_probability = f"{sum(probabilities) / len(probabilities) * 100:.1f}%" if probabilities else "-"
    avg_ai_match = f"{sum(ai_match_values) / len(ai_match_values):.1f}%" if ai_match_values else "-"
    updated = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    return f"""
<div class="summary">
    <div class="summary-card"><div class="summary-label">Picks</div><div class="summary-value">{count}</div></div>
    <div class="summary-card"><div class="summary-label">Average Win %</div><div class="summary-value">{avg_probability}</div></div>
    <div class="summary-card"><div class="summary-label">Average AI Match</div><div class="summary-value">{avg_ai_match}</div></div>
    <div class="summary-card"><div class="summary-label">Updated</div><div class="summary-value small">{updated}</div></div>
</div>
"""


def render_rows(predictions):
    if not predictions:
        return '<tr><td colspan="7" class="empty">No picks available.</td></tr>'

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
        most_likely_score = safe(prediction.get("most_likely_score"), default="")
        match_meta = safe(format_match_meta(prediction), default="")
        match_meta_html = f'<div class="match-meta">{match_meta}</div>' if match_meta else ""
        most_likely_html = f'<div class="intel-row"><span>Score</span><span>{most_likely_score}</span></div>' if most_likely_score else ""
        match_intelligence_html = render_match_intelligence(prediction, expected_sets, sets_probability_label, sets_probability, most_likely_html)

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
    <td class="intel">{match_intelligence_html}</td>
</tr>
""")
    return "\n".join(rows)


def render_page(predictions, title, subtitle):
    rows = render_rows(predictions)
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
:root {{ --bg:#0f172a; --panel:#111827; --panel-2:#1e293b; --border:#334155; --text:#e5e7eb; --muted:#94a3b8; --green:#22c55e; --yellow:#facc15; --blue:#38bdf8; --orange:#fb923c; --red:#ef4444; --gray:#94a3b8; }}
* {{ box-sizing:border-box; }}
html, body {{ margin:0; padding:0; background:var(--bg); color:var(--text); font-family:Arial, Helvetica, sans-serif; }}
.wrapper {{ max-width:1500px; margin:0 auto; padding:28px; }}
.header {{ display:grid; grid-template-columns:minmax(560px, 1fr) auto; gap:40px; align-items:start; margin-bottom:24px; }}
.logo {{ font-size:30px; font-weight:900; line-height:1.15; white-space:nowrap; }}
.subtitle {{ color:var(--muted); margin-top:10px; font-size:14px; line-height:1.45; max-width:800px; }}
.nav {{ display:flex; gap:18px; align-items:center; flex-wrap:nowrap; padding-top:8px; white-space:nowrap; }}
.nav a {{ color:var(--text); text-decoration:none; font-weight:900; font-size:14px; letter-spacing:.04em; }}
.nav a:hover {{ color:var(--blue); }}
.summary {{ display:grid; grid-template-columns:repeat(4, 1fr); gap:14px; margin-bottom:22px; }}
.summary-card {{ background:var(--panel); border:1px solid var(--border); border-radius:14px; padding:16px; }}
.summary-label {{ color:var(--muted); font-size:13px; margin-bottom:8px; }}
.summary-value {{ font-size:22px; font-weight:800; }}
.summary-value.small {{ font-size:14px; }}
.table-wrap {{ overflow-x:auto; background:var(--panel); border:1px solid var(--border); border-radius:16px; }}
table {{ width:100%; border-collapse:collapse; min-width:1220px; }}
thead {{ background:var(--panel-2); }}
th {{ padding:14px 12px; text-align:left; font-size:13px; color:var(--muted); border-bottom:1px solid var(--border); text-transform:uppercase; letter-spacing:.04em; }}
td {{ padding:16px 12px; border-bottom:1px solid var(--border); vertical-align:top; }}
tr:hover {{ background:rgba(255,255,255,.03); }}
.rank {{ font-weight:800; color:var(--blue); }}
.pick-name {{ font-size:16px; font-weight:800; }}
.pick-sub {{ color:var(--green); font-size:12px; margin-top:4px; font-weight:700; }}
.match-name {{ color:var(--muted); font-size:12px; margin-top:8px; }}
.match-meta {{ color:var(--blue); font-size:12px; margin-top:6px; font-weight:700; }}
.probability {{ font-weight:800; color:var(--green); }}
.odds {{ font-weight:800; color:var(--yellow); }}
.intel {{ line-height:1.45; min-width:500px; }}
.intel-title {{ margin-bottom:7px; color:var(--muted); font-size:11px; font-weight:900; letter-spacing:.04em; text-transform:uppercase; }}
.intel-layout {{ display:grid; grid-template-columns:128px 128px 160px; gap:10px; align-items:stretch; }}
.intel-box {{ min-height:104px; padding:9px 10px; border-radius:8px; font-size:11px; line-height:1.45; background:rgba(100,116,139,.12); border:1px solid rgba(148,163,184,.55); overflow:visible; }}
.box-title {{ color:#e5e7eb; font-size:11px; font-weight:900; text-transform:uppercase; letter-spacing:.05em; margin-bottom:7px; }}
.intel-row {{ display:grid; grid-template-columns:64px minmax(48px, 1fr); column-gap:7px; align-items:center; margin-top:4px; }}
.intel-row span:first-child {{ min-width:0; }}
.intel-row span:last-child {{ text-align:right; color:var(--text); font-weight:800; min-width:0; }}
.ai-main-row span:first-child, .ai-main-row span:last-child {{ font-weight:900; }}
.ai-match-green span, .ai-diff-green {{ color:var(--green) !important; }}
.ai-match-orange span, .ai-diff-orange {{ color:var(--orange) !important; }}
.ai-match-red span, .ai-diff-red {{ color:var(--red) !important; }}
.ai-match-gray span, .ai-diff-gray {{ color:var(--gray) !important; }}
.ai-diff {{ margin-top:6px; padding-top:5px; border-top:1px solid rgba(148,163,184,.25); font-size:10px; line-height:1.2; text-align:right; font-weight:900; white-space:nowrap; }}
.sets-box {{ min-width:160px; }}
.sets-box .intel-row {{ grid-template-columns:58px minmax(78px, 1fr); column-gap:8px; }}
.sets-box .intel-row span:first-child {{ white-space:nowrap; }}
.sets-box .intel-row span:last-child {{ white-space:nowrap; overflow:visible; text-align:right; }}
.muted-row {{ color:var(--muted); }}
.marq-signal {{ display:inline-flex; align-items:center; justify-content:center; min-height:32px; width:100%; margin-top:8px; padding:7px 8px; border-radius:6px; font-size:11px; font-weight:900; letter-spacing:.05em; text-transform:uppercase; text-align:center; }}
.market-bullish {{ color:#22c55e; border:1px solid rgba(34,197,94,.55); background:rgba(34,197,94,.10); }}
.market-support {{ color:#38bdf8; border:1px solid rgba(56,189,248,.55); background:rgba(56,189,248,.10); }}
.market-neutral {{ color:#94a3b8; border:1px solid rgba(148,163,184,.55); background:rgba(148,163,184,.10); }}
.market-caution {{ color:#fb923c; border:1px solid rgba(251,146,60,.55); background:rgba(251,146,60,.10); }}
.market-bearish {{ color:#ef4444; border:1px solid rgba(239,68,68,.55); background:rgba(239,68,68,.10); }}
.market-unavailable {{ color:#94a3b8; border:1px solid rgba(148,163,184,.35); background:rgba(148,163,184,.06); font-size:10px; letter-spacing:0; text-transform:none; }}
.empty {{ text-align:center; color:var(--muted); padding:40px; }}
.footer {{ max-width:900px; margin:38px auto 0; color:var(--muted); font-size:12px; text-align:center; line-height:1.7; }}
@media (max-width:1200px) {{ .intel {{ min-width:220px; }} .intel-layout {{ grid-template-columns:1fr; }} }}
@media (max-width:1050px) {{ .header {{ display:block; }} .logo {{ white-space:normal; }} .nav {{ margin-top:16px; padding-top:0; flex-wrap:wrap; }} .summary {{ grid-template-columns:1fr 1fr; }} }}
@media (max-width:600px) {{ .wrapper {{ padding:16px; }} .summary {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<div class="wrapper">
    <div class="header">
        <div><div class="logo">{safe(HEADER_TITLE)}</div><div class="subtitle">{safe(HEADER_SUBTITLE)}</div></div>
        {nav}
    </div>
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
        probability = pct(prediction.get("probability"))
        odd = odds(prediction.get("odds"))
        expected_sets = safe(prediction.get("expected_sets"))
        tournament = safe(prediction.get("tournament"))
        surface = safe(prediction.get("surface"))
        best_of = safe(prediction.get("best_of"))
        sets_label = safe(resolve_sets_label(prediction))
        sets_probability = pct(prediction.get("sets_probability"))
        most_likely_score = safe(prediction.get("most_likely_score"), default="-")
        description_text = (
            f"Pick: {pick}\nOpponent: {opponent}\nTournament: {tournament}\nSurface: {surface}\n"
            f"Best of: {best_of}\nWin probability: {probability}\nOdds: {odd}\n"
            f"Expected sets: {expected_sets}\n{sets_label}: {sets_probability}\n"
            f"Most likely score: {most_likely_score}\n\n{HEADER_SUBTITLE}\n{FOOTER_TEXT}"
        )
        description = html.escape(description_text)
        items.append(f"""
<item>
<title>{pick} to win vs {opponent}</title>
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
