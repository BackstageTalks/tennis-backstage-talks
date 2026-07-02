import os


def render_predictions_page(
    predictions,
    title,
    destination,
):
    rows = []

    for i, p in enumerate(predictions, start=1):

        probability = round(
            p.get("probability", 0) * 100,
            1
        )

        rows.append(f"""
<tr>
<td>{i}</td>

<td>
<b>{p.get('pick', '-')}</b>
</td>

<td>
{p.get('opponent', '-')}
</td>

<td>
{p.get('time', '-')}
</td>

<td>
{probability}%
</td>

<td>
{p.get('odds', '-')}
</td>

<td>
Sets: {p.get('expected_sets', '-')}

<br><br>

Games: {p.get('expected_games', '-')}

<br><br>

Pick: {p.get('games_pick', '-')}

<br><br>

<b>{p.get('bet_tag', '-')}</b>
</td>
</tr>
""")

    html = f"""
<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">

<title>{title}</title>

<style>

body {{
    background: #0f172a;
    color: #e5e7eb;
    font-family: Arial, sans-serif;
    margin: 40px;
}}

h1 {{
    text-align: center;
}}

table {{
    width: 100%;
    border-collapse: collapse;
}}

th {{
    background: #1e293b;
    padding: 12px;
    border: 1px solid #334155;
}}

td {{
    padding: 12px;
    border: 1px solid #334155;
    vertical-align: top;
}}

tr:nth-child(even) {{
    background: #111827;
}}

.footer {{
    margin-top: 40px;
    text-align: center;
    color: #9ca3af;
    font-size: 12px;
}}

</style>
</head>

<body>

<h1>{title}</h1>

<table>
<thead>
<tr>
<th>#</th>
<th>Pick</th>
<th>Opponent</th>
<th>Time</th>
<th>Win %</th>
<th>Odds</th>
<th>Match Intelligence</th>
</tr>
</thead>

<tbody>
{''.join(rows)}
</tbody>

</table>

<div class="footer">

The information presented on this website is for informational and analytical purposes only.

<br><br>

The predictions do not constitute betting advice.

</div>

</body>
</html>
"""

    os.makedirs(
        os.path.dirname(destination)
        or ".",
        exist_ok=True,
    )

    with open(
        destination,
        "w",
        encoding="utf-8",
    ) as f:

        f.write(html)
