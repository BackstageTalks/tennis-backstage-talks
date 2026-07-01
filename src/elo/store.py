import pandas as pd
from pathlib import Path
from datetime import datetime

BASE = Path("data/elo")
BASE.mkdir(parents=True, exist_ok=True)

LATEST = {
    "atp_elo": BASE / "atp_elo_latest.csv",
    "wta_elo": BASE / "wta_elo_latest.csv",
    "atp_yelo": BASE / "atp_yelo_latest.csv",
    "wta_yelo": BASE / "wta_yelo_latest.csv",
}

HISTORY = BASE / "elo_history.csv"


def save_latest(name, df):
    df.to_csv(LATEST[name], index=False)


def load_latest(name):
    return pd.read_csv(LATEST[name])


def load_history():
    if HISTORY.exists():
        return pd.read_csv(HISTORY)

    return pd.DataFrame()


def append_history(name, df):
    df = df.copy()

    today = datetime.utcnow().strftime("%Y-%m-%d")

    tour = "ATP" if "atp" in name else "WTA"
    typ = "yelo" if "yelo" in name else "elo"

    rows = []

    for _, r in df.iterrows():

        player = r["Player"]

        if typ == "elo":

            rows.append({
                "date": today,
                "tour": tour,
                "type": "elo",
                "player": player,
                "elo": r.get("elo", 0),
                "surface": "hard",
                "surface_elo": r.get("hard_elo", 0),
                "yelo": 0
            })

            rows.append({
                "date": today,
                "tour": tour,
                "type": "elo",
                "player": player,
                "elo": r.get("elo", 0),
                "surface": "clay",
                "surface_elo": r.get("clay_elo", 0),
                "yelo": 0
            })

            rows.append({
                "date": today,
                "tour": tour,
                "type": "elo",
                "player": player,
                "elo": r.get("elo", 0),
                "surface": "grass",
                "surface_elo": r.get("grass_elo", 0),
                "yelo": 0
            })

        else:

            rows.append({
                "date": today,
                "tour": tour,
                "type": "yelo",
                "player": player,
                "elo": 0,
                "surface": "",
                "surface_elo": 0,
                "yelo": r.get("yelo", 0)
            })

    new_df = pd.DataFrame(rows)

    if HISTORY.exists():

        old = pd.read_csv(HISTORY)

        exists = (
            (old["date"] == today)
            & (old["tour"] == tour)
            & (old["type"] == typ)
        ).any()

        if exists:
            return

        new_df = pd.concat([old, new_df], ignore_index=True)

    new_df.to_csv(HISTORY, index=False)
