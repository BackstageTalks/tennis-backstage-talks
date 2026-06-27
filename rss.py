import datetime
import json
import os
from xml.etree.ElementTree import Element, SubElement, tostring

def load_predictions(date: str | None = None):
    if date is None:
        date = datetime.date.today().isoformat()
    path = f"data/predictions_{date}.json"
    if not os.path.exists(path):
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def generate_rss(date: str | None = None) -> str:
    if date is None:
        date = datetime.date.today().isoformat()

    preds = load_predictions(date)

    rss = Element("rss", version="2.0")
    channel = SubElement(rss, "channel")

    title = SubElement(channel, "title")
    title.text = f"Tennis Predictions {date}"

    link = SubElement(channel, "link")
    link.text = "https://yourdomain.com/rss"

    desc = SubElement(channel, "description")
    desc.text = "Daily tennis predictions with value betting"

    for p in preds:
        item = SubElement(channel, "item")

        t = SubElement(item, "title")
        t.text = f"{p['player1']} vs {p['player2']} – {p['tournament']}"

        # Value bet text
        vb1 = p.get("value_player1", {})
        vb2 = p.get("value_player2", {})

        vb1_text = ""
        vb2_text = ""

        if vb1.get("is_value_bet"):
            vb1_text = f"VALUE BET on {p['player1']} (value {vb1['value']:.3f})"

        if vb2.get("is_value_bet"):
            vb2_text = f"VALUE BET on {p['player2']} (value {vb2['value']:.3f})"

        value_text = ""
        if vb1_text or vb2_text:
            value_text = f"\n{vb1_text}\n{vb2_text}"

        d = SubElement(item, "description")
        d.text = (
            f"Win probability {p['player1']}: {p['prob_player1']:.2f}, "
            f"{p['player2']}: {p['prob_player2']:.2f}"
            f"{value_text}"
        )

        guid = SubElement(item, "guid")
        guid.text = str(p["match_id"])

    return tostring(rss, encoding="unicode")

if __name__ == "__main__":
    print(generate_rss())
