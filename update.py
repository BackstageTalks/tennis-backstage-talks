import os
from prediction_engine import build_all_predictions, get_top_predictions
from history_tracker import save_today_bets
from rss_generator import generate_rss


def ensure(path):
    os.makedirs(path, exist_ok=True)


def html(title, data):
    out = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{title}</title>
</head>
<body style="background:#111;color:white;font-family:Arial;padding:20px;">
<h1>{title}</h1>
<hr>
"""

    if not data:
        return out + "<h2>No data</h2></body></html>"

    out += f"<p>Total: {len(data)}</p>"

    for i, p in enumerate(data, 1):
        opp = p["player2"] if p["pick"] == p["player1"] else p["player1"]

        out += f"""
<div style="margin-bottom:10px;padding:10px;border:1px solid #333;">
<b>#{i}</b><br>
Pick: {p['pick']}<br>
Opponent: {opp}<br>
Win%: {p['probability']}<br>
Odds: {p['odds']}<br>
Time: {p.get('time','')}
</div>
"""

    return out + "</body></html>"


def run():
    print("BUILDING ALL...")
    all_preds = build_all_predictions()
    print("ALL:", len(all_preds))

    print("BUILDING TOP...")
    top_preds = get_top_predictions(all_preds)
    print("TOP:", len(top_preds))

    save_today_bets(top_preds)

    # ✅ vytvor foldery v ROOT
    ensure("839201239012")
    ensure("777123987111")

    # ✅ ROOT redirect
    with open("index.html", "w") as f:
        f.write("""<html><head>
<meta http-equiv="refresh" content="0; url=777123987111/">
</head></html>""")

    # ✅ ALL
    with open("839201239012/index.html", "w") as f:
        f.write(html("ALL MATCHES", all_preds))

    # ✅ TOP
    with open("777123987111/index.html", "w") as f:
        f.write(html("TOP PICKS", top_preds))

    # ✅ RSS
    rss = generate_rss(top_preds)
    with open("999333111777.xml", "w") as f:
        f.write(rss)

    print("DONE ✅")


if __name__ == "__main__":
    run()
