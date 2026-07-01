import pandas as pd
import requests


URLS = {
    "atp_elo": "https://tennisabstract.com/reports/atp_elo_ratings.html",
    "wta_elo": "https://tennisabstract.com/reports/wta_elo_ratings.html",
    "atp_yelo": "https://tennisabstract.com/reports/atp_season_yelo_ratings.html",
    "wta_yelo": "https://tennisabstract.com/reports/wta_season_yelo_ratings.html",
}


HEADERS = {
    "User-Agent": "Mozilla/5.0"
}


def fetch_table(url):

    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    tables = pd.read_html(response.text)

    if not tables:
        raise RuntimeError(
            f"No table found: {url}"
        )

    return tables[0]


def fetch_all():

    data = {}

    for name, url in URLS.items():
        data[name] = fetch_table(url)

    return data
