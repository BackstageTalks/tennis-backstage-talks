import json
import glob
import os
import html
from datetime import datetime
from zoneinfo import ZoneInfo


PUBLIC_DIR = "public"
ALL_DIR = os.path.join(PUBLIC_DIR, "all")
SITE_TITLE = "Backstage Talks Tennis Picks - All Matches"
SITE_DESCRIPTION = "All available standard Elo tennis predictions."
BASE_URL = "https://backstagetalks.github.io/tennis-backstage-talks"

DISPLAY_TZ = ZoneInfo("Europe/Bratislava")


def latest_json(pattern):
    files = sorted(glob.glob(pattern))

    if not files:
        return None

    return files[-1]


def safe(value, default=""):
    if value is None:
        return default

    return str(value)


def pct(value):
    if value is None:
        return ""

    try:
        return f"{float(value) * 100:.1f}%"
    except Exception:
        return safe(value)


def parse_datetime(value):
    if not value:
        return None

    text = str(value).strip()

    try:
        if text.endswith("Z"):
            text = text.replace("Z", "+00:00")

        return datetime.fromisoformat(text)
    except Exception:
        return None


def get_display_time(item):
    match_start = item.get("match_start")
    raw_time = item.get("match_time_raw")

    parsed = parse_datetime(match_start)

    if parsed is not None:
        if parsed.tzinfo is not None:
            local_dt = parsed.astimezone(DISPLAY_TZ)
            return local_dt.strftime("%d.%m.%Y %H:%M %Z")

        return parsed.strftime("%d.%m.%Y %H:%M")

    if raw_time:
        return str(raw_time)

    return "Time unavailable"


def load_predictions():
    path = latest_json(os.path.join(PUBLIC_DIR, "all_predictions_*.json"))

    if not path:
        return [], None

    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    if isinstance(data, list):
        predictions = data
    elif isinstance(data, dict):
        predictions = data.get("predictions", [])
    else:
        predictions = []

    predictions.sort(
        key=lambda x: (
            x.get("probability") is not None,
            x.get("probability") or 0
        ),
        reverse=True
    )

    return predictions, path


def build_sets_games_html(item):
    alt = item.get("alternative_market_info") or {}

    if not alt:
        return '<span class="muted">No sets/games info</span>'

    most_likely_sets = alt.get("most_likely_sets")
    sets_probability = alt.get("sets_probability")
    sets_fair_odds = alt.get("sets_fair_odds")
    expected_games = alt.get("expected_games")
    games_lean = alt.get("games_lean")

    parts = []

    if most_likely_sets:
        parts.append(
            "Sets: "
            + html.escape(safe(most_likely_sets))
            + " ("
            + html.escape(pct(sets_probability))
            + ", fair odds "
            + html.escape(safe(sets_fair_odds, "n/a"))
            + ")"
        )

    if expected_games is not None:
        parts.append("Expected games: " + html.escape(safe(expected_games)))

    if games_lean:
        parts.append("Games: " + html.escape(safe(games_lean)))

    if not parts:
        parts.append("No clear sets/games info")

    return "<br>".join(parts) + '<br><span class="muted">INFO ONLY</span>'


def generate_html(predictions, source_path):
    os.makedirs(ALL_DIR, exist_ok=True)

    rows = []

    if not predictions:
        rows.append(
            """
            <tr>
              <td colspan="7" class="empty">No all predictions available.</td>
            </tr>
            """
        )
    else:
        for i, item in enumerate(predictions, start=1):
            pick_value = item.get("pick")
            opponent_value = item.get("opponent")

            if pick_value:
                pick = html.escape(safe(pick_value) + " to win")
                opponent = html.escape(safe(opponent_value))
            else:
                pick = '<span class="muted">No standard Elo available</span>'
                opponent = html.escape(safe(item.get("player1"))) + " vs " + html.escape(safe(item.get("player2")))

            match = html.escape(
                safe(item.get("player1"))
                + " vs "
                + safe(item.get("player2"))
            )

            match_time = html.escape(get_display_time(item))
            probability = html.escape(pct(item.get("probability")))
            odds = html.escape(safe(item.get("odds"), ""))
            sets_games = build_sets_games_html(item)

            rows.append(
                f"""
                <tr>
                  <td>#{i}</td>
                  <td><strong>{pick}</strong></td>
                  <td>{opponent}</td>
                  <td>{match}</td>
                  <td>{match_time}</td>
                  <td>{probability}</td>
                  <td>{odds}</td>
                  <td>{sets_games}</td>
                </tr>
                """
            )

    content = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{html.escape(SITE_TITLE)}</title>
  <meta name="viewport" content="width=device-width, initial-scale=1">

  <style>
    body {{
      background: #130d0d;
      color: #ffffff;
      font-family: Arial, Helvetica, sans-serif;
      margin: 0;
      padding: 12px;
    }}

    h1 {{
      font-size: 44px;
      margin: 0 0 8px 0;
      line-height: 1.05;
    }}

    .disclaimer {{
      color: #c9b8ad;
      font-size: 14px;
      margin-bottom: 22px;
      line-height: 1.5;
    }}

    table {{
      width: 100%;
      border-collapse: collapse;
      background: #211717;
      border-radius: 16px;
      overflow: hidden;
    }}

    th, td {{
      border-bottom: 1px solid #3a2929;
      padding: 14px 16px;
      text-align: left;
      vertical-align: top;
      font-size: 15px;
      line-height: 1.35;
    }}

    th {{
      color: #e8e0dc;
      font-weight: 700;
      background: #251a1a;
    }}

    tr:last-child td {{
      border-bottom: none;
    }}

    .empty {{
      padding: 24px;
      color: #f2e8dd;
      font-size: 18px;
    }}

    .muted {{
      color: #c9b8ad;
      font-size: 13px;
    }}

    @media (max-width: 950px) {{
      h1 {{
        font-size: 34px;
      }}

      table, thead, tbody, th, td, tr {{
        display: block;
      }}

      thead {{
        display: none;
      }}

      tr {{
        border-bottom: 1px solid #3a2929;
        padding: 12px 0;
      }}

      td {{
        border-bottom: none;
        padding: 8px 16px;
      }}
    }}
  </style>
