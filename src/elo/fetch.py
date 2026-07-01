import pandas as pd

URLS = {
    "atp_elo": "https://tennisabstract.com/reports/atp_elo_ratings.html",
    "wta_elo": "https://tennisabstract.com/reports/wta_elo_ratings.html",
    "atp_yelo": "https://tennisabstract.com/reports/atp_season_yelo_ratings.html",
    "wta_yelo": "https://tennisabstract.com/reports/wta_season_yelo_ratings.html",
}

def fetch_all():
    data = {}

    for name, url in URLS.items():
        tables = pd.read_html(url)
        data[name] = tables[0]

    return data
