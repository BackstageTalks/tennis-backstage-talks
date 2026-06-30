from datetime import datetime


def generate_rss(top_preds):
    now = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S GMT")

    rss = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
<channel>
<title>Backstage Talks Tennis Picks</title>
<description>Daily TOP tennis betting picks</description>
<link>https://backstagetalks.github.io/tennis-backstage-talks/</link>
<lastBuildDate>{now}</lastBuildDate>
"""

    for p in top_preds:
        pick = p["pick"]
        opponent = p["player2"] if p["pick"] == p["player1"] else p["player1"]
        prob = round(p["probability"] * 100, 1)
        odds = p["odds"] if p["odds"] else "-"
        time = p.get("time", "TBD")

        title = f"{pick} vs {opponent}"
        description = f"""
Pick: {pick} to win
Opponent: {opponent}
Win probability: {prob}%
Odds: {odds}
Time: {time}
"""

        rss += f"""
<item>
<title>{title}</title>
<description>{description}</description>
<pubDate>{now}</pubDate>
</item>
"""

    rss += """
</channel>
</rss>
"""

    return rss