</head>

<body>
  <h1>{html.escape(SITE_TITLE)}</h1>

  <div class="disclaimer">
    The data generated by the Backstage Talks STAT model is for statistical and informational purposes only.
  </div>

  <table>
    <thead>
      <tr>
        <th>#</th>
        <th>Pick</th>
        <th>Opponent</th>
        <th>Match</th>
        <th>Match time</th>
        <th>Win %</th>
        <th>Odds</th>
        <th>Sets / Games info</th>
      </tr>
    </thead>
    <tbody>
      {''.join(rows)}
    </tbody>
  </table>
</body>
</html>
"""

    with open(os.path.join(ALL_DIR, "index.html"), "w", encoding="utf-8") as f:
        f.write(content)


def build_sets_games_text(item):
    alt = item.get("alternative_market_info") or {}

    if not alt:
        return "No sets/games info"

    parts = []

    if alt.get("most_likely_sets"):
        parts.append(
            f"Sets: {alt.get('most_likely_sets')} "
            f"({pct(alt.get('sets_probability'))}, fair odds {safe(alt.get('sets_fair_odds'), 'n/a')})"
        )

    if alt.get("expected_games") is not None:
        parts.append(f"Expected games: {alt.get('expected_games')}")

    if alt.get("games_lean"):
        parts.append(f"Games: {alt.get('games_lean')}")

    parts.append("INFO ONLY")

    return " | ".join(parts)


def generate_rss(predictions):
    os.makedirs(PUBLIC_DIR, exist_ok=True)

    now = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    items = []

    for i, item in enumerate(predictions, start=1):
        pick = html.escape(safe(item.get("pick"), "No standard Elo available"))
        opponent = html.escape(safe(item.get("opponent"), ""))
        probability = html.escape(pct(item.get("probability")))
        odds = html.escape(safe(item.get("odds"), ""))
        sets_games = html.escape(build_sets_games_text(item))

        title = f"#{i} {pick} vs {opponent} | {probability} | odds {odds}"

        description = (
            f"Win %: {probability}<br>"
            f"Odds: {odds}<br>"
            f"Sets/Games: {sets_games}<br>"
            f"The data generated by the Backstage Talks STAT model is for statistical and informational purposes only."
        )

        items.append(f"""
        <item>
          <title>{title}</title>
          <description>{description}</description>
          <pubDate>{now}</pubDate>
          <guid>{BASE_URL}/all-pick-{i}-{pick}</guid>
        </item>
        """)

    rss = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
  <title>{html.escape(SITE_TITLE)}</title>
  <link>{BASE_URL}/all/</link>
  <description>{html.escape(SITE_DESCRIPTION)}</description>
  <lastBuildDate>{now}</lastBuildDate>
  {''.join(items)}
</channel>
</rss>
"""

    with open(os.path.join(PUBLIC_DIR, "tennis_all.xml"), "w", encoding="utf-8") as f:
        f.write(rss)


def main():
    predictions, source_path = load_predictions()

    print("ALL predictions loaded:", len(predictions))
    print("Source:", source_path)

    generate_html(predictions, source_path)
    generate_rss(predictions)

    print("Generated public/all/index.html")
    print("Generated public/tennis_all.xml")


if __name__ == "__main__":
    main()
