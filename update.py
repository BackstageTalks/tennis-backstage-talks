import os
from prediction_engine import build_all_predictions, get_top_predictions
from history_tracker import save_today_bets
from rss_generator import generate_rss


def ensure_path(path):
    os.makedirs(path, exist_ok=True)


def html_header(title):
    return f"""<!DOCTYPE html><html>
<head><meta charset="UTF-8"><title>{title}</title></head>
<body style="background:#1a0f0f;color:white;font-family:Arial;padding:20px;">
<h1>Backstage Talks Tennis Picks</h1>
"""


def render_table(title, data):
    html = html_header(title)
    html += f"<h2>{title}</h2>"

    if not data:
        return html + "<p>No picks</p></body></html>"

    for i, p in enumerate(data, 1):
        html += f"<p>#{i} {p['pick']} vs {p['player2'] if p['pick']==p['player1'] else p['player1']} | {p['probability']} | {p['odds']}</p>"

    return html + "</body></html>"


def run():
    all_preds = build_all_predictions()
    top_preds = get_top_predictions(all_preds)

    save_today_bets(top_preds)

    ensure_path("public/839201239012")
    ensure_path("public/777123987111")

    with open("public/839201239012/index.html", "w") as f:
        f.write(render_table("ALL MATCHES", all_preds))

    with open("public/777123987111/index.html", "w") as f:
        f.write(render_table("TOP 5 PICKS", top_preds))

    rss = generate_rss(top_preds)

    with open("public/999333111777.xml", "w") as f:
        f.write(rss)


if __name__ == "__main__":
    run()
