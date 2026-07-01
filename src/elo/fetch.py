import pandas as pd
from pathlib import Path


RAW_DIR = Path("data/elo/raw")

FILES = {
    "atp_elo": RAW_DIR / "atp_elo.html",
    "wta_elo": RAW_DIR / "wta_elo.html",
    "atp_yelo": RAW_DIR / "atp_yelo.html",
    "wta_yelo": RAW_DIR / "wta_yelo.html",
}


def fetch_all():

    data = {}

    for name, file_path in FILES.items():

        if not file_path.exists():
            raise FileNotFoundError(
                f"Missing file: {file_path}"
            )

        tables = pd.read_html(file_path)

        if not tables:
            raise RuntimeError(
                f"No tables found in: {file_path}"
            )

        data[name] = tables[0]

    return data
