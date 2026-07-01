import pandas as pd
from pathlib import Path
from datetime import datetime

BASE_DIR = Path("data/elo")
BASE_DIR.mkdir(parents=True, exist_ok=True)

LATEST_FILES = {
    "atp_elo": BASE_DIR / "atp_elo_latest.csv",
    "wta_elo": BASE_DIR / "wta_elo_latest.csv",
    "atp_yelo": BASE_DIR / "atp_yelo_latest.csv",
    "wta_yelo": BASE_DIR / "wta_yelo_latest.csv",
}

HISTORY_FILE = BASE_DIR / "elo_history.csv"


def save_latest(name, df):
    """
    Save newest snapshot.
    """
    df.to_csv(LATEST_FILES[name], index=False)


def load_latest(name):
    """
    Load latest snapshot.
    """
    path = LATEST_FILES[name]

    if not path.exists():
        return pd.DataFrame()

    return pd.read_csv(path)


def load_history():
    """
    Load historical Elo database.
    """
    if not HISTORY_FILE.exists():
        return pd.DataFrame()

    return pd.read_csv(HISTORY_FILE)


def append_history(name, df):
    """
    Store weekly historical snapshots.
    """

    today = datetime.utcnow().strftime("%Y-%m-%d")

    tour = "ATP" if name.startswith("atp") else "WTA"
    rating_type = "yelo" if "yelo" in name else "elo"

    snapshot_rows = []

    for _, row in df.iterrows():

        snapshot_rows.append({
            "snapshot_date": today,
            "tour": tour,
            "rating_type": rating_type,
            "player": row.get("Player", ""),

            "elo": row.get("elo", 0),
            "yelo": row.get("yelo", 0),

            "hard_elo": row.get("hard_elo", 0),
            "clay_elo": row.get("clay_elo", 0),
            "grass_elo": row.get("grass_elo", 0)
        })

    new_df = pd.DataFrame(snapshot_rows)

    if HISTORY_FILE.exists():

        history = pd.read_csv(HISTORY_FILE)

        already_exists = (
            (history["snapshot_date"] == today)
            & (history["tour"] == tour)
            & (history["rating_type"] == rating_type)
        ).any()

        if already_exists:
            return

        new_df = pd.concat(
            [history, new_df],
            ignore_index=True
        )

    new_df.to_csv(HISTORY_FILE, index=False)
