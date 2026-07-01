def clean_elo(df):
    df = df.copy()

    # fix names (odstráni hidden znaky)
    df["Player"] = (
        df["Player"]
        .astype(str)
        .str.replace("\xa0", " ", regex=False)
        .str.strip()
    )

    # premenovanie stĺpcov
    df = df.rename(columns={
        "Elo": "elo",
        "yElo": "yelo",
        "hElo": "hard_elo",
        "cElo": "clay_elo",
        "gElo": "grass_elo"
    })

    # doplniť missing values
    df = df.fillna(0)

    # necháme len potrebné stĺpce
    keep_cols = [
        "Player",
        "elo",
        "yelo",
        "hard_elo",
        "clay_elo",
        "grass_elo"
    ]

    keep_cols = [c for c in keep_cols if c in df.columns]

    return df[keep_cols]
