import pandas as pd


def add_trends(df):
    df = df.copy()

    df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values(
        ["player", "date"]
    )

    df["elo_change"] = (
        df.groupby(["player", "surface"])
        ["elo"]
        .diff()
    )

    df["yelo_change"] = (
        df.groupby(["player"])
        ["yelo"]
        .diff()
    )

    return df
