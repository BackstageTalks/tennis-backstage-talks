from prediction_engine import build_all_predictions, get_top_predictions


# ✅ HTML HEADER + STYLE
def html_header(title):
    return f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>{title}</title>
<style>
body {{
    background-color: #1a0f0f;
    color: white;
    font-family: Arial;
    padding: 20px;
}}

h1 {{
    margin-bottom: 20px;
}}

.row {{
    display: flex;
    justify-content: space-between;
    background: #2a1616;
    padding: 15px;
    margin-bottom: 10px;
    border-radius: 8px;
}}

.col {{
    flex: 1;
    padding: 5px;
}}

.pick {{
    font-weight: bold;
}}

.small {{
    color: #ccc;
    font-size: 13px;
}}

.header {{
    display: flex;
    font-weight: bold;
    margin-bottom: 10px;
}}
</style>
</head>
<body>
"""


# ✅ COMMON RENDER FUNCTION
def render_table(title, predictions):
    html = html_header(title)

    html += f"<h1>{title}</h1>"

    # ✅ HEADER ROW
    html += """
<div class="header">
    <div class="col">#</div>
    <div class="col">Pick</div>
    <div class="col">Opponent</div>
    <div class="col">Match time</div>
    <div class="col">Win %</div>
    <div class="col">Odds</div>
    <div class="col">Sets / Games</div>
</div>
"""

    # ✅ ROWS
    for i, p in enumerate(predictions, 1):
        p1 = p["player1"]
        p2 = p["player2"]
        pick = p["pick"]

        opponent = p2 if pick == p1 else p1

        prob = round(p["probability"] * 100, 1)
        odds = p["odds"] if p["odds"] else "-"

        # jednoduchý info blok
        sets_info = f"""
Sets: 2-3 sets<br>
Expected games: ~23<br>
INFO ONLY
"""

        html += f"""
<div class="row">
    <div class="col">#{i}</div>

    <div class="col pick">
        {pick} to win
    </div>

    <div class="col">
        {opponent}
    </div>

    <div class="col small">
        TBD
    </div>

    <div class="col">
        {prob}%
    </div>

    <div class="col">
        {odds}
    </div>

    <div class="col small">
        {sets_info}
    </div>
</div>
"""

    html += "</body></html>"

    return html


# ✅ MAIN RUN
def run():
    print("BUILDING ALL...")
    all_preds = build_all_predictions()

    print("BUILDING TOP...")
    top_preds = get_top_predictions()

    # ✅ SAVE ALL
    with open("public/839201239012/index.html", "w", encoding="utf-8") as f:
        f.write(render_table("All Matches", all_preds))

    # ✅ SAVE TOP
    with open("public/777123987111/index.html", "w", encoding="utf-8") as f:
        f.write(render_table("Top 5 Picks", top_preds))

    print("DONE ✅")


if __name__ == "__main__":
    run()
