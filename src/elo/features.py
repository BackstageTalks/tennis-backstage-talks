import pandas as pd


def add_trends(df):
    """
    Add Elo and yElo trend columns.

    Requires:
    - date
    - player
    - elo
    - yelo
    """

    if df.empty:
        return df

    df = df.copy()

    df["date"] = pd.to_datetime(df["date"])

    df = df.sort_values(
        ["player", "date"]
    )

    if "elo" in df.columns:
        df["elo_change"] = (
            df.groupby("player")["elo"]
            .diff()
            .fillna(0)
        )

    if "yelo" in df.columns:
        df["yelo_change"] = (
            df.groupby("player")["yelo"]
            .diff()
            .fillna(0)
        )

    return df


def latest_player_trend(df, player):
    """
    Returns latest trend info for player.
    """

    if df.empty:
        return None

    player_df = df[df["player"] == player]

    if player_df.empty:
        return None

    player_df = player_df.sort_values("date")

    return player_df.iloc[-1].to_dict()
