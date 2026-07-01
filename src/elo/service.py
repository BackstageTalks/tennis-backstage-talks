from .store import load_latest


class EloService:

    def __init__(self):
        self.atp_elo = load_latest("atp_elo")
        self.wta_elo = load_latest("wta_elo")

        self.atp_yelo = load_latest("atp_yelo")
        self.wta_yelo = load_latest("wta_yelo")

    def _get_df(self, tour, typ):
        return getattr(self, f"{tour}_{typ}")

    def get_player_record(
        self,
        player_name,
        tour="atp",
        surface=None,
    ):
        elo_df = self._get_df(tour, "elo")
        yelo_df = self._get_df(tour, "yelo")

        elo_row = elo_df[
            elo_df["Player"] == player_name
        ]

        if elo_row.empty:
            return {
                "elo": 1500,
                "yelo": 1500,
                "combined": 1500,
            }

        elo = float(
            elo_row.iloc[0]["elo"]
        )

        # optional surface adjustment
        if surface:

            col = f"{surface}_elo"

            if col in elo_row.columns:

                value = elo_row.iloc[0][col]

                if value is not None:
                    elo = (
                        0.5 * elo +
                        0.5 * float(value)
                    )

        yelo = elo

        yelo_row = yelo_df[
            yelo_df["Player"] == player_name
        ]

        if (
            not yelo_row.empty
            and "yelo" in yelo_row.columns
        ):
            yelo = float(
                yelo_row.iloc[0]["yelo"]
            )

        combined = (
            0.7 * elo +
            0.3 * yelo
        )

        return {
            "elo": round(elo, 2),
            "yelo": round(yelo, 2),
            "combined": round(combined, 2),
        }

    def get_elo(
        self,
        player_name,
        tour="atp",
        surface=None,
    ):
        record = self.get_player_record(
            player_name=player_name,
            tour=tour,
            surface=surface,
        )

        return record["combined"]
