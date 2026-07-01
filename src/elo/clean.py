import pandas as pd


def clean_elo(df):

    df = df.copy()

    df.columns = [str(c).strip() for c in df.columns]

    if "Player" in df.columns:
        df["Player"] = (
            df["Player"]
            .astype(str)
            .str.replace("\xa0", " ", regex=False)
            .str.strip()
        )

    return df
